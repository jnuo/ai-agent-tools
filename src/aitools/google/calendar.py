"""Google Calendar operations."""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .auth import get_calendar_service
from ..config import get_timezone


def list_events(
    days: int = 7,
    max_results: int = 50,
    calendar_id: str = "primary",
    timezone: Optional[str] = None,
) -> list[dict]:
    """List upcoming calendar events.

    Args:
        days: Number of days to look ahead
        max_results: Maximum events to return
        calendar_id: Calendar to query (default: primary)
        timezone: Timezone override (uses config default if None)

    Returns:
        List of event dictionaries
    """
    service = get_calendar_service()
    tz = timezone or get_timezone()

    now = datetime.now(ZoneInfo(tz))
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    return [_parse_event(e) for e in events]


def get_event(event_id: str, calendar_id: str = "primary") -> dict:
    """Get a single event by ID.

    Args:
        event_id: The event ID
        calendar_id: Calendar containing the event

    Returns:
        Event dictionary
    """
    service = get_calendar_service()
    event = service.events().get(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()
    return _parse_event(event)


def create_event(
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
    timezone: Optional[str] = None,
) -> dict:
    """Create a new calendar event.

    Args:
        title: Event title/summary
        start: Start datetime
        end: End datetime
        description: Event description
        location: Event location
        calendar_id: Target calendar
        timezone: Timezone override (uses config default if None)

    Returns:
        Created event dictionary
    """
    service = get_calendar_service()
    tz = timezone or get_timezone()

    event_body = {
        "summary": title,
        "start": {"dateTime": start.isoformat(), "timeZone": tz},
        "end": {"dateTime": end.isoformat(), "timeZone": tz},
    }

    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location

    event = service.events().insert(
        calendarId=calendar_id,
        body=event_body,
    ).execute()

    return _parse_event(event)


def update_event(
    event_id: str,
    title: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    calendar_id: str = "primary",
    timezone: Optional[str] = None,
) -> dict:
    """Update an existing event.

    Args:
        event_id: Event to update
        title: New title (if provided)
        start: New start time (if provided)
        end: New end time (if provided)
        description: New description (if provided)
        location: New location (if provided)
        calendar_id: Calendar containing the event
        timezone: Timezone override (uses config default if None)

    Returns:
        Updated event dictionary
    """
    service = get_calendar_service()
    tz = timezone or get_timezone()

    # Get existing event
    event = service.events().get(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()

    # Update fields
    if title is not None:
        event["summary"] = title
    if start is not None:
        event["start"] = {"dateTime": start.isoformat(), "timeZone": tz}
    if end is not None:
        event["end"] = {"dateTime": end.isoformat(), "timeZone": tz}
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location

    updated = service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=event,
    ).execute()

    return _parse_event(updated)


def delete_event(event_id: str, calendar_id: str = "primary") -> bool:
    """Delete an event.

    Args:
        event_id: Event to delete
        calendar_id: Calendar containing the event

    Returns:
        True if deleted successfully
    """
    service = get_calendar_service()
    service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()
    return True


def list_calendars() -> list[dict]:
    """List all accessible calendars.

    Returns:
        List of calendar dictionaries
    """
    service = get_calendar_service()
    result = service.calendarList().list().execute()

    calendars = []
    for cal in result.get("items", []):
        calendars.append({
            "id": cal["id"],
            "name": cal.get("summary", ""),
            "primary": cal.get("primary", False),
            "access_role": cal.get("accessRole", ""),
        })
    return calendars


def _parse_event(event: dict) -> dict:
    """Parse raw event into clean dictionary."""
    start = event.get("start", {})
    end = event.get("end", {})

    return {
        "id": event.get("id"),
        "title": event.get("summary", "(No title)"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "all_day": "date" in start,
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "link": event.get("htmlLink", ""),
        "status": event.get("status", ""),
        "attendees": [
            {"email": a.get("email"), "status": a.get("responseStatus")}
            for a in event.get("attendees", [])
        ],
    }
