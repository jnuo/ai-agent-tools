"""YouTube operations (channel comments: read and reply; video upload)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .auth import (
    YOUTUBE_UPLOAD_SCOPES,
    get_youtube_credentials,
    get_youtube_service,
)

PRIVACY_STATUSES = ("public", "private", "unlisted")

# Container formats YouTube accepts. Checked locally so a wrong file fails
# instantly instead of after uploading tens of megabytes.
# https://support.google.com/youtube/troubleshooter/2888402
SUPPORTED_FORMATS = frozenset(
    {
        ".mov",
        ".mpeg4",
        ".mp4",
        ".avi",
        ".wmv",
        ".mpegps",
        ".flv",
        ".3gpp",
        ".3gp",
        ".webm",
        ".mkv",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".hevc",
    }
)

# Upload in 5 MB chunks so progress is reported and an interrupted transfer
# resumes from the last chunk instead of restarting.
CHUNK_SIZE = 5 * 1024 * 1024

# Per-chunk retries with exponential backoff, handled by googleapiclient.
NUM_RETRIES = 5


class ScopeError(Exception):
    """The cached OAuth token lacks a scope the requested operation needs."""


def _resolve_channel(service, handle: str) -> tuple[str, str]:
    """Resolve an @handle to (channel_id, uploads_playlist_id).

    Args:
        service: Authenticated YouTube service
        handle: Channel handle, with or without the leading '@'

    Returns:
        Tuple of (channel_id, uploads_playlist_id)

    Raises:
        LookupError: If no channel exists for the handle
    """
    result = (
        service.channels()
        .list(part="id,contentDetails", forHandle=handle.lstrip("@"))
        .execute()
    )

    items = result.get("items", [])
    if not items:
        raise LookupError(f"No YouTube channel found for handle @{handle.lstrip('@')}")

    channel = items[0]
    return channel["id"], channel["contentDetails"]["relatedPlaylists"]["uploads"]


def _list_videos(service, uploads_playlist: str, max_videos: int) -> list[dict]:
    """List the most recent videos on a channel's uploads playlist."""
    videos: list[dict] = []
    page_token = None

    while len(videos) < max_videos:
        result = (
            service.playlistItems()
            .list(
                part="contentDetails,snippet",
                playlistId=uploads_playlist,
                maxResults=min(50, max_videos - len(videos)),
                pageToken=page_token,
            )
            .execute()
        )

        for item in result.get("items", []):
            videos.append(
                {
                    "id": item["contentDetails"]["videoId"],
                    "title": item["snippet"].get("title", ""),
                }
            )

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return videos


