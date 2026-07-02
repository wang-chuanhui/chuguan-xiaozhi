from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, ATTR_RGB_COLOR
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.util.color import value_to_brightness, brightness_to_value
import logging
import math
from .chuguan.const import DOMAIN
from homeassistant.core import callback
from .chuguan.RealDevice import realDevice
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)
BRIGHTNESS_SCALE = (1, 100)



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
        self._cancelable = None

    @property
    def is_on(self) -> bool:
        return self._is_on
    
    async def async_turn_on(self, **kwargs):
        await realDevice.setWayOn(self._way, True)
        self._is_on = await realDevice.getWayOn(self._way)
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        await realDevice.setWayOn(self._way, False)
        self._is_on = await realDevice.getWayOn(self._way)
        self.schedule_update_ha_state()

    async def update_way(self, now):
        self._is_on = await realDevice.getWayOn(self._way)
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        await super().async_added_to_hass()
        self._is_on = await realDevice.getWayOn(self._way)
        self.async_write_ha_state()
        self._cancelable = async_track_time_interval(self.hass, self.update_way, timedelta(seconds=1))

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()
        if self._cancelable:
            self._cancelable()
            self._cancelable = None

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
        self._brightness = 100

    @property
    def is_on(slef):
        return True

    @property
    def brightness(self) -> int:
        return value_to_brightness(BRIGHTNESS_SCALE, self._brightness)
    
    async def async_turn_on(self, **kwargs):
        """"""
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS]))
            await self.set_brightness(value_in_range)

    def turn_off(self):
        """"""

    async def set_brightness(self, value: int):
        await realDevice.setAllBrightness(self._isOn, value)
        self._brightness = await realDevice.getAllBrightness(self._isOn)
        self.schedule_update_ha_state()
        self.hass.bus.fire(WAY_BACKLIGHT_BRIGHTNESS_EVENT)

    def get_initial_entity_options(self) -> er.EntityOptionsType | None:
        return {"conversation":{"should_expose":False}}
    
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._brightness = await realDevice.getAllBrightness(self._isOn)
        self.schedule_update_ha_state()



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
        self._brightness = brightness
        self._listen_event = None
        self._rgb_color = (255, 215, 0)

    @property
    def is_on(self) -> bool:
        return True
    
    @property
    def brightness(self) -> int:
        return self._brightness.brightness
    
    @property
    def rgb_color(self) -> tuple[int, int, int]:
        return tuple(self._rgb_color)

    async def async_turn_on(self, **kwargs):
        """"""
        _LOGGER.warning(f"turn_on kwargs: {kwargs}")
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS]))
            await self._brightness.set_brightness(value_in_range)
        if ATTR_RGB_COLOR in kwargs:
            rgb_color = kwargs[ATTR_RGB_COLOR]
            await realDevice.setWayColor(self._way, self._isOn, rgb_color)
            self._rgb_color = await realDevice.getWayColor(self._way, self._isOn)
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
        self._rgb_color = await realDevice.getWayColor(self._way, self._isOn)
        self._listen_event = self.hass.bus.async_listen(WAY_BACKLIGHT_BRIGHTNESS_EVENT, self._on_way_backlight_brightness_event)
        self.schedule_update_ha_state()

    async def async_will_remove_from_hass(self):
        await super().async_will_remove_from_hass()
        if self._listen_event:
            self._listen_event()
            self._listen_event = None
    
    def get_initial_entity_options(self) -> er.EntityOptionsType | None:
        return {"conversation":{"should_expose":False}}
    
def getAllWayDevices():
    way1 = WayLight(1, realDevice.way1Device)
    way2 = WayLight(2, realDevice.way2Device)
    way3 = WayLight(3, realDevice.way3Device)
    waysOnBrightness = BacklightBrightness(True, realDevice.device)
    waysOffBrightness = BacklightBrightness(False, realDevice.device)
    backlight10 = WayBacklight(1, False, realDevice.way1Device, waysOffBrightness)
    backlight11 = WayBacklight(1, True, realDevice.way1Device, waysOnBrightness)
    backlight20 = WayBacklight(2, False, realDevice.way2Device, waysOffBrightness)
    backlight21 = WayBacklight(2, True, realDevice.way2Device, waysOnBrightness)
    backlight30 = WayBacklight(3, False, realDevice.way3Device, waysOffBrightness)
    backlight31 = WayBacklight(3, True, realDevice.way3Device, waysOnBrightness)

    wayDevices = [waysOnBrightness, waysOffBrightness, way1, way2, way3, backlight10, backlight11, backlight20, backlight21, backlight30, backlight31]
    return wayDevices