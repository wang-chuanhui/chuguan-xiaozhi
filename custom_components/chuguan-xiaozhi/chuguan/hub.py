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
from .utils import send_messages
import json
from datetime import timedelta
from .store import MyStore
from .const import ACCESS_TOKEN_EXPIRATION_DAYS, ACCESS_TOKEN_UPDATE_DAYS
from homeassistant.helpers.event import async_track_time_interval

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BUTTON, Platform.CLIMATE, Platform.CAMERA, Platform.COVER, Platform.FAN, Platform.HUMIDIFIER, Platform.LAWN_MOWER, Platform.LIGHT, Platform.LOCK, Platform.MEDIA_PLAYER, Platform.SCENE, Platform.SIREN, Platform.SWITCH, Platform.VACUUM, Platform.VALVE, Platform.WATER_HEATER]
_LOGGER = logging.getLogger(__name__)

class Hub:
    """Chuguan Xiaozhi Hub"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntries | None):
        self.hass = hass
        self.entry = entry
        self.later_update_cancel = None
        self.interval_update_cancel = None
        self.store = MyStore(hass)
        if self.hass.state == "running":
            self.update_entities()


    def __del__(self):
        """Stop the hub when the instance is deleted"""
        _LOGGER.info("Stop the hub when the instance is deleted")
        self.stop()

    def remove_interval_update(self):
        """Remove the interval update cancel"""
        if self.interval_update_cancel is not None:
            _LOGGER.info("Remove the interval update cancel")
            self.interval_update_cancel()
            self.interval_update_cancel = None

    def stop(self):
        """Stop the hub"""
        _LOGGER.info("Stop the hub")
        self.hass.bus._async_remove_listener(EVENT_HOMEASSISTANT_STARTED, self._on_homeassistant_started)
        self.hass.bus._async_remove_listener(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._on_device_registry_updated)
        self.hass.bus._async_remove_listener(EVENT_ENTITY_REGISTRY_UPDATED, self._on_entity_registry_updated)
        self.remove_interval_update()

    async def setup(self):
        self.hass.bus.async_listen(EVENT_HOMEASSISTANT_STARTED, self._on_homeassistant_started)
        self.hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._on_device_registry_updated)
        self.hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, self._on_entity_registry_updated)
        self.setup_later_update()

    def setup_later_update(self):
        _LOGGER.info("Setup later update")
        self.remove_interval_update()
        cancelable = async_track_time_interval(self.hass, self.interval_update_entities, timedelta(days=1))
        self.interval_update_cancel = cancelable

    @callback
    async def _on_homeassistant_started(self, ev: Event[NoEventData]):
        """Handle home assistant started event."""
        _LOGGER.info("Home assistant started: %s", ev)
        self.update_entities()
        # self.setup_later_update()

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

    def interval_update_entities(self, now: datetime):
        """定时更新实体"""
        self.hass.create_task(self.do_update_entities())

    def update_entities(self):
        """Update entities"""
        if self.later_update_cancel is not None:
            self.later_update_cancel()
            self.later_update_cancel = None
        self.later_update_cancel = async_call_later(self.hass, 1, self._update_entities)

    @callback
    async def _update_entities(self, now: datetime = None):
        """Get all data from the hub"""
        await self.do_update_entities()

    async def do_update_entities(self):
        """Get all data from the hub"""
        update_entities = self.get_all_entities()
        access_token = await self.setup_refresh_token()
        stored_data = await self.store.async_get_devices()
        api_key = await self.store.async_get_api_key()
        if stored_data == update_entities and api_key == access_token:
            _LOGGER.info("No update entities")
            return
        await self.upload_entities(update_entities, access_token)
        await self.store.async_set_devices(update_entities)
        await self.store.async_set_api_key(access_token)

    async def upload_entities(self, entities: list[str], api_key: str):
        """Upload entities"""
        _LOGGER.info(f"Upload entities: {entities}")
        data = {
            "devices": ";".join(entities),
            "apiKey": api_key
        }
        message = json.dumps(data, ensure_ascii=False)
        res = await send_messages(message)
        if res is None:
            return False
        return res.success
    
    def get_all_entities(self):
        device_registry = async_get_device_registry(self.hass)
        area_registry = async_get_area_registry(self.hass)
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
        return update_entities

    async def setup_refresh_token(self, now: datetime = None):
        """Setup API key"""
        users = await self.hass.auth.async_get_users()
        filtered_users = [user for user in users if user.is_owner == True]
        if len(filtered_users) == 0:
            return None
        user = filtered_users[0]
        ole_refresh_token, old_access_token = await self.check_refresh_token(user.id)
        if ole_refresh_token is not None:
            return old_access_token
        now = datetime.now().strftime("%Y-%m-%d")
        refresh_token = await self.hass.auth.async_create_refresh_token(
            user, 
            client_name="语音控制" + now, 
            token_type="long_lived_access_token", 
            access_token_expiration=timedelta(days=ACCESS_TOKEN_EXPIRATION_DAYS))
        access_token = self.hass.auth.async_create_access_token(refresh_token)
        refresh_token.expire_at
        await self.store.async_set_token(user.id, refresh_token.id, access_token, refresh_token.expire_at)
        _LOGGER.info("create Refresh token: %s", refresh_token.id)
        return access_token
    
    async def check_refresh_token(self, user_id: str):
        """Check refresh token"""
        token = await self.store.async_get_token(user_id)
        if token is None:
            return None, None
        token_id = token["token_id"]
        if token_id is None:
            return None, None
        refresh_token = self.hass.auth.async_get_refresh_token(token_id)
        if refresh_token is None:
            return None, None
        expire_at = refresh_token.created_at + refresh_token.access_token_expiration
        if expire_at.timestamp() < (datetime.now() + timedelta(days=ACCESS_TOKEN_UPDATE_DAYS)).timestamp(): 
            _LOGGER.info("Refresh token expired: %s", refresh_token.id)
            self.hass.auth.async_remove_refresh_token(refresh_token)
            return None, None
        access_token = token["access_token"]
        return refresh_token, access_token

