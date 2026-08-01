"""DataForSEO app-store fetchers — keyword mining, store SERPs, difficulty scoring.

The rest of the ASO module runs on free first-party data (iTunes Search API,
console exports). This module adds the one thing those cannot give us: what real
users search in the stores, and who already owns those searches.

Three primitives:

- :func:`serp`              — *can we win it?*  The actual store search results for
  a keyword: real ranks, real incumbents, real review counts. This is the only
  non-modelled signal in the module, and the one worth trusting.
- :func:`keywords_for_app`  — *what does a rival rank for?*  The keyword universe an
  app appears for. Mine a competitor to harvest phrases we'd never have guessed;
  mine ourselves for a baseline.
- :func:`app_competitors`   — *who else is in this space?*  The apps sharing an
  app's keyword footprint. Seeds the mining list.

**Two limits, verified live against the API on 2026-07-13 — do not design around
them being otherwise:**

1. The ``search_volume`` attached to mined keywords is DataForSEO's **Google web**
   volume, not App Store search demand (which is why mining a to-do app surfaces
   "reddit" at 2M). Treat it as a coarse relative signal only. Apple's own keyword
   popularity index (Apple Search Ads) is the sole authoritative App Store demand
   source; wire it in as soon as an ASA account exists.
2. The Labs app databases (``keywords_for_app``, ``app_competitors``) are **US-only** —
   a Turkish location returns ``Invalid Field: 'location_code'``. The SERP endpoint
   :func:`serp` *does* cover Turkiye (2792), so winnability is measurable in TR even
   though demand, for now, is not.

Costs (DataForSEO price list, checked 2026-07):
- keywords_for_app / app_competitors: $0.012 per request + $0.00012 per result
- app SERP: $0.0012 per keyword (task_post; task_get is free)

Every entry point returns its accrued cost so callers can enforce a budget.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from ..seo.client import API_BASE, _auth_header, post, resolve_language, resolve_location

import httpx

# DataForSEO calls the stores "apple" and "google"; we speak ios/android everywhere else.
STORE_BY_PLATFORM: Dict[str, str] = {"ios": "apple", "android": "google"}

# Named for what it actually is: a Google web-search estimate, not store demand.
VOLUME_SOURCE_DFS = "dataforseo_google_web_estimate"

# Labs app databases only carry the US location; the SERP endpoint carries many more.
LABS_SUPPORTED_COUNTRIES = ("us",)

# SERP polling: tasks land in a few seconds, but a cold queue can take longer.
POLL_INTERVAL_S = 8.0
POLL_TIMEOUT_S = 180.0

# Difficulty: how entrenched the top of the SERP is. An app with a huge review
# count is unassailable at our size; an app with 20 reviews is not.
FORTRESS_VOTES = 50_000
ESTABLISHED_VOTES = 2_000
SERP_HEAD_DEPTH = 10


def resolve_store(platform: str) -> str:
    """Map ``ios``/``android`` to DataForSEO's ``apple``/``google`` store slug."""
    store = STORE_BY_PLATFORM.get(platform.lower())
    if not store:
        raise ValueError(
            f"Unknown platform: {platform}. Supported: {', '.join(sorted(STORE_BY_PLATFORM))}"
        )
    return store


@dataclass
class Keyword:
    """A candidate keyword with whatever demand signal we could attach to it."""

    keyword: str
    search_volume: Optional[int] = None
    volume_source: str = VOLUME_SOURCE_DFS
    competition: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "search_volume": self.search_volume,
            "volume_source": self.volume_source,
            "competition": self.competition,
        }


@dataclass
class SerpApp:
    """One app occupying a position in a store SERP."""

    rank: int
    app_id: str
    title: str
    rating: Optional[float] = None
    votes: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "app_id": self.app_id,
            "title": self.title,
            "rating": self.rating,
            "votes": self.votes,
        }


