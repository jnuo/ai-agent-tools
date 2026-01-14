"""Tests for Google Calendar module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from aitools.google.calendar import (
    _parse_event,
    create_event,
    delete_event,
    get_event,
    list_calendars,
    list_events,
    update_event,
)


class TestParseEvent:
    """Tests for _parse_event internal function."""

    def test_parses_datetime_event(self, sample_calendar_event):
        """Should parse event with dateTime start/end."""
        result = _parse_event(sample_calendar_event)

        assert result["id"] == "event-id-12345"
        assert result["title"] == "Team Meeting"
        assert result["start"] == "2024-01-15T14:00:00+01:00"
        assert result["end"] == "2024-01-15T15:00:00+01:00"
        assert result["all_day"] is False
        assert result["description"] == "Weekly sync"
        assert result["location"] == "Conference Room A"
        assert result["status"] == "confirmed"
        assert len(result["attendees"]) == 2

    def test_parses_all_day_event(self, sample_calendar_event_all_day):
        """Should parse all-day event with date start/end."""
        result = _parse_event(sample_calendar_event_all_day)

        assert result["id"] == "event-allday-12345"
        assert result["title"] == "Company Holiday"
        assert result["start"] == "2024-01-15"
        assert result["end"] == "2024-01-16"
        assert result["all_day"] is True

    def test_handles_missing_fields(self):
        """Should handle events with missing optional fields."""
        minimal_event = {
            "id": "minimal-event",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
        }

        result = _parse_event(minimal_event)

        assert result["title"] == "(No title)"
        assert result["description"] == ""
        assert result["location"] == ""
        assert result["attendees"] == []


class TestListEvents:
    """Tests for list_events function."""

    @patch("aitools.google.calendar.get_calendar_service")
    @patch("aitools.google.calendar.get_timezone")
    def test_lists_events(self, mock_tz, mock_get_service, sample_calendar_event):
        """Should list events and parse them."""
        mock_tz.return_value = "UTC"

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.events().list().execute.return_value = {
            "items": [sample_calendar_event]
        }

        result = list_events(days=7, max_results=10)

        assert len(result) == 1
        assert result[0]["title"] == "Team Meeting"
        mock_service.events().list.assert_called()

    @patch("aitools.google.calendar.get_calendar_service")
    @patch("aitools.google.calendar.get_timezone")
    def test_returns_empty_list_when_no_events(self, mock_tz, mock_get_service):
        """Should return empty list when no events."""
        mock_tz.return_value = "UTC"

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.events().list().execute.return_value = {"items": []}

        result = list_events()

        assert result == []


class TestGetEvent:
    """Tests for get_event function."""

    @patch("aitools.google.calendar.get_calendar_service")
    def test_gets_single_event(self, mock_get_service, sample_calendar_event):
        """Should fetch and parse single event."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.events().get().execute.return_value = sample_calendar_event

        result = get_event("event-id-12345")

        assert result["id"] == "event-id-12345"
        assert result["title"] == "Team Meeting"


class TestCreateEvent:
    """Tests for create_event function."""

    @patch("aitools.google.calendar.get_calendar_service")
    @patch("aitools.google.calendar.get_timezone")
    def test_creates_event(self, mock_tz, mock_get_service, sample_calendar_event):
        """Should create event with provided details."""
        mock_tz.return_value = "Europe/Amsterdam"

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.events().insert().execute.return_value = sample_calendar_event

        start = datetime(2024, 1, 15, 14, 0)
        end = datetime(2024, 1, 15, 15, 0)

        result = create_event(
            title="Team Meeting",
            start=start,
            end=end,
            description="Weekly sync",
            location="Conference Room A",
        )

        assert result["title"] == "Team Meeting"
        mock_service.events().insert.assert_called()

    @patch("aitools.google.calendar.get_calendar_service")
    @patch("aitools.google.calendar.get_timezone")
    def test_creates_minimal_event(self, mock_tz, mock_get_service):
        """Should create event with only required fields."""
        mock_tz.return_value = "UTC"

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.events().insert().execute.return_value = {
            "id": "new-event",
            "summary": "Quick Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T10:30:00Z"},
        }

        start = datetime(2024, 1, 15, 10, 0)
        end = datetime(2024, 1, 15, 10, 30)

        result = create_event(title="Quick Meeting", start=start, end=end)

        assert result["title"] == "Quick Meeting"


class TestUpdateEvent:
    """Tests for update_event function."""

    @patch("aitools.google.calendar.get_calendar_service")
    @patch("aitools.google.calendar.get_timezone")
    def test_updates_event_title(self, mock_tz, mock_get_service, sample_calendar_event):
        """Should update event fields."""
        mock_tz.return_value = "UTC"

        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock get and update
        mock_service.events().get().execute.return_value = sample_calendar_event.copy()
        updated_event = sample_calendar_event.copy()
        updated_event["summary"] = "Updated Meeting"
        mock_service.events().update().execute.return_value = updated_event

        result = update_event("event-id-12345", title="Updated Meeting")

        assert result["title"] == "Updated Meeting"
        mock_service.events().update.assert_called()


class TestDeleteEvent:
    """Tests for delete_event function."""

    @patch("aitools.google.calendar.get_calendar_service")
    def test_deletes_event(self, mock_get_service):
        """Should delete event and return True."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.events().delete().execute.return_value = None

        result = delete_event("event-id-12345")

        assert result is True
        mock_service.events().delete.assert_called()


class TestListCalendars:
    """Tests for list_calendars function."""

    @patch("aitools.google.calendar.get_calendar_service")
    def test_lists_calendars(self, mock_get_service, sample_calendar_list):
        """Should list and parse calendars."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.calendarList().list().execute.return_value = sample_calendar_list

        result = list_calendars()

        assert len(result) == 2
        assert result[0]["id"] == "primary"
        assert result[0]["name"] == "My Calendar"
        assert result[0]["primary"] is True
        assert result[1]["id"] == "work@group.calendar.google.com"
        assert result[1]["primary"] is False
