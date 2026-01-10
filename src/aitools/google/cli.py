"""CLI for Google Workspace tools."""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import click
from dateutil import parser as dateparser

from . import calendar as gcal
from . import gmail
from .auth import clear_credentials
from ..config import get_timezone


@click.group()
def google():
    """Google Workspace operations (Calendar, Gmail)."""
    pass


# =============================================================================
# CALENDAR COMMANDS
# =============================================================================


@google.group()
def calendar():
    """Calendar operations."""
    pass


@calendar.command("list")
@click.option("--days", "-d", default=7, help="Days to look ahead")
@click.option("--max", "-n", "max_results", default=20, help="Max events")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def calendar_list(days: int, max_results: int, as_json: bool):
    """List upcoming calendar events."""
    events = gcal.list_events(days=days, max_results=max_results)

    if as_json:
        click.echo(json.dumps(events, indent=2, default=str))
        return

    if not events:
        click.echo("No upcoming events.")
        return

    click.echo(f"\n📅 Next {days} days ({len(events)} events):\n")
    for event in events:
        _print_event(event)


@calendar.command("get")
@click.argument("event_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def calendar_get(event_id: str, as_json: bool):
    """Get a single event by ID."""
    event = gcal.get_event(event_id)

    if as_json:
        click.echo(json.dumps(event, indent=2, default=str))
    else:
        _print_event(event, verbose=True)


@calendar.command("create")
@click.argument("title")
@click.option("--start", "-s", required=True, help="Start time (e.g., 'tomorrow 2pm')")
@click.option("--duration", "-d", default=60, help="Duration in minutes")
@click.option("--end", "-e", help="End time (overrides duration)")
@click.option("--desc", help="Description")
@click.option("--location", "-l", help="Location")
def calendar_create(title: str, start: str, duration: int, end: str, desc: str, location: str):
    """Create a new calendar event."""
    tz = ZoneInfo(get_timezone())
    start_dt = dateparser.parse(start)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz)

    if end:
        end_dt = dateparser.parse(end)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=tz)
    else:
        end_dt = start_dt + timedelta(minutes=duration)

    event = gcal.create_event(
        title=title,
        start=start_dt,
        end=end_dt,
        description=desc or "",
        location=location or "",
    )

    click.echo(f"Created: {event['title']}")
    click.echo(f"   ID: {event['id']}")
    click.echo(f"   Link: {event['link']}")


