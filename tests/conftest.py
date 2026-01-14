"""Shared pytest fixtures for all tests."""

import pytest
import responses

# Notion API base URL for mocking
NOTION_API_BASE = "https://api.notion.com/v1"


def get_request_body(call) -> str:
    """Get request body as string (handles bytes in Python 3.14+)."""
    body = call.request.body
    if isinstance(body, bytes):
        return body.decode("utf-8")
    return body or ""


@pytest.fixture
def mock_notion_api_key(monkeypatch, tmp_path):
    """Set a fake Notion API key and credentials dir for testing."""
    monkeypatch.setenv("NOTION_API_KEY", "secret_test_key_12345")
    # Point credentials to empty temp dir to avoid reading real .env
    monkeypatch.setenv("AITOOLS_CREDENTIALS_DIR", str(tmp_path))


@pytest.fixture
def notion_api_mock():
    """Context manager for mocking Notion API responses."""
    with responses.RequestsMock() as rsps:
        yield rsps


# Sample Notion API response data

@pytest.fixture
def sample_page_response():
    """Sample Notion page response."""
    return {
        "object": "page",
        "id": "page-id-12345",
        "created_time": "2024-01-15T10:00:00.000Z",
        "last_edited_time": "2024-01-15T12:00:00.000Z",
        "url": "https://www.notion.so/Test-Page-12345",
        "properties": {
            "Task": {
                "type": "title",
                "title": [{"type": "text", "text": {"content": "Test Task"}}]
            },
            "Status": {
                "type": "select",
                "select": {"name": "Todo"}
            },
            "Priority Level": {
                "type": "select",
                "select": {"name": "High"}
            },
            "topic": {
                "type": "select",
                "select": {"name": "work"}
            },
            "due date": {
                "type": "date",
                "date": {"start": "2024-01-20"}
            },
            "URL": {
                "type": "url",
                "url": "https://example.com"
            }
        }
    }


@pytest.fixture
def sample_task():
    """Sample parsed task dictionary."""
    return {
        "id": "page-id-12345",
        "title": "Test Task",
        "status": "Todo",
        "priority": "High",
        "topic": "work",
        "due_date": "2024-01-20",
        "url": "https://example.com",
        "created_time": "2024-01-15T10:00:00.000Z",
        "last_edited_time": "2024-01-15T12:00:00.000Z",
        "notion_url": "https://www.notion.so/Test-Page-12345",
    }


@pytest.fixture
def sample_block_response():
    """Sample Notion block response."""
    return {
        "object": "block",
        "id": "block-id-12345",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "Test paragraph"}}]
        }
    }


@pytest.fixture
def sample_database_query_response(sample_page_response):
    """Sample database query response with pagination."""
    return {
        "object": "list",
        "results": [sample_page_response],
        "has_more": False,
        "next_cursor": None,
    }


@pytest.fixture
def sample_blocks_response(sample_block_response):
    """Sample blocks list response."""
    return {
        "object": "list",
        "results": [sample_block_response],
        "has_more": False,
        "next_cursor": None,
    }


@pytest.fixture
def sample_user_response():
    """Sample bot user response for auth verification."""
    return {
        "object": "user",
        "id": "bot-user-id-12345",
        "type": "bot",
        "name": "Test Integration",
        "bot": {
            "owner": {"type": "workspace", "workspace": True}
        }
    }


# =============================================================================
# Google API Fixtures
# =============================================================================


@pytest.fixture
def sample_calendar_event():
    """Sample Google Calendar event from API."""
    return {
        "id": "event-id-12345",
        "summary": "Team Meeting",
        "start": {"dateTime": "2024-01-15T14:00:00+01:00", "timeZone": "Europe/Amsterdam"},
        "end": {"dateTime": "2024-01-15T15:00:00+01:00", "timeZone": "Europe/Amsterdam"},
        "description": "Weekly sync",
        "location": "Conference Room A",
        "htmlLink": "https://calendar.google.com/event?eid=xxx",
        "status": "confirmed",
        "attendees": [
            {"email": "alice@example.com", "responseStatus": "accepted"},
            {"email": "bob@example.com", "responseStatus": "tentative"},
        ],
    }


@pytest.fixture
def sample_calendar_event_all_day():
    """Sample all-day calendar event."""
    return {
        "id": "event-allday-12345",
        "summary": "Company Holiday",
        "start": {"date": "2024-01-15"},
        "end": {"date": "2024-01-16"},
        "status": "confirmed",
    }


@pytest.fixture
def sample_calendar_list():
    """Sample calendar list response."""
    return {
        "items": [
            {
                "id": "primary",
                "summary": "My Calendar",
                "primary": True,
                "accessRole": "owner",
            },
            {
                "id": "work@group.calendar.google.com",
                "summary": "Work Calendar",
                "primary": False,
                "accessRole": "writer",
            },
        ]
    }


@pytest.fixture
def sample_gmail_message():
    """Sample Gmail message metadata."""
    return {
        "id": "msg-id-12345",
        "threadId": "thread-id-12345",
        "snippet": "This is a preview of the email content...",
        "labelIds": ["INBOX", "UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "me@example.com"},
                {"name": "Subject", "value": "Test Email Subject"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 +0000"},
            ]
        }
    }


@pytest.fixture
def sample_gmail_message_full(sample_gmail_message):
    """Sample Gmail message with full body."""
    import base64
    body_text = "Hello,\n\nThis is the email body.\n\nBest regards"
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()

    msg = sample_gmail_message.copy()
    msg["payload"] = {
        **msg["payload"],
        "body": {"data": encoded_body},
    }
    return msg


@pytest.fixture
def sample_gmail_labels():
    """Sample Gmail labels list."""
    return {
        "labels": [
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "SENT", "name": "SENT", "type": "system"},
            {"id": "Label_1", "name": "Work", "type": "user"},
        ]
    }


@pytest.fixture
def sample_gmail_draft():
    """Sample Gmail draft response."""
    return {
        "id": "draft-id-12345",
        "message": {
            "id": "msg-id-67890",
        }
    }
