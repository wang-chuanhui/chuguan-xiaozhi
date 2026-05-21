from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the binary sensor platform."""
    binary_sensor = MotionBinarySensor()
    async_add_entities([binary_sensor])

class MotionBinarySensor(BinarySensorEntity):
    """A binary sensor entity."""
    def __init__(self):
        """Initialize the motion binary sensor."""
        super().__init__()
        self._attr_unique_id = f"human_motion"
        self._attr_name = f"人体存在"
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on
