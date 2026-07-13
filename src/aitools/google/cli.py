"""CLI for Google Workspace tools."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import click
from dateutil import parser as dateparser
from googleapiclient.errors import HttpError

from . import calendar as gcal
from . import gmail
from . import youtube as yt
from .auth import clear_credentials
from ..config import get_timezone


@click.group()
def google():
    """Google Workspace operations (Calendar, Gmail, YouTube)."""
    pass


# =============================================================================
# CALENDAR COMMANDS
# =============================================================================


@google.group()
def calendar():
    """Calendar operations."""
    pass


@calendar.command("list")
@click.option("--days", "-d", default=7, help="Days to look ahead")
@click.option("--max", "-n", "max_results", default=20, help="Max events")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def calendar_list(days: int, max_results: int, as_json: bool):
    """List upcoming calendar events."""
    events = gcal.list_events(days=days, max_results=max_results)

    if as_json:
        click.echo(json.dumps(events, indent=2, default=str))
        return

    if not events:
        click.echo("No upcoming events.")
        return

    click.echo(f"\n📅 Next {days} days ({len(events)} events):\n")
    for event in events:
        _print_event(event)


@calendar.command("get")
@click.argument("event_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def calendar_get(event_id: str, as_json: bool):
    """Get a single event by ID."""
    event = gcal.get_event(event_id)

    if as_json:
        click.echo(json.dumps(event, indent=2, default=str))
    else:
        _print_event(event, verbose=True)


@calendar.command("create")
@click.argument("title")
@click.option("--start", "-s", required=True, help="Start time (e.g., 'tomorrow 2pm')")
@click.option("--duration", "-d", default=60, help="Duration in minutes")
@click.option("--end", "-e", help="End time (overrides duration)")
@click.option("--desc", help="Description")
@click.option("--location", "-l", help="Location")
def calendar_create(title: str, start: str, duration: int, end: str, desc: str, location: str):
    """Create a new calendar event."""
    tz = ZoneInfo(get_timezone())
    start_dt = dateparser.parse(start)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz)

    if end:
        end_dt = dateparser.parse(end)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=tz)
    else:
        end_dt = start_dt + timedelta(minutes=duration)

    event = gcal.create_event(
        title=title,
        start=start_dt,
        end=end_dt,
        description=desc or "",
        location=location or "",
    )

    click.echo(f"Created: {event['title']}")
    click.echo(f"   ID: {event['id']}")
    click.echo(f"   Link: {event['link']}")


@calendar.command("delete")
@click.argument("event_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def calendar_delete(event_id: str, yes: bool):
    """Delete a calendar event."""
    if not yes:
        click.confirm("Are you sure you want to delete this event?", abort=True)
    gcal.delete_event(event_id)
    click.echo(f"Deleted event {event_id}")


@calendar.command("calendars")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def calendar_list_calendars(as_json: bool):
    """List all accessible calendars."""
    calendars = gcal.list_calendars()

    if as_json:
        click.echo(json.dumps(calendars, indent=2))
        return

    click.echo("\nCalendars:\n")
    for cal in calendars:
        primary = " (primary)" if cal["primary"] else ""
        click.echo(f"  - {cal['name']}{primary}")
        click.echo(f"    ID: {cal['id']}")


def _print_event(event: dict, verbose: bool = False):
    """Print formatted event."""
    start = event["start"]
    if event["all_day"]:
        time_str = f"All day ({start})"
    else:
        dt = dateparser.parse(start)
        time_str = dt.strftime("%a %b %d, %H:%M")

    click.echo(f"  - {event['title']}")
    click.echo(f"    {time_str}")

    if verbose or event.get("location"):
        if event.get("location"):
            click.echo(f"    Location: {event['location']}")
    if verbose and event.get("description"):
        click.echo(f"    Note: {event['description'][:100]}...")
    if verbose:
        click.echo(f"    Link: {event['link']}")
        click.echo(f"    ID: {event['id']}")

    click.echo()


# =============================================================================
# GMAIL COMMANDS
# =============================================================================


@google.group()
def mail():
    """Gmail operations."""
    pass


@mail.command("list")
@click.option("--max", "-n", "max_results", default=10, help="Max emails")
@click.option("--label", "-l", default="INBOX", help="Label to filter")
@click.option("--query", "-q", default="", help="Search query")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_list(max_results: int, label: str, query: str, as_json: bool):
    """List recent emails."""
    emails = gmail.list_emails(max_results=max_results, label=label, query=query)

    if as_json:
        click.echo(json.dumps(emails, indent=2))
        return

    if not emails:
        click.echo("No emails found.")
        return

    click.echo(f"\nRecent emails ({len(emails)}):\n")
    for email in emails:
        _print_email(email)


@mail.command("read")
@click.argument("message_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_read(message_id: str, as_json: bool):
    """Read a full email."""
    email = gmail.read_email(message_id)

    if as_json:
        click.echo(json.dumps(email, indent=2))
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"From: {email['from']}")
    click.echo(f"To: {email['to']}")
    click.echo(f"Subject: {email['subject']}")
    click.echo(f"Date: {email['date']}")
    click.echo(f"{'='*60}\n")
    click.echo(email.get("body", "(No body)"))


@mail.command("draft")
@click.argument("subject")
@click.option("--to", "-t", required=True, help="Recipient email")
@click.option("--body", "-b", default="", help="Email body")
@click.option("--cc", default="", help="CC recipients")
@click.option("--reply-to", "-r", "reply_to", default="", help="Message ID to reply to (creates threaded reply)")
def mail_draft(subject: str, to: str, body: str, cc: str, reply_to: str):
    """Create an email draft (does NOT send)."""
    draft = gmail.create_draft(to=to, subject=subject, body=body, cc=cc, reply_to_message_id=reply_to)

    click.echo(f"Draft created")
    click.echo(f"   To: {draft['to']}")
    click.echo(f"   Subject: {draft['subject']}")
    click.echo(f"   Draft ID: {draft['id']}")
    if draft.get("thread_id"):
        click.echo(f"   Thread ID: {draft['thread_id']} (reply)")
    click.echo("\n   Open Gmail to review and send")


@mail.command("drafts")
@click.option("--max", "-n", "max_results", default=10, help="Max drafts")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_drafts(max_results: int, as_json: bool):
    """List email drafts."""
    drafts = gmail.list_drafts(max_results=max_results)

    if as_json:
        click.echo(json.dumps(drafts, indent=2))
        return

    if not drafts:
        click.echo("No drafts found.")
        return

    click.echo(f"\nDrafts ({len(drafts)}):\n")
    for draft in drafts:
        click.echo(f"  - {draft['subject']}")
        click.echo(f"    To: {draft['to']}")
        click.echo(f"    ID: {draft['draft_id']}")
        click.echo()


@mail.command("search")
@click.argument("query")
@click.option("--max", "-n", "max_results", default=10, help="Max results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_search(query: str, max_results: int, as_json: bool):
    """Search emails (Gmail query syntax)."""
    emails = gmail.search_emails(query=query, max_results=max_results)

    if as_json:
        click.echo(json.dumps(emails, indent=2))
        return

    if not emails:
        click.echo("No emails found.")
        return

    click.echo(f"\nSearch results for '{query}' ({len(emails)}):\n")
    for email in emails:
        _print_email(email)


@mail.command("labels")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_labels(as_json: bool):
    """List Gmail labels."""
    labels = gmail.list_labels()

    if as_json:
        click.echo(json.dumps(labels, indent=2))
        return

    click.echo("\nLabels:\n")
    for label in labels:
        click.echo(f"  - {label['name']} ({label['type']})")


@mail.group("label")
def mail_label():
    """Label management."""
    pass


@mail_label.command("create")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_label_create(name: str, as_json: bool):
    """Create a new Gmail label."""
    result = gmail.create_label(name)

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    click.echo(f"Label created: {result['name']}")
    click.echo(f"   ID: {result['id']}")


@mail.command("modify")
@click.argument("message_id")
@click.option("--add-label", multiple=True, help="Label ID to add")
@click.option("--remove-label", multiple=True, help="Label ID to remove")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_modify(message_id: str, add_label: tuple, remove_label: tuple, as_json: bool):
    """Modify labels on a message."""
    result = gmail.modify_message(
        message_id=message_id,
        add_labels=list(add_label) if add_label else None,
        remove_labels=list(remove_label) if remove_label else None,
    )

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    click.echo(f"Modified message {result['message_id']}")
    if result["labels_added"]:
        click.echo(f"   Added: {', '.join(result['labels_added'])}")
    if result["labels_removed"]:
        click.echo(f"   Removed: {', '.join(result['labels_removed'])}")


@mail.command("archive")
@click.argument("message_ids", nargs=-1, required=True)
def mail_archive(message_ids: tuple):
    """Archive messages (remove from inbox)."""
    ids = list(message_ids)
    result = gmail.batch_modify_messages(
        message_ids=ids,
        remove_labels=["INBOX"],
    )

    click.echo(f"Archived {result['modified_count']} message(s)")


@mail.command("trash")
@click.argument("message_id")
def mail_trash(message_id: str):
    """Move a message to trash."""
    gmail.trash_message(message_id)
    click.echo(f"Trashed message {message_id}")


@mail.command("batch-modify")
@click.option("--ids", required=True, help="Comma-separated message IDs")
@click.option("--add-label", multiple=True, help="Label ID to add")
@click.option("--remove-label", multiple=True, help="Label ID to remove")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mail_batch_modify(ids: str, add_label: tuple, remove_label: tuple, as_json: bool):
    """Batch modify labels on multiple messages."""
    message_ids = [id.strip() for id in ids.split(",")]
    result = gmail.batch_modify_messages(
        message_ids=message_ids,
        add_labels=list(add_label) if add_label else None,
        remove_labels=list(remove_label) if remove_label else None,
    )

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    click.echo(f"Modified {result['modified_count']} message(s)")
    if result["labels_added"]:
        click.echo(f"   Added: {', '.join(result['labels_added'])}")
    if result["labels_removed"]:
        click.echo(f"   Removed: {', '.join(result['labels_removed'])}")


def _print_email(email: dict):
    """Print formatted email summary."""
    click.echo(f"  - {email['subject']}")
    click.echo(f"    From: {email['from']}")
    click.echo(f"    Date: {email['date']}")
    if email.get("snippet"):
        snippet = email["snippet"][:80] + "..." if len(email["snippet"]) > 80 else email["snippet"]
        click.echo(f"    {snippet}")
    click.echo(f"    ID: {email['id']}")
    click.echo()


# =============================================================================
# YOUTUBE COMMANDS
# =============================================================================


@google.group()
def youtube():
    """YouTube operations (channel comments, video upload).

    Uses its own OAuth token (token_youtube.json), because the YouTube channel
    is typically owned by a different Google account than Calendar/Gmail. The
    first command opens a browser once — sign in as the CHANNEL OWNER.

    All commands act on the channel the cached token owns. To work with a second
    channel (e.g. a different product or a work account), pass --account NAME —
    each name gets its own token file and its own consent.
    """
    pass


def _fail(message: str):
    """Print an actionable error and exit non-zero (no traceback)."""
    raise click.ClickException(message)


def _run_youtube(fn):
    """Run a YouTube call, turning the known API failures into readable errors."""
    try:
        return fn()
    except yt.ScopeError as err:
        _fail(str(err))
    except (FileNotFoundError, ValueError) as err:
        _fail(str(err))
    except LookupError as err:
        _fail(str(err))
    except ConnectionError as err:
        _fail(
            f"Upload interrupted: {err}\n"
            "The transfer is resumable — just re-run the same command."
        )
    except HttpError as err:
        status = err.resp.status
        reason = str(err)

        if status == 403 and "has not been used in project" in reason:
            project = reason.split("project ")[1].split(" ")[0].rstrip(".")
            _fail(
                "YouTube Data API v3 is not enabled for this Google Cloud project.\n"
                "Enable it here, wait a minute, then retry:\n"
                f"  https://console.developers.google.com/apis/api/youtube.googleapis.com/overview?project={project}"
            )
        if status == 403 and (
            "quota" in reason.lower() or "uploadLimitExceeded" in reason
        ):
            _fail(
                "YouTube API quota exhausted for today.\n"
                "videos.insert has its own daily bucket (100 uploads/day by default). "
                "Retry tomorrow, or request more quota in the Google Cloud Console."
            )
        if status == 400 and "invalidCategoryId" in reason:
            _fail(
                "Invalid --category-id for this region.\n"
                "Valid ids: https://developers.google.com/youtube/v3/docs/videoCategories/list"
            )
        if status in (401, 403):
            _fail(
                "Not authorized for this channel.\n"
                "The cached token must belong to the CHANNEL OWNER. Re-authenticate with:\n"
                "  aitools google logout --youtube\n"
                f"Raw: {err}"
            )
        _fail(f"YouTube API error (HTTP {status}): {err}")


account_option = click.option(
    "--account",
    default=None,
    help="Named OAuth profile, to use a channel owned by another Google account",
)


@youtube.command("comments")
@click.option("--handle", "-h", required=True, help="Channel handle (e.g. salta_app)")
@click.option("--days", "-d", default=7, help="Only comments from the last N days")
@click.option("--max-videos", "-n", default=25, help="How many recent videos to scan")
@click.option("--unanswered", is_flag=True, help="Only show comments we haven't replied to")
@account_option
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def youtube_comments(
    handle: str,
    days: int,
    max_videos: int,
    unanswered: bool,
    account: str,
    as_json: bool,
):
    """List recent comments across a channel's videos."""
    result = _run_youtube(
        lambda: yt.list_comments(
            handle=handle, days=days, max_videos=max_videos, account=account
        )
    )

    comments = result["comments"]
    if unanswered:
        comments = [c for c in comments if not c["has_response"]]
        result = {**result, "comments": comments, "total": len(comments)}

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return

    click.echo(
        f"@{result['handle']} — {result['total']} comment(s) in the last {days}d "
        f"across {result['videos_scanned']} video(s), "
        f"{result['unanswered']} unanswered"
    )
    click.echo()

    for comment in comments:
        mark = " " if comment["has_response"] else "*"
        click.echo(f"{mark} {comment['author']}: {comment['body']}")
        click.echo(f"    On: {comment['video_title']} ({comment['video_url']})")
        click.echo(f"    Date: {comment['date']}  Likes: {comment['likes']}")
        if comment["has_response"]:
            click.echo(f"    Replied: {comment['response']}")
        click.echo(f"    ID: {comment['id']}")
        click.echo()

    if result.get("videos_with_comments_disabled"):
        disabled = result["videos_with_comments_disabled"]
        click.echo(f"Note: comments disabled on {len(disabled)} video(s).")


