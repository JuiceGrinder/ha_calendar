"""Config flow for Apple Calendar 7-Day View integration."""
from __future__ import annotations

import logging
from typing import Any

import caldav
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_AUTO_REFRESH,
    CONF_DAYS_TO_SYNC,
    DEFAULT_AUTO_REFRESH,
    DEFAULT_DAYS_TO_SYNC,
    DOMAIN,
    ERROR_AUTH_FAILED,
    ERROR_CONNECTION_FAILED,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default="https://caldav.icloud.com/"): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_OPTIONS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DAYS_TO_SYNC, default=DEFAULT_DAYS_TO_SYNC): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=30)
        ),
        vol.Optional(CONF_AUTO_REFRESH, default=DEFAULT_AUTO_REFRESH): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    def _test_connection():
        """Test connection in executor."""
        client = caldav.DAVClient(
            url=data[CONF_URL],
            username=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
        )
        
        # Test connection by trying to get principal
        principal = client.principal()
        calendars = principal.calendars()
        
        # Get calendar info
        calendar_info = {}
        for calendar in calendars[:5]:  # Limit to first 5 calendars for validation
            try:
                props = calendar.get_properties([caldav.dav.DisplayName()])
                name = props.get(caldav.dav.DisplayName.tag, "Unknown")
                if isinstance(name, list) and name:
                    name = name[0]
                calendar_info[calendar.id] = str(name)
            except Exception as err:
                _LOGGER.debug("Error getting calendar properties: %s", err)
                calendar_info[calendar.id] = "Unknown Calendar"
                
        return {"calendars": calendar_info}

    try:
        info = await hass.async_add_executor_job(_test_connection)
    except Exception as exc:
        if "401" in str(exc) or "authentication" in str(exc).lower():
            raise InvalidAuth from exc
        raise CannotConnect from exc

    return {"title": f"Apple Calendar ({data[CONF_USERNAME]})", **info}


class AppleCalendarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apple Calendar 7-Day View."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = ERROR_CONNECTION_FAILED
            except InvalidAuth:
                errors["base"] = ERROR_AUTH_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create unique ID based on username and URL
                unique_id = f"{user_input[CONF_USERNAME]}@{user_input[CONF_URL]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"], 
                    data=user_input,
                    options={
                        CONF_DAYS_TO_SYNC: DEFAULT_DAYS_TO_SYNC,
                        CONF_AUTO_REFRESH: DEFAULT_AUTO_REFRESH,
                    }
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "icloud_url": "https://caldav.icloud.com/",
                "setup_url": "https://appleid.apple.com/account/manage",
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return AppleCalendarOptionsFlowHandler(config_entry)


class AppleCalendarOptionsFlowHandler(ConfigFlow):
    """Handle options flow for Apple Calendar integration."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DAYS_TO_SYNC,
                        default=self.config_entry.options.get(
                            CONF_DAYS_TO_SYNC, DEFAULT_DAYS_TO_SYNC
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                    vol.Optional(
                        CONF_AUTO_REFRESH,
                        default=self.config_entry.options.get(
                            CONF_AUTO_REFRESH, DEFAULT_AUTO_REFRESH
                        ),
                    ): bool,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""