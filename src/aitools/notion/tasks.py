"""Notion task database operations.

This module provides CRUD operations for Notion task databases.
The database schema is expected to have these properties:
- Task (title): Task name
- Status (select): e.g., Todo, In Progress, Done
- Priority Level (select): e.g., High, Medium, Low
- topic (select): e.g., work, personal
- due date (date): Due date
- URL (url): Related URL
"""

from typing import Optional

from .auth import make_request
from . import pages as notion_pages


def list_tasks(
    database_id: str,
    status: Optional[str] = None,
    topic: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """List tasks from a Notion database.

    Args:
        database_id: The Notion database ID
        status: Filter by status (e.g., "Todo", "In Progress", "Done")
        topic: Filter by topic
        priority: Filter by priority level
        limit: Maximum tasks to return

    Returns:
        List of normalized task dictionaries
    """
    # Build filter conditions
    filters = []

    if status:
        filters.append({
            "property": "Status",
            "select": {"equals": status}
        })

    if topic:
        filters.append({
            "property": "topic",
            "select": {"equals": topic}
        })

    if priority:
        filters.append({
            "property": "Priority Level",
            "select": {"equals": priority}
        })

    # Build request body
    body = {"page_size": min(limit, 100)}

    if filters:
        if len(filters) == 1:
            body["filter"] = filters[0]
        else:
            body["filter"] = {"and": filters}

    # Query database
    response = make_request(
        "POST",
        f"/databases/{database_id}/query",
        json=body,
    )

    tasks = []
    for page in response.get("results", []):
        tasks.append(_parse_task(page))

    return tasks


def get_task(task_id: str) -> dict:
    """Get a single task by page ID.

    Args:
        task_id: The Notion page ID

    Returns:
        Normalized task dictionary
    """
    response = make_request("GET", f"/pages/{task_id}")
    return _parse_task(response)


def create_task(
    database_id: str,
    title: str,
    status: str = "Todo",
    priority: Optional[str] = None,
    topic: Optional[str] = None,
    due_date: Optional[str] = None,
    url: Optional[str] = None,
) -> dict:
    """Create a new task in the database.

    Args:
        database_id: The Notion database ID
        title: Task title
        status: Status value (default: "Todo")
        priority: Priority level (e.g., "High", "Medium", "Low")
        topic: Topic/category
        due_date: Due date in ISO format (YYYY-MM-DD)
        url: Related URL

    Returns:
        Created task dictionary
    """
    properties = {
        "Task": {
            "title": [{"text": {"content": title}}]
        },
        "Status": {
            "select": {"name": status}
        },
    }

    if priority:
        properties["Priority Level"] = {"select": {"name": priority}}

    if topic:
        properties["topic"] = {"select": {"name": topic}}

    if due_date:
        properties["due date"] = {"date": {"start": due_date}}

    if url:
        properties["URL"] = {"url": url}

    response = make_request(
        "POST",
        "/pages",
        json={
            "parent": {"database_id": database_id},
            "properties": properties,
        },
    )

    return _parse_task(response)


def update_task(
    task_id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    topic: Optional[str] = None,
    due_date: Optional[str] = None,
    url: Optional[str] = None,
) -> dict:
    """Update an existing task.

    Args:
        task_id: The Notion page ID
        title: New title (if provided)
        status: New status (if provided)
        priority: New priority (if provided)
        topic: New topic (if provided)
        due_date: New due date in ISO format (if provided)
        url: New URL (if provided)

    Returns:
        Updated task dictionary
    """
    properties = {}

    if title is not None:
        properties["Task"] = {"title": [{"text": {"content": title}}]}

    if status is not None:
        properties["Status"] = {"select": {"name": status}}

    if priority is not None:
        properties["Priority Level"] = {"select": {"name": priority}}

    if topic is not None:
        properties["topic"] = {"select": {"name": topic}}

    if due_date is not None:
        if due_date:
            properties["due date"] = {"date": {"start": due_date}}
        else:
            properties["due date"] = {"date": None}

    if url is not None:
        properties["URL"] = {"url": url if url else None}

    if not properties:
        # Nothing to update, just return current task
        return get_task(task_id)

    response = make_request(
        "PATCH",
        f"/pages/{task_id}",
        json={"properties": properties},
    )

    return _parse_task(response)


def set_task_content(task_id: str, content: str, replace: bool = False) -> list[dict]:
    """Set the body content of a task page.

    Parses simple markdown-like text into Notion blocks:
    - Lines starting with "# " become heading_1
    - Lines starting with "## " become heading_2
    - Lines starting with "### " become heading_3
    - Lines starting with "- " become bulleted list items
    - Lines starting with "1. " (or any digit) become numbered list items
    - Lines that are "---" become dividers
    - Everything else becomes a paragraph
    - Empty lines become empty paragraphs (spacing)

    Args:
        task_id: The Notion page ID
        content: Text content to write (simple markdown)
        replace: If True, delete existing blocks first

    Returns:
        List of created block objects
    """
    if replace:
        existing = notion_pages.get_blocks(task_id)
        for block in existing:
            try:
                notion_pages.delete_block(block["id"])
            except Exception:
                pass

    blocks = _parse_markdown_to_blocks(content)

    # Notion API allows max 100 blocks per request
    results = []
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i + 100]
        results.extend(notion_pages.append_blocks(task_id, chunk))

    return results


