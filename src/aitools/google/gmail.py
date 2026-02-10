"""Gmail operations."""

import base64
from email.mime.text import MIMEText

from .auth import get_gmail_service


def list_emails(
    max_results: int = 10,
    label: str = "INBOX",
    query: str = "",
) -> list[dict]:
    """List recent emails.

    Args:
        max_results: Maximum emails to return
        label: Label to filter by (INBOX, SENT, etc.)
        query: Gmail search query (e.g., "from:someone@example.com")

    Returns:
        List of email summaries
    """
    service = get_gmail_service()

    # Build query
    q = f"label:{label}" if label else ""
    if query:
        q = f"{q} {query}".strip()

    result = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q=q if q else None,
    ).execute()

    messages = result.get("messages", [])
    emails = []

    for msg in messages:
        # Get message details (metadata only for speed)
        detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        emails.append(_parse_email_summary(detail))

    return emails


def read_email(message_id: str) -> dict:
    """Read full email content.

    Args:
        message_id: The message ID

    Returns:
        Full email dictionary with body
    """
    service = get_gmail_service()

    message = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()

    return _parse_email_full(message)


def create_draft(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
    reply_to_message_id: str = "",
) -> dict:
    """Create an email draft (does NOT send).

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body (plain text)
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
        reply_to_message_id: Message ID to reply to (creates threaded reply)

    Returns:
        Draft info dictionary
    """
    service = get_gmail_service()

    thread_id = None
    original_message_id_header = None

    # If replying, get thread info and Message-ID header from original
    if reply_to_message_id:
        original = service.users().messages().get(
            userId="me",
            id=reply_to_message_id,
            format="metadata",
            metadataHeaders=["Message-ID", "Subject"],
        ).execute()

        thread_id = original.get("threadId")

        # Get Message-ID header for In-Reply-To and References
        for header in original.get("payload", {}).get("headers", []):
            if header["name"] == "Message-ID":
                original_message_id_header = header["value"]
                break

    # Convert plain text to HTML so Gmail handles line wrapping naturally.
    # Split on double-newlines (paragraph breaks) and wrap each in <p> tags.
    paragraphs = body.strip().split("\n\n")
    html_body = "".join(f"<p>{p.replace(chr(10), ' ')}</p>" for p in paragraphs)
    message = MIMEText(html_body, "html")
    message["to"] = to
    message["subject"] = subject

    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc

    # Add threading headers if replying
    if original_message_id_header:
        message["In-Reply-To"] = original_message_id_header
        message["References"] = original_message_id_header

    # Encode
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Create draft body
    draft_body = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    # Create draft
    draft = service.users().drafts().create(
        userId="me",
        body=draft_body,
    ).execute()

    return {
        "id": draft["id"],
        "message_id": draft["message"]["id"],
        "thread_id": thread_id,
        "status": "draft_created",
        "to": to,
        "subject": subject,
    }


def list_drafts(max_results: int = 10) -> list[dict]:
    """List email drafts.

    Args:
        max_results: Maximum drafts to return

    Returns:
        List of draft summaries
    """
    service = get_gmail_service()

    result = service.users().drafts().list(
        userId="me",
        maxResults=max_results,
    ).execute()

    drafts = result.get("drafts", [])
    parsed = []

    for draft in drafts:
        detail = service.users().drafts().get(
            userId="me",
            id=draft["id"],
            format="metadata",
        ).execute()

        msg = detail.get("message", {})
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

        parsed.append({
            "draft_id": draft["id"],
            "message_id": msg.get("id"),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", "(No subject)"),
        })

    return parsed


def delete_draft(draft_id: str) -> bool:
    """Delete a draft.

    Args:
        draft_id: Draft to delete

    Returns:
        True if deleted
    """
    service = get_gmail_service()
    service.users().drafts().delete(
        userId="me",
        id=draft_id,
    ).execute()
    return True


def list_labels() -> list[dict]:
    """List all Gmail labels.

    Returns:
        List of label dictionaries
    """
    service = get_gmail_service()
    result = service.users().labels().list(userId="me").execute()

    labels = []
    for label in result.get("labels", []):
        labels.append({
            "id": label["id"],
            "name": label["name"],
            "type": label.get("type", "user"),
        })
    return labels


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search emails using Gmail query syntax.

    Args:
        query: Gmail search query (e.g., "from:x subject:y has:attachment")
        max_results: Maximum results

    Returns:
        List of matching email summaries
    """
    return list_emails(max_results=max_results, label="", query=query)


def _parse_email_summary(message: dict) -> dict:
    """Parse message into summary dict."""
    headers = {}
    for header in message.get("payload", {}).get("headers", []):
        headers[header["name"]] = header["value"]

    return {
        "id": message["id"],
        "thread_id": message.get("threadId"),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(No subject)"),
        "date": headers.get("Date", ""),
        "snippet": message.get("snippet", ""),
        "labels": message.get("labelIds", []),
    }


def _parse_email_full(message: dict) -> dict:
    """Parse full message with body."""
    summary = _parse_email_summary(message)

    # Extract body
    body = ""
    payload = message.get("payload", {})

    if "body" in payload and payload["body"].get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
            elif part.get("mimeType") == "text/html" and part.get("body", {}).get("data") and not body:
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    summary["body"] = body
    return summary
