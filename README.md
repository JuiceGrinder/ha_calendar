# Apple Calendar 7-Day View - Home Assistant Integration

A comprehensive Home Assistant custom integration that provides seamless Apple Calendar (iCloud) connectivity with a beautiful 7-day view interface.

## ✨ Features

### 🍎 **Native Apple Integration**
- Direct CalDAV connection to iCloud calendars
- Support for multiple calendars
- Real-time event synchronization
- App-specific password security

### 📅 **Comprehensive Calendar Entities**
- **Unified Calendar Entity**: All calendars combined
- **Individual Calendar Entities**: Per-calendar access
- **Smart Sensors**: Today, Tomorrow, Week, Next Event
- **Rich Attributes**: Event details, attendees, locations

### 🎨 **Modern Frontend**
- **Custom 7-Day Card**: Beautiful, responsive design
- **Apple-inspired UI**: Clean, modern interface
- **Mobile Optimized**: Works perfectly on all devices
- **Customizable**: Multiple themes and layouts

### 🔔 **Intelligent Automations**
- Event reminders (15min, 5min before)
- Daily and weekly summaries
- All-day event notifications
- Smart scheduling insights

### ⚙️ **Advanced Configuration**
- GUI-based setup flow
- Options configuration
- Service calls for automation
- Developer-friendly API

## 🚀 Installation

### Method 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the "+" button
4. Search for "Apple Calendar 7-Day View"
5. Click "Download"
6. Restart Home Assistant

### Method 2: Manual Installation

1. Download this repository
2. Copy `custom_components/apple_calendar_7day/` to your Home Assistant `custom_components/` directory
3. Copy `www/apple-calendar-7day-card.js` to your `www/` directory
4. Restart Home Assistant

## 📱 Apple Setup

### 1. Generate App-Specific Password

