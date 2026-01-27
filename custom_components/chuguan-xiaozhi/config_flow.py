"""Config flow for the chuguan_xiaozhi integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow as ParentConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

import uuid
import string
import random
from .chuguan.hub import DOMAIN

_LOGGER = logging.getLogger(__name__)



# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
    }
)


class ConfigFlow(ParentConfigFlow, domain=DOMAIN):
    """Handle a config flow for chuguan_home."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        return self.async_create_entry(title="Chuguan Xiaozhi", data={})
        

