from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.config_entries import ConfigEntries
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import NoEventData
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.device_registry import EventDeviceRegistryUpdatedData, async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry, EVENT_ENTITY_REGISTRY_UPDATED, EventEntityRegistryUpdatedData
from homeassistant.helpers.area_registry import async_get as async_get_area_registry
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_call_later
import logging
from homeassistant.const import Platform
from datetime import datetime
from .utils import get_main_mac, send_messages
import json

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BUTTON, Platform.CLIMATE, Platform.CAMERA, Platform.COVER, Platform.FAN, Platform.HUMIDIFIER, Platform.LAWN_MOWER, Platform.LIGHT, Platform.LOCK, Platform.MEDIA_PLAYER, Platform.SCENE, Platform.SIREN, Platform.SWITCH, Platform.VACUUM, Platform.VALVE, Platform.WATER_HEATER]
_LOGGER = logging.getLogger(__name__)

DOMAIN = 'chuguan-xiaozhi'


STORAGE_VERSION = 1

class Hub:
    """Chuguan Xiaozhi Hub"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntries):
        self.hass = hass
        self.entry = entry
        self.later_update_cancel = None
        self.mac = get_main_mac()
        store = Store(hass, STORAGE_VERSION, f"chuguan-xiaozhi.{self.mac}")
        hass.data[DOMAIN] = {
            self.mac: store,
        }
        _LOGGER.info("MAC addresse: %s", self.mac)
        if self.hass.state == "running":
            self.update_entities()
        pass

    def __del__(self):
        """Stop the hub when the instance is deleted"""
        _LOGGER.info("Stop the hub when the instance is deleted")
        self.stop()

    def stop(self):
        """Stop the hub"""
        _LOGGER.info("Stop the hub")
        self.hass.bus._async_remove_listener(EVENT_HOMEASSISTANT_STARTED, self._on_homeassistant_started)
        self.hass.bus._async_remove_listener(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._on_device_registry_updated)
        self.hass.bus._async_remove_listener(EVENT_ENTITY_REGISTRY_UPDATED, self._on_entity_registry_updated)

    def setup(self):
        self.hass.bus.async_listen(EVENT_HOMEASSISTANT_STARTED, self._on_homeassistant_started)
        self.hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._on_device_registry_updated)
        self.hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, self._on_entity_registry_updated)

    @callback
    def _on_homeassistant_started(self, ev: Event[NoEventData]):
        """Handle home assistant started event."""
        _LOGGER.info("Home assistant started: %s", ev)
        self.update_entities()

    @callback
    def _on_device_registry_updated(self, ev: Event[EventDeviceRegistryUpdatedData]):
        """Handle device registry updated event."""
        _LOGGER.info("Device registry updated: %s", ev)
        self.update_entities()

    @callback
    def _on_entity_registry_updated(self, ev: Event[EventEntityRegistryUpdatedData]):
        """Handle entity registry updated event."""
        _LOGGER.info("Entity registry updated: %s", ev)
        self.update_entities()

    def update_entities(self):
        """Update entities"""
        if self.later_update_cancel is not None:
            self.later_update_cancel()
            self.later_update_cancel = None
        self.later_update_cancel = async_call_later(self.hass, 1, self._update_entities)
        # self.hass.async_create_task(self._update_entities())

    @callback
    async def _update_entities(self, now: datetime):
        """Get all data from the hub"""
        device_registry = async_get_device_registry(self.hass)

        area_registry = async_get_area_registry(self.hass)

        # _LOGGER.info("All devices: %s", devices)
        entity_registry = async_get_entity_registry(self.hass)
        entities = list(entity_registry.entities.values())
        entities.sort(key=lambda x: (x.entity_id))
        update_entities: list[str] = []
        for entity in entities:
            if entity.disabled or entity.hidden:
                continue
            if entity.entity_category is not None and entity.entity_category == 'diagnostic':
                continue
            if entity.domain in PLATFORMS:
                name = entity.name if entity.name is not None else entity.original_name
                if name is None:
                    name = entity.entity_id.split('.')[1]
                area = entity.area_id
                if area is None and entity.device_id is not None:
                    area = device_registry.devices[entity.device_id].area_id
                if area is not None:
                    area = area_registry.areas[area].name
                if area is None:
                    area = ""
                update_entities.append(f"{area},{name},{entity.entity_id}")
                # _LOGGER.info(f"Entity: {area}, name: {name}, id: {entity.entity_id}, {entity.disabled}, {entity.hidden}, {entity}")
        stored_data = await self.hass.data[DOMAIN][self.mac].async_load()
        if stored_data is not None and stored_data == update_entities:
            _LOGGER.info("No update entities")
            return
        await self.upload_entities(update_entities)
        await self.hass.data[DOMAIN][self.mac].async_save(update_entities)
        pass

    async def upload_entities(self, entities: list[str]):
        """Upload entities"""
        _LOGGER.info(f"Upload entities: {self.mac} {entities}")
        data = {
            "devices": ";".join(entities)
        }
        message = json.dumps(data, ensure_ascii=False)
        res = await send_messages(message)
        if res is None:
            return False
        return res.success
    
    def stop(self):
        """Stop the hub"""
        pass



