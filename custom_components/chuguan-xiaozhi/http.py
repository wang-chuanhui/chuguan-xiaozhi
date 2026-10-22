from homeassistant.components.api import APIConfigView
from homeassistant.helpers.http import HomeAssistantView, KEY_HASS
from aiohttp import web
from homeassistant.helpers.system_info import async_get_system_info

class CGAPIConfigView(APIConfigView):
    """Chuguan API Config View."""
    name = "api:cgconfig"
    url = "/api/cgconfig"
    requires_auth = False

class CGSystemInfoView(HomeAssistantView):
    """Chuguan System Info View."""
    name = "api:cgsysteminfo"
    url = "/api/cgsysteminfo"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Return the onboarding status."""

        hass = request.app[KEY_HASS]
        info = await async_get_system_info(hass)
        return self.json(info)

