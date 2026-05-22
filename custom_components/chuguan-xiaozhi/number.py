from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.number import NumberEntity, NumberDeviceClass
from .chuguan.volume import watch_volume, get_volume, set_volume
import asyncio

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
        self._monitor_process = None

    @property
    def native_value(self):
        return self._volume

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await set_volume(int(value))
        self._volume = int(value)

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        await super().async_added_to_hass()
        self._volume = await get_volume()
        self.async_write_ha_state()
        @callback
        def handle_volume_change(info):
            mute = info["muted"]
            if mute:
                self._volume = 0
            else:
                self._volume = info["volume"]
            self.async_write_ha_state()
            self.hass.bus.async_fire("volume_mute_changed", info)

        self._monitor_process = await watch_volume(handle_volume_change)

    async def will_remove_from_hass(self) -> None:
        """Entity will be removed from hass."""
        await super().will_remove_from_hass()
        # 终止 pactl 订阅进程，防止产生僵尸进程
        if self._monitor_process:
            self._monitor_process.terminate()
            try:
                # 等待进程完全退出
                await asyncio.wait_for(self._monitor_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # 如果超时未退出，强制杀死
                self._monitor_process.kill()
            self._monitor_process = None


