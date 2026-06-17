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


def get_app_store_connect_credentials_dir() -> Path:
    """Get App Store Connect credentials directory."""
    return get_credentials_dir("app_store_connect")


def _app_store_connect_env() -> dict:
    """Merge App Store Connect settings from env vars and the module .env file.

    Env vars win over the .env file. Recognized keys:
        ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH
    """
    vals: dict = {}
    env_file = get_app_store_connect_credentials_dir() / ".env"
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            vals.update({k: v for k, v in dotenv_values(env_file).items() if v})
        except ImportError:
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip().strip('"\'')
    for key in ("ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_PRIVATE_KEY_PATH"):
        if os.environ.get(key):
            vals[key] = os.environ[key]
    return vals


def get_app_store_connect_config() -> Optional[dict]:
    """Get App Store Connect API key config for JWT signing.

    Priority for each setting: environment variable, then
    credentials/app_store_connect/.env.

    The private key (.p8) path defaults to
    ~/.appstoreconnect/private_keys/AuthKey_<ASC_KEY_ID>.p8 (Apple's
    convention) when ASC_PRIVATE_KEY_PATH is not set.

    Returns:
        dict with key_id, issuer_id, private_key (PEM text), key_path —
        or None if key id / issuer id / key file are not all available.
    """
    vals = _app_store_connect_env()
    key_id = vals.get("ASC_KEY_ID")
    issuer_id = vals.get("ASC_ISSUER_ID")
    if not (key_id and issuer_id):
        return None

    key_path = vals.get("ASC_PRIVATE_KEY_PATH")
    if key_path:
        path = Path(key_path).expanduser()
    else:
        path = Path.home() / ".appstoreconnect" / "private_keys" / f"AuthKey_{key_id}.p8"
    if not path.exists():
        return None

    return {
        "key_id": key_id,
        "issuer_id": issuer_id,
        "private_key": path.read_text(),
        "key_path": str(path),
    }


def get_play_store_credentials_dir() -> Path:
    """Get Google Play Store credentials directory."""
    return get_credentials_dir("play_store")


def _play_store_env() -> dict:
    """Merge Play Store settings from env vars and the module .env file."""
    vals: dict = {}
    env_file = get_play_store_credentials_dir() / ".env"
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            vals.update({k: v for k, v in dotenv_values(env_file).items() if v})
        except ImportError:
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip().strip('"\'')
    for key in ("PLAY_REPORTS_BUCKET", "PLAY_SERVICE_ACCOUNT_PATH"):
        if os.environ.get(key):
            vals[key] = os.environ[key]
    return vals


def get_play_store_service_account_path() -> Optional[Path]:
    """Path to the Play reporting service-account JSON.

    Priority: PLAY_SERVICE_ACCOUNT_PATH, then
    credentials/play_store/service-account.json.
    """
    vals = _play_store_env()
    p = vals.get("PLAY_SERVICE_ACCOUNT_PATH")
    path = Path(p).expanduser() if p else get_play_store_credentials_dir() / "service-account.json"
    return path if path.exists() else None


def get_play_reports_bucket() -> Optional[str]:
    """Google Play reporting GCS bucket (e.g. pubsite_prod_<developerId>).

    Find it in Play Console -> Download reports -> Statistics -> "Copy Cloud
    Storage URI". Set via PLAY_REPORTS_BUCKET or credentials/play_store/.env.
    """
    return _play_store_env().get("PLAY_REPORTS_BUCKET")


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
