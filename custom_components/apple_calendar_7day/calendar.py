"""Calendar platform for Apple Calendar 7-Day View integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ALL_DAY,
    ATTR_ATTENDEES,
    ATTR_CALENDAR,
    ATTR_DESCRIPTION,
    ATTR_END,
    ATTR_LOCATION,
    ATTR_ORGANIZER,
    ATTR_START,
    ATTR_SUMMARY,
    ATTR_UID,
    DOMAIN,
)
from .coordinator import AppleCalendarCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Apple Calendar entities from config entry."""
    coordinator: AppleCalendarCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for initial data
    await coordinator.async_config_entry_first_refresh()

    # Create calendar entities for each calendar
    entities = []
    
    # Main unified calendar entity
    entities.append(AppleCalendarEntity(coordinator, entry, "all"))
    
    # Individual calendar entities
    if coordinator.data and "calendars" in coordinator.data:
        for calendar_id, calendar_info in coordinator.data["calendars"].items():
            entities.append(AppleCalendarEntity(coordinator, entry, calendar_id, calendar_info["name"]))

    async_add_entities(entities, True)


class AppleCalendarEntity(CoordinatorEntity, CalendarEntity):
    """Apple Calendar entity."""

    def __init__(
        self,
        coordinator: AppleCalendarCoordinator,
        entry: ConfigEntry,
        calendar_id: str,
        calendar_name: str | None = None,
    ) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator)
        self.entry = entry
        self._calendar_id = calendar_id
        self._calendar_name = calendar_name or "Apple Calendar"
        
        if calendar_id == "all":
            self._attr_name = "Apple Calendar (All)"
            self._attr_unique_id = f"{entry.entry_id}_all_calendars"
        else:
            self._attr_name = f"Apple Calendar ({self._calendar_name})"
            self._attr_unique_id = f"{entry.entry_id}_{calendar_id}"
            
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Apple Calendar 7-Day View",
            manufacturer="Apple",
            model="CalDAV Calendar",
            sw_version="1.0.0",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming calendar event."""
        if not self.coordinator.data:
            return None

        events = self._get_filtered_events()
        if not events:
            return None

        # Find the next upcoming event
        now = dt_util.now()
        for event_data in events:
            start_time = event_data[ATTR_START]
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            
            if start_time and start_time > now:
                return self._create_calendar_event(event_data)

        # If no future events, return the current ongoing event
        for event_data in events:
            start_time = event_data[ATTR_START]
            end_time = event_data[ATTR_END]
            
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            if isinstance(end_time, str):
                end_time = dt_util.parse_datetime(end_time)
                
            if start_time and end_time and start_time <= now <= end_time:
                return self._create_calendar_event(event_data)

        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Get events in a specific time range."""
        if not self.coordinator.data:
            return []

        events = self._get_filtered_events()
        calendar_events = []

        for event_data in events:
            start_time = event_data[ATTR_START]
            end_time = event_data[ATTR_END]
            
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            if isinstance(end_time, str):
                end_time = dt_util.parse_datetime(end_time)

            if not start_time or not end_time:
                continue

            # Check if event overlaps with requested range
            if start_time < end_date and end_time > start_date:
                calendar_events.append(self._create_calendar_event(event_data))

        return sorted(calendar_events, key=lambda x: x.start)

    def _get_filtered_events(self) -> list[dict[str, Any]]:
        """Get events filtered by calendar ID."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return []

        events = self.coordinator.data["events"]
        
        if self._calendar_id == "all":
            return events
        
        return [
            event for event in events 
            if event.get("calendar_id") == self._calendar_id
        ]

    def _create_calendar_event(self, event_data: dict[str, Any]) -> CalendarEvent:
        """Create a CalendarEvent from event data."""
        start_time = event_data[ATTR_START]
        end_time = event_data[ATTR_END]
        
        if isinstance(start_time, str):
            start_time = dt_util.parse_datetime(start_time)
        if isinstance(end_time, str):
            end_time = dt_util.parse_datetime(end_time)

        return CalendarEvent(
            start=start_time,
            end=end_time,
            summary=event_data.get(ATTR_SUMMARY, ""),
            description=event_data.get(ATTR_DESCRIPTION, ""),
            location=event_data.get(ATTR_LOCATION, ""),
            uid=event_data.get(ATTR_UID, ""),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}

        events = self._get_filtered_events()
        
        # Count events by day for the next 7 days
        now = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_counts = {}
        weekly_events = []
        
        for i in range(7):
            day = now + timedelta(days=i)
            day_key = day.strftime("%Y-%m-%d")
            daily_counts[day_key] = 0
            
        for event_data in events:
            start_time = event_data[ATTR_START]
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
                
            if start_time:
                day_key = start_time.strftime("%Y-%m-%d")
                if day_key in daily_counts:
                    daily_counts[day_key] += 1
                    
                # Add to weekly events list
                if start_time >= now and start_time < now + timedelta(days=7):
                    weekly_events.append({
                        "summary": event_data.get(ATTR_SUMMARY, ""),
                        "start": start_time.isoformat(),
                        "end": event_data.get(ATTR_END, ""),
                        "location": event_data.get(ATTR_LOCATION, ""),
                        "calendar": event_data.get(ATTR_CALENDAR, ""),
                        "all_day": event_data.get(ATTR_ALL_DAY, False),
                    })

        return {
            "events": weekly_events,
            "events_today": daily_counts.get(now.strftime("%Y-%m-%d"), 0),
            "events_tomorrow": daily_counts.get((now + timedelta(days=1)).strftime("%Y-%m-%d"), 0),
            "events_this_week": len(weekly_events),
            "daily_counts": daily_counts,
            "last_updated": self.coordinator.data.get("last_updated"),
            "calendar_count": len(self.coordinator.data.get("calendars", {})),
        }