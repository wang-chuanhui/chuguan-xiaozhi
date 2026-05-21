from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
import subprocess


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
        self._attr_color_mode = ColorMode.ONOFF
        self._is_on = False
        self._brightness = 100

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> int:
        return self._brightness / 100 * 255
    
    def turn_on(self, **kwargs):
        self._is_on = True
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            value = brightness / 255 * 100
            self._brightness = round(value)

    def turn_off(self, **kwargs):
        self._is_on = False
