"""Demo implementation of the media player."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util


SOUND_MODE_LIST = ["Music", "Movie"]
DEFAULT_SOUND_MODE = "Music"

YOUTUBE_PLAYER_SUPPORT = (
    MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.PLAY_MEDIA
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.SHUFFLE_SET
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    | MediaPlayerEntityFeature.SEEK
    | MediaPlayerEntityFeature.STOP
)




class AbstractDemoPlayer(MediaPlayerEntity):
    """A demo media players."""

    _attr_should_poll = False
    _attr_sound_mode_list = SOUND_MODE_LIST

    # We only implement the methods that we support

    def __init__(
        self, name: str, device_class: MediaPlayerDeviceClass | None = None
    ) -> None:
        """Initialize the demo device."""
        self._attr_name = name
        self._attr_state = MediaPlayerState.PLAYING
        self._attr_volume_level = 1.0
        self._attr_is_volume_muted = False
        self._attr_shuffle = False
        self._attr_sound_mode = DEFAULT_SOUND_MODE
        self._attr_device_class = device_class
        self._attr_unique_id = name

    def turn_on(self) -> None:
        """Turn the media player on."""
        self._attr_state = MediaPlayerState.PLAYING
        self.schedule_update_ha_state()

    def turn_off(self) -> None:
        """Turn the media player off."""
        self._attr_state = MediaPlayerState.OFF
        self.schedule_update_ha_state()

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

    def media_play(self) -> None:
        """Send play command."""
        self._attr_state = MediaPlayerState.PLAYING
        self.schedule_update_ha_state()

    def media_pause(self) -> None:
        """Send pause command."""
        self._attr_state = MediaPlayerState.PAUSED
        self.schedule_update_ha_state()

    def media_stop(self) -> None:
        """Send stop command."""
        self._attr_state = MediaPlayerState.OFF
        self.schedule_update_ha_state()

    def set_shuffle(self, shuffle: bool) -> None:
        """Enable/disable shuffle mode."""
        self._attr_shuffle = shuffle
        self.schedule_update_ha_state()

    def select_sound_mode(self, sound_mode: str) -> None:
        """Select sound mode."""
        self._attr_sound_mode = sound_mode
        self.schedule_update_ha_state()


class DemoYoutubePlayer(AbstractDemoPlayer):
    """A Demo media player that only supports YouTube."""

    # We only implement the methods that we support

    _attr_app_name = "YouTube"
    _attr_media_content_type = MediaType.MOVIE
    _attr_supported_features = YOUTUBE_PLAYER_SUPPORT

    def __init__(
        self, name: str, youtube_id: str, media_title: str, duration: int
    ) -> None:
        """Initialize the demo device."""
        super().__init__(name)
        self._attr_media_content_id = youtube_id
        self._attr_media_title = media_title
        self._attr_media_duration = duration
        self._progress: int | None = int(duration * 0.15)
        self._progress_updated_at = dt_util.utcnow()

    @property
    def media_image_url(self) -> str:
        """Return the image url of current playing media."""
        return f"https://img.youtube.com/vi/{self.media_content_id}/hqdefault.jpg"

    @property
    def media_position(self) -> int | None:
        """Position of current playing media in seconds."""
        if self._progress is None:
            return None

        position = self._progress

        if self.state == MediaPlayerState.PLAYING:
            position += int(
                (dt_util.utcnow() - self._progress_updated_at).total_seconds()
            )

        return position

    @property
    def media_position_updated_at(self) -> datetime | None:
        """When was the position of the current playing media valid.

        Returns value from homeassistant.util.dt.utcnow().
        """
        if self.state == MediaPlayerState.PLAYING:
            return self._progress_updated_at
        return None

    def play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a piece of media."""
        self._attr_media_content_id = media_id
        self.schedule_update_ha_state()

    def media_pause(self) -> None:
        """Send pause command."""
        self._progress = self.media_position
        self._progress_updated_at = dt_util.utcnow()
        super().media_pause()

