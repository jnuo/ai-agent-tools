"""API key authentication for Google Gemini API."""

import os
from pathlib import Path
from typing import Optional

from ..config import get_credentials_dir


def get_gemini_credentials_dir() -> Path:
    """Get Gemini credentials directory."""
    return get_credentials_dir("gemini")


def get_gemini_api_key() -> Optional[str]:
    """Get Gemini API key.

    Priority:
    1. GEMINI_API_KEY environment variable
    2. .env file in gemini credentials directory

    Returns:
        API key string or None if not found
    """
    # Check environment variable first
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key

    # Try loading from .env file
    env_file = get_gemini_credentials_dir() / ".env"
    if env_file.exists():
        try:
            from dotenv import dotenv_values
            values = dotenv_values(env_file)
            return values.get("GEMINI_API_KEY")
        except ImportError:
            # dotenv not installed, try manual parsing
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"\'')

    return None


def require_api_key() -> str:
    """Get API key or raise an error with setup instructions.

    Returns:
        Valid API key

    Raises:
        ValueError: If no API key is configured
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError(
            "Gemini API key not found.\n\n"
            "Set up your API key using one of these methods:\n\n"
            "Option 1: Environment variable\n"
            "  export GEMINI_API_KEY='your-api-key'\n\n"
            "Option 2: Create credentials file\n"
            "  echo 'GEMINI_API_KEY=your-api-key' > credentials/gemini/.env\n\n"
            "Get your API key from: https://aistudio.google.com/apikey"
        )
    return api_key
