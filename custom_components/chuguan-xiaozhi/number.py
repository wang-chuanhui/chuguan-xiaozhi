from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.number import NumberEntity, NumberDeviceClass


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the number platform."""
    volume = VolumeNumber()
    async_add_entities([volume])



class VolumeNumber(NumberEntity):
    """A number entity."""

    def __init__(self):
        """Initialize the volume number."""
        super().__init__()
        self._attr_unique_id = f"volume"
        self._attr_name = f"音量"
        self._attr_device_class = NumberDeviceClass.VOLUME
        self._attr_min_value = 0
        self._attr_max_value = 100
        self._attr_step = 1
        self._volume = 100

    @property
    def native_value(self):
        return self._volume

    def set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._volume = value