def list_comments(
    handle: str,
    days: int = 7,
    max_videos: int = 25,
    account: Optional[str] = None,
) -> dict:
    """List recent comments across a channel's videos.

    A comment counts as answered when one of its replies is authored by the
    channel itself.

    Args:
        handle: Channel handle (e.g., 'salta_app')
        days: Only include comments posted within this many days
        max_videos: How many recent videos to scan
        account: Named OAuth account profile (default profile when None)

    Returns:
        Dict with totals and the comment list (newest first)
    """
    service = get_youtube_service(account=account)
    channel_id, uploads = _resolve_channel(service, handle)
    videos = _list_videos(service, uploads, max_videos)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    comments: list[dict] = []
    comments_disabled: list[dict] = []

    for video in videos:
        page_token = None

        while True:
            try:
                result = (
                    service.commentThreads()
                    .list(
                        part="snippet,replies",
                        videoId=video["id"],
                        maxResults=100,
                        order="time",
                        textFormat="plainText",
                        pageToken=page_token,
                    )
                    .execute()
                )
            except HttpError as err:
                # Comments disabled on a video is expected — record it, keep going.
                if err.resp.status == 403:
                    comments_disabled.append(video)
                    break
                raise

            for thread in result.get("items", []):
                top = thread["snippet"]["topLevelComment"]
                snippet = top["snippet"]
                published = datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                )
                if published < cutoff:
                    continue

                replies = thread.get("replies", {}).get("comments", [])
                own_reply = next(
                    (
                        reply["snippet"]["textDisplay"]
                        for reply in replies
                        if reply["snippet"].get("authorChannelId", {}).get("value")
                        == channel_id
                    ),
                    None,
                )

                comments.append(
                    {
                        "id": top["id"],
                        "video_id": video["id"],
                        "video_title": video["title"],
                        "video_url": f"https://youtube.com/watch?v={video['id']}",
                        "author": snippet.get("authorDisplayName"),
                        "body": (snippet.get("textDisplay") or "").strip(),
                        "likes": snippet.get("likeCount", 0),
                        "date": published.isoformat(),
                        "reply_count": thread["snippet"].get("totalReplyCount", 0),
                        "has_response": own_reply is not None,
                        "response": own_reply,
                    }
                )

            page_token = result.get("nextPageToken")
            if not page_token:
                break

    comments.sort(key=lambda c: c["date"], reverse=True)

    output = {
        "total": len(comments),
        "unanswered": sum(1 for c in comments if not c["has_response"]),
        "days": days,
        "handle": handle.lstrip("@"),
        "channel_id": channel_id,
        "videos_scanned": len(videos),
        "comments": comments,
    }

    if comments_disabled:
        output["videos_with_comments_disabled"] = comments_disabled

    return output


def reply_to_comment(
    comment_id: str, text: str, account: Optional[str] = None
) -> dict:
    """Reply to a comment as the channel.

    Args:
        comment_id: The parent comment ID
        text: The reply text
        account: Named OAuth account profile (default profile when None)

    Returns:
        Dict describing the posted reply
    """
    service = get_youtube_service(account=account)

    result = (
        service.comments()
        .insert(
            part="snippet",
            body={"snippet": {"parentId": comment_id, "textOriginal": text}},
        )
        .execute()
    )

    return {
        "status": "ok",
        "parent_comment_id": comment_id,
        "reply_id": result.get("id"),
        "response": result.get("snippet", {}).get("textOriginal", text),
    }


# =============================================================================
# UPLOAD
# =============================================================================


def assert_upload_scope(account: Optional[str] = None) -> None:
    """Fail early (and readably) if the cached token cannot upload.

    videos.insert needs one of YOUTUBE_UPLOAD_SCOPES. A token minted for a
    read-only scope would otherwise die with an opaque 403 partway through the
    transfer.

    Raises:
        ScopeError: If the cached token holds none of the upload scopes
    """
    creds = get_youtube_credentials(account=account)
    granted = set(creds.scopes or [])

    if granted & YOUTUBE_UPLOAD_SCOPES:
        return

    logout = "aitools google logout --youtube"
    if account:
        logout += f" --account {account}"

    raise ScopeError(
        "The cached YouTube token cannot upload videos.\n"
        f"  Granted scopes: {', '.join(sorted(granted)) or '(none)'}\n"
        "  videos.insert needs one of: "
        f"{', '.join(sorted(YOUTUBE_UPLOAD_SCOPES))}\n"
        "Re-authenticate (as the CHANNEL OWNER) to grant it:\n"
        f"  {logout}\n"
        "  then re-run this command."
    )


def _validate_video_file(video_path: str) -> Path:
    """Resolve the video path, checking it exists and is a format YouTube accepts."""
    path = Path(video_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"Video file is empty: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported video format '{path.suffix or '(no extension)'}'.\n"
            f"YouTube accepts: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    return path


def build_video_body(
    title: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    privacy: str = "public",
    category_id: str = "28",
    made_for_kids: bool = False,
) -> dict:
    """Build the videos.insert request body.

    Split out from the upload so the argument -> API body mapping is unit-testable
    without touching the network.

    Args:
        title: Video title
        description: Video description (may be multiline)
        tags: Keyword tags
        privacy: One of PRIVACY_STATUSES
        category_id: YouTube category id (28 = Science & Technology)
        made_for_kids: Self-declared "made for kids" status

    Returns:
        The request body dict for videos.insert
    """
    if privacy not in PRIVACY_STATUSES:
        raise ValueError(
            f"Invalid privacy '{privacy}'. Must be one of: "
            f"{', '.join(PRIVACY_STATUSES)}"
        )

    if not title.strip():
        raise ValueError("Title is required.")

    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": str(category_id),
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }


