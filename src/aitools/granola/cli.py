"""CLI for Granola meeting notes."""

import json

import click

from . import meetings


@click.group()
def granola():
    """Granola meeting notes operations."""
    pass


@granola.command("list")
@click.option("--max", "-n", "max_results", default=20, help="Max meetings to return")
@click.option("--query", "-q", default="", help="Search by title")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def meetings_list(max_results: int, query: str, as_json: bool):
    """List recent meetings."""
    try:
        results = meetings.list_meetings(max_results=max_results, query=query)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(results, indent=2))
        return

    if not results:
        click.echo("No meetings found.")
        return

    click.echo(f"\nMeetings ({len(results)}):\n")
    for m in results:
        transcript_icon = "T" if m["has_transcript"] else "-"
        notes_icon = "N" if m["has_notes"] else "-"
        click.echo(f"  [{transcript_icon}{notes_icon}] {m['title'][:60]}")
        click.echo(f"       {m['created_at'][:10]}")
        click.echo(f"       ID: {m['id']}")
        click.echo()


@granola.command("get")
@click.argument("meeting_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def meeting_get(meeting_id: str, as_json: bool):
    """Get meeting details and notes."""
    try:
        result = meetings.get_meeting(meeting_id)
    except (FileNotFoundError, KeyError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"Title: {result['title']}")
    click.echo(f"Date: {result['created_at'][:10]}")
    click.echo(f"Has transcript: {result['has_transcript']}")
    click.echo(f"{'='*60}\n")

    if result.get("overview"):
        click.echo("Overview:")
        click.echo(result["overview"])
        click.echo()

    if result.get("notes_plain"):
        click.echo("Notes:")
        click.echo(result["notes_plain"])


@granola.command("transcript")
@click.argument("meeting_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--raw", is_flag=True, help="Include raw segments")
def meeting_transcript(meeting_id: str, as_json: bool, raw: bool):
    """Get meeting transcript."""
    try:
        result = meetings.get_transcript(meeting_id)
    except (FileNotFoundError, KeyError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        # Optionally exclude raw segments to reduce output size
        if not raw:
            result.pop("segments", None)
        click.echo(json.dumps(result, indent=2))
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"Transcript: {result['title']}")
    click.echo(f"Date: {result['created_at'][:10]}")
    click.echo(f"Segments: {result['segment_count']}")
    click.echo(f"{'='*60}\n")
    click.echo(result["transcript"])
