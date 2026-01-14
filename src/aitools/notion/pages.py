"""Notion page and block operations.

Generic operations for Notion pages and blocks.
"""

from typing import Optional

from .auth import make_request


def get_page(page_id: str) -> dict:
    """Get a Notion page by ID.

    Args:
        page_id: The Notion page ID

    Returns:
        Page object with properties
    """
    return make_request("GET", f"/pages/{page_id}")


def get_blocks(
    page_id: str,
    max_blocks: int = 1000,
) -> list[dict]:
    """Get all blocks from a page.

    Handles pagination automatically for large pages.

    Args:
        page_id: The Notion page or block ID
        max_blocks: Maximum blocks to retrieve

    Returns:
        List of block objects
    """
    blocks = []
    cursor = None

    while len(blocks) < max_blocks:
        params = {"page_size": min(100, max_blocks - len(blocks))}
        if cursor:
            params["start_cursor"] = cursor

        response = make_request(
            "GET",
            f"/blocks/{page_id}/children",
            params=params,
        )

        blocks.extend(response.get("results", []))

        if not response.get("has_more"):
            break

        cursor = response.get("next_cursor")

    return blocks


def get_block(block_id: str) -> dict:
    """Get a single block by ID.

    Args:
        block_id: The Notion block ID

    Returns:
        Block object
    """
    return make_request("GET", f"/blocks/{block_id}")


def append_blocks(
    page_id: str,
    blocks: list[dict],
    after: Optional[str] = None,
) -> list[dict]:
    """Append blocks to a page.

    Args:
        page_id: The Notion page or block ID to append to
        blocks: List of block objects to append
        after: Optional block ID to insert after

    Returns:
        List of created block objects
    """
    body = {"children": blocks}
    if after:
        body["after"] = after

    response = make_request(
        "PATCH",
        f"/blocks/{page_id}/children",
        json=body,
    )

    return response.get("results", [])


def update_block(block_id: str, updates: dict) -> dict:
    """Update a block.

    Args:
        block_id: The Notion block ID
        updates: Block updates (type-specific content)

    Returns:
        Updated block object
    """
    return make_request(
        "PATCH",
        f"/blocks/{block_id}",
        json=updates,
    )


def delete_block(block_id: str) -> bool:
    """Delete (archive) a block.

    Args:
        block_id: The Notion block ID

    Returns:
        True if deleted successfully
    """
    make_request("DELETE", f"/blocks/{block_id}")
    return True


def search(
    query: str,
    filter_type: Optional[str] = None,
    max_results: int = 100,
) -> list[dict]:
    """Search for pages and databases.

    Args:
        query: Search query
        filter_type: Filter by type ("page" or "database")
        max_results: Maximum results to return

    Returns:
        List of search results
    """
    body = {
        "query": query,
        "page_size": min(max_results, 100),
    }

    if filter_type:
        body["filter"] = {
            "property": "object",
            "value": filter_type,
        }

    response = make_request("POST", "/search", json=body)
    return response.get("results", [])


# Block creation helpers

def create_paragraph_block(text: str) -> dict:
    """Create a paragraph block.

    Args:
        text: Paragraph text content

    Returns:
        Block object for appending
    """
    return {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def create_heading_block(text: str, level: int = 2) -> dict:
    """Create a heading block.

    Args:
        text: Heading text
        level: Heading level (1, 2, or 3)

    Returns:
        Block object for appending
    """
    heading_type = f"heading_{level}"
    return {
        "type": heading_type,
        heading_type: {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def create_bulleted_list_item(text: str) -> dict:
    """Create a bulleted list item block.

    Args:
        text: List item text

    Returns:
        Block object for appending
    """
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def create_todo_block(text: str, checked: bool = False) -> dict:
    """Create a to-do block.

    Args:
        text: To-do text
        checked: Whether checked

    Returns:
        Block object for appending
    """
    return {
        "type": "to_do",
        "to_do": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "checked": checked,
        }
    }


def create_toggle_block(text: str, children: list[dict] = None) -> dict:
    """Create a toggle block.

    Args:
        text: Toggle header text
        children: Optional list of child blocks

    Returns:
        Block object for appending
    """
    block = {
        "type": "toggle",
        "toggle": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }
    if children:
        block["toggle"]["children"] = children
    return block


def create_numbered_list_item(text: str) -> dict:
    """Create a numbered list item block.

    Args:
        text: List item text

    Returns:
        Block object for appending
    """
    return {
        "type": "numbered_list_item",
        "numbered_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        }
    }


def create_divider_block() -> dict:
    """Create a divider block.

    Returns:
        Block object for appending
    """
    return {"type": "divider", "divider": {}}
