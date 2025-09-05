/**
 * Apple Calendar 7-Day Card
 * A custom Lovelace card for displaying Apple Calendar events in a 7-day view
 */

class AppleCalendar7DayCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = {};
  }

  static getConfigElement() {
    return document.createElement('apple-calendar-7day-card-editor');
  }

  static getStubConfig() {
    return {
      entity: 'calendar.apple_calendar_all',
      name: 'Apple Calendar 7-Day View',
      show_description: true,
      show_location: true,
      show_time: true,
      compact_mode: false,
      max_events_per_day: 5,
      theme: 'auto'
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity');
    }
    this._config = { ...this.constructor.getStubConfig(), ...config };
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return this._config.compact_mode ? 4 : 6;
  }

  render() {
    if (!this._hass || !this._config.entity) return;

    const entity = this._hass.states[this._config.entity];
    if (!entity) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="card-content">
            <div class="error">Entity ${this._config.entity} not found</div>
          </div>
        </ha-card>
      `;
      return;
    }

    const events = entity.attributes.events || [];
    const dailyCounts = entity.attributes.daily_counts || {};
    
    // Get next 7 days
    const today = new Date();
    const days = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      days.push(date);
    }

    // Organize events by day
    const eventsByDay = this.organizeEventsByDay(events, days);

    this.shadowRoot.innerHTML = `
      ${this.getStyles()}
      <ha-card class="apple-calendar-card ${this._config.compact_mode ? 'compact' : ''}">
        <div class="card-header">
          <div class="header-content">
            <div class="title">${this._config.name || 'Apple Calendar'}</div>
            <div class="subtitle">Next 7 days • ${events.length} events</div>
          </div>
          <ha-icon-button class="refresh-button" @click="${this.refreshCalendar}">
            <ha-icon icon="mdi:refresh"></ha-icon>
          </ha-icon-button>
        </div>
        
        <div class="card-content">
          <div class="days-container">
            ${days.map(day => this.renderDay(day, eventsByDay[this.formatDate(day)] || [])).join('')}
          </div>
        </div>
      </ha-card>
    `;
  }

  organizeEventsByDay(events, days) {
    const eventsByDay = {};
    
    days.forEach(day => {
      eventsByDay[this.formatDate(day)] = [];
    });

    events.forEach(event => {
      const eventDate = new Date(event.start);
      const dayKey = this.formatDate(eventDate);
      
      if (eventsByDay[dayKey]) {
        eventsByDay[dayKey].push(event);
      }
    });

    // Sort events within each day by time
    Object.keys(eventsByDay).forEach(day => {
      eventsByDay[day].sort((a, b) => new Date(a.start) - new Date(b.start));
      
      // Limit events per day if configured
      if (this._config.max_events_per_day) {
        eventsByDay[day] = eventsByDay[day].slice(0, this._config.max_events_per_day);
      }
    });

    return eventsByDay;
  }

  renderDay(date, events) {
    const isToday = this.isToday(date);
    const dayName = date.toLocaleDateString('en-US', { weekday: 'long' });
    const dayDate = date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric' 
    });

    return `
      <div class="day-section ${isToday ? 'today' : ''}">
        <div class="day-header">
          <div class="day-info">
            <div class="day-name">${dayName}</div>
            <div class="day-date">${dayDate}</div>
          </div>
          <div class="event-count">${events.length}</div>
        </div>
        
        <div class="events-list">
          ${events.length > 0 
            ? events.map(event => this.renderEvent(event)).join('')
            : '<div class="no-events">No events</div>'
          }
        </div>
      </div>
    `;
  }

  renderEvent(event) {
    const startTime = new Date(event.start);
    const endTime = new Date(event.end);
    const isAllDay = event.all_day || false;
    
    const timeStr = isAllDay 
      ? 'All day' 
      : this.formatTime(startTime) + (endTime ? ' - ' + this.formatTime(endTime) : '');

    return `
      <div class="event-item ${isAllDay ? 'all-day' : ''}" 
           @click="${() => this.showEventDetails(event)}">
        ${this._config.show_time ? `<div class="event-time">${timeStr}</div>` : ''}
        <div class="event-summary">${event.summary || 'Untitled Event'}</div>
        ${this._config.show_location && event.location ? 
          `<div class="event-location">
            <ha-icon icon="mdi:map-marker"></ha-icon>
            ${event.location}
          </div>` : ''
        }
        ${this._config.show_description && event.description ? 
          `<div class="event-description">${event.description}</div>` : ''
        }
        <div class="event-calendar">${event.calendar || 'Unknown'}</div>
      </div>
    `;
  }

  showEventDetails(event) {
    this._hass.callService('browser_mod', 'popup', {
      title: event.summary,
      content: {
        type: 'markdown',
        content: `
**Time:** ${this.formatDateTime(new Date(event.start))}${event.end ? ' - ' + this.formatDateTime(new Date(event.end)) : ''}
${event.location ? `\n**Location:** ${event.location}` : ''}
${event.description ? `\n**Description:** ${event.description}` : ''}
${event.calendar ? `\n**Calendar:** ${event.calendar}` : ''}
        `
      }
    });
  }

  refreshCalendar() {
    this._hass.callService('apple_calendar_7day', 'refresh_calendar', {
      entity_id: this._config.entity
    });
  }

  formatDate(date) {
    return date.toISOString().split('T')[0];
  }

  formatTime(date) {
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  }

  formatDateTime(date) {
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  }

  isToday(date) {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }

  getStyles() {
    return `
      <style>
        .apple-calendar-card {
          --primary-color: #007AFF;
          --secondary-color: #34C759;
          --warning-color: #FF9500;
          --error-color: #FF3B30;
          --background-color: var(--card-background-color, #ffffff);
          --text-primary: var(--primary-text-color, #000000);
          --text-secondary: var(--secondary-text-color, #666666);
          --border-color: var(--divider-color, #e0e0e0);
        }

        .apple-calendar-card.compact {
          --card-padding: 12px;
          --day-spacing: 8px;
          --event-padding: 8px;
        }

        ha-card {
          overflow: hidden;
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
          color: white;
        }

        .header-content .title {
          font-size: 1.3em;
          font-weight: 600;
          margin-bottom: 2px;
        }

        .header-content .subtitle {
          font-size: 0.9em;
          opacity: 0.9;
        }

        .refresh-button {
          --mdc-icon-button-size: 36px;
          --mdc-icon-size: 20px;
          color: white;
        }

        .card-content {
          padding: var(--card-padding, 16px);
        }

        .days-container {
          display: flex;
          flex-direction: column;
          gap: var(--day-spacing, 16px);
        }

        .day-section {
          border-left: 3px solid var(--border-color);
          padding-left: 12px;
          transition: border-color 0.3s ease;
        }

        .day-section.today {
          border-left-color: var(--primary-color);
        }

        .day-section.today .day-name {
          color: var(--primary-color);
          font-weight: 600;
        }

        .day-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .day-info {
          display: flex;
          align-items: baseline;
          gap: 8px;
        }

        .day-name {
          font-size: 1.1em;
          font-weight: 500;
          color: var(--text-primary);
        }

        .day-date {
          font-size: 0.9em;
          color: var(--text-secondary);
        }

        .event-count {
          background: var(--primary-color);
          color: white;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.8em;
          font-weight: 500;
          min-width: 20px;
          text-align: center;
        }

        .events-list {
          margin-left: 8px;
        }

        .event-item {
          background: var(--background-color);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          padding: var(--event-padding, 12px);
          margin-bottom: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
          border-left: 4px solid var(--primary-color);
        }

        .event-item:hover {
          background: var(--secondary-background-color, #f5f5f5);
          border-color: var(--primary-color);
          transform: translateX(2px);
        }

        .event-item.all-day {
          border-left-color: var(--secondary-color);
        }

        .event-time {
          font-size: 0.85em;
          color: var(--primary-color);
          font-weight: 500;
          margin-bottom: 4px;
        }

        .event-summary {
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 4px;
          line-height: 1.3;
        }

        .event-location {
          font-size: 0.8em;
          color: var(--text-secondary);
          display: flex;
          align-items: center;
          gap: 4px;
          margin-bottom: 4px;
        }

        .event-location ha-icon {
          --mdc-icon-size: 14px;
        }

        .event-description {
          font-size: 0.8em;
          color: var(--text-secondary);
          margin-bottom: 4px;
          font-style: italic;
          line-height: 1.2;
        }

        .event-calendar {
          font-size: 0.75em;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .no-events {
          color: var(--text-secondary);
          font-style: italic;
          text-align: center;
          padding: 16px 0;
        }

        .error {
          color: var(--error-color);
          text-align: center;
          padding: 16px;
          font-style: italic;
        }

        /* Compact mode styles */
        .compact .card-header {
          padding: 12px;
        }

        .compact .header-content .title {
          font-size: 1.1em;
        }

        .compact .day-name {
          font-size: 1em;
        }

        .compact .event-item {
          padding: 8px;
          margin-bottom: 6px;
        }

        .compact .event-summary {
          font-size: 0.9em;
        }

        .compact .no-events {
          padding: 12px 0;
        }

        /* Responsive design */
        @media (max-width: 768px) {
          .card-header {
            padding: 12px;
          }

          .card-content {
            padding: 12px;
          }

          .day-info {
            flex-direction: column;
            gap: 2px;
          }

          .event-item {
            padding: 10px;
          }
        }
      </style>
    `;
  }
}

// Register the card
customElements.define('apple-calendar-7day-card', AppleCalendar7DayCard);

// Add to custom cards registry
window.customCards = window.customCards || [];
window.customCards.push({
  type: "apple-calendar-7day-card",
  name: "Apple Calendar 7-Day Card",
  description: "Display Apple Calendar events in a beautiful 7-day view",
  preview: true,
});

console.info(
  `%c APPLE-CALENDAR-7DAY-CARD %c v1.0.0 `,
  'color: white; background: #007AFF; font-weight: 700;',
  'color: #007AFF; background: white; font-weight: 700;'
);