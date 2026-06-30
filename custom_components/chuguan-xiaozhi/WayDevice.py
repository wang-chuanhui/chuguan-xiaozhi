from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, ATTR_RGB_COLOR
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.util.color import value_to_brightness, brightness_to_value
import logging
import math
from .chuguan.const import DOMAIN
from homeassistant.core import callback
from .chuguan.utils import execute_shell

_LOGGER = logging.getLogger(__name__)
BRIGHTNESS_SCALE = (1, 100)


waysDevice = DeviceInfo(manufacturer="初冠", model="小智", name="所有按键", identifiers={(DOMAIN, "device_way_all")}, model_id="cgxz")
way1Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键1", identifiers={(DOMAIN, "device_way_1")}, model_id="cgxz")
way2Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键2", identifiers={(DOMAIN, "device_way_2")}, model_id="cgxz")
way3Device = DeviceInfo(manufacturer="初冠", model="小智", name="按键3", identifiers={(DOMAIN, "device_way_3")}, model_id="cgxz")

class RealDevice:

    def __init__(self):
        """"""

    def getWayOn(self, way: int) -> bool:
        return execute_shell(['test_way.sh', '-g', str(way), 'on']) == '1'
    
    def setWayOn(self, way: int, value: bool):
        execute_shell(['test_way.sh', '-s', str(way), 'on', '1' if value else '0'])

    def getAllBrightness(self, on: bool) -> int:
        status = 'on' if on else 'off'
        value = execute_shell(['test_way.sh', '-g', 'all', f'{status}_brightness'])
        if value:
            return int(value)
        return 100
    
    def setAllBrightness(self, on: bool, value: int):
        status = 'on' if on else 'off'
        execute_shell(['test_way.sh', '-s', 'all', f'{status}_brightness', str(value)])

    def getWayColor(self, way: int, on: bool) -> tuple[int, int, int]:
        status = 'on' if on else 'off'
        value = execute_shell(['test_way.sh', '-g', str(way), f'{status}_color'])
        if value:
            items = value.split(',')
            items = list(map(int, items))
            return items
        return (255, 215, 0)
    
    def setWayColor(slef, way: int, on: bool, value: tuple[int, int, int]):
        status = 'on' if on else 'off'
        value = ','.join(map(str, value))
        execute_shell(['test_way.sh', '-s', str(way), f'{status}_color', value])

realDevice = RealDevice()

class WayLight(LightEntity):
    """A light entity."""

    def __init__(self, way: int, device_info: DeviceInfo = None):
        """Initialize the light."""
        self._way = way
        self._attr_device_info = device_info
        self._attr_unique_id = f"way_{way}"
        self._attr_name = f"灯{way}"
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF
        self._is_on = realDevice.getWayOn(way)
        self._cancelable = None

    @property
    def is_on(self) -> bool:
        return self._is_on
    
    def turn_on(self, **kwargs):
        realDevice.setWayOn(self._way, True)
        self._is_on = realDevice.getWayOn(self._way)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        realDevice.setWayOn(self._way, False)
        self._is_on = realDevice.getWayOn(self._way)
        self.schedule_update_ha_state()

WAY_BACKLIGHT_BRIGHTNESS_EVENT = "chuguan-xiaozhi.way_backlight_brightness"

class BacklightBrightness(LightEntity):

    def __init__(self, isOn: bool, deviceInfo: DeviceInfo):
        self._isOn = isOn
        self._attr_device_info = deviceInfo
        self._attr_unique_id = f"ways_backlight_{isOn}"
        status = "开启" if isOn else "关闭"
        self._attr_name = f"按键{status}时背光亮度"
        self._attr_supported_color_modes = [ColorMode.BRIGHTNESS]
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._brightness = realDevice.getAllBrightness(isOn)

    @property
    def is_on(slef):
        return True

    @property
    def brightness(self) -> int:
        return value_to_brightness(BRIGHTNESS_SCALE, self._brightness)
    
    def turn_on(self, **kwargs):
        """"""
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS]))
            self.set_brightness(value_in_range)

    def turn_off(self):
        """"""

    def set_brightness(self, value: int):
        realDevice.setAllBrightness(self._isOn, value)
        self._brightness = realDevice.getAllBrightness(self._isOn)
        self.schedule_update_ha_state()
        self.hass.bus.fire(WAY_BACKLIGHT_BRIGHTNESS_EVENT)

    def get_initial_entity_options(self) -> er.EntityOptionsType | None:
        return {"conversation":{"should_expose":False}}



class WayBacklight(LightEntity):
    """A way backlight entity."""

    def __init__(self, way: int, isOn: bool, device_info: DeviceInfo, brightness: BacklightBrightness):
        self._way = way
        self._isOn = isOn
        self._attr_device_info = device_info
        self._attr_unique_id = f"way_{way}_backlight_{isOn}"
        status = "开启" if isOn else "关闭"
        self._attr_name = f"灯{way}{status}时背光颜色"
        self._attr_supported_color_modes = [ColorMode.RGB]
        self._attr_color_mode = ColorMode.RGB
        self._rgb_color = realDevice.getWayColor(way, isOn)
        self._brightness = brightness
        self._listen_event = None
        self.get_initial_entity_options

    @property
    def is_on(self) -> bool:
        return True
    
    @property
    def brightness(self) -> int:
        return self._brightness.brightness
    
    @property
    def rgb_color(self) -> tuple[int, int, int]:
        return tuple(self._rgb_color)

    def turn_on(self, **kwargs):
        """"""
        _LOGGER.warning(f"turn_on kwargs: {kwargs}")
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS]))
            self._brightness.set_brightness(value_in_range)
        if ATTR_RGB_COLOR in kwargs:
            rgb_color = kwargs[ATTR_RGB_COLOR]
            realDevice.setWayColor(self._way, self._isOn, rgb_color)
            self._rgb_color = realDevice.getWayColor(self._way, self._isOn)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """"""
        self.schedule_update_ha_state()

    @callback
    async def _on_way_backlight_brightness_event(self, ev):
        """"""
        self.schedule_update_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._listen_event = self.hass.bus.async_listen(WAY_BACKLIGHT_BRIGHTNESS_EVENT, self._on_way_backlight_brightness_event)

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()
        if self._listen_event:
            self._listen_event()
            self._listen_event = None
    
    def get_initial_entity_options(self) -> er.EntityOptionsType | None:
        return {"conversation":{"should_expose":False}}
    
def getAllWayDevices():
    way1 = WayLight(1, way1Device)
    way2 = WayLight(2, way2Device)
    way3 = WayLight(3, way3Device)
    waysOnBrightness = BacklightBrightness(True, waysDevice)
    waysOffBrightness = BacklightBrightness(False, waysDevice)
    backlight10 = WayBacklight(1, False, way1Device, waysOffBrightness)
    backlight11 = WayBacklight(1, True, way1Device, waysOnBrightness)
    backlight20 = WayBacklight(2, False, way2Device, waysOffBrightness)
    backlight21 = WayBacklight(2, True, way2Device, waysOnBrightness)
    backlight30 = WayBacklight(3, False, way3Device, waysOffBrightness)
    backlight31 = WayBacklight(3, True, way3Device, waysOnBrightness)

    wayDevices = [way1, way2, way3, backlight10, backlight11, backlight20, backlight21, backlight30, backlight31, waysOnBrightness, waysOffBrightness]
    return wayDevices