"""Demo platform for the cover component."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_utc_time_change



async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the demo cover platform."""
    async_add_entities(
        [
            DemoCover(hass, "volume", "亮度"),
        ]
    )


class DemoCover(CoverEntity):
    """Representation of a demo cover."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        device_name: str,
        position: int | None = None,
        tilt_position: int | None = None,
        device_class: CoverDeviceClass | None = None,
        supported_features: CoverEntityFeature | None = None,
    ) -> None:
        """Initialize the cover."""
        self.hass = hass
        self._attr_unique_id = "volume"
        self._attr_name = "音量"
        self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
        self._position = 100
        self._closed = False

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of the cover."""
        return self._position

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        return self._closed

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self._position == 0:
            return
        self._position = 0
        self._closed = True
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self._position == 100:
            return
        self._position = 100
        self._closed = False
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position: int = kwargs[ATTR_POSITION]
        if self._position == position:
            return
        self._position = position
        self._closed = False
        self.async_write_ha_state()