def _parse_markdown_to_blocks(content: str) -> list[dict]:
    """Parse simple markdown into Notion block objects."""
    lines = content.split("\n")
    blocks = []

    for line in lines:
        if line.strip() == "---":
            blocks.append(notion_pages.create_divider_block())
        elif line.startswith("### "):
            blocks.append(notion_pages.create_heading_block(line[4:], level=3))
        elif line.startswith("## "):
            blocks.append(notion_pages.create_heading_block(line[3:], level=2))
        elif line.startswith("# "):
            blocks.append(notion_pages.create_heading_block(line[2:], level=1))
        elif line.startswith("- "):
            blocks.append(notion_pages.create_bulleted_list_item(line[2:]))
        elif len(line) >= 3 and line[0].isdigit() and ". " in line[:4]:
            text = line[line.index(". ") + 2:]
            blocks.append(notion_pages.create_numbered_list_item(text))
        elif line.strip() == "":
            blocks.append(notion_pages.create_paragraph_block(""))
        else:
            blocks.append(notion_pages.create_paragraph_block(line))

    return blocks


def delete_task(task_id: str) -> bool:
    """Delete (archive) a task.

    Args:
        task_id: The Notion page ID

    Returns:
        True if deleted successfully
    """
    make_request(
        "PATCH",
        f"/pages/{task_id}",
        json={"archived": True},
    )
    return True


def _parse_task(page: dict) -> dict:
    """Parse a Notion page into a normalized task dict."""
    props = page.get("properties", {})

    # Extract title
    title_prop = props.get("Task", {}).get("title", [])
    title = title_prop[0]["text"]["content"] if title_prop else ""

    # Extract status
    status_prop = props.get("Status", {}).get("select")
    status = status_prop["name"] if status_prop else None

    # Extract priority
    priority_prop = props.get("Priority Level", {}).get("select")
    priority = priority_prop["name"] if priority_prop else None

    # Extract topic
    topic_prop = props.get("topic", {}).get("select")
    topic = topic_prop["name"] if topic_prop else None

    # Extract due date
    due_prop = props.get("due date", {}).get("date")
    due_date = due_prop["start"] if due_prop else None

    # Extract URL
    url = props.get("URL", {}).get("url")

    return {
        "id": page["id"],
        "title": title,
        "status": status,
        "priority": priority,
        "topic": topic,
        "due_date": due_date,
        "url": url,
        "created_time": page.get("created_time"),
        "last_edited_time": page.get("last_edited_time"),
        "notion_url": page.get("url"),
    }
