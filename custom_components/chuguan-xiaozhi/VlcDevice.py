"""Provide functionality to interact with vlc devices on the network."""

from __future__ import annotations

import logging
from typing import Any

import vlc
import voluptuous as vol

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA as MEDIA_PLAYER_PLATFORM_SCHEMA,
    BrowseMedia,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

CONF_ARGUMENTS = "arguments"
DEFAULT_NAME = "Vlc"

PLATFORM_SCHEMA = MEDIA_PLAYER_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ARGUMENTS, default=""): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)


class VlcDevice(MediaPlayerEntity):
    """Representation of a vlc player."""

    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.SEEK
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )

    def __init__(self, name, arguments):
        """Initialize the vlc device."""
        self._instance = vlc.Instance(arguments)
        self._vlc = self._instance.media_player_new()
        self._attr_name = name
        self._attr_unique_id = "media_player"
        self._attr_should_poll = True
        self._cancelable = None

    def update(self):
        """Get the latest details from the device."""
        status = self._vlc.get_state()
        if status == vlc.State.Playing:
            self._attr_state = MediaPlayerState.PLAYING
        elif status == vlc.State.Paused:
            self._attr_state = MediaPlayerState.PAUSED
        else:
            self._attr_state = MediaPlayerState.IDLE
        self._attr_media_duration = self._vlc.get_length() / 1000
        position = self._vlc.get_position() * self._attr_media_duration
        if position != self._attr_media_position:
            self._attr_media_position_updated_at = dt_util.utcnow()
            self._attr_media_position = position

        self._attr_volume_level = self._vlc.audio_get_volume() / 100
        self._attr_is_volume_muted = self._vlc.audio_get_mute() == 1

        return True

    def media_seek(self, position: float) -> None:
        """Seek the media to a specific location."""
        _LOGGER.warning(f"vlc device seek: position: {position}")
        track_length = self._vlc.get_length() / 1000
        self._vlc.set_position(position / track_length)

    def mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        self._vlc.audio_set_mute(mute)
        self._attr_is_volume_muted = mute

    def set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        self._vlc.audio_set_volume(int(volume * 100))
        self._attr_volume_level = volume

    def media_play(self) -> None:
        """Send play command."""
        self._vlc.play()
        self._attr_state = MediaPlayerState.PLAYING

    def media_pause(self) -> None:
        """Send pause command."""
        self._vlc.pause()
        self._attr_state = MediaPlayerState.PAUSED

    def media_stop(self) -> None:
        """Send stop command."""
        self._vlc.stop()
        self._attr_state = MediaPlayerState.IDLE

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play media from a URL or file."""
        # Handle media_source
        _LOGGER.warning(f"vlc device play media: media_id: {media_id}, media_type: {media_type}")
        if media_source.is_media_source_id(media_id):
            sourced_media = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )
            media_id = sourced_media.url

        elif media_type != MediaType.MUSIC:
            _LOGGER.error(
                "Invalid media type %s. Only %s is supported",
                media_type,
                MediaType.MUSIC,
            )
            return
        
        media_id = async_process_play_media_url(self.hass, media_id)
        _LOGGER.warning(f"vlc device play media: media_id: {media_id}")
        def play():
            self._vlc.set_media(self._instance.media_new(media_id))
            self._vlc.play()

        await self.hass.async_add_executor_job(play)
        self._attr_state = MediaPlayerState.PLAYING

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the websocket media browsing helper."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        await super().async_added_to_hass()
        self._cancelable = async_track_time_interval(self.hass, self.update_state, timedelta(seconds=1))

    async def async_will_remove_from_hass(self) -> None:
        """Entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        if self._cancelable:
            self._cancelable()
            self._cancelable = None

    def update_state(self, now):
        old_attr_state = self._attr_state
        old_attr_media_position = self._attr_media_position
        old_attr_media_duration = self._attr_media_duration
        old__attr_volume_level = self._attr_volume_level
        old_attr_is_volume_muted = self._attr_is_volume_muted
        change = False
        self.update()
        if old_attr_state != self._attr_state or old_attr_media_position != self._attr_media_position or old_attr_media_duration != self._attr_media_duration or old__attr_volume_level != self._attr_volume_level or old_attr_is_volume_muted != self._attr_is_volume_muted:
            change = True
        if change:
            self.hass.loop.call_soon_threadsafe(self._update_state)

    def _update_state(self):
        self.async_write_ha_state()