@dataclass
class Serp:
    """A store SERP for one keyword, plus the difficulty read derived from it."""

    keyword: str
    apps: List[SerpApp] = field(default_factory=list)
    cost: float = 0.0

    def rank_of(self, app_id: str) -> Optional[int]:
        """Our own rank for this keyword, or ``None`` if we don't appear at all."""
        for app in self.apps:
            if app.app_id == str(app_id):
                return app.rank
        return None

    def difficulty(self) -> Optional[float]:
        """Score 0-100 for how hard the top of this SERP is to break into.

        Driven by incumbency, not by volume: we count how many of the head results
        are entrenched apps (by review count, the one proxy for install base the
        store exposes publicly). A SERP of 20-review indie apps is winnable at our
        size; one guarded by a 50k-review incumbent is not, whatever the volume says.

        Returns ``None`` for an empty SERP — no data is not the same as easy.
        """
        head = [a for a in self.apps if a.rank <= SERP_HEAD_DEPTH]
        if not head:
            return None
        score = 0.0
        for app in head:
            if app.votes >= FORTRESS_VOTES:
                score += 10.0
            elif app.votes >= ESTABLISHED_VOTES:
                score += 5.0
            elif app.votes > 0:
                score += 1.5
        return round(min(100.0, score * (10.0 / len(head))), 1)


def _check_labs_country(country: str) -> None:
    """Fail loudly on a location the Labs app databases don't carry.

    Without this the API answers a Turkish request with a bare ``Invalid Field:
    'location_code'``, which reads like a bug in our payload rather than a hard
    limit of the data source.
    """
    if country.lower() not in LABS_SUPPORTED_COUNTRIES:
        raise ValueError(
            f"DataForSEO's Labs app database has no {country.upper()} data — it is "
            f"{'/'.join(c.upper() for c in LABS_SUPPORTED_COUNTRIES)}-only. Keyword "
            "mining is unavailable here. Store SERPs (aso.dfs.serp) DO cover this "
            "country, so winnability is still measurable; for demand, use Apple "
            "Search Ads popularity or the Play Console search-queries report."
        )


def _live(store: str, endpoint: str, payload: Dict[str, Any]) -> tuple[List[Dict[str, Any]], float]:
    """POST a DataForSEO Labs app endpoint and return ``(items, cost)``."""
    task = post(f"dataforseo_labs/{store}/{endpoint}/live", [payload])
    results = task.get("result") or []
    items = (results[0].get("items") or []) if results else []
    return items, float(task.get("cost") or 0.0)


def keywords_for_app(
    app_id: str,
    platform: str = "ios",
    country: str = "us",
    language: str = "en",
    limit: int = 200,
) -> tuple[List[Keyword], float]:
    """Keywords an app ranks for in the store, ranked by estimated search volume.

    Point this at a competitor to mine their long-tails; point it at ourselves for
    a baseline. An app with no store presence legitimately returns an empty list —
    that is a finding, not an error.

    ``search_volume`` here is Google web volume, NOT App Store demand (see the module
    docstring). US-only; other countries raise.

    Returns:
        ``(keywords, cost)`` — keywords sorted by descending volume.
    """
    _check_labs_country(country)
    store = resolve_store(platform)
    items, cost = _live(
        store,
        "keywords_for_app",
        {
            "app_id": str(app_id),
            "location_code": resolve_location(country),
            "language_code": resolve_language(language),
            "limit": limit,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        },
    )

    keywords: List[Keyword] = []
    for item in items:
        data = item.get("keyword_data") or {}
        info = data.get("keyword_info") or {}
        term = data.get("keyword")
        if not term:
            continue
        keywords.append(
            Keyword(
                keyword=term,
                search_volume=info.get("search_volume"),
                competition=info.get("competition_level"),
            )
        )
    return keywords, cost


def app_competitors(
    app_id: str,
    platform: str = "ios",
    country: str = "us",
    language: str = "en",
    limit: int = 20,
) -> tuple[List[Dict[str, Any]], float]:
    """Apps whose keyword footprint overlaps this app's — the mining list. US-only."""
    _check_labs_country(country)
    store = resolve_store(platform)
    items, cost = _live(
        store,
        "app_competitors",
        {
            "app_id": str(app_id),
            "location_code": resolve_location(country),
            "language_code": resolve_language(language),
            "limit": limit,
        },
    )

    competitors = []
    for item in items:
        competitors.append(
            {
                "app_id": item.get("app_id"),
                "title": (item.get("app_info") or {}).get("title"),
                "intersections": item.get("intersections"),
                "avg_position": (item.get("full_domain_metrics") or {}).get("pos_1"),
            }
        )
    return competitors, cost


