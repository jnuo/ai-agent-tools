"""Integration tests for Notion API.

These tests make REAL API calls to Notion.
They require:
- NOTION_API_KEY environment variable
- NOTION_TEST_DATABASE_ID environment variable (a task database for testing)
- NOTION_TEST_PAGE_ID environment variable (a page for testing blocks)

Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import os
import pytest

# Skip all tests in this module if credentials not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("NOTION_API_KEY"),
        reason="NOTION_API_KEY not set"
    ),
]


@pytest.fixture
def test_database_id():
    """Get test database ID from environment."""
    db_id = os.environ.get("NOTION_TEST_DATABASE_ID")
    if not db_id:
        pytest.skip("NOTION_TEST_DATABASE_ID not set")
    return db_id


@pytest.fixture
def test_page_id():
    """Get test page ID from environment."""
    page_id = os.environ.get("NOTION_TEST_PAGE_ID")
    if not page_id:
        pytest.skip("NOTION_TEST_PAGE_ID not set")
    return page_id


class TestNotionConnection:
    """Test basic Notion API connection."""

    def test_verify_connection(self):
        """Should successfully connect to Notion API."""
        from aitools.notion.auth import verify_connection

        result = verify_connection()

        assert result is not None
        assert "id" in result
        print(f"\nConnected as: {result.get('name', 'Unknown')}")


class TestNotionTaskLifecycle:
    """Test full task CRUD lifecycle with real API."""

    def test_create_read_update_delete_task(self, test_database_id):
        """Should create, read, update, and delete a task."""
        from aitools.notion.tasks import (
            create_task,
            get_task,
            update_task,
            delete_task,
        )

        task_id = None

        try:
            # 1. CREATE
            task = create_task(
                database_id=test_database_id,
                title="[TEST] Integration Test Task",
                status="Todo",
                priority="Low",
            )
            task_id = task["id"]

            assert task["title"] == "[TEST] Integration Test Task"
            assert task["status"] == "Todo"
            print(f"\nCreated task: {task_id}")

            # 2. READ
            fetched = get_task(task_id)

            assert fetched["id"] == task_id
            assert fetched["title"] == "[TEST] Integration Test Task"
            print(f"Read task: {fetched['title']}")

            # 3. UPDATE
            updated = update_task(task_id, status="Done", title="[TEST] Updated Task")

            assert updated["status"] == "Done"
            assert updated["title"] == "[TEST] Updated Task"
            print(f"Updated task status to: {updated['status']}")

            # 4. DELETE
            delete_task(task_id)
            print(f"Deleted task: {task_id}")
            task_id = None  # Mark as cleaned up

        finally:
            # Cleanup if test failed mid-way
            if task_id:
                try:
                    from aitools.notion.tasks import delete_task
                    delete_task(task_id)
                    print(f"Cleanup: deleted task {task_id}")
                except Exception:
                    print(f"Warning: failed to cleanup task {task_id}")

    def test_list_tasks_with_filters(self, test_database_id):
        """Should list and filter tasks."""
        from aitools.notion.tasks import list_tasks

        # Just verify the API call works, don't assert on count
        tasks = list_tasks(test_database_id, limit=5)

        assert isinstance(tasks, list)
        print(f"\nFound {len(tasks)} tasks in database")


class TestNotionPageOperations:
    """Test page and block operations with real API."""

    def test_get_page(self, test_page_id):
        """Should fetch a page."""
        from aitools.notion.pages import get_page

        page = get_page(test_page_id)

        assert page is not None
        assert page["id"] == test_page_id
        print(f"\nFetched page: {test_page_id}")

    def test_get_blocks(self, test_page_id):
        """Should fetch blocks from a page."""
        from aitools.notion.pages import get_blocks

        blocks = get_blocks(test_page_id, max_blocks=10)

        assert isinstance(blocks, list)
        print(f"\nFound {len(blocks)} blocks in page")

    def test_append_and_delete_block(self, test_page_id):
        """Should append a block and then delete it."""
        from aitools.notion.pages import (
            append_blocks,
            create_paragraph_block,
            delete_block,
        )

        block_id = None

        try:
            # 1. APPEND
            blocks = [create_paragraph_block("[TEST] Integration test block - safe to delete")]
            result = append_blocks(test_page_id, blocks)

            assert len(result) == 1
            block_id = result[0]["id"]
            print(f"\nAppended block: {block_id}")

            # 2. DELETE
            delete_block(block_id)
            print(f"Deleted block: {block_id}")
            block_id = None

        finally:
            # Cleanup if test failed
            if block_id:
                try:
                    from aitools.notion.pages import delete_block
                    delete_block(block_id)
                    print(f"Cleanup: deleted block {block_id}")
                except Exception:
                    print(f"Warning: failed to cleanup block {block_id}")


class TestNotionSearch:
    """Test search functionality."""

    def test_search(self):
        """Should search for pages."""
        from aitools.notion.pages import search

        # Search for something generic that likely exists
        results = search("test", max_results=5)

        assert isinstance(results, list)
        print(f"\nSearch returned {len(results)} results")
