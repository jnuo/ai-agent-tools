"""Tests for Granola meetings module."""

import json
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from aitools.granola.meetings import (
    _get_cache_path,
    _load_state,
    list_meetings,
    get_meeting,
    get_transcript,
)


@pytest.fixture
def sample_granola_state():
    """Sample Granola state with documents and transcripts."""
    return {
        "documents": {
            "meeting-1": {
                "title": "Team Standup",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "notes": "# Notes\n- Item 1\n- Item 2",
                "notes_plain": "Notes\n- Item 1\n- Item 2",
                "overview": "Daily sync meeting",
                "people": ["Alice", "Bob"],
            },
            "meeting-2": {
                "title": "Product Review",
                "created_at": "2024-01-14T14:00:00Z",
                "updated_at": "2024-01-14T15:00:00Z",
                "notes_plain": "Reviewed Q1 roadmap",
            },
            "meeting-deleted": {
                "title": "Deleted Meeting",
                "created_at": "2024-01-13T09:00:00Z",
                "deleted_at": "2024-01-13T10:00:00Z",
            },
        },
        "transcripts": {
            "meeting-1": [
                {"text": "Hello everyone", "source": "microphone"},
                {"text": "Hi there", "source": "speaker"},
                {"text": "Let's get started", "source": "microphone"},
            ],
        },
    }


@pytest.fixture
def sample_granola_cache(sample_granola_state):
    """Sample Granola cache file structure."""
    return {
        "cache": json.dumps({"state": sample_granola_state})
    }


class TestGetCachePath:
    """Tests for _get_cache_path function."""

    def test_returns_correct_path(self):
        """Should return path in Library/Application Support."""
        path = _get_cache_path()
        assert "Library/Application Support/Granola/cache-v3.json" in str(path)


class TestLoadState:
    """Tests for _load_state function."""

    def test_loads_state_from_cache(self, sample_granola_cache, sample_granola_state):
        """Should parse nested JSON and return state."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                state = _load_state()

        assert "documents" in state
        assert "meeting-1" in state["documents"]

    def test_raises_when_cache_missing(self):
        """Should raise FileNotFoundError when cache doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Granola cache not found"):
                _load_state()


class TestListMeetings:
    """Tests for list_meetings function."""

    def test_lists_meetings(self, sample_granola_cache):
        """Should list meetings sorted by date."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                result = list_meetings()

        assert len(result) == 2  # Excludes deleted
        assert result[0]["id"] == "meeting-1"  # Newest first
        assert result[0]["title"] == "Team Standup"
        assert result[0]["has_transcript"] is True
        assert result[1]["id"] == "meeting-2"
        assert result[1]["has_transcript"] is False

    def test_filters_by_query(self, sample_granola_cache):
        """Should filter meetings by title query."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                result = list_meetings(query="standup")

        assert len(result) == 1
        assert result[0]["title"] == "Team Standup"

    def test_respects_max_results(self, sample_granola_cache):
        """Should limit results to max_results."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                result = list_meetings(max_results=1)

        assert len(result) == 1

    def test_excludes_deleted_meetings(self, sample_granola_cache):
        """Should not include deleted meetings."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                result = list_meetings()

        ids = [m["id"] for m in result]
        assert "meeting-deleted" not in ids


class TestGetMeeting:
    """Tests for get_meeting function."""

    def test_gets_meeting_details(self, sample_granola_cache):
        """Should return full meeting details."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                result = get_meeting("meeting-1")

        assert result["id"] == "meeting-1"
        assert result["title"] == "Team Standup"
        assert result["notes_plain"] == "Notes\n- Item 1\n- Item 2"
        assert result["overview"] == "Daily sync meeting"
        assert result["has_transcript"] is True
        assert result["people"] == ["Alice", "Bob"]

    def test_raises_when_not_found(self, sample_granola_cache):
        """Should raise KeyError when meeting doesn't exist."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                with pytest.raises(KeyError, match="Meeting not found"):
                    get_meeting("nonexistent")


class TestGetTranscript:
    """Tests for get_transcript function."""

    def test_gets_transcript(self, sample_granola_cache):
        """Should return formatted transcript."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                result = get_transcript("meeting-1")

        assert result["id"] == "meeting-1"
        assert result["title"] == "Team Standup"
        assert result["segment_count"] == 3
        assert "[Me]" in result["transcript"]
        assert "[Them]" in result["transcript"]
        assert "Hello everyone" in result["transcript"]
        assert len(result["segments"]) == 3

    def test_raises_when_no_transcript(self, sample_granola_cache):
        """Should raise KeyError when transcript doesn't exist."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                with pytest.raises(KeyError, match="No transcript available"):
                    get_transcript("meeting-2")

    def test_raises_when_meeting_not_found(self, sample_granola_cache):
        """Should raise KeyError when meeting doesn't exist."""
        cache_json = json.dumps(sample_granola_cache)

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=cache_json)):
                with pytest.raises(KeyError, match="Meeting not found"):
                    get_transcript("nonexistent")
