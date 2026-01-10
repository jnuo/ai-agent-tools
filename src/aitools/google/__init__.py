"""Google API integrations (Calendar, Gmail)."""

from .auth import (
    get_credentials,
    get_calendar_service,
    get_gmail_service,
    clear_credentials,
)
from .calendar import (
    list_events,
    get_event,
    create_event,
    update_event,
    delete_event,
    list_calendars,
)
from .gmail import (
    list_emails,
    read_email,
    create_draft,
    list_drafts,
    delete_draft,
    list_labels,
    search_emails,
)

__all__ = [
    # Auth
    "get_credentials",
    "get_calendar_service",
    "get_gmail_service",
    "clear_credentials",
    # Calendar
    "list_events",
    "get_event",
    "create_event",
    "update_event",
    "delete_event",
    "list_calendars",
    # Gmail
    "list_emails",
    "read_email",
    "create_draft",
    "list_drafts",
    "delete_draft",
    "list_labels",
    "search_emails",
]
