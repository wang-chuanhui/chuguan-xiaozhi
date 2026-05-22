"""Demo platform that has two fake switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .chuguan.volume import get_mute, set_mute


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the demo switch platform."""
    async_add_entities(
        [
            MuteSwitch(),
        ]
    )


class MuteSwitch(SwitchEntity):
    """Representation of a mute switch."""


    def __init__(
        self
    ) -> None:
        """Initialize the mute switch."""
        self._attr_unique_id = "mute_switch"
        self._attr_name = "静音"
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._is_on = False
        self.cancel = None

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await set_mute(True)
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await set_mute(False)
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._is_on = await get_mute()
        self.async_write_ha_state()

        def handle_mute_change(event):
            self._is_on = event.data.get("muted", False)
            self.schedule_update_ha_state()

        self.cancel = self.hass.bus.async_listen("volume_mute_changed", handle_mute_change)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        super().async_will_remove_from_hass()
        self.cancel()
