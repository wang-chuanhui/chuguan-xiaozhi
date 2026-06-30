from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .WayDevice import getAllWayDevices
from .ScreenDevice import getScreenDevice


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up the light platform."""    
    wayDevices = getAllWayDevices()
    async_add_entities([*wayDevices, getScreenDevice()])