@youtube.command("reply")
@click.argument("comment_id")
@click.argument("text")
@account_option
def youtube_reply(comment_id: str, text: str, account: str):
    """Reply to a comment AS THE CHANNEL. Posts immediately."""
    result = _run_youtube(
        lambda: yt.reply_to_comment(comment_id, text, account=account)
    )
    click.echo(f"Replied to {result['parent_comment_id']} (reply {result['reply_id']})")


@youtube.command("upload")
@click.argument("video_path", type=click.Path())
@click.option("--title", "-t", required=True, help="Video title")
@click.option("--description", "-d", default="", help="Video description")
@click.option(
    "--description-file",
    type=click.Path(),
    help="Read the description from a file (for long, multiline text)",
)
@click.option("--tags", default="", help="Comma-separated keyword tags")
@click.option(
    "--privacy",
    type=click.Choice(yt.PRIVACY_STATUSES),
    default="public",
    show_default=True,
    help="public = live for everyone; unlisted = only people with the link "
    "(internal shares); private = only you",
)
@click.option(
    "--category-id",
    default="28",
    show_default=True,
    help="YouTube category id (28 = Science & Technology). See videoCategories.list",
)
@click.option(
    "--made-for-kids/--not-made-for-kids",
    default=False,
    show_default=True,
    help="Self-declared 'made for kids' status",
)
@click.option("--playlist", default=None, help="Add the video to this playlist (name or id)")
@account_option
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def youtube_upload(
    video_path: str,
    title: str,
    description: str,
    description_file: str,
    tags: str,
    privacy: str,
    category_id: str,
    made_for_kids: bool,
    playlist: str,
    account: str,
    as_json: bool,
):
    """Upload a video to the YouTube channel this token owns.

    PUBLISHES IMMEDIATELY at --privacy (default: public). Use --privacy unlisted
    for link-only internal shares, or --privacy private to keep it to yourself.

    The upload is resumable and chunked, so an interrupted transfer can be
    resumed by re-running the same command.

    Quota: videos.insert has had its own daily quota bucket since June 2026 —
    100 uploads/day by default, separate from the 10,000-unit pool the read
    endpoints share. (It used to cost 1600 units of that pool, i.e. ~6/day;
    Google cut that in December 2025.)

    A 9:16 video of 3 minutes or less is classified as a Short by YouTube
    automatically — there is no API flag for it.

    \b
    Examples:
      # Public release video
      aitools google youtube upload out.mp4 --title "v1.27" \\
          --description-file notes.md --tags "release,ai"
    \b
      # Unlisted video, shared by link with colleagues
      aitools google youtube upload demo.mp4 --title "Internal demo" \\
          --privacy unlisted
    """
    if description_file:
        path = Path(description_file).expanduser()
        if not path.exists():
            raise click.ClickException(f"Description file not found: {path}")
        description = path.read_text(encoding="utf-8")

    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    if not as_json:
        click.echo(f"Uploading {video_path} ...")

    def _progress(percent: int):
        if not as_json:
            click.echo(f"  {percent}%", nl=False)
            click.echo("\r", nl=False)

    result = _run_youtube(
        lambda: yt.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tag_list,
            privacy=privacy,
            category_id=category_id,
            made_for_kids=made_for_kids,
            playlist=playlist,
            account=account,
            on_progress=_progress,
        )
    )

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return

    click.echo()
    click.echo(f"Uploaded: {result['title']}")
    click.echo(f"  Video ID: {result['video_id']}")
    click.echo(f"  URL:      {result['url']}")
    click.echo(f"  Privacy:  {result['privacy']}")

    if result.get("playlist_id"):
        click.echo(f"  Playlist: {result['playlist_id']}")
    if result.get("playlist_error"):
        click.echo(f"  Warning:  {result['playlist_error']}")


# =============================================================================
# AUTH COMMANDS
# =============================================================================


@google.command("logout")
@click.option("--youtube", "youtube_token", is_flag=True, help="Clear the YouTube token instead")
@click.option("--account", default=None, help="Named YouTube OAuth profile to clear")
def logout(youtube_token: bool, account: str):
    """Clear stored credentials (re-authenticate on next use)."""
    if account and not youtube_token:
        raise click.ClickException("--account only applies with --youtube.")

    clear_credentials(youtube=youtube_token, account=account)
    click.echo("Logged out. Next command will require re-authentication.")
