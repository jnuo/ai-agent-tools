"""Integration tests for Google APIs.

These tests make REAL API calls to Google Calendar and Gmail.
They require:
- credentials/google/token.json (OAuth token from previous auth)

Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from aitools.config import get_google_credentials_dir


def google_credentials_exist():
    """Check if Google credentials are available."""
    token_file = get_google_credentials_dir() / "token.json"
    return token_file.exists()


# Skip all tests if no Google credentials
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not google_credentials_exist(),
        reason="Google credentials not found (run 'aitools google calendar list' first to authenticate)"
    ),
]


class TestGoogleCalendarConnection:
    """Test Google Calendar API connection."""

    def test_calendar_service_connects(self):
        """Should successfully build calendar service."""
        from aitools.google.auth import get_calendar_service

        service = get_calendar_service()

        assert service is not None
        print("\nCalendar service connected successfully")

    def test_list_calendars(self):
        """Should list available calendars."""
        from aitools.google.calendar import list_calendars

        calendars = list_calendars()

        assert isinstance(calendars, list)
        assert len(calendars) > 0  # At least primary calendar
        print(f"\nFound {len(calendars)} calendars:")
        for cal in calendars[:3]:
            print(f"  - {cal['name']} {'(primary)' if cal.get('primary') else ''}")

    def test_list_events(self):
        """Should list upcoming events."""
        from aitools.google.calendar import list_events

        events = list_events(days=7, max_results=5)

        assert isinstance(events, list)
        print(f"\nFound {len(events)} events in next 7 days")
        for event in events[:3]:
            print(f"  - {event['title']} @ {event['start']}")


class TestGoogleCalendarEventLifecycle:
    """Test creating and deleting calendar events."""

    def test_create_and_delete_event(self):
        """Should create an event and then delete it."""
        from aitools.google.calendar import create_event, delete_event, get_event

        event_id = None

        try:
            # Create event 1 hour from now
            start = datetime.now() + timedelta(hours=1)
            end = start + timedelta(minutes=30)

            # 1. CREATE
            event = create_event(
                title="[TEST] Integration Test Event - Safe to Delete",
                start=start,
                end=end,
                description="Created by pytest integration test",
            )
            event_id = event["id"]

            assert event["title"] == "[TEST] Integration Test Event - Safe to Delete"
            print(f"\nCreated event: {event_id}")

            # 2. READ
            fetched = get_event(event_id)
            assert fetched["id"] == event_id
            print(f"Verified event exists")

            # 3. DELETE
            delete_event(event_id)
            print(f"Deleted event: {event_id}")
            event_id = None

        finally:
            # Cleanup if test failed
            if event_id:
                try:
                    from aitools.google.calendar import delete_event
                    delete_event(event_id)
                    print(f"Cleanup: deleted event {event_id}")
                except Exception:
                    print(f"Warning: failed to cleanup event {event_id}")


class TestGmailConnection:
    """Test Gmail API connection."""

    def test_gmail_service_connects(self):
        """Should successfully build Gmail service."""
        from aitools.google.auth import get_gmail_service

        service = get_gmail_service()

        assert service is not None
        print("\nGmail service connected successfully")

    def test_list_labels(self):
        """Should list Gmail labels."""
        from aitools.google.gmail import list_labels

        labels = list_labels()

        assert isinstance(labels, list)
        assert len(labels) > 0  # At least system labels
        print(f"\nFound {len(labels)} labels:")
        for label in labels[:5]:
            print(f"  - {label['name']} ({label['type']})")

    def test_list_emails(self):
        """Should list recent emails."""
        from aitools.google.gmail import list_emails

        emails = list_emails(max_results=5, label="INBOX")

        assert isinstance(emails, list)
        print(f"\nFound {len(emails)} emails in INBOX")
        for email in emails[:3]:
            print(f"  - {email['subject'][:50]}... from {email['from'][:30]}")


class TestGmailDraftLifecycle:
    """Test creating and deleting Gmail drafts."""

    def test_create_and_delete_draft(self):
        """Should create a draft and then delete it."""
        from aitools.google.gmail import create_draft, delete_draft, list_drafts

        draft_id = None

        try:
            # 1. CREATE DRAFT
            draft = create_draft(
                to="test@example.com",
                subject="[TEST] Integration Test Draft - Safe to Delete",
                body="This is a test draft created by pytest.\nIt should be automatically deleted.",
            )
            draft_id = draft["id"]

            assert draft["status"] == "draft_created"
            print(f"\nCreated draft: {draft_id}")

            # 2. VERIFY IT EXISTS
            drafts = list_drafts(max_results=10)
            draft_ids = [d["draft_id"] for d in drafts]
            assert draft_id in draft_ids
            print(f"Verified draft exists in drafts list")

            # 3. DELETE
            delete_draft(draft_id)
            print(f"Deleted draft: {draft_id}")
            draft_id = None

        finally:
            # Cleanup if test failed
            if draft_id:
                try:
                    from aitools.google.gmail import delete_draft
                    delete_draft(draft_id)
                    print(f"Cleanup: deleted draft {draft_id}")
                except Exception:
                    print(f"Warning: failed to cleanup draft {draft_id}")
