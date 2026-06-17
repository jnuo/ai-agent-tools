"""App Store Connect API authentication and HTTP helpers.

Auth is a short-lived ES256 JWT signed with an App Store Connect API key (.p8),
its key id, and the team's issuer id. See config.get_app_store_connect_config.

Docs: https://developer.apple.com/documentation/appstoreconnectapi
"""

import csv
import gzip
import io
import time
from typing import Optional

import jwt
import requests

from ..config import get_app_store_connect_config

ASC_API_BASE = "https://api.appstoreconnect.apple.com"
# JWT lifetime: Apple rejects tokens with exp > 20 minutes out.
_JWT_TTL_SECONDS = 1200


class AscAuthError(Exception):
    """Raised when App Store Connect auth fails or credentials are missing."""


class AscAPIError(Exception):
    """Raised when an App Store Connect API call fails with a non-auth error."""


def _make_jwt() -> str:
    cfg = get_app_store_connect_config()
    if not cfg:
        raise AscAuthError(
            "Missing App Store Connect API credentials.\n"
            "Set ASC_KEY_ID and ASC_ISSUER_ID (env vars or "
            "credentials/app_store_connect/.env). The .p8 key defaults to "
            "~/.appstoreconnect/private_keys/AuthKey_<ASC_KEY_ID>.p8, or set "
            "ASC_PRIVATE_KEY_PATH.\n"
            "Create a key in App Store Connect: Users and Access → Integrations "
            "→ App Store Connect API."
        )
    now = int(time.time())
    payload = {
        "iss": cfg["issuer_id"],
        "iat": now,
        "exp": now + _JWT_TTL_SECONDS,
        "aud": "appstoreconnect-v1",
    }
    return jwt.encode(
        payload,
        cfg["private_key"],
        algorithm="ES256",
        headers={"kid": cfg["key_id"], "typ": "JWT"},
    )


def _check(resp: requests.Response) -> None:
    if resp.status_code in (401, 403):
        raise AscAuthError(
            f"App Store Connect auth failed ({resp.status_code}). The API key may "
            f"lack the required role (Admin/Finance/Sales for reports) or be "
            f"invalid. Response: {resp.text[:300]}"
        )
    if resp.status_code == 404:
        raise AscAPIError(
            f"App Store Connect resource not found (404): {resp.url}"
        )
    if not resp.ok:
        raise AscAPIError(
            f"App Store Connect API error ({resp.status_code}): {resp.text[:400]}"
        )


def api_get(path_or_url: str, params: Optional[dict] = None, timeout: int = 60) -> dict:
    """GET an App Store Connect API resource. Accepts a path or a full URL
    (the API's pagination `links.next` returns absolute URLs)."""
    url = path_or_url if path_or_url.startswith("http") else f"{ASC_API_BASE}{path_or_url}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {_make_jwt()}", "Accept": "application/json"},
        params=params or {},
        timeout=timeout,
    )
    _check(resp)
    return resp.json()


def api_post(path: str, body: dict, timeout: int = 60) -> dict:
    resp = requests.post(
        f"{ASC_API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {_make_jwt()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=body,
        timeout=timeout,
    )
    _check(resp)
    return resp.json()


def paginate(path: str, params: Optional[dict] = None, max_pages: int = 50) -> list[dict]:
    """Follow `links.next` and concatenate `data` arrays across pages."""
    out: list[dict] = []
    page = api_get(path, params)
    out.extend(page.get("data", []))
    pages = 1
    while pages < max_pages:
        nxt = (page.get("links") or {}).get("next")
        if not nxt:
            break
        page = api_get(nxt)
        out.extend(page.get("data", []))
        pages += 1
    return out


def download_report_segment(url: str, timeout: int = 120) -> list[dict]:
    """Download a report segment (a pre-signed, gzipped CSV URL) into rows.

    Segment URLs are pre-signed; they take no Authorization header.
    """
    resp = requests.get(url, timeout=timeout)
    if not resp.ok:
        raise AscAPIError(
            f"Failed to download report segment ({resp.status_code}). The "
            f"pre-signed URL may have expired; retry the request."
        )
    raw = gzip.decompress(resp.content).decode("utf-8")
    lines = raw.splitlines()
    if not lines or not lines[0].strip():
        return []  # empty segment (a date with no events) — not an error
    # Analytics report segments are tab-separated despite the .csv naming.
    dialect = "\t" if "\t" in lines[0] else ","
    reader = csv.DictReader(io.StringIO(raw), delimiter=dialect)
    return list(reader)