1. Go to [Apple ID Account Management](https://appleid.apple.com)
2. Sign in with your Apple ID
3. Navigate to **Sign-In and Security** → **App-Specific Passwords**
4. Click **"+"** to generate a new password
5. Label it "Home Assistant Calendar"
6. Copy the generated password (format: `xxxx-xxxx-xxxx-xxxx`)

### 2. Two-Factor Authentication

⚠️ **Important**: Two-factor authentication must be enabled on your Apple ID for App-Specific Passwords to work.

## ⚙️ Home Assistant Configuration

### 1. Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"Apple Calendar 7-Day View"**
4. Enter your credentials:
   - **URL**: `https://caldav.icloud.com/`
   - **Username**: Your Apple ID email
   - **Password**: Your App-Specific Password

### 2. Configure Options

After setup, you can configure:
- **Days to Sync**: 1-30 days (default: 7)
- **Auto Refresh**: Enable/disable automatic updates

### 3. Add Frontend Card

Add to your dashboard:

```yaml
type: custom:apple-calendar-7day-card
entity: calendar.apple_calendar_all
name: "My Apple Calendar"
show_description: true
show_location: true
show_time: true
compact_mode: false
max_events_per_day: 5
```

## 📊 Entities Created

### Calendar Entities
- `calendar.apple_calendar_all` - All calendars combined
- `calendar.apple_calendar_[calendar_name]` - Individual calendars

### Sensor Entities
- `sensor.apple_calendar_events_today` - Today's event count
- `sensor.apple_calendar_events_tomorrow` - Tomorrow's event count  
- `sensor.apple_calendar_events_this_week` - This week's event count
- `sensor.apple_calendar_next_event` - Next upcoming event

## 🛠️ Services

### `apple_calendar_7day.refresh_calendar`
Manually refresh calendar data.

```yaml
service: apple_calendar_7day.refresh_calendar
data:
  entity_id: calendar.apple_calendar_all
```

### `apple_calendar_7day.create_event`
Create a new event in Apple Calendar.

```yaml
service: apple_calendar_7day.create_event
data:
  calendar_id: "calendar-id"
  title: "Meeting with Team"
  start_datetime: "2025-01-15T10:00:00"
  end_datetime: "2025-01-15T11:00:00"
  description: "Weekly team sync"
  location: "Conference Room A"
```

## 🤖 Automation Examples

### Daily Morning Briefing

```yaml
- alias: "Morning Calendar Briefing"
  trigger:
    - platform: time
      at: "08:00:00"
  condition:
    - condition: numeric_state
      entity_id: sensor.apple_calendar_events_today
      above: 0
  action:
    - service: notify.persistent_notification
      data:
        title: "📅 Today's Schedule"
        message: >
          You have {{ states('sensor.apple_calendar_events_today') }} events today:
          {% for event in state_attr('sensor.apple_calendar_events_today', 'events') %}
          • {{ event.start }} - {{ event.summary }}{% if event.location %} ({{ event.location }}){% endif %}
          {% endfor %}
```

### Event Reminders

```yaml
- alias: "Event Reminder"
  trigger:
    - platform: calendar
      entity_id: calendar.apple_calendar_all
      event: start
      offset: "-0:15:00"
  action:
    - service: notify.mobile_app
      data:
        title: "📅 Event Starting Soon"
        message: "{{ trigger.calendar_event.summary }} starts in 15 minutes"
```

## 🎨 Card Configuration

### Basic Configuration

```yaml
type: custom:apple-calendar-7day-card
entity: calendar.apple_calendar_all
name: "Apple Calendar"
```

### Advanced Configuration

```yaml
type: custom:apple-calendar-7day-card
entity: calendar.apple_calendar_all
name: "My Schedule"
show_description: true
show_location: true
show_time: true
compact_mode: false
max_events_per_day: 5
theme: "auto"
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | **Required** | Calendar entity ID |
| `name` | string | "Apple Calendar" | Card title |
| `show_description` | boolean | `true` | Show event descriptions |
| `show_location` | boolean | `true` | Show event locations |
| `show_time` | boolean | `true` | Show event times |
| `compact_mode` | boolean | `false` | Compact layout mode |
| `max_events_per_day` | number | `5` | Max events per day |
| `theme` | string | `"auto"` | Color theme |

## 🔧 Troubleshooting

### Common Issues

#### 1. Authentication Failed
- **Cause**: Invalid App-Specific Password
- **Solution**: 
  - Generate a new App-Specific Password
  - Ensure 2FA is enabled on Apple ID
  - Use your full Apple ID email as username

#### 2. No Events Showing
- **Cause**: Calendar permissions or sync issues
- **Solution**:
  - Check calendar sharing settings
  - Verify calendar is not hidden
  - Wait up to 15 minutes for initial sync

#### 3. Card Not Loading
- **Cause**: Frontend card not registered
- **Solution**:
  - Clear browser cache
  - Ensure `apple-calendar-7day-card.js` is in `/www/` folder
  - Check browser console for errors

### Debug Steps

1. **Check Entity States**
   - Go to **Developer Tools** → **States**
   - Search for `calendar.apple_calendar`
   - Verify entities exist and have data

2. **Test Services**
   - Go to **Developer Tools** → **Services**
   - Test `apple_calendar_7day.refresh_calendar`
   - Check logs for errors

3. **Enable Debug Logging**
   ```yaml
   logger:
     default: info
     logs:
       custom_components.apple_calendar_7day: debug
   ```

## 📋 Requirements

- Home Assistant 2024.1.0 or newer
- Apple ID with Two-Factor Authentication
- iCloud Calendar access
- App-Specific Password

## 🔒 Security & Privacy

- Uses secure CalDAV protocol
- App-Specific Passwords (not main password)
- Local data processing
- No third-party services
- Encrypted communication

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [Home Assistant Community](https://community.home-assistant.io)
- **Documentation**: This README and inline code comments

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Calendar creation/deletion
- [ ] Recurring event management
- [ ] Advanced filtering options
- [ ] Export/import functionality
- [ ] Integration with other calendar services

---

**Enjoy your beautifully integrated Apple Calendar experience! 📅✨**