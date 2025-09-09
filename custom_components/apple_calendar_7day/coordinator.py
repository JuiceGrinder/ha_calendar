"""Data update coordinator for Apple Calendar integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import caldav
from caldav.objects import Calendar, Event
from icalendar import Event as ICalEvent, vDDDTypes
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ALL_DAY,
    ATTR_ATTENDEES,
    ATTR_CALENDAR,
    ATTR_DESCRIPTION,
    ATTR_END,
    ATTR_LOCATION,
    ATTR_ORGANIZER,
    ATTR_RRULE,
    ATTR_START,
    ATTR_SUMMARY,
    ATTR_UID,
    CONF_DAYS_TO_SYNC,
    DEFAULT_DAYS_TO_SYNC,
    DOMAIN,
    ERROR_AUTH_FAILED,
    ERROR_CONNECTION_FAILED,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class AppleCalendarCoordinator(DataUpdateCoordinator):
    """Apple Calendar data coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.client: caldav.DAVClient | None = None
        self.calendars: dict[str, Calendar] = {}
        self._events_cache: dict[str, list[dict[str, Any]]] = {}

    async def _async_setup(self) -> None:
        """Set up the CalDAV client with retry logic."""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                await self.hass.async_add_executor_job(self._setup_client)
                _LOGGER.info("CalDAV client setup successful on attempt %d", attempt + 1)
                return
            except Exception as err:
                _LOGGER.warning("CalDAV client setup attempt %d failed: %s", attempt + 1, err)
                
                # Check for authentication errors (don't retry these)
                if "401" in str(err) or "authentication" in str(err).lower():
                    _LOGGER.error("Authentication failed - not retrying")
                    raise ConfigEntryAuthFailed(ERROR_AUTH_FAILED) from err
                
                # If this is the last attempt, raise the error
                if attempt == max_retries - 1:
                    _LOGGER.error("CalDAV client setup failed after %d attempts", max_retries)
                    raise UpdateFailed(ERROR_CONNECTION_FAILED) from err
                
                # Wait before retrying
                if attempt < max_retries - 1:
                    _LOGGER.info("Retrying CalDAV setup in %d seconds...", retry_delay)
                    await asyncio.sleep(retry_delay)

    def _setup_client(self) -> None:
        """Set up CalDAV client (runs in executor)."""
        url = self.entry.data[CONF_URL]
        username = self.entry.data[CONF_USERNAME]
        password = self.entry.data[CONF_PASSWORD]

        _LOGGER.debug("Connecting to CalDAV server: %s", url)
        
        self.client = caldav.DAVClient(
            url=url,
            username=username,
            password=password,
        )
        
        # Test connection and get calendars
        principal = self.client.principal()
        calendars = principal.calendars()
        
        self.calendars = {}
        for calendar in calendars:
            try:
                calendar_name = calendar.get_properties([caldav.dav.DisplayName()])[
                    caldav.dav.DisplayName.tag
                ]
                if isinstance(calendar_name, list):
                    calendar_name = calendar_name[0] if calendar_name else "Unknown"
                
                self.calendars[calendar.id] = calendar
                _LOGGER.debug("Found calendar: %s (%s)", calendar_name, calendar.id)
            except Exception as err:
                _LOGGER.warning("Error getting calendar info: %s", err)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update calendar data."""
        if self.client is None:
            await self._async_setup()

        try:
            return await self.hass.async_add_executor_job(self._fetch_events)
        except Exception as err:
            _LOGGER.error("Failed to retrieve events from calendars: %s", err)
            if self.data:
                # Return cached data if available
                _LOGGER.info("Returning cached calendar data due to fetch failure")
                return self.data
            # Return empty structure if no cached data
            return {"events": [], "calendars": {}, "last_updated": dt_util.now().isoformat()}

    def _fetch_events(self) -> dict[str, Any]:
        """Fetch events from all calendars."""
        if not self.calendars:
            _LOGGER.warning("No calendars available for fetching events")
            return {"events": [], "calendars": {}}

        days_to_sync = self.entry.options.get(CONF_DAYS_TO_SYNC, DEFAULT_DAYS_TO_SYNC)
        start_date = dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=days_to_sync)

        _LOGGER.debug("Fetching events from %d calendars for date range %s to %s", 
                     len(self.calendars), start_date, end_date)

        all_events = []
        calendar_info = {}
        failed_calendars = []

        for calendar_id, calendar in self.calendars.items():
            try:
                calendar_name = self._get_calendar_name(calendar)
                calendar_info[calendar_id] = {
                    "name": calendar_name,
                    "id": calendar_id,
                }

                _LOGGER.debug("Fetching events from calendar: %s (%s)", calendar_name, calendar_id)

                # Fetch events for this calendar with timeout
                events = calendar.search(
                    start=start_date,
                    end=end_date,
                    event=True,
                    expand=True,
                )

                event_count = 0
                for event in events:
                    try:
                        parsed_event = self._parse_event(event, calendar_id, calendar_name)
                        if parsed_event:
                            all_events.append(parsed_event)
                            event_count += 1
                    except Exception as err:
                        _LOGGER.warning("Error parsing event from calendar %s: %s", calendar_name, err)

                _LOGGER.debug("Successfully fetched %d events from calendar %s", event_count, calendar_name)

            except Exception as err:
                _LOGGER.error("Failed to fetch events from calendar %s (%s): %s", 
                             calendar_info.get(calendar_id, {}).get("name", calendar_id), 
                             calendar_id, err)
                failed_calendars.append(calendar_id)

        # Sort events by start time
        all_events.sort(key=lambda x: x[ATTR_START])

        # Log summary
        if failed_calendars:
            _LOGGER.warning("Failed to fetch events from %d calendars: %s", 
                           len(failed_calendars), failed_calendars)
        
        _LOGGER.info("Successfully retrieved %d events from %d calendars (%d failed)", 
                    len(all_events), len(calendar_info) - len(failed_calendars), len(failed_calendars))

        return {
            "events": all_events,
            "calendars": calendar_info,
            "last_updated": dt_util.now().isoformat(),
            "failed_calendars": failed_calendars,
        }

    def _get_calendar_name(self, calendar: Calendar) -> str:
        """Get calendar display name."""
        try:
            props = calendar.get_properties([caldav.dav.DisplayName()])
            name = props.get(caldav.dav.DisplayName.tag)
            if isinstance(name, list) and name:
                return str(name[0])
            return str(name) if name else "Unknown Calendar"
        except Exception:
            return "Unknown Calendar"

    def _parse_event(self, event: Event, calendar_id: str, calendar_name: str) -> dict[str, Any] | None:
        """Parse a CalDAV event into our format."""
        try:
            ical_event: ICalEvent = event.icalendar_component
            
            # Get basic event info
            summary = str(ical_event.get("SUMMARY", ""))
            description = str(ical_event.get("DESCRIPTION", ""))
            location = str(ical_event.get("LOCATION", ""))
            uid = str(ical_event.get("UID", ""))
            
            # Parse start and end times
            dtstart = ical_event.get("DTSTART")
            dtend = ical_event.get("DTEND")
            
            if not dtstart:
                return None
                
            start_dt = self._parse_datetime(dtstart.dt)
            end_dt = self._parse_datetime(dtend.dt) if dtend else start_dt
            
            # Check if it's an all-day event
            all_day = False
            try:
                if hasattr(dtstart, 'dt'):
                    # All-day events are typically stored as date objects, not datetime
                    from datetime import date
                    all_day = isinstance(dtstart.dt, date) and not isinstance(dtstart.dt, datetime)
                else:
                    all_day = False
            except Exception:
                all_day = False
            
            # Get attendees
            attendees = []
            if "ATTENDEE" in ical_event:
                attendee_list = ical_event.get("ATTENDEE")
                if not isinstance(attendee_list, list):
                    attendee_list = [attendee_list]
                    
                for attendee in attendee_list:
                    if hasattr(attendee, 'params'):
                        name = attendee.params.get('CN', str(attendee))
                        attendees.append(name)
            
            # Get organizer
            organizer = ""
            if "ORGANIZER" in ical_event:
                org = ical_event.get("ORGANIZER")
                if hasattr(org, 'params') and 'CN' in org.params:
                    organizer = org.params['CN']
                else:
                    organizer = str(org)
            
            return {
                ATTR_UID: uid,
                ATTR_SUMMARY: summary,
                ATTR_DESCRIPTION: description,
                ATTR_LOCATION: location,
                ATTR_START: start_dt,
                ATTR_END: end_dt,
                ATTR_ALL_DAY: all_day,
                ATTR_CALENDAR: calendar_name,
                ATTR_ATTENDEES: attendees,
                ATTR_ORGANIZER: organizer,
                ATTR_RRULE: str(ical_event.get("RRULE", "")),
                "calendar_id": calendar_id,
            }
            
        except Exception as err:
            _LOGGER.exception("Error parsing event: %s", err)
            return None

    def _parse_datetime(self, dt_value: Any) -> datetime:
        """Parse datetime value from iCalendar."""
        if dt_value is None:
            return dt_util.now()
            
        try:
            if isinstance(dt_value, datetime):
                # If it's already a datetime, ensure it's timezone-aware
                if dt_value.tzinfo is None:
                    return dt_util.as_local(dt_value)
                return dt_value
            elif hasattr(dt_value, 'date') and callable(dt_value.date):
                # Date object, convert to datetime at start of day
                return dt_util.as_local(datetime.combine(dt_value.date(), datetime.min.time()))
            elif hasattr(dt_value, 'date') and not callable(dt_value.date):
                # Date property, use directly
                return dt_util.as_local(datetime.combine(dt_value.date, datetime.min.time()))
            else:
                # Try to parse as string
                parsed_dt = dt_util.parse_datetime(str(dt_value))
                if parsed_dt:
                    return parsed_dt
                # Fallback: try to parse as date only
                from datetime import date
                try:
                    date_only = date.fromisoformat(str(dt_value).split('T')[0])
                    return dt_util.as_local(datetime.combine(date_only, datetime.min.time()))
                except (ValueError, AttributeError):
                    _LOGGER.warning("Unable to parse datetime value: %s (%s)", dt_value, type(dt_value))
                    return dt_util.now()
        except Exception as err:
            _LOGGER.warning("Error parsing datetime %s: %s", dt_value, err)
            return dt_util.now()

    async def async_create_event(
        self,
        calendar_id: str,
        title: str,
        start_datetime: datetime,
        end_datetime: datetime,
        description: str = "",
        location: str = "",
    ) -> bool:
        """Create a new event in the specified calendar."""
        if calendar_id not in self.calendars:
            _LOGGER.error("Calendar %s not found", calendar_id)
            return False

        try:
            await self.hass.async_add_executor_job(
                self._create_event_sync,
                calendar_id,
                title,
                start_datetime,
                end_datetime,
                description,
                location,
            )
            
            # Trigger a refresh after creating the event
            await self.async_request_refresh()
            return True
            
        except Exception as err:
            _LOGGER.exception("Error creating event: %s", err)
            return False

    def _create_event_sync(
        self,
        calendar_id: str,
        title: str,
        start_datetime: datetime,
        end_datetime: datetime,
        description: str,
        location: str,
    ) -> None:
        """Create event synchronously."""
        calendar = self.calendars[calendar_id]
        
        # Create iCalendar event
        event = ICalEvent()
        event.add('summary', title)
        event.add('dtstart', start_datetime)
        event.add('dtend', end_datetime)
        
        if description:
            event.add('description', description)
        if location:
            event.add('location', location)
            
        event.add('uid', f"{dt_util.utcnow().timestamp()}@homeassistant")
        event.add('dtstamp', dt_util.utcnow())

        # Add to calendar
        calendar.save_event(event.to_ical().decode('utf-8'))