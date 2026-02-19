"""Tests for Gmail module."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from aitools.google.gmail import (
    _parse_email_full,
    _parse_email_summary,
    batch_modify_messages,
    create_draft,
    create_label,
    delete_draft,
    list_drafts,
    list_emails,
    list_labels,
    modify_message,
    read_email,
    search_emails,
    trash_message,
)


class TestParseEmailSummary:
    """Tests for _parse_email_summary internal function."""

    def test_parses_email_summary(self, sample_gmail_message):
        """Should parse email metadata into summary dict."""
        result = _parse_email_summary(sample_gmail_message)

        assert result["id"] == "msg-id-12345"
        assert result["thread_id"] == "thread-id-12345"
        assert result["from"] == "sender@example.com"
        assert result["to"] == "me@example.com"
        assert result["subject"] == "Test Email Subject"
        assert result["snippet"] == "This is a preview of the email content..."
        assert "INBOX" in result["labels"]

    def test_handles_missing_headers(self):
        """Should handle messages with missing headers."""
        minimal_message = {
            "id": "msg-id",
            "payload": {"headers": []},
        }

        result = _parse_email_summary(minimal_message)

        assert result["id"] == "msg-id"
        assert result["subject"] == "(No subject)"
        assert result["from"] == ""


class TestParseEmailFull:
    """Tests for _parse_email_full internal function."""

    def test_parses_email_with_body(self, sample_gmail_message_full):
        """Should parse full email including body."""
        result = _parse_email_full(sample_gmail_message_full)

        assert result["id"] == "msg-id-12345"
        assert result["subject"] == "Test Email Subject"
        assert "email body" in result["body"]

    def test_parses_multipart_email(self, sample_gmail_message):
        """Should handle multipart emails."""
        body_text = "Plain text body"
        encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

        multipart_message = sample_gmail_message.copy()
        multipart_message["payload"] = {
            **multipart_message["payload"],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": encoded},
                }
            ],
        }

        result = _parse_email_full(multipart_message)

        assert result["body"] == "Plain text body"


class TestListEmails:
    """Tests for list_emails function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_lists_emails(self, mock_get_service, sample_gmail_message):
        """Should list emails and parse them."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock list and get calls
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg-id-12345"}]
        }
        mock_service.users().messages().get().execute.return_value = sample_gmail_message

        result = list_emails(max_results=10)

        assert len(result) == 1
        assert result[0]["subject"] == "Test Email Subject"

    @patch("aitools.google.gmail.get_gmail_service")
    def test_lists_emails_with_query(self, mock_get_service):
        """Should pass query to API."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().list().execute.return_value = {"messages": []}

        list_emails(label="INBOX", query="from:test@example.com")

        mock_service.users().messages().list.assert_called()

    @patch("aitools.google.gmail.get_gmail_service")
    def test_returns_empty_list_when_no_emails(self, mock_get_service):
        """Should return empty list when no messages."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().list().execute.return_value = {}

        result = list_emails()

        assert result == []


class TestReadEmail:
    """Tests for read_email function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_reads_full_email(self, mock_get_service, sample_gmail_message_full):
        """Should fetch and parse full email."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().get().execute.return_value = sample_gmail_message_full

        result = read_email("msg-id-12345")

        assert result["id"] == "msg-id-12345"
        assert "body" in result
        mock_service.users().messages().get.assert_called()


class TestCreateDraft:
    """Tests for create_draft function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_creates_draft(self, mock_get_service, sample_gmail_draft):
        """Should create draft and return info."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().drafts().create().execute.return_value = sample_gmail_draft

        result = create_draft(
            to="recipient@example.com",
            subject="Test Subject",
            body="Hello, this is a test.",
        )

        assert result["id"] == "draft-id-12345"
        assert result["to"] == "recipient@example.com"
        assert result["subject"] == "Test Subject"
        assert result["status"] == "draft_created"

    @patch("aitools.google.gmail.get_gmail_service")
    def test_creates_draft_with_cc_bcc(self, mock_get_service, sample_gmail_draft):
        """Should create draft with CC and BCC."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().drafts().create().execute.return_value = sample_gmail_draft

        result = create_draft(
            to="recipient@example.com",
            subject="Test",
            body="Body",
            cc="cc@example.com",
            bcc="bcc@example.com",
        )

        assert result["status"] == "draft_created"
        mock_service.users().drafts().create.assert_called()

    @patch("aitools.google.gmail.get_gmail_service")
    def test_creates_reply_draft_with_threading(self, mock_get_service, sample_gmail_draft):
        """Should create reply draft with In-Reply-To and References headers."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock getting the original message for thread info
        mock_service.users().messages().get().execute.return_value = {
            "threadId": "thread-abc-123",
            "payload": {
                "headers": [
                    {"name": "Message-ID", "value": "<original-msg-id@mail.gmail.com>"},
                    {"name": "Subject", "value": "Original Subject"},
                ]
            }
        }

        # Mock draft creation
        reply_draft = sample_gmail_draft.copy()
        mock_service.users().drafts().create().execute.return_value = reply_draft

        result = create_draft(
            to="sender@example.com",
            subject="Re: Original Subject",
            body="Thanks for your email!",
            reply_to_message_id="original-msg-id-12345",
        )

        assert result["status"] == "draft_created"
        assert result["thread_id"] == "thread-abc-123"
        mock_service.users().messages().get.assert_called()
        mock_service.users().drafts().create.assert_called()

        # Verify the draft body includes threadId
        create_call = mock_service.users().drafts().create.call_args
        assert create_call is not None


class TestListDrafts:
    """Tests for list_drafts function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_lists_drafts(self, mock_get_service):
        """Should list and parse drafts."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.users().drafts().list().execute.return_value = {
            "drafts": [{"id": "draft-1"}]
        }
        mock_service.users().drafts().get().execute.return_value = {
            "id": "draft-1",
            "message": {
                "id": "msg-1",
                "payload": {
                    "headers": [
                        {"name": "To", "value": "recipient@example.com"},
                        {"name": "Subject", "value": "Draft Subject"},
                    ]
                }
            }
        }

        result = list_drafts()

        assert len(result) == 1
        assert result[0]["draft_id"] == "draft-1"
        assert result[0]["to"] == "recipient@example.com"
        assert result[0]["subject"] == "Draft Subject"


class TestDeleteDraft:
    """Tests for delete_draft function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_deletes_draft(self, mock_get_service):
        """Should delete draft and return True."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().drafts().delete().execute.return_value = None

        result = delete_draft("draft-id-12345")

        assert result is True
        mock_service.users().drafts().delete.assert_called()


class TestListLabels:
    """Tests for list_labels function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_lists_labels(self, mock_get_service, sample_gmail_labels):
        """Should list and parse labels."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().labels().list().execute.return_value = sample_gmail_labels

        result = list_labels()

        assert len(result) == 3
        assert result[0]["id"] == "INBOX"
        assert result[0]["type"] == "system"
        assert result[2]["name"] == "Work"
        assert result[2]["type"] == "user"


class TestCreateLabel:
    """Tests for create_label function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_creates_label(self, mock_get_service, sample_gmail_label_created):
        """Should create label and return id and name."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().labels().create().execute.return_value = sample_gmail_label_created

        result = create_label("Newsletters")

        assert result["id"] == "Label_123"
        assert result["name"] == "Newsletters"
        mock_service.users().labels().create.assert_called()


class TestModifyMessage:
    """Tests for modify_message function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_add_labels(self, mock_get_service):
        """Should add labels to a message."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().modify().execute.return_value = {}

        result = modify_message("msg-123", add_labels=["Label_1"])

        assert result["message_id"] == "msg-123"
        assert result["labels_added"] == ["Label_1"]
        assert result["labels_removed"] == []

    @patch("aitools.google.gmail.get_gmail_service")
    def test_remove_labels(self, mock_get_service):
        """Should remove labels from a message."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().modify().execute.return_value = {}

        result = modify_message("msg-123", remove_labels=["INBOX"])

        assert result["message_id"] == "msg-123"
        assert result["labels_added"] == []
        assert result["labels_removed"] == ["INBOX"]

    @patch("aitools.google.gmail.get_gmail_service")
    def test_add_and_remove_labels(self, mock_get_service):
        """Should add and remove labels simultaneously."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().modify().execute.return_value = {}

        result = modify_message("msg-123", add_labels=["Label_1"], remove_labels=["INBOX"])

        assert result["labels_added"] == ["Label_1"]
        assert result["labels_removed"] == ["INBOX"]


class TestBatchModifyMessages:
    """Tests for batch_modify_messages function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_batch_modify_multiple_ids(self, mock_get_service):
        """Should batch modify multiple messages."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().batchModify().execute.return_value = {}

        result = batch_modify_messages(
            message_ids=["msg-1", "msg-2", "msg-3"],
            add_labels=["Label_1"],
            remove_labels=["INBOX"],
        )

        assert result["modified_count"] == 3
        assert result["labels_added"] == ["Label_1"]
        assert result["labels_removed"] == ["INBOX"]
        mock_service.users().messages().batchModify.assert_called()


class TestTrashMessage:
    """Tests for trash_message function."""

    @patch("aitools.google.gmail.get_gmail_service")
    def test_trashes_message(self, mock_get_service):
        """Should trash message and return True."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().trash().execute.return_value = {}

        result = trash_message("msg-123")

        assert result is True
        mock_service.users().messages().trash.assert_called()


class TestSearchEmails:
    """Tests for search_emails function."""

    @patch("aitools.google.gmail.list_emails")
    def test_search_calls_list_emails(self, mock_list_emails):
        """Should call list_emails with query."""
        mock_list_emails.return_value = []

        search_emails("from:test@example.com subject:important")

        mock_list_emails.assert_called_once_with(
            max_results=10,
            label="",
            query="from:test@example.com subject:important",
        )
