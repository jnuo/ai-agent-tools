"""Granola meeting operations.

Reads meeting data from Granola's local cache file.
Granola stores data at: ~/Library/Application Support/Granola/cache-v3.json
"""

import json
from pathlib import Path
from datetime import datetime


def _get_cache_path() -> Path:
    """Get the Granola cache file path."""
    return Path.home() / "Library" / "Application Support" / "Granola" / "cache-v3.json"


def _load_state() -> dict:
    """Load and parse Granola's cached state.

    Returns:
        The state dict containing documents, transcripts, etc.

    Raises:
        FileNotFoundError: If Granola cache doesn't exist
        json.JSONDecodeError: If cache is corrupted
    """
    cache_path = _get_cache_path()

    if not cache_path.exists():
        raise FileNotFoundError(
            f"Granola cache not found at {cache_path}. "
            "Make sure Granola is installed and has been used."
        )

    with open(cache_path) as f:
        data = json.load(f)

    # Granola stores state as a nested JSON string
    inner = json.loads(data["cache"])
    return inner["state"]


def list_meetings(
    max_results: int = 20,
    query: str = "",
) -> list[dict]:
    """List recent meetings from Granola.

    Args:
        max_results: Maximum meetings to return
        query: Search query to filter by title (case-insensitive)

    Returns:
        List of meeting summaries sorted by date (newest first)
    """
    state = _load_state()
    documents = state.get("documents", {})

    meetings = []
    for doc_id, doc in documents.items():
        # Skip deleted documents
        if doc.get("deleted_at"):
            continue

        title = doc.get("title") or "Untitled"

        # Filter by query if provided
        if query and query.lower() not in title.lower():
            continue

        meetings.append({
            "id": doc_id,
            "title": title,
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", ""),
            "has_transcript": doc_id in state.get("transcripts", {}),
            "has_notes": bool(doc.get("notes_plain")),
        })

    # Sort by created_at descending (newest first)
    meetings.sort(key=lambda x: x["created_at"], reverse=True)

    return meetings[:max_results]


def get_meeting(meeting_id: str) -> dict:
    """Get full meeting details including notes.

    Args:
        meeting_id: The meeting document ID

    Returns:
        Meeting dict with notes and metadata

    Raises:
        KeyError: If meeting not found
    """
    state = _load_state()
    documents = state.get("documents", {})

    if meeting_id not in documents:
        raise KeyError(f"Meeting not found: {meeting_id}")

    doc = documents[meeting_id]
    transcripts = state.get("transcripts", {})

    return {
        "id": meeting_id,
        "title": doc.get("title") or "Untitled",
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
        "notes": doc.get("notes", ""),
        "notes_plain": doc.get("notes_plain", ""),
        "overview": doc.get("overview", ""),
        "has_transcript": meeting_id in transcripts,
        "people": doc.get("people", []),
    }


def get_transcript(meeting_id: str) -> dict:
    """Get the transcript for a meeting.

    Args:
        meeting_id: The meeting document ID

    Returns:
        Dict with transcript segments and formatted text

    Raises:
        KeyError: If meeting or transcript not found
    """
    state = _load_state()
    documents = state.get("documents", {})
    transcripts = state.get("transcripts", {})

    if meeting_id not in documents:
        raise KeyError(f"Meeting not found: {meeting_id}")

    if meeting_id not in transcripts:
        raise KeyError(f"No transcript available for meeting: {meeting_id}")

    doc = documents[meeting_id]
    segments = transcripts[meeting_id]

    # Format transcript as readable text
    formatted_lines = []
    current_source = None

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        source = seg.get("source", "unknown")

        # Group by source (microphone = you, speaker = them)
        if source != current_source:
            current_source = source
            speaker = "Me" if source == "microphone" else "Them"
            formatted_lines.append(f"\n[{speaker}]")

        formatted_lines.append(text)

    return {
        "id": meeting_id,
        "title": doc.get("title") or "Untitled",
        "created_at": doc.get("created_at", ""),
        "segment_count": len(segments),
        "transcript": " ".join(formatted_lines).strip(),
        "segments": segments,  # Raw segments for detailed analysis
    }
