"""CLI for Resend operations."""

import json

import click

from . import mail as resend_mail


@click.group()
def resend():
    """Resend email operations (Inbox, Send)."""
    pass


@resend.command("inbox")
@click.option("--limit", "-n", default=20, help="Max emails to return (1-100)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def inbox(limit: int, as_json: bool):
    """List received emails."""
    emails = resend_mail.list_received_emails(limit=limit)

    if as_json:
        click.echo(json.dumps(emails, indent=2))
        return

    if not emails:
        click.echo("No received emails.")
        return

    click.echo(f"\nInbox ({len(emails)}):\n")
    for email in emails:
        _print_email_summary(email)


@resend.command("read")
@click.argument("email_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def read(email_id: str, as_json: bool):
    """Read a received email by ID."""
    email = resend_mail.get_received_email(email_id)

    if as_json:
        click.echo(json.dumps(email, indent=2))
        return

    click.echo(f"\nFrom: {email.get('from', 'Unknown')}")
    click.echo(f"To: {', '.join(email.get('to', []))}")
    if email.get("cc"):
        click.echo(f"CC: {', '.join(email['cc'])}")
    click.echo(f"Subject: {email.get('subject', '(no subject)')}")
    click.echo(f"Date: {email.get('created_at', 'Unknown')}")

    attachments = email.get("attachments", [])
    if attachments:
        click.echo(f"Attachments: {len(attachments)}")
        for att in attachments:
            click.echo(f"  - {att.get('filename', 'unnamed')} ({att.get('content_type', 'unknown')})")

    click.echo(f"\n{'─' * 60}\n")

    # Prefer text, fall back to html
    body = email.get("text") or email.get("html") or "(empty body)"
    click.echo(body)


@resend.command("send")
@click.option("--from", "from_addr", required=True, help="Sender address (e.g., noreply@viziai.app)")
@click.option("--to", required=True, help="Recipient address")
@click.option("--subject", required=True, help="Email subject")
@click.option("--body", required=True, help="Email body (plain text)")
@click.option("--html", is_flag=True, help="Treat body as HTML")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def send(from_addr: str, to: str, subject: str, body: str, html: bool, as_json: bool):
    """Send an email."""
    if html:
        result = resend_mail.send_email(from_addr, to, subject, html=body)
    else:
        result = resend_mail.send_email(from_addr, to, subject, text=body)

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Email sent! ID: {result.get('id', 'unknown')}")


def _print_email_summary(email: dict):
    """Print a formatted email summary line."""
    sender = email.get("from", "Unknown")
    subject = email.get("subject", "(no subject)")
    date = email.get("created_at", "")[:10]  # Just the date part
    email_id = email.get("id", "")

    # Truncate long subjects
    if len(subject) > 50:
        subject = subject[:47] + "..."

    click.echo(f"  {date}  {sender}")
    click.echo(f"    {subject}")
    click.echo(f"    ID: {email_id}")
    click.echo()
