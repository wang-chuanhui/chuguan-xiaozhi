from .utils import async_execute_shell
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

via_device=(DOMAIN, "ha_screen_device")

class RealDevice:

    device = DeviceInfo(manufacturer="初冠", model="小智", name="HA屏", identifiers={via_device}, model_id="cgxz")
    
    way1Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键1", identifiers={(DOMAIN, "device_way_1")}, model_id="cgxz", via_device=via_device)
    way2Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键2", identifiers={(DOMAIN, "device_way_2")}, model_id="cgxz", via_device=via_device)
    way3Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键3", identifiers={(DOMAIN, "device_way_3")}, model_id="cgxz", via_device=via_device)
    presenceDevice = DeviceInfo(manufacturer="初冠", model="小智", name="人体存在", identifiers={(DOMAIN, "device_human_presence")}, model_id="cgxz", via_device=via_device)
    motionDevice = DeviceInfo(manufacturer="初冠", model="小智", name="运动感应", identifiers={(DOMAIN, "device_human_motion")}, model_id="cgxz", via_device=via_device)

    def __init__(self):
        """"""

    async def getWayOn(self, way: int) -> bool:
        return await async_execute_shell(['test_way.sh', '-g', str(way), 'on']) == '1'
    
    async def setWayOn(self, way: int, value: bool):
        await async_execute_shell(['test_way.sh', '-s', str(way), 'on', '1' if value else '0'])

    async def getAllBrightness(self, on: bool) -> int:
        status = 'on' if on else 'off'
        value = await async_execute_shell(['test_way.sh', '-g', 'all', f'{status}_brightness'])
        if value:
            return int(value)
        return 100
    
    async def setAllBrightness(self, on: bool, value: int):
        status = 'on' if on else 'off'
        await async_execute_shell(['test_way.sh', '-s', 'all', f'{status}_brightness', str(value)])

    async def getWayColor(self, way: int, on: bool) -> tuple[int, int, int]:
        status = 'on' if on else 'off'
        value = await async_execute_shell(['test_way.sh', '-g', str(way), f'{status}_color'])
        if value:
            items = value.split(',')
            items = list(map(int, items))
            return items
        return (255, 215, 0)
    
    async def setWayColor(slef, way: int, on: bool, value: tuple[int, int, int]):
        status = 'on' if on else 'off'
        value = ','.join(map(str, value))
        await async_execute_shell(['test_way.sh', '-s', str(way), f'{status}_color', value])

    async def getKV(self, key: str) -> str:
        return await async_execute_shell(['test_way.sh', '-g', 'kv', key])
    
    async def setKV(self, key: str, value: str):
        await async_execute_shell(['test_way.sh', '-s', 'kv', key, value])

realDevice = RealDevice()