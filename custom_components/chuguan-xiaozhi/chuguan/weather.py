from homeassistant.core import HomeAssistant, State
import logging
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, RegistryEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import asyncio

_LOGGER = logging.getLogger(__name__)

async def met_weather_state_changed(hass: HomeAssistant, entity_id: str, new_state: State):
    """Handle state changes for weather entities"""
    if entity_id.startswith("weather.") == False:
        return
    if new_state is None:
        return
    if new_state.state != 'unavailable':
        return
    _LOGGER.info(f"met_weather_state_changed {entity_id} {new_state.state}")
    entity_registry = async_get_entity_registry(hass)
    entity = entity_registry.async_get(entity_id)
    if entity is None:
        return
    if entity.platform != 'met':
        return
    await asyncio.sleep(30)
    await check_weather_state(hass, entity)

async def check_all_met_weather(hass: HomeAssistant):
    """Check all met weather entities"""
    entity_registry = async_get_entity_registry(hass)
    entities = entity_registry.entities.values()
    for entity in entities:
        if entity.platform != 'met':
            continue
        await check_weather_state(hass, entity)

async def check_weather_state(hass: HomeAssistant, entity: RegistryEntry):
    """Check weather state"""
    current_state = hass.states.get(entity.entity_id)
    if current_state is None:
        return
    if current_state.state == 'unavailable':
        _LOGGER.warning(f"check_weather_state met {entity.entity_id} state is {current_state.state}")
        await update_met_weather(hass, entity)

async def update_met_weather(hass: HomeAssistant, entity: RegistryEntry):
    """Update all met weather entities"""
    config_entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    if config_entry is None:
        _LOGGER.warning(f"met config_entry not found")
        return
    if hasattr(config_entry, "runtime_data") == False:
        _LOGGER.warning(f"met config_entry runtime_data not found")
        return
    coordinator: DataUpdateCoordinator = config_entry.runtime_data
    if coordinator is None:
        _LOGGER.warning(f"met config_entry coordinator is None")
        return
    await coordinator.async_refresh()
