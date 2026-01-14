"""Tests for Notion pages module."""

import pytest
import responses

from aitools.notion.auth import NOTION_API_BASE
from aitools.notion.pages import (
    append_blocks,
    create_bulleted_list_item,
    create_divider_block,
    create_heading_block,
    create_numbered_list_item,
    create_paragraph_block,
    create_todo_block,
    create_toggle_block,
    delete_block,
    get_block,
    get_blocks,
    get_page,
    search,
    update_block,
)
from tests.conftest import get_request_body


class TestGetPage:
    """Tests for get_page function."""

    @responses.activate
    def test_returns_page_data(self, mock_notion_api_key, sample_page_response):
        """Should fetch and return page data."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/pages/page-id-12345",
            json=sample_page_response,
            status=200,
        )

        result = get_page("page-id-12345")

        assert result["id"] == "page-id-12345"
        assert result["object"] == "page"


class TestGetBlocks:
    """Tests for get_blocks function."""

    @responses.activate
    def test_returns_blocks_list(self, mock_notion_api_key, sample_blocks_response):
        """Should fetch and return blocks."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json=sample_blocks_response,
            status=200,
        )

        result = get_blocks("page-id")

        assert len(result) == 1
        assert result[0]["type"] == "paragraph"

    @responses.activate
    def test_handles_pagination(self, mock_notion_api_key):
        """Should handle paginated responses."""
        # First page
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={
                "results": [{"id": "block-1", "type": "paragraph"}],
                "has_more": True,
                "next_cursor": "cursor-123",
            },
            status=200,
        )
        # Second page
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={
                "results": [{"id": "block-2", "type": "paragraph"}],
                "has_more": False,
                "next_cursor": None,
            },
            status=200,
        )

        result = get_blocks("page-id")

        assert len(result) == 2
        assert result[0]["id"] == "block-1"
        assert result[1]["id"] == "block-2"

    @responses.activate
    def test_respects_max_blocks_limit(self, mock_notion_api_key):
        """Should stop fetching when max_blocks is reached."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={
                "results": [{"id": f"block-{i}"} for i in range(50)],
                "has_more": True,
                "next_cursor": "cursor",
            },
            status=200,
        )

        result = get_blocks("page-id", max_blocks=50)

        assert len(result) == 50
        assert len(responses.calls) == 1  # Should not make second request


class TestGetBlock:
    """Tests for get_block function."""

    @responses.activate
    def test_returns_single_block(self, mock_notion_api_key, sample_block_response):
        """Should fetch and return a single block."""
        responses.add(
            responses.GET,
            f"{NOTION_API_BASE}/blocks/block-id-12345",
            json=sample_block_response,
            status=200,
        )

        result = get_block("block-id-12345")

        assert result["id"] == "block-id-12345"
        assert result["type"] == "paragraph"


class TestAppendBlocks:
    """Tests for append_blocks function."""

    @responses.activate
    def test_appends_blocks_to_page(self, mock_notion_api_key):
        """Should append blocks and return created blocks."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={"results": [{"id": "new-block", "type": "paragraph"}]},
            status=200,
        )

        blocks = [create_paragraph_block("Test")]
        result = append_blocks("page-id", blocks)

        assert len(result) == 1
        assert result[0]["id"] == "new-block"

    @responses.activate
    def test_appends_after_specific_block(self, mock_notion_api_key):
        """Should include 'after' parameter when specified."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/blocks/page-id/children",
            json={"results": []},
            status=200,
        )

        append_blocks("page-id", [create_paragraph_block("Test")], after="block-123")

        request_body = get_request_body(responses.calls[0])
        assert '"after": "block-123"' in request_body


class TestUpdateBlock:
    """Tests for update_block function."""

    @responses.activate
    def test_updates_block(self, mock_notion_api_key):
        """Should update and return block."""
        responses.add(
            responses.PATCH,
            f"{NOTION_API_BASE}/blocks/block-id",
            json={"id": "block-id", "type": "paragraph"},
            status=200,
        )

        result = update_block("block-id", {"paragraph": {"rich_text": []}})

        assert result["id"] == "block-id"


class TestDeleteBlock:
    """Tests for delete_block function."""

    @responses.activate
    def test_deletes_block(self, mock_notion_api_key):
        """Should delete block and return True."""
        responses.add(
            responses.DELETE,
            f"{NOTION_API_BASE}/blocks/block-id",
            body="",
            status=200,
        )

        result = delete_block("block-id")

        assert result is True


class TestSearch:
    """Tests for search function."""

    @responses.activate
    def test_searches_with_query(self, mock_notion_api_key):
        """Should search and return results."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/search",
            json={"results": [{"id": "page-1", "object": "page"}]},
            status=200,
        )

        result = search("test query")

        assert len(result) == 1
        assert result[0]["id"] == "page-1"

    @responses.activate
    def test_filters_by_type(self, mock_notion_api_key):
        """Should include filter when type specified."""
        responses.add(
            responses.POST,
            f"{NOTION_API_BASE}/search",
            json={"results": []},
            status=200,
        )

        search("test", filter_type="database")

        request_body = get_request_body(responses.calls[0])
        assert '"filter"' in request_body
        assert '"value": "database"' in request_body


class TestBlockCreationHelpers:
    """Tests for block creation helper functions."""

    def test_create_paragraph_block(self):
        """Should create valid paragraph block."""
        block = create_paragraph_block("Hello world")

        assert block["type"] == "paragraph"
        assert block["paragraph"]["rich_text"][0]["text"]["content"] == "Hello world"

    def test_create_heading_block_level_2(self):
        """Should create heading_2 block."""
        block = create_heading_block("My Heading", level=2)

        assert block["type"] == "heading_2"
        assert block["heading_2"]["rich_text"][0]["text"]["content"] == "My Heading"

    def test_create_heading_block_level_3(self):
        """Should create heading_3 block."""
        block = create_heading_block("Subheading", level=3)

        assert block["type"] == "heading_3"
        assert block["heading_3"]["rich_text"][0]["text"]["content"] == "Subheading"

    def test_create_bulleted_list_item(self):
        """Should create bulleted list item block."""
        block = create_bulleted_list_item("List item")

        assert block["type"] == "bulleted_list_item"
        assert block["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "List item"

    def test_create_numbered_list_item(self):
        """Should create numbered list item block."""
        block = create_numbered_list_item("Numbered item")

        assert block["type"] == "numbered_list_item"
        assert block["numbered_list_item"]["rich_text"][0]["text"]["content"] == "Numbered item"

    def test_create_todo_block_unchecked(self):
        """Should create unchecked to-do block."""
        block = create_todo_block("Task to do")

        assert block["type"] == "to_do"
        assert block["to_do"]["rich_text"][0]["text"]["content"] == "Task to do"
        assert block["to_do"]["checked"] is False

    def test_create_todo_block_checked(self):
        """Should create checked to-do block."""
        block = create_todo_block("Completed task", checked=True)

        assert block["to_do"]["checked"] is True

    def test_create_toggle_block(self):
        """Should create toggle block."""
        block = create_toggle_block("Toggle header")

        assert block["type"] == "toggle"
        assert block["toggle"]["rich_text"][0]["text"]["content"] == "Toggle header"

    def test_create_toggle_block_with_children(self):
        """Should create toggle block with nested children."""
        child = create_paragraph_block("Nested content")
        block = create_toggle_block("Toggle", children=[child])

        assert block["toggle"]["children"] == [child]

    def test_create_divider_block(self):
        """Should create divider block."""
        block = create_divider_block()

        assert block["type"] == "divider"
        assert block["divider"] == {}
