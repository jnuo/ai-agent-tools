"""Resend email operations."""

from typing import Optional

from .auth import make_request


def list_received_emails(limit: int = 20) -> list[dict]:
    """List received emails.

    Args:
        limit: Max emails to return (1-100, default 20)

    Returns:
        List of email dicts
    """
    params = {"limit": min(limit, 100)}
    result = make_request("GET", "/emails/receiving", params=params)
    return result.get("data", [])


def get_received_email(email_id: str) -> dict:
    """Get a single received email with full body.

    Args:
        email_id: The email ID

    Returns:
        Full email dict with html/text body
    """
    return make_request("GET", f"/emails/receiving/{email_id}")


def send_email(
    from_addr: str,
    to: str | list[str],
    subject: str,
    html: Optional[str] = None,
    text: Optional[str] = None,
) -> dict:
    """Send an email.

    Args:
        from_addr: Sender address (e.g., "noreply@viziai.app")
        to: Recipient(s)
        subject: Email subject
        html: HTML body
        text: Plain text body

    Returns:
        Send result dict with email ID
    """
    if isinstance(to, str):
        to = [to]

    payload = {
        "from": from_addr,
        "to": to,
        "subject": subject,
    }
    if html:
        payload["html"] = html
    if text:
        payload["text"] = text

    return make_request("POST", "/emails", json=payload)