def _serp_post(
    keywords: Iterable[str],
    store: str,
    country: str,
    language: str,
    depth: int,
) -> tuple[Dict[str, str], float]:
    """Queue one SERP task per keyword. Returns ``({task_id: keyword}, cost)``."""
    tasks = [
        {
            "keyword": kw,
            "location_code": resolve_location(country),
            "language_code": resolve_language(language),
            "depth": depth,
        }
        for kw in keywords
    ]
    if not tasks:
        return {}, 0.0

    headers = {"Authorization": _auth_header(), "Content-Type": "application/json"}
    try:
        response = httpx.post(
            f"{API_BASE}/app_data/{store}/app_searches/task_post",
            json=tasks,
            headers=headers,
            timeout=120.0,
        )
    except httpx.HTTPError as exc:
        raise ValueError(f"DataForSEO network error: {exc}") from exc

    if response.status_code != 200:
        raise ValueError(
            f"DataForSEO API error (HTTP {response.status_code}): {response.text}"
        )

    body = response.json()
    if body.get("status_code") != 20000:
        raise ValueError(
            f"DataForSEO API error [{body.get('status_code')}]: {body.get('status_message')}"
        )

    queued: Dict[str, str] = {}
    failures: List[str] = []
    for task in body.get("tasks") or []:
        # 20100 = "Task Created". Anything else means this keyword never queued.
        if task.get("status_code") != 20100 or not task.get("id"):
            failures.append(
                f"{(task.get('data') or {}).get('keyword')!r}: "
                f"[{task.get('status_code')}] {task.get('status_message')}"
            )
            continue
        queued[task["id"]] = (task.get("data") or {}).get("keyword", "")

    if failures:
        raise ValueError(
            "DataForSEO refused "
            f"{len(failures)}/{len(tasks)} SERP task(s):\n  " + "\n  ".join(failures)
        )

    return queued, float(body.get("cost") or 0.0)


def _serp_get(task_id: str, store: str) -> Optional[Serp]:
    """Fetch one finished SERP task. ``None`` while it is still queued."""
    headers = {"Authorization": _auth_header()}
    try:
        response = httpx.get(
            f"{API_BASE}/app_data/{store}/app_searches/task_get/advanced/{task_id}",
            headers=headers,
            timeout=120.0,
        )
    except httpx.HTTPError as exc:
        raise ValueError(f"DataForSEO network error: {exc}") from exc

    if response.status_code != 200:
        raise ValueError(
            f"DataForSEO API error (HTTP {response.status_code}): {response.text}"
        )

    task = (response.json().get("tasks") or [{}])[0]
    status = task.get("status_code")
    # 40602 = "Task In Queue", 40601 = "Task Handed"; both mean "not ready yet".
    if status in (40601, 40602):
        return None
    if status != 20000:
        raise ValueError(
            f"DataForSEO SERP task failed [{status}]: {task.get('status_message')}"
        )

    result = (task.get("result") or [{}])[0]
    apps = []
    for item in result.get("items") or []:
        if not item.get("app_id"):
            continue
        rating = item.get("rating") or {}
        apps.append(
            SerpApp(
                rank=item.get("rank_absolute") or 0,
                app_id=str(item["app_id"]),
                title=item.get("title") or "",
                rating=rating.get("value"),
                votes=rating.get("votes_count") or item.get("reviews_count") or 0,
            )
        )
    return Serp(keyword=result.get("keyword") or "", apps=apps)


def serp(
    keywords: List[str],
    platform: str = "ios",
    country: str = "us",
    language: str = "en",
    depth: int = 30,
    timeout_s: float = POLL_TIMEOUT_S,
) -> tuple[List[Serp], float]:
    """Real store search results for each keyword — the "can we win it" check.

    Queues every keyword in a single task_post (DataForSEO's SERP endpoint is
    async-only), then polls until all tasks land. A keyword whose task never
    lands raises rather than silently returning a partial set — a missing SERP
    reads as "empty, therefore easy", which is exactly the wrong conclusion.

    Returns:
        ``(serps, cost)`` in the order the keywords were passed.
    """
    store = resolve_store(platform)
    queued, cost = _serp_post(keywords, store, country, language, depth)

    collected: Dict[str, Serp] = {}
    deadline = time.monotonic() + timeout_s
    pending = dict(queued)

    while pending and time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_S)
        for task_id, keyword in list(pending.items()):
            result = _serp_get(task_id, store)
            if result is None:
                continue
            collected[keyword or result.keyword] = result
            pending.pop(task_id)

    if pending:
        raise ValueError(
            f"{len(pending)} SERP task(s) did not finish within {timeout_s:.0f}s: "
            f"{', '.join(sorted(pending.values()))}. Re-run — DataForSEO keeps "
            "finished tasks for 30 days, so no budget is lost."
        )

    ordered = [collected[kw] for kw in keywords if kw in collected]
    for item in ordered:
        item.cost = cost / max(len(ordered), 1)
    return ordered, cost
