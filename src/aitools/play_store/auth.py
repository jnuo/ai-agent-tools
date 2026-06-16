"""Google Play reporting access: service-account auth + GCS read helpers.

Reads the Play statistics export bucket via the Cloud Storage JSON API. The
service account needs read access to the reporting bucket (Play auto-grants the
developer's linked service accounts; otherwise grant Storage Object Viewer).
"""

import csv
import io
import json
import urllib.parse
import urllib.request
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account

from ..config import get_play_reports_bucket, get_play_store_service_account_path

_SCOPE = "https://www.googleapis.com/auth/devstorage.read_only"
_GCS = "https://storage.googleapis.com/storage/v1/b"


class PlayStoreAuthError(Exception):
    """Raised when Play reporting credentials/bucket are missing or invalid."""


class PlayStoreAPIError(Exception):
    """Raised when a Cloud Storage request fails."""


def _credentials():
    path = get_play_store_service_account_path()
    if not path:
        raise PlayStoreAuthError(
            "Missing Play service-account JSON. Place it at "
            "credentials/play_store/service-account.json or set "
            "PLAY_SERVICE_ACCOUNT_PATH."
        )
    creds = service_account.Credentials.from_service_account_file(
        str(path), scopes=[_SCOPE]
    )
    creds.refresh(Request())
    return creds


def _bucket() -> str:
    bucket = get_play_reports_bucket()
    if not bucket:
        raise PlayStoreAuthError(
            "Missing PLAY_REPORTS_BUCKET. Find it in Play Console -> Download "
            "reports -> Statistics -> 'Copy Cloud Storage URI' (pubsite_prod_...), "
            "and set it in credentials/play_store/.env."
        )
    return bucket


def _get(url: str, token: str, raw: bool = False):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            return data if raw else json.loads(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        if e.code in (401, 403):
            raise PlayStoreAuthError(
                f"Play bucket access denied ({e.code}). The service account needs "
                f"read access to the reporting bucket. {body}"
            )
        raise PlayStoreAPIError(f"Cloud Storage error ({e.code}): {body}")


def list_objects(prefix: str) -> list[str]:
    """List object names under a prefix in the reporting bucket."""
    creds = _credentials()
    bucket = _bucket()
    names: list[str] = []
    page_token = None
    while True:
        params = {"prefix": prefix, "maxResults": 1000}
        if page_token:
            params["pageToken"] = page_token
        url = f"{_GCS}/{bucket}/o?{urllib.parse.urlencode(params)}"
        data = _get(url, creds.token)
        names.extend(i["name"] for i in data.get("items", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return names


def read_csv(object_name: str) -> list[dict]:
    """Download a Play report CSV (UTF-16) into a list of row dicts."""
    creds = _credentials()
    bucket = _bucket()
    url = f"{_GCS}/{bucket}/o/{urllib.parse.quote(object_name, safe='')}?alt=media"
    raw = _get(url, creds.token, raw=True)
    # Play report CSVs are UTF-16 (with BOM); fall back to utf-8 just in case.
    try:
        text = raw.decode("utf-16")
    except UnicodeError:
        text = raw.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))
