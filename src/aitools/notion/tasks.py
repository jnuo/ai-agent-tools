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
