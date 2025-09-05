"""Constants for Apple Calendar 7-Day View integration."""
from datetime import timedelta

DOMAIN = "apple_calendar_7day"

# Configuration
CONF_CALENDARS = "calendars"
CONF_DAYS_TO_SYNC = "days_to_sync"
CONF_AUTO_REFRESH = "auto_refresh"

# Defaults
DEFAULT_NAME = "Apple Calendar"
DEFAULT_DAYS_TO_SYNC = 7
DEFAULT_AUTO_REFRESH = True

# Update intervals
UPDATE_INTERVAL = timedelta(minutes=15)
FAST_UPDATE_INTERVAL = timedelta(minutes=5)

# Calendar event attributes
ATTR_SUMMARY = "summary"
ATTR_DESCRIPTION = "description"
ATTR_LOCATION = "location"
ATTR_START = "start"
ATTR_END = "end"
ATTR_CALENDAR = "calendar"
ATTR_UID = "uid"
ATTR_RRULE = "rrule"
ATTR_ALL_DAY = "all_day"
ATTR_ATTENDEES = "attendees"
ATTR_ORGANIZER = "organizer"

# Service names
SERVICE_REFRESH = "refresh_calendar"
SERVICE_CREATE_EVENT = "create_event"

# Error messages
ERROR_AUTH_FAILED = "Authentication failed"
ERROR_CONNECTION_FAILED = "Connection failed"
ERROR_CALENDAR_NOT_FOUND = "Calendar not found"

# Event colors (for different calendar types)
CALENDAR_COLORS = {
    "personal": "#3498db",
    "work": "#e74c3c", 
    "family": "#2ecc71",
    "holidays": "#f39c12",
    "birthdays": "#9b59b6",
    "default": "#34495e"
}