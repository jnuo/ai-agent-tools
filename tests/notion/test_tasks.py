"""Tests for Notion tasks module."""

import pytest
import responses

from aitools.notion.auth import NOTION_API_BASE
from aitools.notion.tasks import (
    _parse_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)
from tests.conftest import get_request_body


class TestParseTask:
    """Tests for _parse_task internal function."""

    def test_parses_complete_task(self, sample_page_response):
        """Should parse all task fields correctly."""
        result = _parse_task(sample_page_response)

        assert result["id"] == "page-id-12345"
        assert result["title"] == "Test Task"
        assert result["status"] == "Todo"
        assert result["priority"] == "High"
        assert result["topic"] == "work"
        assert result["due_date"] == "2024-01-20"
        assert result["url"] == "https://example.com"
        assert result["notion_url"] == "https://www.notion.so/Test-Page-12345"

    def test_handles_missing_optional_fields(self):
        """Should handle missing optional fields gracefully."""
        minimal_page = {
            "id": "page-id",
            "properties": {
                "Task": {"title": [{"text": {"content": "Minimal Task"}}]},
                "Status": {"select": None},
            }
        }

        result = _parse_task(minimal_page)

        assert result["title"] == "Minimal Task"
        assert result["status"] is None
        assert result["priority"] is None
        assert result["topic"] is None
        assert result["due_date"] is None
        assert result["url"] is None

    def test_handles_empty_title(self):
        """Should handle empty title array."""
        page = {
            "id": "page-id",
            "properties": {
                "Task": {"title": []},
            }
        }

        result = _parse_task(page)

        assert result["title"] == ""


class TestListTasks:
    """Tests for list_tasks function."""

    @responses.activate
    def test_lists_tasks_without_filters(
        self, mock_notion_api_key, sample_database_query_response
    ):
        """Should query database and return parsed tasks."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json=sample_database_query_response,
            status=200,
        )

        result = list_tasks("db-id")

        assert len(result) == 1
        assert result[0]["title"] == "Test Task"

    @responses.activate
    def test_filters_by_status(self, mock_notion_api_key):
        """Should include status filter in query."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json={"results": []},
            status=200,
        )

        list_tasks("db-id", status="In Progress")

        request_body = get_request_body(responses.calls[0])
        assert '"property": "Status"' in request_body
        assert '"equals": "In Progress"' in request_body

    @responses.activate
    def test_filters_by_multiple_conditions(self, mock_notion_api_key):
        """Should combine multiple filters with AND."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json={"results": []},
            status=200,
        )

        list_tasks("db-id", status="Todo", priority="High", topic="work")

        request_body = get_request_body(responses.calls[0])
        assert '"and"' in request_body
        assert '"property": "Status"' in request_body
        assert '"property": "Priority Level"' in request_body
        assert '"property": "topic"' in request_body

    @responses.activate
    def test_respects_limit(self, mock_notion_api_key):
        """Should pass limit as page_size."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json={"results": []},
            status=200,
        )

        list_tasks("db-id", limit=25)

        request_body = get_request_body(responses.calls[0])
        assert '"page_size": 25' in request_body


class TestGetTask:
    """Tests for get_task function."""

    @responses.activate
    def test_gets_and_parses_task(self, mock_notion_api_key, sample_page_response):
        """Should fetch page and return parsed task."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/pages/task-id",
            json=sample_page_response,
            status=200,
        )

        result = get_task("task-id")

        assert result["title"] == "Test Task"
        assert result["status"] == "Todo"


class TestCreateTask:
    """Tests for create_task function."""

    @responses.activate
    def test_creates_minimal_task(self, mock_notion_api_key, sample_page_response):
        """Should create task with title and default status."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/pages",
            json=sample_page_response,
            status=200,
        )

        result = create_task("db-id", "New Task")

        request_body = get_request_body(responses.calls[0])
        assert '"database_id": "db-id"' in request_body
        assert '"content": "New Task"' in request_body
        assert '"name": "Todo"' in request_body  # default status

    @responses.activate
    def test_creates_task_with_all_fields(self, mock_notion_api_key, sample_page_response):
        """Should include all optional fields when provided."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/pages",
            json=sample_page_response,
            status=200,
        )

        create_task(
            database_id="db-id",
            title="Full Task",
            status="In Progress",
            priority="High",
            topic="work",
            due_date="2024-01-20",
            url="https://example.com",
        )

        request_body = get_request_body(responses.calls[0])
        assert '"Priority Level"' in request_body
        assert '"topic"' in request_body
        assert '"due date"' in request_body
        assert '"URL"' in request_body


class TestUpdateTask:
    """Tests for update_task function."""

    @responses.activate
    def test_updates_single_field(self, mock_notion_api_key, sample_page_response):
        """Should update only specified field."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/pages/task-id",
            json=sample_page_response,
            status=200,
        )

        update_task("task-id", status="Done")

        request_body = get_request_body(responses.calls[0])
        assert '"Status"' in request_body
        assert '"name": "Done"' in request_body

    @responses.activate
    def test_updates_multiple_fields(self, mock_notion_api_key, sample_page_response):
        """Should update multiple fields at once."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/pages/task-id",
            json=sample_page_response,
            status=200,
        )

        update_task("task-id", title="Updated", status="Done", priority="Low")

        request_body = get_request_body(responses.calls[0])
        assert '"Task"' in request_body
        assert '"Status"' in request_body
        assert '"Priority Level"' in request_body

    @responses.activate
    def test_clears_due_date_with_empty_string(self, mock_notion_api_key, sample_page_response):
        """Should clear due date when empty string passed."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/pages/task-id",
            json=sample_page_response,
            status=200,
        )

        update_task("task-id", due_date="")

        request_body = get_request_body(responses.calls[0])
        assert '"due date"' in request_body
        assert '"date": null' in request_body

    @responses.activate
    def test_returns_current_task_when_no_updates(
        self, mock_notion_api_key, sample_page_response
    ):
        """Should fetch and return current task when nothing to update."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/pages/task-id",
            json=sample_page_response,
            status=200,
        )

        result = update_task("task-id")

        assert result["title"] == "Test Task"
        assert len(responses.calls) == 1
        assert responses.calls[0].request.method == "GET"


class TestDeleteTask:
    """Tests for delete_task function."""

    @responses.activate
    def test_archives_task(self, mock_notion_api_key):
        """Should archive task by setting archived=True."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/pages/task-id",
            json={"id": "task-id", "archived": True},
            status=200,
        )

        result = delete_task("task-id")

        assert result is True
        request_body = get_request_body(responses.calls[0])
        assert '"archived": true' in request_body
