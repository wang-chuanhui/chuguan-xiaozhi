"""Home Assistant ttyd transparent proxy."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
from aiohttp import WSMsgType, web

from homeassistant.components.http import HomeAssistantView
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = "ttyd_proxy"
_LOGGER = logging.getLogger(__name__)

# ttyd 地址
TTYD_HOST = "192.168.0.173"
TTYD_PORT = 7681

# 浏览器访问的前缀，不要在开头或结尾添加斜杠
BASE_PATH = "api/ttyd_proxy"

stop_event = asyncio.Event()


class TTYDProxyView(HomeAssistantView):
    """Transparent proxy for ttyd."""

    url = "/api/ttyd_proxy/{path:.*}"
    name = "api:ttyd_proxy"
    requires_auth = True

    async def get(
        self, request: web.Request, path: str = ""
    ) -> web.StreamResponse:
        """Proxy HTTP GET and WebSocket."""
        return await self._proxy(request, path)

    async def head(
        self, request: web.Request, path: str = ""
    ) -> web.StreamResponse:
        """Proxy HTTP HEAD."""
        return await self._proxy(request, path)

    async def post(
        self, request: web.Request, path: str = ""
    ) -> web.StreamResponse:
        """Proxy HTTP POST."""
        return await self._proxy(request, path)

    async def put(
        self, request: web.Request, path: str = ""
    ) -> web.StreamResponse:
        """Proxy HTTP PUT."""
        return await self._proxy(request, path)

    async def patch(
        self, request: web.Request, path: str = ""
    ) -> web.StreamResponse:
        """Proxy HTTP PATCH."""
        return await self._proxy(request, path)

    async def delete(
        self, request: web.Request, path: str = ""
    ) -> web.StreamResponse:
        """Proxy HTTP DELETE."""
        return await self._proxy(request, path)

    async def _proxy(
        self, request: web.Request, path: str
    ) -> web.StreamResponse:
        """Dispatch the request to HTTP or WebSocket proxy."""
        # Home Assistant authenticates this view because requires_auth=True.
        # If administrator-only access is required, validate the authenticated
        # user here using the Home Assistant version's supported API.

        ws = web.WebSocketResponse()
        if ws.can_prepare(request).ok:
            return await self._proxy_websocket(request, path)

        return await self._proxy_http(request, path)

    async def _proxy_http(
        self, request: web.Request, path: str
    ) -> web.StreamResponse:
        """Proxy an ordinary HTTP request to ttyd."""
        target_url = self._build_upstream_url(path, request.query_string)

        # Avoid forwarding hop-by-hop headers. Let aiohttp set Host and
        # connection-specific headers for the upstream connection.
        skip_headers = {
            "host",
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailer",
            "trailers",
            "transfer-encoding",
            "upgrade",
        }
        headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() not in skip_headers
        }

        try:
            body = await request.read() if request.can_read_body else None
            async with aiohttp.ClientSession(auto_decompress=False) as session:
                async with session.request(
                    request.method,
                    target_url,
                    headers=headers,
                    data=body,
                    allow_redirects=False,
                ) as response:
                    response_body = await response.read()
                    response_headers = {
                        name: value
                        for name, value in response.headers.items()
                        if name.lower()
                        not in {
                            "connection",
                            "keep-alive",
                            "proxy-authenticate",
                            "proxy-authorization",
                            "te",
                            "trailer",
                            "trailers",
                            "transfer-encoding",
                            "upgrade",
                        }
                    }

                    return web.Response(
                        status=response.status,
                        headers=response_headers,
                        body=response_body,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.exception(
                "ttyd HTTP proxy failed: %s %s",
                request.method,
                target_url,
            )
            return web.Response(status=502, text=f"Bad Gateway: {err}")

    async def _proxy_websocket(
        self, request: web.Request, path: str
    ) -> web.WebSocketResponse:
        """Proxy a WebSocket connection transparently."""
        hass: HomeAssistant = request.app["hass"]
        session = async_get_clientsession(hass)

        browser_ws = web.WebSocketResponse(
            protocols=("tty",),
            autoping=True,
            heartbeat=None,
            max_msg_size=0,
        )
        await browser_ws.prepare(request)

        upstream_url = self._build_upstream_ws_url(path, request.query_string)
        headers = {}
        origin = request.headers.get("Origin")
        if origin:
            headers["Origin"] = origin

        _LOGGER.info(
            "ttyd WebSocket proxy: %s -> %s",
            request.path_qs,
            upstream_url,
        )

        ttyd_ws = None
        tasks: list[asyncio.Task] = []
        shutdown_task = asyncio.create_task(
            stop_event.wait(), name="ttyd_shutdown_task"
        )

        try:
            ttyd_ws = await session.ws_connect(
                upstream_url,
                headers=headers,
                protocols=("tty",),
                heartbeat=None,
                autoping=True,
                autoclose=False,
                max_msg_size=0,
            )

            async def browser_to_ttyd() -> None:
                """Forward browser messages to ttyd."""
                try:
                    async for message in browser_ws:
                        if message.type == WSMsgType.TEXT:
                            await ttyd_ws.send_str(message.data)
                        elif message.type == WSMsgType.BINARY:
                            await ttyd_ws.send_bytes(message.data)
                        elif message.type == WSMsgType.ERROR:
                            _LOGGER.warning(
                                "Browser WebSocket error: %s",
                                browser_ws.exception(),
                            )
                            break
                        elif message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED):
                            break
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.exception("Browser -> ttyd proxy failed")
                finally:
                    if not ttyd_ws.closed:
                        await ttyd_ws.close()

            async def ttyd_to_browser() -> None:
                """Forward ttyd messages to the browser."""
                try:
                    async for message in ttyd_ws:
                        if message.type == WSMsgType.TEXT:
                            await browser_ws.send_str(message.data)
                        elif message.type == WSMsgType.BINARY:
                            await browser_ws.send_bytes(message.data)
                        elif message.type == WSMsgType.ERROR:
                            _LOGGER.warning(
                                "ttyd WebSocket error: %s",
                                ttyd_ws.exception(),
                            )
                            break
                        elif message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED):
                            break
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.exception("ttyd -> Browser proxy failed")
                finally:
                    if not browser_ws.closed:
                        await browser_ws.close()

            tasks = [
                asyncio.create_task(
                    browser_to_ttyd(), name="ttyd_browser_to_ttyd"
                ),
                asyncio.create_task(
                    ttyd_to_browser(), name="ttyd_ttyd_to_browser"
                ),
            ]

            done, _ = await asyncio.wait(
                [*tasks, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                if task is not shutdown_task:
                    # Retrieve task exceptions to avoid unhandled-task warnings.
                    try:
                        task.result()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        _LOGGER.exception("ttyd WebSocket relay task failed")

        except asyncio.CancelledError:
            _LOGGER.info("ttyd WebSocket proxy cancelled")
            raise
        except Exception:
            _LOGGER.exception("Failed to connect to ttyd WebSocket: %s", upstream_url)
            if not browser_ws.closed:
                await browser_ws.close(
                    code=1011,
                    message=b"Unable to connect to ttyd",
                )
        finally:
            for task in [*tasks, shutdown_task]:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, shutdown_task, return_exceptions=True)

            if ttyd_ws is not None and not ttyd_ws.closed:
                await ttyd_ws.close()
            if not browser_ws.closed:
                await browser_ws.close()

            _LOGGER.info("ttyd WebSocket proxy disconnected")

        return browser_ws

    @staticmethod
    def _build_upstream_url(path: str, query_string: str) -> str:
        """Build ttyd HTTP URL."""
        path = path.lstrip("/")
        url = f"http://{TTYD_HOST}:{TTYD_PORT}/{BASE_PATH}/"
        if path:
            url += path
        if query_string:
            url += f"?{query_string}"
        return url

    @staticmethod
    def _build_upstream_ws_url(path: str, query_string: str) -> str:
        """Build ttyd WebSocket URL."""
        path = path.lstrip("/")
        url = f"ws://{TTYD_HOST}:{TTYD_PORT}/{BASE_PATH}/"
        if path:
            url += path
        if query_string:
            url += f"?{query_string}"
        return url


async def handle_shutdown(event) -> None:
    """Stop active WebSocket proxies when Home Assistant shuts down."""
    _LOGGER.warning("HA shutdown detected, closing ttyd proxy")
    stop_event.set()


async def async_setup_ttyd(hass: HomeAssistant) -> bool:
    """Set up ttyd proxy."""
    # Reset the event in case the integration is set up again in this process.
    stop_event.clear()

    hass.http.register_view(TTYDProxyView)
    _LOGGER.info("ttyd proxy registered at /%s/", BASE_PATH)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, handle_shutdown)
    return True
