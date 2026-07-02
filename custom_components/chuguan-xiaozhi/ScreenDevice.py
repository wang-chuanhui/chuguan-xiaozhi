import math
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from .chuguan.screen import get_brightness, set_brightness, no_sudo_get_brightness, is_screen_on, set_screen_on
import logging
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from .chuguan.RealDevice import realDevice

from homeassistant.util.color import value_to_brightness, brightness_to_value

BRIGHTNESS_SCALE = (1, 100)


class ScreenLight(LightEntity):
    """A screen light entity."""
    def __init__(self):
        """Initialize the screen light."""
        super().__init__()
        self._attr_device_info
        self._attr_unique_id = f"screen"
        self._attr_name = f"屏幕"
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._is_on = False
        self._brightness = 100
        self.extra_state_attributes = {"cannot_turn_off": True, "cannot_turn_off_reason": "请使用按键关闭屏幕"}
        self._attr_device_info = realDevice.device
        self.entity_registry_visible_default = False

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> int:
        return value_to_brightness(BRIGHTNESS_SCALE, self._brightness)
    
    def turn_on(self, **kwargs):
        set_screen_on(True)
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = math.ceil(brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS]))
            set_brightness(value_in_range)
            self._brightness = value_in_range

    def turn_off(self, **kwargs):
        set_screen_on(False)

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        await super().async_added_to_hass()
        self._brightness = get_brightness()
        self._is_on = is_screen_on()
        self.async_write_ha_state()
        self._cancelable = async_track_time_interval(self.hass, self.update_brightness, timedelta(seconds=1))

    async def async_will_remove_from_hass(self) -> None:
        """Entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        if self._cancelable:
            self._cancelable()
            self._cancelable = None

    def update_brightness(self, now):
        value = no_sudo_get_brightness()
        is_on = is_screen_on()
        change = False
        if is_on != self._is_on:
            self._is_on = is_on
            change = True
        if value != self._brightness:
            self._brightness = value
            change = True
        if change:
            self.hass.loop.call_soon_threadsafe(self._update_brightness)

    def _update_brightness(self):
        self.async_write_ha_state()

    def _reset_is_on(self, now):
        self._is_on = is_screen_on()
        self.schedule_update_ha_state()

def getScreenDevice():
    screen = ScreenLight()
    return screen