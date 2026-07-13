"""Tests for YouTube operations module."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _thread(comment_id, author, body, published, replies=None, total_replies=0):
    thread = {
        "snippet": {
            "totalReplyCount": total_replies,
            "topLevelComment": {
                "id": comment_id,
                "snippet": {
                    "authorDisplayName": author,
                    "textDisplay": body,
                    "likeCount": 0,
                    "publishedAt": _iso(published),
                },
            },
        }
    }
    if replies:
        thread["replies"] = {"comments": replies}
    return thread


def _reply(author_channel_id, text):
    return {
        "snippet": {
            "textDisplay": text,
            "authorChannelId": {"value": author_channel_id},
        }
    }


def _service_with(threads, channel_id="UC_salta"):
    """Build a mock YouTube service returning one video with the given threads."""
    service = MagicMock()

    service.channels.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": channel_id,
                "contentDetails": {"relatedPlaylists": {"uploads": "UU_salta"}},
            }
        ]
    }

    service.playlistItems.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "contentDetails": {"videoId": "vid1"},
                "snippet": {"title": "Salta demo"},
            }
        ]
    }

    service.commentThreads.return_value.list.return_value.execute.return_value = {
        "items": threads
    }

    return service


class TestListComments:
    """Tests for list_comments."""

    def test_returns_recent_comments(self):
        from aitools.google import youtube

        now = datetime.now(timezone.utc)
        service = _service_with([_thread("c1", "Ada", "Love this", now - timedelta(days=1))])

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.list_comments("salta_app", days=7)

        assert result["total"] == 1
        assert result["unanswered"] == 1
        assert result["videos_scanned"] == 1
        assert result["channel_id"] == "UC_salta"

        comment = result["comments"][0]
        assert comment["id"] == "c1"
        assert comment["author"] == "Ada"
        assert comment["body"] == "Love this"
        assert comment["has_response"] is False
        assert comment["video_url"] == "https://youtube.com/watch?v=vid1"

    def test_excludes_comments_older_than_cutoff(self):
        from aitools.google import youtube

        now = datetime.now(timezone.utc)
        service = _service_with(
            [
                _thread("fresh", "Ada", "New", now - timedelta(days=2)),
                _thread("stale", "Bob", "Old", now - timedelta(days=30)),
            ]
        )

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.list_comments("salta_app", days=7)

        assert result["total"] == 1
        assert result["comments"][0]["id"] == "fresh"

    def test_marks_comment_answered_when_channel_replied(self):
        from aitools.google import youtube

        now = datetime.now(timezone.utc)
        service = _service_with(
            [
                _thread(
                    "c1",
                    "Ada",
                    "Does it do voice?",
                    now - timedelta(hours=3),
                    replies=[_reply("UC_salta", "It does — give it a try.")],
                    total_replies=1,
                )
            ]
        )

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.list_comments("salta_app", days=7)

        comment = result["comments"][0]
        assert comment["has_response"] is True
        assert comment["response"] == "It does — give it a try."
        assert result["unanswered"] == 0

    def test_reply_from_someone_else_does_not_count_as_answered(self):
        """A reply from another viewer must not be mistaken for our own reply."""
        from aitools.google import youtube

        now = datetime.now(timezone.utc)
        service = _service_with(
            [
                _thread(
                    "c1",
                    "Ada",
                    "Does it do voice?",
                    now - timedelta(hours=3),
                    replies=[_reply("UC_stranger", "I think so")],
                    total_replies=1,
                )
            ]
        )

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.list_comments("salta_app", days=7)

        comment = result["comments"][0]
        assert comment["has_response"] is False
        assert comment["response"] is None
        assert result["unanswered"] == 1

    def test_comments_sorted_newest_first(self):
        from aitools.google import youtube

        now = datetime.now(timezone.utc)
        service = _service_with(
            [
                _thread("older", "Ada", "First", now - timedelta(days=5)),
                _thread("newer", "Bob", "Second", now - timedelta(days=1)),
            ]
        )

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.list_comments("salta_app", days=7)

        assert [c["id"] for c in result["comments"]] == ["newer", "older"]

    def test_handle_accepts_leading_at_sign(self):
        from aitools.google import youtube

        service = _service_with([])

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.list_comments("@salta_app", days=7)

        assert result["handle"] == "salta_app"
        service.channels.return_value.list.assert_called_once()
        assert (
            service.channels.return_value.list.call_args.kwargs["forHandle"]
            == "salta_app"
        )

    def test_unknown_handle_raises(self):
        from aitools.google import youtube

        service = MagicMock()
        service.channels.return_value.list.return_value.execute.return_value = {"items": []}

        with patch.object(youtube, "get_youtube_service", return_value=service):
            with pytest.raises(LookupError, match="No YouTube channel found"):
                youtube.list_comments("ghost_channel")

    def test_disabled_comments_are_recorded_not_fatal(self):
        """A 403 on one video means comments are off — keep going, but report it."""
        from googleapiclient.errors import HttpError

        from aitools.google import youtube

        service = _service_with([])
        resp = MagicMock()
        resp.status = 403
        service.commentThreads.return_value.list.return_value.execute.side_effect = (
            HttpError(resp=resp, content=b"comments disabled")
        )

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.list_comments("salta_app", days=7)

        assert result["total"] == 0
        assert result["videos_with_comments_disabled"] == [
            {"id": "vid1", "title": "Salta demo"}
        ]

    def test_other_http_errors_are_raised(self):
        """A non-403 failure must surface, never be swallowed."""
        from googleapiclient.errors import HttpError

        from aitools.google import youtube

        service = _service_with([])
        resp = MagicMock()
        resp.status = 500
        service.commentThreads.return_value.list.return_value.execute.side_effect = (
            HttpError(resp=resp, content=b"boom")
        )

        with patch.object(youtube, "get_youtube_service", return_value=service):
            with pytest.raises(HttpError):
                youtube.list_comments("salta_app", days=7)


class TestReplyToComment:
    """Tests for reply_to_comment."""

    def test_posts_reply_with_parent_id(self):
        from aitools.google import youtube

        service = MagicMock()
        service.comments.return_value.insert.return_value.execute.return_value = {
            "id": "reply1",
            "snippet": {"textOriginal": "Thank you."},
        }

        with patch.object(youtube, "get_youtube_service", return_value=service):
            result = youtube.reply_to_comment("c1", "Thank you.")

        assert result["status"] == "ok"
        assert result["parent_comment_id"] == "c1"
        assert result["reply_id"] == "reply1"
        assert result["response"] == "Thank you."

        body = service.comments.return_value.insert.call_args.kwargs["body"]
        assert body["snippet"]["parentId"] == "c1"
        assert body["snippet"]["textOriginal"] == "Thank you."


class TestYouTubeAuth:
    """The YouTube token must be a separate profile from Gmail/Calendar."""

    def test_uses_its_own_token_file_and_scope(self, tmp_path):
        from aitools.google.auth import YOUTUBE_SCOPES, get_youtube_credentials

        token_file = tmp_path / "token_youtube.json"
        token_file.write_text(json.dumps({"token": "yt"}))

        with patch("aitools.google.auth.Credentials") as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_creds_class.from_authorized_user_file.return_value = mock_creds

            result = get_youtube_credentials(tmp_path)

        assert result == mock_creds
        args = mock_creds_class.from_authorized_user_file.call_args.args
        assert args[0] == str(token_file)
        assert args[1] == YOUTUBE_SCOPES

    def test_does_not_reuse_the_gmail_token(self, tmp_path):
        """A Gmail token must not satisfy YouTube — different account, different file."""
        from aitools.google.auth import get_youtube_credentials

        (tmp_path / "token.json").write_text(json.dumps({"token": "gmail"}))
        # No token_youtube.json and no client_secret.json -> must fail loudly.
        with pytest.raises(FileNotFoundError, match="client_secret.json"):
            get_youtube_credentials(tmp_path)


# =============================================================================
# UPLOAD
# =============================================================================


FORCE_SSL = "https://www.googleapis.com/auth/youtube.force-ssl"
UPLOAD_ONLY = "https://www.googleapis.com/auth/youtube.upload"
READONLY = "https://www.googleapis.com/auth/youtube.readonly"


@pytest.fixture
def video_file(tmp_path):
    """A non-empty file with a format YouTube accepts."""
    path = tmp_path / "release.mp4"
    path.write_bytes(b"\x00" * 2048)
    return path


def _creds(scopes):
    creds = MagicMock()
    creds.scopes = scopes
    return creds


def _upload_service(video_id="vid_new", playlists=None):
    """Mock service whose videos().insert() completes in two resumable chunks."""
    service = MagicMock()

    progress_half = MagicMock()
    progress_half.progress.return_value = 0.5

    request = service.videos.return_value.insert.return_value
    request.next_chunk.side_effect = [
        (progress_half, None),
        (
            None,
            {
                "id": video_id,
                "snippet": {"title": "Release v1"},
                "status": {"privacyStatus": "public"},
            },
        ),
    ]

    service.playlists.return_value.list.return_value.execute.return_value = {
        "items": playlists or []
    }

    return service


def _patch_upload(monkeypatch, youtube, service, scopes=(FORCE_SSL,)):
    monkeypatch.setattr(youtube, "get_youtube_service", lambda account=None: service)
    monkeypatch.setattr(
        youtube, "get_youtube_credentials", lambda account=None: _creds(list(scopes))
    )
    # Don't touch the filesystem through the real MediaFileUpload.
    monkeypatch.setattr(youtube, "MediaFileUpload", MagicMock())


class TestBuildVideoBody:
    """The argument -> API body mapping, tested without any network."""

    def test_maps_all_fields(self):
        from aitools.google import youtube

        body = youtube.build_video_body(
            title="Release v1",
            description="Line one\nLine two",
            tags=["ai", "release"],
            privacy="unlisted",
            category_id="22",
            made_for_kids=True,
        )

        assert body == {
            "snippet": {
                "title": "Release v1",
                "description": "Line one\nLine two",
                "tags": ["ai", "release"],
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": True,
            },
        }

    def test_defaults_are_public_science_and_tech_not_for_kids(self):
        from aitools.google import youtube

        body = youtube.build_video_body(title="Release v1")

        assert body["status"]["privacyStatus"] == "public"
        assert body["status"]["selfDeclaredMadeForKids"] is False
        assert body["snippet"]["categoryId"] == "28"
        assert body["snippet"]["tags"] == []

    @pytest.mark.parametrize("privacy", ["public", "private", "unlisted"])
    def test_accepts_every_privacy_status(self, privacy):
        from aitools.google import youtube

        body = youtube.build_video_body(title="T", privacy=privacy)
        assert body["status"]["privacyStatus"] == privacy

    def test_rejects_unknown_privacy(self):
        from aitools.google import youtube

        with pytest.raises(ValueError, match="Invalid privacy"):
            youtube.build_video_body(title="T", privacy="secret")

    def test_rejects_empty_title(self):
        from aitools.google import youtube

        with pytest.raises(ValueError, match="Title is required"):
            youtube.build_video_body(title="   ")

    def test_category_id_is_coerced_to_string(self):
        from aitools.google import youtube

        body = youtube.build_video_body(title="T", category_id=22)
        assert body["snippet"]["categoryId"] == "22"


class TestUploadScope:
    """An under-scoped token must fail before any bytes are sent."""

    @pytest.mark.parametrize("scope", [FORCE_SSL, UPLOAD_ONLY])
    def test_upload_scopes_pass(self, monkeypatch, scope):
        from aitools.google import youtube

        monkeypatch.setattr(
            youtube, "get_youtube_credentials", lambda account=None: _creds([scope])
        )
        youtube.assert_upload_scope()  # does not raise

    def test_readonly_token_raises_actionable_scope_error(self, monkeypatch):
        from aitools.google import youtube

        monkeypatch.setattr(
            youtube, "get_youtube_credentials", lambda account=None: _creds([READONLY])
        )

        with pytest.raises(youtube.ScopeError) as err:
            youtube.assert_upload_scope()

        message = str(err.value)
        assert "cannot upload" in message
        assert "aitools google logout --youtube" in message
        assert READONLY in message

    def test_scope_error_names_the_account_profile(self, monkeypatch):
        from aitools.google import youtube

        monkeypatch.setattr(
            youtube, "get_youtube_credentials", lambda account=None: _creds([READONLY])
        )

        with pytest.raises(youtube.ScopeError) as err:
            youtube.assert_upload_scope(account="cosmo")

        assert "--account cosmo" in str(err.value)

    def test_upload_checks_scope_before_touching_the_api(
        self, monkeypatch, video_file
    ):
        from aitools.google import youtube

        service = _upload_service()
        _patch_upload(monkeypatch, youtube, service, scopes=(READONLY,))

        with pytest.raises(youtube.ScopeError):
            youtube.upload_video(str(video_file), title="Release v1")

        service.videos.return_value.insert.assert_not_called()


class TestUploadVideo:
    """Tests for upload_video."""

    def test_returns_video_id_and_url(self, monkeypatch, video_file):
        from aitools.google import youtube

        service = _upload_service(video_id="abc123")
        _patch_upload(monkeypatch, youtube, service)

        result = youtube.upload_video(str(video_file), title="Release v1")

        assert result["status"] == "ok"
        assert result["video_id"] == "abc123"
        assert result["url"] == "https://youtube.com/watch?v=abc123"
        assert result["size_bytes"] == 2048

    def test_sends_the_mapped_body_to_videos_insert(self, monkeypatch, video_file):
        from aitools.google import youtube

        service = _upload_service()
        _patch_upload(monkeypatch, youtube, service)

        youtube.upload_video(
            str(video_file),
            title="Internal demo",
            description="For the team",
            tags=["demo"],
            privacy="unlisted",
            category_id="22",
            made_for_kids=False,
        )

        kwargs = service.videos.return_value.insert.call_args.kwargs
        assert kwargs["part"] == "snippet,status"
        assert kwargs["body"]["snippet"]["title"] == "Internal demo"
        assert kwargs["body"]["snippet"]["tags"] == ["demo"]
        assert kwargs["body"]["status"]["privacyStatus"] == "unlisted"

    def test_unlisted_upload_reports_unlisted(self, monkeypatch, video_file):
        """Unlisted is a first-class case — link-only internal shares."""
        from aitools.google import youtube

        service = _upload_service()
        service.videos.return_value.insert.return_value.next_chunk.side_effect = [
            (
                None,
                {
                    "id": "int1",
                    "snippet": {"title": "Internal demo"},
                    "status": {"privacyStatus": "unlisted"},
                },
            )
        ]
        _patch_upload(monkeypatch, youtube, service)

        result = youtube.upload_video(
            str(video_file), title="Internal demo", privacy="unlisted"
        )

        assert result["privacy"] == "unlisted"
        assert result["url"] == "https://youtube.com/watch?v=int1"

    def test_upload_is_resumable_and_chunked(self, monkeypatch, video_file):
        from aitools.google import youtube

        service = _upload_service()
        media = MagicMock()
        monkeypatch.setattr(youtube, "MediaFileUpload", media)
        monkeypatch.setattr(
            youtube, "get_youtube_service", lambda account=None: service
        )
        monkeypatch.setattr(
            youtube,
            "get_youtube_credentials",
            lambda account=None: _creds([FORCE_SSL]),
        )

        youtube.upload_video(str(video_file), title="Release v1")

        assert media.call_args.kwargs["resumable"] is True
        assert media.call_args.kwargs["chunksize"] == youtube.CHUNK_SIZE

    def test_reports_progress_per_chunk(self, monkeypatch, video_file):
        from aitools.google import youtube

        service = _upload_service()
        _patch_upload(monkeypatch, youtube, service)

        seen = []
        youtube.upload_video(
            str(video_file), title="Release v1", on_progress=seen.append
        )

        assert seen == [50, 100]

    def test_missing_file_raises_before_any_api_call(self, monkeypatch, tmp_path):
        from aitools.google import youtube

        service = _upload_service()
        _patch_upload(monkeypatch, youtube, service)

        with pytest.raises(FileNotFoundError, match="Video file not found"):
            youtube.upload_video(str(tmp_path / "nope.mp4"), title="T")

        service.videos.return_value.insert.assert_not_called()

    def test_unsupported_format_raises(self, monkeypatch, tmp_path):
        from aitools.google import youtube

        bad = tmp_path / "notes.pdf"
        bad.write_bytes(b"\x00" * 10)

        service = _upload_service()
        _patch_upload(monkeypatch, youtube, service)

        with pytest.raises(ValueError, match="Unsupported video format"):
            youtube.upload_video(str(bad), title="T")

        service.videos.return_value.insert.assert_not_called()

    def test_empty_file_raises(self, monkeypatch, tmp_path):
        from aitools.google import youtube

        empty = tmp_path / "empty.mp4"
        empty.touch()

        service = _upload_service()
        _patch_upload(monkeypatch, youtube, service)

        with pytest.raises(ValueError, match="empty"):
            youtube.upload_video(str(empty), title="T")


class TestUploadPlaylist:
    """Adding the uploaded video to a playlist."""

    def test_resolves_playlist_by_name(self, monkeypatch, video_file):
        from aitools.google import youtube

        service = _upload_service(
            playlists=[{"id": "PL_releases", "snippet": {"title": "Releases"}}]
        )
        _patch_upload(monkeypatch, youtube, service)

        result = youtube.upload_video(
            str(video_file), title="Release v1", playlist="Releases"
        )

        assert result["playlist_id"] == "PL_releases"
        body = service.playlistItems.return_value.insert.call_args.kwargs["body"]
        assert body["snippet"]["playlistId"] == "PL_releases"
        assert body["snippet"]["resourceId"]["videoId"] == "vid_new"

    def test_playlist_id_is_used_directly(self, monkeypatch, video_file):
        from aitools.google import youtube

        service = _upload_service()
        _patch_upload(monkeypatch, youtube, service)

        result = youtube.upload_video(
            str(video_file), title="Release v1", playlist="PL_explicit"
        )

        assert result["playlist_id"] == "PL_explicit"
        service.playlists.return_value.list.assert_not_called()

    def test_unknown_playlist_does_not_lose_the_uploaded_url(
        self, monkeypatch, video_file
    ):
        """The video is already up — a playlist miss must not read as an upload failure."""
        from aitools.google import youtube

        service = _upload_service(playlists=[])
        _patch_upload(monkeypatch, youtube, service)

        result = youtube.upload_video(
            str(video_file), title="Release v1", playlist="Ghost"
        )

        assert result["status"] == "ok"
        assert result["url"] == "https://youtube.com/watch?v=vid_new"
        assert "No playlist named 'Ghost'" in result["playlist_error"]
