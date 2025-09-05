"""Apple Calendar 7-Day View Integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import AppleCalendarCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Apple Calendar 7-Day View component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Apple Calendar 7-Day View from a config entry."""
    _LOGGER.info("Setting up Apple Calendar 7-Day View")
    
    coordinator = AppleCalendarCoordinator(hass, entry)
    
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.exception("Error setting up Apple Calendar integration: %s", err)
        raise ConfigEntryNotReady from err
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_register_services(hass, coordinator)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Unregister services if no more instances
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "refresh_calendar")
            hass.services.async_remove(DOMAIN, "create_event")
    
    return unload_ok


async def _async_register_services(hass: HomeAssistant, coordinator: AppleCalendarCoordinator) -> None:
    """Register integration services."""
    
    async def async_refresh_calendar(call) -> None:
        """Refresh calendar data."""
        await coordinator.async_request_refresh()
    
    async def async_create_event(call) -> None:
        """Create a new calendar event."""
        calendar_id = call.data.get("calendar_id")
        title = call.data.get("title")
        start_datetime = call.data.get("start_datetime")
        end_datetime = call.data.get("end_datetime")
        description = call.data.get("description", "")
        location = call.data.get("location", "")
        
        await coordinator.async_create_event(
            calendar_id, title, start_datetime, end_datetime, description, location
        )
    
    # Register services
    hass.services.async_register(
        DOMAIN, "refresh_calendar", async_refresh_calendar
    )
    
    hass.services.async_register(
        DOMAIN, 
        "create_event", 
        async_create_event,
        schema=None  # TODO: Add proper schema validation
    )