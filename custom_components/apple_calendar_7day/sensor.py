"""Sensor platform for Apple Calendar 7-Day View integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTR_START, ATTR_SUMMARY, DOMAIN
from .coordinator import AppleCalendarCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Apple Calendar sensor entities from config entry."""
    coordinator: AppleCalendarCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        AppleCalendarTodaySensor(coordinator, entry),
        AppleCalendarTomorrowSensor(coordinator, entry),
        AppleCalendarWeekSensor(coordinator, entry),
        AppleCalendarNextEventSensor(coordinator, entry),
    ]

    async_add_entities(entities, True)


class AppleCalendarBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Apple Calendar sensors."""

    def __init__(
        self,
        coordinator: AppleCalendarCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._sensor_type = sensor_type
        self._attr_name = f"Apple Calendar {name}"
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
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


class AppleCalendarTodaySensor(AppleCalendarBaseSensor):
    """Sensor for today's events count."""

    def __init__(self, coordinator: AppleCalendarCoordinator, entry: ConfigEntry) -> None:
        """Initialize today's events sensor."""
        super().__init__(coordinator, entry, "events_today", "Events Today")
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:calendar-today"

    @property
    def native_value(self) -> int:
        """Return the number of events today."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return 0

        today = dt_util.start_of_local_day()
        tomorrow = today + timedelta(days=1)
        
        count = 0
        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and hasattr(start_time, 'tzinfo'):
                try:
                    if today <= start_time < tomorrow:
                        count += 1
                except TypeError:
                    # Skip events with incompatible datetime types
                    continue
                
        return count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return {}

        today = dt_util.start_of_local_day()
        tomorrow = today + timedelta(days=1)
        
        today_events = []
        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and hasattr(start_time, 'tzinfo'):
                try:
                    if today <= start_time < tomorrow:
                        today_events.append({
                            "summary": event.get(ATTR_SUMMARY, ""),
                            "start": start_time.strftime("%H:%M"),
                            "location": event.get("location", ""),
                            "calendar": event.get("calendar", ""),
                        })
                except TypeError:
                    # Skip events with incompatible datetime types
                    continue

        return {
            "events": sorted(today_events, key=lambda x: x["start"]),
            "date": today.strftime("%Y-%m-%d"),
        }


class AppleCalendarTomorrowSensor(AppleCalendarBaseSensor):
    """Sensor for tomorrow's events count."""

    def __init__(self, coordinator: AppleCalendarCoordinator, entry: ConfigEntry) -> None:
        """Initialize tomorrow's events sensor."""
        super().__init__(coordinator, entry, "events_tomorrow", "Events Tomorrow")
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:calendar-arrow-right"

    @property
    def native_value(self) -> int:
        """Return the number of events tomorrow."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return 0

        tomorrow = dt_util.start_of_local_day() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        count = 0
        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and hasattr(start_time, 'tzinfo'):
                try:
                    if tomorrow <= start_time < day_after:
                        count += 1
                except TypeError:
                    # Skip events with incompatible datetime types
                    continue
                
        return count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return {}

        tomorrow = dt_util.start_of_local_day() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        
        tomorrow_events = []
        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and hasattr(start_time, 'tzinfo'):
                try:
                    if tomorrow <= start_time < day_after:
                        tomorrow_events.append({
                            "summary": event.get(ATTR_SUMMARY, ""),
                            "start": start_time.strftime("%H:%M"),
                            "location": event.get("location", ""),
                            "calendar": event.get("calendar", ""),
                        })
                except TypeError:
                    # Skip events with incompatible datetime types
                    continue

        return {
            "events": sorted(tomorrow_events, key=lambda x: x["start"]),
            "date": tomorrow.strftime("%Y-%m-%d"),
        }


class AppleCalendarWeekSensor(AppleCalendarBaseSensor):
    """Sensor for this week's events count."""

    def __init__(self, coordinator: AppleCalendarCoordinator, entry: ConfigEntry) -> None:
        """Initialize week's events sensor."""
        super().__init__(coordinator, entry, "events_this_week", "Events This Week")
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:calendar-week"

    @property
    def native_value(self) -> int:
        """Return the number of events this week."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return 0

        now = dt_util.now()
        week_start = dt_util.start_of_local_day()
        week_end = week_start + timedelta(days=7)
        
        count = 0
        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and hasattr(start_time, 'tzinfo'):
                try:
                    if week_start <= start_time < week_end:
                        count += 1
                except TypeError:
                    # Skip events with incompatible datetime types
                    continue
                
        return count

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return {}

        now = dt_util.now()
        week_start = dt_util.start_of_local_day()
        week_end = week_start + timedelta(days=7)
        
        # Group events by day
        daily_events = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_key = day.strftime("%A")
            daily_events[day_key] = []

        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and hasattr(start_time, 'tzinfo'):
                try:
                    if week_start <= start_time < week_end:
                        day_name = start_time.strftime("%A")
                        daily_events[day_name].append({
                            "summary": event.get(ATTR_SUMMARY, ""),
                            "start": start_time.strftime("%H:%M"),
                            "date": start_time.strftime("%Y-%m-%d"),
                            "location": event.get("location", ""),
                            "calendar": event.get("calendar", ""),
                        })
                except TypeError:
                    # Skip events with incompatible datetime types
                    continue

        return {
            "daily_events": daily_events,
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": (week_end - timedelta(days=1)).strftime("%Y-%m-%d"),
        }


class AppleCalendarNextEventSensor(AppleCalendarBaseSensor):
    """Sensor for the next upcoming event."""

    def __init__(self, coordinator: AppleCalendarCoordinator, entry: ConfigEntry) -> None:
        """Initialize next event sensor."""
        super().__init__(coordinator, entry, "next_event", "Next Event")
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> str:
        """Return the next event summary."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return "No upcoming events"

        now = dt_util.now()
        
        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and start_time > now:
                return event.get(ATTR_SUMMARY, "Untitled Event")
                
        return "No upcoming events"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or "events" not in self.coordinator.data:
            return {}

        now = dt_util.now()
        
        for event in self.coordinator.data["events"]:
            start_time = event.get(ATTR_START)
            if isinstance(start_time, str):
                start_time = dt_util.parse_datetime(start_time)
            elif start_time:
                # Ensure all datetime objects are timezone-aware
                try:
                    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is None:
                        start_time = dt_util.as_local(start_time)
                    elif not hasattr(start_time, 'tzinfo'):
                        # Handle other datetime-like objects
                        start_time = dt_util.as_local(start_time)
                except Exception:
                    # If conversion fails, skip this event
                    continue
            
            if start_time and start_time > now:
                # Calculate time until event
                time_diff = start_time - now
                
                if time_diff.days > 0:
                    time_until = f"in {time_diff.days} day{'s' if time_diff.days > 1 else ''}"
                elif time_diff.seconds >= 3600:
                    hours = time_diff.seconds // 3600
                    time_until = f"in {hours} hour{'s' if hours > 1 else ''}"
                elif time_diff.seconds >= 60:
                    minutes = time_diff.seconds // 60
                    time_until = f"in {minutes} minute{'s' if minutes > 1 else ''}"
                else:
                    time_until = "starting soon"
                    
                return {
                    "summary": event.get(ATTR_SUMMARY, ""),
                    "start": start_time.strftime("%Y-%m-%d %H:%M"),
                    "location": event.get("location", ""),
                    "calendar": event.get("calendar", ""),
                    "time_until": time_until,
                    "description": event.get("description", ""),
                }
                
        return {"message": "No upcoming events"}