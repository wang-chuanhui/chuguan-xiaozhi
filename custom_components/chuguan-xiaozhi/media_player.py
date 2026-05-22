from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Demo config entry."""
    device = DevicePlayer()
    async_add_entities(
        [
            device,
        ]
    )

PLAYER_SUPPORT = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
)

class DevicePlayer(MediaPlayerEntity):
    """A demo media players."""

    _attr_should_poll = False

    # We only implement the methods that we support

    def __init__(self) -> None:
        """Initialize the demo device."""
        self._attr_supported_features = PLAYER_SUPPORT
        self._attr_name = "音量"
        self._attr_state = MediaPlayerState.IDLE
        self._attr_volume_level = 1.0
        self._attr_is_volume_muted = False
        self._attr_shuffle = False
        self._attr_unique_id = "volume_mute_control"

    def mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        self._attr_is_volume_muted = mute
        self.schedule_update_ha_state()

    def volume_up(self) -> None:
        """Increase volume."""
        assert self.volume_level is not None
        self._attr_volume_level = min(1.0, self.volume_level + 0.1)
        self.schedule_update_ha_state()

    def volume_down(self) -> None:
        """Decrease volume."""
        assert self.volume_level is not None
        self._attr_volume_level = max(0.0, self.volume_level - 0.1)
        self.schedule_update_ha_state()

    def set_volume_level(self, volume: float) -> None:
        """Set the volume level, range 0..1."""
        self._attr_volume_level = volume
        self.schedule_update_ha_state()

