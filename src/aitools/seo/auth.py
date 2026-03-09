"""API authentication for DataForSEO."""

import os
from pathlib import Path
from typing import Optional, Tuple

from ..config import get_credentials_dir


def get_seo_credentials_dir() -> Path:
    """Get SEO credentials directory."""
    return get_credentials_dir("seo")


def get_dataforseo_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Get DataForSEO login and password.

    Priority:
    1. DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD environment variables
    2. .env file in seo credentials directory

    Returns:
        Tuple of (login, password) or (None, None) if not found
    """
    # Check environment variables first
    login = os.environ.get("DATAFORSEO_LOGIN")
    password = os.environ.get("DATAFORSEO_PASSWORD")
    if login and password:
        return login, password

    # Try loading from .env file
    env_file = get_seo_credentials_dir() / ".env"
    if env_file.exists():
        values = {}
        try:
            from dotenv import dotenv_values
            values = dotenv_values(env_file)
        except ImportError:
            # dotenv not installed, try manual parsing
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, val = line.split("=", 1)
                        values[key.strip()] = val.strip().strip('"\'')

        login = values.get("DATAFORSEO_LOGIN")
        password = values.get("DATAFORSEO_PASSWORD")
        if login and password:
            return login, password

    return None, None


def require_credentials() -> Tuple[str, str]:
    """Get credentials or raise an error with setup instructions.

    Returns:
        Tuple of (login, password)

    Raises:
        ValueError: If credentials are not configured
    """
    login, password = get_dataforseo_credentials()
    if not login or not password:
        raise ValueError(
            "DataForSEO credentials not found.\n\n"
            "Set up your credentials using one of these methods:\n\n"
            "Option 1: Environment variables\n"
            "  export DATAFORSEO_LOGIN='your-login'\n"
            "  export DATAFORSEO_PASSWORD='your-password'\n\n"
            "Option 2: Create credentials file\n"
            "  mkdir -p credentials/seo\n"
            "  echo 'DATAFORSEO_LOGIN=your-login' > credentials/seo/.env\n"
            "  echo 'DATAFORSEO_PASSWORD=your-password' >> credentials/seo/.env\n\n"
            "Get your credentials from: https://app.dataforseo.com/api-access"
        )
    return login, password
