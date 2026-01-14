"""Integration tests for Notion CLI commands."""

import json

import pytest
import responses
from click.testing import CliRunner

from aitools.notion.auth import NOTION_API_BASE
from aitools.notion.cli import notion
from tests.conftest import get_request_body


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner."""
    return CliRunner()


class TestNotionVerifyCommand:
    """Tests for 'notion verify' command."""

    @responses.activate
    def test_verify_success(self, cli_runner, mock_notion_api_key, sample_user_response):
        """Should show success message on valid connection."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/users/me",
            json=sample_user_response,
            status=200,
        )

        result = cli_runner.invoke(notion, ["verify"])

        assert result.exit_code == 0
        assert "Connection verified!" in result.output
        assert "Test Integration" in result.output

    @responses.activate
    def test_verify_json_output(self, cli_runner, mock_notion_api_key, sample_user_response):
        """Should output JSON when --json flag is used."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/users/me",
            json=sample_user_response,
            status=200,
        )

        result = cli_runner.invoke(notion, ["verify", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["name"] == "Test Integration"

    @responses.activate
    def test_verify_failure(self, cli_runner, mock_notion_api_key):
        """Should show error on auth failure."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/users/me",
            json={"code": "unauthorized"},
            status=401,
        )

        result = cli_runner.invoke(notion, ["verify"])

        assert result.exit_code == 1
        assert "Connection failed" in result.output


class TestTasksListCommand:
    """Tests for 'notion tasks list' command."""

    @responses.activate
    def test_list_tasks(
        self, cli_runner, mock_notion_api_key, sample_database_query_response
    ):
        """Should list tasks from database."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json=sample_database_query_response,
            status=200,
        )

        result = cli_runner.invoke(notion, ["tasks", "list", "db-id"])

        assert result.exit_code == 0
        assert "Test Task" in result.output
        assert "Tasks (1)" in result.output

    @responses.activate
    def test_list_tasks_json(
        self, cli_runner, mock_notion_api_key, sample_database_query_response
    ):
        """Should output JSON when --json flag is used."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json=sample_database_query_response,
            status=200,
        )

        result = cli_runner.invoke(notion, ["tasks", "list", "db-id", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1
        assert output[0]["title"] == "Test Task"

    @responses.activate
    def test_list_tasks_empty(self, cli_runner, mock_notion_api_key):
        """Should show message when no tasks found."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json={"results": []},
            status=200,
        )

        result = cli_runner.invoke(notion, ["tasks", "list", "db-id"])

        assert result.exit_code == 0
        assert "No tasks found" in result.output

    @responses.activate
    def test_list_tasks_with_filters(self, cli_runner, mock_notion_api_key):
        """Should pass filter options to API."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/databases/db-id/query",
            json={"results": []},
            status=200,
        )

        result = cli_runner.invoke(
            notion,
            ["tasks", "list", "db-id", "-s", "Todo", "-p", "High", "-t", "work"],
        )

        assert result.exit_code == 0
        request_body = get_request_body(responses.calls[0])
        assert "Status" in request_body
        assert "Priority Level" in request_body
        assert "topic" in request_body


class TestTasksCreateCommand:
    """Tests for 'notion tasks create' command."""

    @responses.activate
    def test_create_task(self, cli_runner, mock_notion_api_key, sample_page_response):
        """Should create task and show confirmation."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/pages",
            json=sample_page_response,
            status=200,
        )

        result = cli_runner.invoke(
            notion, ["tasks", "create", "db-id", "New Task"]
        )

        assert result.exit_code == 0
        assert "Created task" in result.output

    @responses.activate
    def test_create_task_with_options(
        self, cli_runner, mock_notion_api_key, sample_page_response
    ):
        """Should pass all options to API."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/pages",
            json=sample_page_response,
            status=200,
        )

        result = cli_runner.invoke(
            notion,
            [
                "tasks", "create", "db-id", "Task",
                "-s", "In Progress",
                "-p", "High",
                "-t", "work",
                "-d", "2024-01-20",
                "-u", "https://example.com",
            ],
        )

        assert result.exit_code == 0


class TestPageBlocksCommand:
    """Tests for 'notion page blocks' command."""

    @responses.activate
    def test_list_blocks(self, cli_runner, mock_notion_api_key, sample_blocks_response):
        """Should list blocks from page."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json=sample_blocks_response,
            status=200,
        )

        result = cli_runner.invoke(notion, ["page", "blocks", "page-id"])

        assert result.exit_code == 0
        assert "Blocks (1)" in result.output

    @responses.activate
    def test_list_blocks_json(
        self, cli_runner, mock_notion_api_key, sample_blocks_response
    ):
        """Should output JSON when --json flag is used."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json=sample_blocks_response,
            status=200,
        )

        result = cli_runner.invoke(notion, ["page", "blocks", "page-id", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output) == 1


class TestPageAppendCommand:
    """Tests for 'notion page append' command."""

    @responses.activate
    def test_append_paragraph(self, cli_runner, mock_notion_api_key):
        """Should append paragraph block."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={"results": [{"id": "new-block"}]},
            status=200,
        )

        result = cli_runner.invoke(
            notion, ["page", "append", "page-id", "-x", "Test content"]
        )

        assert result.exit_code == 0
        assert "Appended 1 block(s)" in result.output

    @responses.activate
    def test_append_bullet(self, cli_runner, mock_notion_api_key):
        """Should append bullet block."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={"results": [{"id": "new-block"}]},
            status=200,
        )

        result = cli_runner.invoke(
            notion, ["page", "append", "page-id", "-t", "bullet", "-x", "List item"]
        )

        assert result.exit_code == 0
        request_body = get_request_body(responses.calls[0])
        assert "bulleted_list_item" in request_body

    @responses.activate
    def test_append_divider(self, cli_runner, mock_notion_api_key):
        """Should append divider without text."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={"results": [{"id": "new-block"}]},
            status=200,
        )

        result = cli_runner.invoke(
            notion, ["page", "append", "page-id", "-t", "divider"]
        )

        assert result.exit_code == 0

    def test_append_requires_text_for_non_divider(self, cli_runner, mock_notion_api_key):
        """Should error when text missing for non-divider blocks."""
        result = cli_runner.invoke(
            notion, ["page", "append", "page-id", "-t", "paragraph"]
        )

        assert result.exit_code == 1
        assert "Either --text or --json-blocks is required" in result.output


class TestPageSearchCommand:
    """Tests for 'notion page search' command."""

    @responses.activate
    def test_search(self, cli_runner, mock_notion_api_key):
        """Should search and display results."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/search",
            json={
                "results": [{
                    "id": "page-1",
                    "object": "page",
                    "properties": {
                        "title": {"title": [{"text": {"content": "Found Page"}}]}
                    }
                }]
            },
            status=200,
        )

        result = cli_runner.invoke(notion, ["page", "search", "test query"])

        assert result.exit_code == 0
        assert "Found Page" in result.output

    @responses.activate
    def test_search_no_results(self, cli_runner, mock_notion_api_key):
        """Should show message when no results found."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/search",
            json={"results": []},
            status=200,
        )

        result = cli_runner.invoke(notion, ["page", "search", "nothing"])

        assert result.exit_code == 0
        assert "No results found" in result.output
