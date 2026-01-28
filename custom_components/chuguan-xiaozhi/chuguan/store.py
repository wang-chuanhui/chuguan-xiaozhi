from homeassistant.core import HomeAssistant
from .utils import get_main_mac
from homeassistant.helpers.storage import Store
from .const import DOMAIN, STORAGE_VERSION
from datetime import datetime, timedelta

class MyStore:
    """Chuguan Xiaozhi Store"""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.mac = get_main_mac()
        self.store = Store(hass, STORAGE_VERSION, f"chuguan-xiaozhi.{self.mac}")

    async def async_get_api_key(self):
        """Get api key from store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        if stored_data:
            return stored_data.get("api_key", None)
        return None
    
    async def async_set_api_key(self, api_key: str):
        """Set api key to store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        stored_data["api_key"] = api_key
        await self.store.async_save(stored_data)

    async def async_get_devices(self):
        """Get devices from store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        if stored_data:
            return stored_data.get("devices", [])
        return []
    
    async def async_set_devices(self, devices: list):
        """Set devices to store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        stored_data["devices"] = devices
        await self.store.async_save(stored_data)

    async def async_get_token(self, user_id: str):
        """Get token from store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        if stored_data:
            return stored_data.get(user_id, None)
        return None

    async def async_set_token(self, user_id: str, token_id: str, access_token: str, expire_time: float):
        """Set token to store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        stored_data[user_id] = {
            "token_id": token_id,
            "access_token": access_token,
            "expire_time": expire_time,
        }
        await self.store.async_save(stored_data)

    async def async_get_host(self):
        """Get host from store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        if stored_data:
            return stored_data.get("host", None)
        return None
    
    async def async_set_host(self, host: str):
        """Set host to store"""
        stored_data = await self.store.async_load()
        if isinstance(stored_data, dict) == False:
            stored_data = {}
        stored_data["host"] = host
        await self.store.async_save(stored_data)