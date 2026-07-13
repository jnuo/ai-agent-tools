"""Tests for Google authentication module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGetCredentials:
    """Tests for get_credentials function."""

    def test_loads_existing_valid_token(self, tmp_path):
        """Should load credentials from existing token file."""
        from aitools.google.auth import get_credentials

        # Create a mock token file
        token_data = {
            "token": "ya29.test_token",
            "refresh_token": "1//test_refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_secret",
            "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
        }
        token_file = tmp_path / "token.json"
        token_file.write_text(json.dumps(token_data))

        with patch("aitools.google.auth.Credentials") as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_creds_class.from_authorized_user_file.return_value = mock_creds

            result = get_credentials(tmp_path)

            assert result == mock_creds
            mock_creds_class.from_authorized_user_file.assert_called_once()

    def test_refreshes_expired_token(self, tmp_path):
        """Should refresh expired credentials if refresh token exists."""
        from aitools.google.auth import get_credentials

        token_file = tmp_path / "token.json"
        token_file.write_text('{"token": "expired"}')

        with patch("aitools.google.auth.Credentials") as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh_token_here"
            mock_creds.to_json.return_value = '{"token": "refreshed"}'
            mock_creds_class.from_authorized_user_file.return_value = mock_creds

            with patch("aitools.google.auth.Request") as mock_request:
                result = get_credentials(tmp_path)

                mock_creds.refresh.assert_called_once()
                assert result == mock_creds

    def test_raises_error_when_no_client_secret(self, tmp_path):
        """Should raise FileNotFoundError when client_secret.json is missing."""
        from aitools.google.auth import get_credentials

        # No token file, no client_secret file
        with pytest.raises(FileNotFoundError) as exc_info:
            get_credentials(tmp_path)

        assert "client_secret.json" in str(exc_info.value)
        assert "Google Cloud Console" in str(exc_info.value)


class TestGetCalendarService:
    """Tests for get_calendar_service function."""

    def test_builds_calendar_service(self, tmp_path):
        """Should build and return calendar service."""
        from aitools.google.auth import get_calendar_service

        with patch("aitools.google.auth.get_credentials") as mock_get_creds:
            mock_creds = MagicMock()
            mock_get_creds.return_value = mock_creds

            with patch("aitools.google.auth.build") as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service

                result = get_calendar_service(tmp_path)

                mock_build.assert_called_once_with("calendar", "v3", credentials=mock_creds)
                assert result == mock_service


class TestGetGmailService:
    """Tests for get_gmail_service function."""

    def test_builds_gmail_service(self, tmp_path):
        """Should build and return Gmail service."""
        from aitools.google.auth import get_gmail_service

        with patch("aitools.google.auth.get_credentials") as mock_get_creds:
            mock_creds = MagicMock()
            mock_get_creds.return_value = mock_creds

            with patch("aitools.google.auth.build") as mock_build:
                mock_service = MagicMock()
                mock_build.return_value = mock_service

                result = get_gmail_service(tmp_path)

                mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)
                assert result == mock_service


class TestClearCredentials:
    """Tests for clear_credentials function."""

    def test_removes_token_file(self, tmp_path, capsys):
        """Should remove token file if it exists."""
        from aitools.google.auth import clear_credentials

        token_file = tmp_path / "token.json"
        token_file.write_text('{"token": "test"}')

        clear_credentials(tmp_path)

        assert not token_file.exists()
        captured = capsys.readouterr()
        assert "Removed" in captured.out

    def test_handles_missing_token_file(self, tmp_path, capsys):
        """Should print message when no token file exists."""
        from aitools.google.auth import clear_credentials

        clear_credentials(tmp_path)

        captured = capsys.readouterr()
        assert "No stored credentials" in captured.out


class TestYouTubeTokenFilename:
    """Each YouTube account profile gets its own token file."""

    def test_default_profile_keeps_the_historical_name(self):
        from aitools.google.auth import youtube_token_filename

        assert youtube_token_filename() is not None
        assert youtube_token_filename() == "token_youtube.json"
        assert youtube_token_filename(None) == "token_youtube.json"

    def test_named_profile_gets_its_own_file(self):
        from aitools.google.auth import youtube_token_filename

        assert youtube_token_filename("cosmo") == "token_youtube_cosmo.json"

    def test_name_is_normalized(self):
        from aitools.google.auth import youtube_token_filename

        assert youtube_token_filename(" Cosmo Work ") == "token_youtube_cosmo-work.json"

    def test_rejects_a_name_that_normalizes_to_nothing(self):
        import pytest

        from aitools.google.auth import youtube_token_filename

        with pytest.raises(ValueError, match="Invalid account name"):
            youtube_token_filename("///")

    def test_clear_credentials_removes_the_named_youtube_token(self, tmp_path, capsys):
        from aitools.google.auth import clear_credentials

        token_file = tmp_path / "token_youtube_cosmo.json"
        token_file.write_text('{"token": "test"}')

        clear_credentials(tmp_path, youtube=True, account="cosmo")

        assert not token_file.exists()
        assert "Removed" in capsys.readouterr().out


class TestYouTubeUploadScopes:
    """force-ssl must cover videos.insert, or every upload 403s."""

    def test_default_youtube_scope_authorizes_upload(self):
        from aitools.google.auth import YOUTUBE_SCOPES, YOUTUBE_UPLOAD_SCOPES

        assert set(YOUTUBE_SCOPES) & YOUTUBE_UPLOAD_SCOPES
