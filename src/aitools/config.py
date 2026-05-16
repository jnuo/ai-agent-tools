"""Configuration management for AI Agent Tools.

Supports configuration via environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional

# Package root directory
_PACKAGE_ROOT = Path(__file__).parent.parent.parent


def get_credentials_dir(subdir: Optional[str] = None) -> Path:
    """Get the credentials directory path.

    Priority:
    1. AITOOLS_CREDENTIALS_DIR environment variable
    2. Default: credentials/ relative to package root

    Args:
        subdir: Optional subdirectory (e.g., 'google', 'notion')

    Returns:
        Path to credentials directory
    """
    base_dir = os.environ.get("AITOOLS_CREDENTIALS_DIR")
    if base_dir:
        path = Path(base_dir)
    else:
        path = _PACKAGE_ROOT / "credentials"

    if subdir:
        path = path / subdir

    return path


def get_timezone() -> str:
    """Get the configured timezone.

    Priority:
    1. AITOOLS_TIMEZONE environment variable
    2. Default: UTC

    Returns:
        Timezone string (e.g., 'Europe/Amsterdam', 'UTC')
    """
    return os.environ.get("AITOOLS_TIMEZONE", "UTC")


def get_google_credentials_dir() -> Path:
    """Get Google credentials directory."""
    return get_credentials_dir("google")


def get_notion_credentials_dir() -> Path:
    """Get Notion credentials directory."""
    return get_credentials_dir("notion")


def get_notion_api_key() -> Optional[str]:
    """Get Notion API key.

    Priority:
    1. NOTION_API_KEY environment variable
    2. .env file in notion credentials directory

    Returns:
        API key string or None if not found
    """
    # Check environment variable first
    api_key = os.environ.get("NOTION_API_KEY")
    if api_key:
        return api_key

    # Try loading from .env file
    env_file = get_notion_credentials_dir() / ".env"
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            values = dotenv_values(env_file)
            return values.get("NOTION_API_KEY")
        except ImportError:
            # dotenv not installed, try manual parsing
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("NOTION_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"\'')

    return None


def get_resend_credentials_dir() -> Path:
    """Get Resend credentials directory."""
    return get_credentials_dir("resend")


def get_resend_api_key() -> Optional[str]:
    """Get Resend API key.

    Priority:
    1. RESEND_API_KEY environment variable
    2. .env file in resend credentials directory

    Returns:
        API key string or None if not found
    """
    # Check environment variable first
    api_key = os.environ.get("RESEND_API_KEY")
    if api_key:
        return api_key

    # Try loading from .env file
    env_file = get_resend_credentials_dir() / ".env"
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            values = dotenv_values(env_file)
            return values.get("RESEND_API_KEY")
        except ImportError:
            # dotenv not installed, try manual parsing
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("RESEND_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"\'')

    return None


def get_appsflyer_credentials_dir() -> Path:
    """Get AppsFlyer credentials directory."""
    return get_credentials_dir("appsflyer")


def get_appsflyer_api_token() -> Optional[str]:
    """Get AppsFlyer Pull API V2 Bearer token.

    Priority:
    1. APPSFLYER_API_TOKEN environment variable
    2. .env file in appsflyer credentials directory

    Returns:
        Token string or None if not found
    """
    token = os.environ.get("APPSFLYER_API_TOKEN")
    if token:
        return token

    env_file = get_appsflyer_credentials_dir() / ".env"
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            values = dotenv_values(env_file)
            return values.get("APPSFLYER_API_TOKEN")
        except ImportError:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("APPSFLYER_API_TOKEN="):
                        return line.split("=", 1)[1].strip().strip('"\'')

    return None
