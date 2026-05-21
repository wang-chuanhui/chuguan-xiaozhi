from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from .chuguan.screen import get_brightness, set_brightness, no_sudo_get_brightness, is_screen_on, set_screen_on
import logging
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the light platform."""
    way2 = WayLight(2)
    way3 = WayLight(3)
    screen = ScreenLight()
    async_add_entities([way2, way3, screen])


class WayLight(LightEntity):
    """A light entity."""

    def __init__(self, way: int):
        """Initialize the light."""
        self._way = way
        self._attr_unique_id = f"way_{way}"
        self._attr_name = f"灯{way}"
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF
        self._is_on = False
        self._cancelable = None

    @property
    def is_on(self) -> bool:
        return self._is_on
    
    def turn_on(self, **kwargs):
        self._is_on = True

    def turn_off(self, **kwargs):
        self._is_on = False


class ScreenLight(LightEntity):
    """A screen light entity."""
    def __init__(self):
        """Initialize the screen light."""
        super().__init__()
        self._attr_unique_id = f"screen"
        self._attr_name = f"屏幕"
        self._attr_supported_color_modes = {ColorMode.ONOFF, ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._is_on = False
        self._brightness = 100

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> int:
        return self._brightness / 100 * 255
    
    def turn_on(self, **kwargs):
        set_screen_on(True)
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            value = brightness / 255 * 100
            set_brightness(value)
            self._brightness = round(value)

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
