"""CLI for Notion operations."""

import json

import click

from . import tasks as notion_tasks
from . import pages as notion_pages
from .auth import verify_connection


@click.group()
def notion():
    """Notion operations (Tasks, Pages)."""
    pass


# =============================================================================
# TASKS COMMANDS
# =============================================================================


@notion.group()
def tasks():
    """Task database operations."""
    pass


@tasks.command("list")
@click.argument("database_id")
@click.option("--status", "-s", help="Filter by status (e.g., Todo, In Progress, Done)")
@click.option("--topic", "-t", help="Filter by topic")
@click.option("--priority", "-p", help="Filter by priority (e.g., High, Medium, Low)")
@click.option("--limit", "-n", default=100, help="Max tasks to return")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tasks_list(database_id: str, status: str, topic: str, priority: str, limit: int, as_json: bool):
    """List tasks from a database."""
    task_list = notion_tasks.list_tasks(
        database_id=database_id,
        status=status,
        topic=topic,
        priority=priority,
        limit=limit,
    )

    if as_json:
        click.echo(json.dumps(task_list, indent=2))
        return

    if not task_list:
        click.echo("No tasks found.")
        return

    click.echo(f"\nTasks ({len(task_list)}):\n")
    for task in task_list:
        _print_task(task)


@tasks.command("get")
@click.argument("task_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tasks_get(task_id: str, as_json: bool):
    """Get a single task by ID."""
    task = notion_tasks.get_task(task_id)

    if as_json:
        click.echo(json.dumps(task, indent=2))
    else:
        _print_task(task, verbose=True)


@tasks.command("create")
@click.argument("database_id")
@click.argument("title")
@click.option("--status", "-s", default="Todo", help="Status (default: Todo)")
@click.option("--priority", "-p", help="Priority level")
@click.option("--topic", "-t", help="Topic/category")
@click.option("--due", "-d", help="Due date (YYYY-MM-DD)")
@click.option("--url", "-u", help="Related URL")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tasks_create(database_id: str, title: str, status: str, priority: str, topic: str, due: str, url: str, as_json: bool):
    """Create a new task."""
    task = notion_tasks.create_task(
        database_id=database_id,
        title=title,
        status=status,
        priority=priority,
        topic=topic,
        due_date=due,
        url=url,
    )

    if as_json:
        click.echo(json.dumps(task, indent=2))
    else:
        click.echo(f"Created task: {task['title']}")
        click.echo(f"   ID: {task['id']}")
        click.echo(f"   Status: {task['status']}")


@tasks.command("update")
@click.argument("task_id")
@click.option("--title", help="New title")
@click.option("--status", "-s", help="New status")
@click.option("--priority", "-p", help="New priority")
@click.option("--topic", "-t", help="New topic")
@click.option("--due", "-d", help="New due date (YYYY-MM-DD)")
@click.option("--url", "-u", help="New URL")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def tasks_update(task_id: str, title: str, status: str, priority: str, topic: str, due: str, url: str, as_json: bool):
    """Update an existing task."""
    task = notion_tasks.update_task(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        topic=topic,
        due_date=due,
        url=url,
    )

    if as_json:
        click.echo(json.dumps(task, indent=2))
    else:
        click.echo(f"Updated task: {task['title']}")
        click.echo(f"   Status: {task['status']}")


@tasks.command("delete")
@click.argument("task_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def tasks_delete(task_id: str, yes: bool):
    """Delete (archive) a task."""
    if not yes:
        click.confirm("Are you sure you want to delete this task?", abort=True)

    notion_tasks.delete_task(task_id)
    click.echo(f"Deleted task {task_id}")


def _print_task(task: dict, verbose: bool = False):
    """Print formatted task."""
    status_icons = {
        "Todo": "[ ]",
        "In Progress": "[~]",
        "Done": "[x]",
    }
    icon = status_icons.get(task.get("status"), "[ ]")

    click.echo(f"  {icon} {task['title']}")

    meta = []
    if task.get("priority"):
        meta.append(f"Priority: {task['priority']}")
    if task.get("topic"):
        meta.append(f"Topic: {task['topic']}")
    if task.get("due_date"):
        meta.append(f"Due: {task['due_date']}")

    if meta:
        click.echo(f"      {' | '.join(meta)}")

    if verbose:
        if task.get("url"):
            click.echo(f"      URL: {task['url']}")
        click.echo(f"      ID: {task['id']}")
        click.echo(f"      Notion: {task.get('notion_url', 'N/A')}")

    click.echo()


# =============================================================================
# PAGE COMMANDS
# =============================================================================


@notion.group()
def page():
    """Page and block operations."""
    pass


@page.command("get")
@click.argument("page_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def page_get(page_id: str, as_json: bool):
    """Get a page by ID."""
    page_data = notion_pages.get_page(page_id)

    if as_json:
        click.echo(json.dumps(page_data, indent=2))
    else:
        click.echo(f"\nPage: {page_id}")
        click.echo(f"URL: {page_data.get('url', 'N/A')}")
        click.echo(f"Created: {page_data.get('created_time')}")
        click.echo(f"Last edited: {page_data.get('last_edited_time')}")


@page.command("blocks")
@click.argument("page_id")
@click.option("--max", "-n", "max_blocks", default=100, help="Max blocks to retrieve")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def page_blocks(page_id: str, max_blocks: int, as_json: bool):
    """Get blocks from a page."""
    blocks = notion_pages.get_blocks(page_id, max_blocks=max_blocks)

    if as_json:
        click.echo(json.dumps(blocks, indent=2))
        return

    if not blocks:
        click.echo("No blocks found.")
        return

    click.echo(f"\nBlocks ({len(blocks)}):\n")
    for block in blocks:
        _print_block(block)


@page.command("search")
@click.argument("query")
@click.option("--type", "-t", "filter_type", type=click.Choice(["page", "database"]), help="Filter by type")
@click.option("--max", "-n", "max_results", default=20, help="Max results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def page_search(query: str, filter_type: str, max_results: int, as_json: bool):
    """Search for pages and databases."""
    results = notion_pages.search(query, filter_type=filter_type, max_results=max_results)

    if as_json:
        click.echo(json.dumps(results, indent=2))
        return

    if not results:
        click.echo("No results found.")
        return

    click.echo(f"\nSearch results for '{query}' ({len(results)}):\n")
    for item in results:
        obj_type = item.get("object", "unknown")
        item_id = item.get("id", "")

        if obj_type == "page":
            props = item.get("properties", {})
            # Try to get title from various property names
            title = "(Untitled)"
            for prop_name in ["title", "Title", "Name", "name"]:
                if prop_name in props:
                    title_arr = props[prop_name].get("title", [])
                    if title_arr:
                        title = title_arr[0].get("text", {}).get("content", "(Untitled)")
                    break

            click.echo(f"  [Page] {title}")
            click.echo(f"    ID: {item_id}")
        elif obj_type == "database":
            title_arr = item.get("title", [])
            title = title_arr[0].get("text", {}).get("content", "(Untitled)") if title_arr else "(Untitled)"
            click.echo(f"  [Database] {title}")
            click.echo(f"    ID: {item_id}")

        click.echo()


@page.command("append")
@click.argument("page_id")
@click.option("--type", "-t", "block_type", type=click.Choice(["paragraph", "heading1", "heading2", "heading3", "bullet", "numbered", "todo", "toggle", "divider"]), default="paragraph", help="Block type")
@click.option("--text", "-x", help="Block text content")
@click.option("--after", "-a", help="Insert after this block ID")
@click.option("--checked", "-c", is_flag=True, help="For todo: mark as checked")
@click.option("--json-blocks", "-j", help="JSON array of blocks to append (advanced)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def page_append(page_id: str, block_type: str, text: str, after: str, checked: bool, json_blocks: str, as_json: bool):
    """Append blocks to a page or block.

    Simple usage: aitools notion page append PAGE_ID --type bullet --text "My item"

    Advanced: aitools notion page append PAGE_ID --json-blocks '[{"type": "paragraph", ...}]'
    """
    if json_blocks:
        try:
            blocks = json.loads(json_blocks)
        except json.JSONDecodeError as e:
            click.echo(f"Invalid JSON: {e}", err=True)
            raise SystemExit(1)
    elif block_type == "divider":
        blocks = [notion_pages.create_divider_block()]
    elif not text:
        click.echo("Either --text or --json-blocks is required (except for divider)", err=True)
        raise SystemExit(1)
    else:
        block_creators = {
            "paragraph": lambda: notion_pages.create_paragraph_block(text),
            "heading1": lambda: notion_pages.create_heading_block(text, level=1),
            "heading2": lambda: notion_pages.create_heading_block(text, level=2),
            "heading3": lambda: notion_pages.create_heading_block(text, level=3),
            "bullet": lambda: notion_pages.create_bulleted_list_item(text),
            "numbered": lambda: notion_pages.create_numbered_list_item(text),
            "todo": lambda: notion_pages.create_todo_block(text, checked=checked),
            "toggle": lambda: notion_pages.create_toggle_block(text),
        }
        blocks = [block_creators[block_type]()]

    result = notion_pages.append_blocks(page_id, blocks, after=after)

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Appended {len(result)} block(s)")
        for block in result:
            click.echo(f"  ID: {block.get('id', 'unknown')}")


@page.command("delete")
@click.argument("block_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def page_delete(block_id: str, yes: bool):
    """Delete (archive) a block."""
    if not yes:
        click.confirm("Are you sure you want to delete this block?", abort=True)

    notion_pages.delete_block(block_id)
    click.echo(f"Deleted block {block_id}")


def _print_block(block: dict):
    """Print a formatted block."""
    block_type = block.get("type", "unknown")
    block_id = block.get("id", "")[:8]

    content = ""
    if block_type == "paragraph":
        rich_text = block.get("paragraph", {}).get("rich_text", [])
        content = "".join(t.get("text", {}).get("content", "") for t in rich_text)
    elif block_type.startswith("heading_"):
        rich_text = block.get(block_type, {}).get("rich_text", [])
        content = "".join(t.get("text", {}).get("content", "") for t in rich_text)
    elif block_type == "bulleted_list_item":
        rich_text = block.get("bulleted_list_item", {}).get("rich_text", [])
        content = "• " + "".join(t.get("text", {}).get("content", "") for t in rich_text)
    elif block_type == "to_do":
        rich_text = block.get("to_do", {}).get("rich_text", [])
        checked = block.get("to_do", {}).get("checked", False)
        icon = "[x]" if checked else "[ ]"
        content = f"{icon} " + "".join(t.get("text", {}).get("content", "") for t in rich_text)
    else:
        content = f"({block_type})"

    # Truncate long content
    if len(content) > 80:
        content = content[:77] + "..."

    click.echo(f"  [{block_id}] {content}")


# =============================================================================
# AUTH COMMANDS
# =============================================================================


@notion.command("verify")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def verify(as_json: bool):
    """Verify Notion API connection."""
    try:
        user = verify_connection()
        if as_json:
            click.echo(json.dumps(user, indent=2))
        else:
            click.echo("Connection verified!")
            click.echo(f"   Bot: {user.get('name', 'Unknown')}")
            click.echo(f"   ID: {user.get('id', 'Unknown')}")
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        raise SystemExit(1)
