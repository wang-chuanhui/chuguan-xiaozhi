"""The chuguan_home integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry, ConfigEntryAuthFailed
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import logging
from .chuguan.hub import Hub

_LOGGER = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.LIGHT, Platform.COVER, Platform.BUTTON, Platform.CLIMATE, Platform.VALVE]
PLATFORMS = []

type HubConfigEntry = ConfigEntry[Hub]

# TODO Update entry annotation
async def async_setup_entry(hass: HomeAssistant, entry: HubConfigEntry) -> bool:
    """Set up chuguan_home from a config entry."""

    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # entry.runtime_data = MyAPI(...)

    # TODO 4. Create an instance of your platform class
    # TODO 5. Add the instance to hass.data
    _LOGGER.info("async_setup_entry with entry %s %s", entry, entry.data)

    hub = Hub(hass, entry)
    try:
        entry.runtime_data = hub
        await hub.setup()
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True
    except Exception as e:
        hub.stop()
        _LOGGER.error("start failed %s", e)
        raise ConfigEntryAuthFailed from e


# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: HubConfigEntry) -> bool:
    """Unload a config entry."""
    hub = entry.runtime_data
    if hub is not None:
        hub.stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