@calendar.command("delete")
@click.argument("event_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def calendar_delete(event_id: str, yes: bool):
    """Delete a calendar event."""
    if not yes:
        click.confirm("Are you sure you want to delete this event?", abort=True)
    gcal.delete_event(event_id)
    click.echo(f"Deleted event {event_id}")


@calendar.command("calendars")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def calendar_list_calendars(as_json: bool):
    """List all accessible calendars."""
    calendars = gcal.list_calendars()

    if as_json:
        click.echo(json.dumps(calendars, indent=2))
        return

    click.echo("\nCalendars:\n")
    for cal in calendars:
        primary = " (primary)" if cal["primary"] else ""
        click.echo(f"  - {cal['name']}{primary}")
        click.echo(f"    ID: {cal['id']}")


def _print_event(event: dict, verbose: bool = False):
    """Print formatted event."""
    start = event["start"]
    if event["all_day"]:
        time_str = f"All day ({start})"
    else:
        dt = dateparser.parse(start)
        time_str = dt.strftime("%a %b %d, %H:%M")

    click.echo(f"  - {event['title']}")
    click.echo(f"    {time_str}")

    if verbose or event.get("location"):
        if event.get("location"):
            click.echo(f"    Location: {event['location']}")
    if verbose and event.get("description"):
        click.echo(f"    Note: {event['description'][:100]}...")
    if verbose:
        click.echo(f"    Link: {event['link']}")
        click.echo(f"    ID: {event['id']}")

    click.echo()


# =============================================================================
# GMAIL COMMANDS
# =============================================================================


@google.group()
def mail():
    """Gmail operations."""
    pass


@mail.command("list")
@click.option("--max", "-n", "max_results", default=10, help="Max emails")
@click.option("--label", "-l", default="INBOX", help="Label to filter")
@click.option("--query", "-q", default="", help="Search query")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_list(max_results: int, label: str, query: str, as_json: bool):
    """List recent emails."""
    emails = gmail.list_emails(max_results=max_results, label=label, query=query)

    if as_json:
        click.echo(json.dumps(emails, indent=2))
        return

    if not emails:
        click.echo("No emails found.")
        return

    click.echo(f"\nRecent emails ({len(emails)}):\n")
    for email in emails:
        _print_email(email)


@mail.command("read")
@click.argument("message_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_read(message_id: str, as_json: bool):
    """Read a full email."""
    email = gmail.read_email(message_id)

    if as_json:
        click.echo(json.dumps(email, indent=2))
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"From: {email['from']}")
    click.echo(f"To: {email['to']}")
    click.echo(f"Subject: {email['subject']}")
    click.echo(f"Date: {email['date']}")
    click.echo(f"{'='*60}\n")
    click.echo(email.get("body", "(No body)"))


@mail.command("draft")
@click.argument("subject")
@click.option("--to", "-t", required=True, help="Recipient email")
@click.option("--body", "-b", default="", help="Email body")
@click.option("--cc", default="", help="CC recipients")
def mail_draft(subject: str, to: str, body: str, cc: str):
    """Create an email draft (does NOT send)."""
    draft = gmail.create_draft(to=to, subject=subject, body=body, cc=cc)

    click.echo(f"Draft created")
    click.echo(f"   To: {draft['to']}")
    click.echo(f"   Subject: {draft['subject']}")
    click.echo(f"   Draft ID: {draft['id']}")
    click.echo("\n   Open Gmail to review and send")


@mail.command("drafts")
@click.option("--max", "-n", "max_results", default=10, help="Max drafts")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_drafts(max_results: int, as_json: bool):
    """List email drafts."""
    drafts = gmail.list_drafts(max_results=max_results)

    if as_json:
        click.echo(json.dumps(drafts, indent=2))
        return

    if not drafts:
        click.echo("No drafts found.")
        return

    click.echo(f"\nDrafts ({len(drafts)}):\n")
    for draft in drafts:
        click.echo(f"  - {draft['subject']}")
        click.echo(f"    To: {draft['to']}")
        click.echo(f"    ID: {draft['draft_id']}")
        click.echo()


@mail.command("search")
@click.argument("query")
@click.option("--max", "-n", "max_results", default=10, help="Max results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_search(query: str, max_results: int, as_json: bool):
    """Search emails (Gmail query syntax)."""
    emails = gmail.search_emails(query=query, max_results=max_results)

    if as_json:
        click.echo(json.dumps(emails, indent=2))
        return

    if not emails:
        click.echo("No emails found.")
        return

    click.echo(f"\nSearch results for '{query}' ({len(emails)}):\n")
    for email in emails:
        _print_email(email)


@mail.command("labels")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_labels(as_json: bool):
    """List Gmail labels."""
    labels = gmail.list_labels()

    if as_json:
        click.echo(json.dumps(labels, indent=2))
        return

    click.echo("\nLabels:\n")
    for label in labels:
        click.echo(f"  - {label['name']} ({label['type']})")


def _print_email(email: dict):
    """Print formatted email summary."""
    click.echo(f"  - {email['subject']}")
    click.echo(f"    From: {email['from']}")
    click.echo(f"    Date: {email['date']}")
    if email.get("snippet"):
        snippet = email["snippet"][:80] + "..." if len(email["snippet"]) > 80 else email["snippet"]
        click.echo(f"    {snippet}")
    click.echo(f"    ID: {email['id']}")
    click.echo()


# =============================================================================
# AUTH COMMANDS
# =============================================================================


@google.command("logout")
def logout():
    """Clear stored credentials (re-authenticate on next use)."""
    clear_credentials()
    click.echo("Logged out. Next command will require re-authentication.")
