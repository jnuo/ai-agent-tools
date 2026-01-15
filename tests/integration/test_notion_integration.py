"""Integration tests for Notion API.

These tests make REAL API calls to Notion.
They require:
- NOTION_API_KEY environment variable (or credentials/notion/.env file)

Test resources (database, page) are created automatically and cleaned up after tests.

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


@pytest.fixture(scope="module")
def test_resources():
    """Create test database and page, clean up after all tests.

    This fixture:
    1. Searches for any accessible page to use as parent
    2. Creates a test database with task schema
    3. Creates a test page for block operations
    4. Yields the IDs to tests
    5. Cleans up everything after tests complete
    """
    from aitools.notion.pages import (
        search,
        create_database,
        create_page,
        delete_page,
        delete_database,
    )

    created_resources = []

    try:
        # Find a parent page (search for any page we have access to)
        results = search("", filter_type="page", max_results=1)
        if not results:
            pytest.skip("No accessible pages found in Notion workspace")

        parent_page_id = results[0]["id"]
        print(f"\nUsing parent page: {parent_page_id}")

        # Create test database
        database = create_database(
            parent_page_id,
            "[TEST] Integration Test Database - Safe to Delete"
        )
        database_id = database["id"]
        created_resources.append(("database", database_id))
        print(f"Created test database: {database_id}")

        # Create test page for block operations
        page = create_page(
            parent_page_id,
            "[TEST] Integration Test Page - Safe to Delete"
        )
        page_id = page["id"]
        created_resources.append(("page", page_id))
        print(f"Created test page: {page_id}")

        yield {"database_id": database_id, "page_id": page_id}

    finally:
        # Cleanup: delete all created resources in reverse order
        for resource_type, resource_id in reversed(created_resources):
            try:
                if resource_type == "database":
                    delete_database(resource_id)
                else:
                    delete_page(resource_id)
                print(f"Cleaned up {resource_type}: {resource_id}")
            except Exception as e:
                print(f"Warning: failed to cleanup {resource_type} {resource_id}: {e}")


@pytest.fixture
def test_database_id(test_resources):
    """Get test database ID."""
    return test_resources["database_id"]


@pytest.fixture
def test_page_id(test_resources):
    """Get test page ID."""
    return test_resources["page_id"]


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
