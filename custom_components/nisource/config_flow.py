"""Config flow for NiSource integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import NiSourceAPI
from .const import CONF_PROVIDER, DOMAIN, PROVIDERS

_LOGGER = logging.getLogger(__name__)

# Create provider options for dropdown
PROVIDER_OPTIONS = {
    code: f"{info['name']} ({code})"
    for code, info in PROVIDERS.items()
}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROVIDER, default="OH"): vol.In(PROVIDER_OPTIONS),
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NiSource."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Get provider configuration
                provider_code = user_input[CONF_PROVIDER]
                provider_info = PROVIDERS[provider_code]

                # Validate the credentials
                api = NiSourceAPI(
                    base_url=provider_info["base_url"],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    state_code=provider_info["state_code"],
                )

                # Test authentication
                await self.hass.async_add_executor_job(api.authenticate)

                # Store provider info in config entry
                entry_data = {
                    **user_input,
                    "base_url": provider_info["base_url"],
                    "state_code": provider_info["state_code"],
                    "provider_name": provider_info["name"],
                }

                # Create the config entry
                return self.async_create_entry(
                    title=f"{provider_info['name']} ({user_input[CONF_USERNAME]})",
                    data=entry_data,
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