def _resolve_playlist(service, playlist: str) -> str:
    """Resolve a playlist name to its id. An id is returned unchanged.

    Raises:
        LookupError: If no playlist on the authenticated channel matches the name
    """
    # Playlist ids are opaque but always carry a known prefix; anything else is
    # treated as a human-typed name to look up.
    if playlist.startswith(("PL", "UU", "LL", "FL", "OL", "RD")):
        return playlist

    titles = []
    page_token = None

    while True:
        result = (
            service.playlists()
            .list(part="id,snippet", mine=True, maxResults=50, pageToken=page_token)
            .execute()
        )

        for item in result.get("items", []):
            title = item["snippet"].get("title", "")
            titles.append(title)
            if title.strip().lower() == playlist.strip().lower():
                return item["id"]

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    raise LookupError(
        f"No playlist named '{playlist}' on this channel.\n"
        f"Available: {', '.join(titles) if titles else '(none)'}"
    )


def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    privacy: str = "public",
    category_id: str = "28",
    made_for_kids: bool = False,
    playlist: Optional[str] = None,
    account: Optional[str] = None,
    on_progress: Optional[Callable[[int], None]] = None,
) -> dict:
    """Upload a video to the YouTube channel the cached token owns.

    The upload is resumable and chunked, so a dropped connection retries the
    current chunk instead of restarting a multi-megabyte transfer.

    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description (may be multiline)
        tags: Keyword tags
        privacy: 'public', 'private', or 'unlisted'
        category_id: YouTube category id (28 = Science & Technology)
        made_for_kids: Self-declared "made for kids" status
        playlist: Optional playlist name or id to add the video to
        account: Named OAuth account profile (default profile when None)
        on_progress: Called with the completed percentage (0-100) per chunk

    Returns:
        Dict with the video id, url, and the settings it was published with

    Raises:
        ScopeError: The cached token lacks an upload scope
        FileNotFoundError: The video file does not exist
        ValueError: Bad privacy value, empty title, or unsupported format
    """
    path = _validate_video_file(video_path)
    body = build_video_body(
        title=title,
        description=description,
        tags=tags,
        privacy=privacy,
        category_id=category_id,
        made_for_kids=made_for_kids,
    )

    # Check the token BEFORE streaming bytes, so an under-scoped token fails in a
    # second with an actionable message rather than a 403 mid-transfer.
    assert_upload_scope(account)

    service = get_youtube_service(account=account)

    media = MediaFileUpload(
        str(path),
        chunksize=CHUNK_SIZE,
        resumable=True,
        mimetype="video/*",
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk(num_retries=NUM_RETRIES)
        if status and on_progress:
            on_progress(int(status.progress() * 100))

    if on_progress:
        on_progress(100)

    video_id = response["id"]

    result = {
        "status": "ok",
        "video_id": video_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "title": response.get("snippet", {}).get("title", title),
        "privacy": response.get("status", {}).get("privacyStatus", privacy),
        "category_id": str(category_id),
        "made_for_kids": made_for_kids,
        "tags": tags or [],
        "file": str(path),
        "size_bytes": path.stat().st_size,
    }

    if playlist:
        # The video is already uploaded at this point — a playlist failure must not
        # look like an upload failure, or the caller loses the URL.
        try:
            playlist_id = _resolve_playlist(service, playlist)
            service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            result["playlist_id"] = playlist_id
        except (LookupError, HttpError) as err:
            result["playlist_error"] = (
                f"Video uploaded, but adding it to playlist '{playlist}' failed: {err}"
            )

    return result
