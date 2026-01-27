import asyncio
import psutil
import logging
from .model import SockResponse

_LOGGER = logging.getLogger(__name__)


def get_all_macs():
    """返回所有非回环网卡的 MAC 地址字典"""
    macs = {}
    for name, addrs in psutil.net_if_addrs().items():
        # 跳过回环接口
        if name == 'lo':
            continue
        for addr in addrs:
            if addr.family == psutil.AF_LINK:  # AF_LINK 表示 MAC
                macs[name] = addr.address.lower()
    return macs
def get_main_mac():
    """返回主网卡的 MAC 地址"""
    macs = get_all_macs()
    # 通常主网卡是 eth0 或 wlan0
    for name in ['wlan0', 'eth0', 'en0']:
        if name in macs:
            return macs[name]
    # 如果以上都没有，返回第一个找到的 MAC
    return next(iter(macs.values())) if macs else None


async def send_messages(message: str):
    """Upload entities"""
    reader, writer = await asyncio.open_unix_connection("/tmp/frpc_loader.sock")
    try:
        writer.write(message.encode())
        await writer.drain()   # 确保发送出去
        writer.write_eof()     # 相当于 shutdown(SHUT_WR)
        response = await reader.read(1024 * 1024)
        res = response.decode()
        _LOGGER.info(res)
        obj = SockResponse.model_validate_json(res)
        return obj
    finally:
        writer.close()
        await writer.wait_closed()