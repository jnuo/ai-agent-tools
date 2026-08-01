"""Keyword validation — turn a list of candidate keywords into a target/watch/kill call.

This is the gate that has to sit in front of any metadata rewrite. Writing a
keyword into a store's title, subtitle, or keyword field spends a finite budget of
characters, so a phrase earns its slot only if it clears two independent bars:

1. **Demand** — somebody actually searches it. Modelled volume from DataForSEO
   (see ``dfs.VOLUME_SOURCE_DFS``); a phrase nobody searches is a wasted slot no
   matter how well it describes the product.
2. **Winnability** — the head of that SERP isn't a fortress. A keyword owned by a
   50k-review incumbent is unwinnable for a near-zero-rank app whatever its volume.

Neither bar predicts success. Both are *elimination* filters: at ~28 signups/month
nothing store-side is statistically significant, so the job here is to stop us from
spending characters on phrases that are provably dead, and to leave the actual
conversion read to AppsFlyer (per-CPP install→activation) downstream.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import dfs

# Difficulty bands, scored by SERP incumbency (see dfs.Serp.difficulty).
DIFFICULTY_CONTESTED = 60.0  # entrenched head — don't spend characters here
DIFFICULTY_WINNABLE = 40.0   # thin head — this is where a small app ranks

VERDICT_TARGET = "target"
VERDICT_WATCH = "watch"
VERDICT_KILL = "kill"
VERDICT_UNKNOWN = "unknown"


@dataclass
class Candidate:
    """One keyword, scored on both bars, with the verdict that follows."""

    keyword: str
    cluster: Optional[str] = None
    search_volume: Optional[int] = None
    volume_source: str = dfs.VOLUME_SOURCE_DFS
    difficulty: Optional[float] = None
    our_rank: Optional[int] = None
    top_apps: Optional[List[Dict[str, Any]]] = None
    verdict: str = VERDICT_UNKNOWN
    reason: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "cluster": self.cluster,
            "search_volume": self.search_volume,
            "volume_source": self.volume_source,
            "difficulty": self.difficulty,
            "our_rank": self.our_rank,
            "top_apps": self.top_apps,
            "verdict": self.verdict,
            "reason": self.reason,
        }


def judge(candidate: Candidate) -> Candidate:
    """Assign a verdict from demand + winnability. Mutates and returns the candidate.

    Order matters: a dead SERP read is reported as unknown rather than guessed at,
    because "no data" and "easy" look identical in a table and only one of them is
    safe to act on.
    """
    if candidate.difficulty is None:
        candidate.verdict = VERDICT_UNKNOWN
        candidate.reason = "no SERP returned — re-pull before deciding"
        return candidate

    if candidate.search_volume == 0:
        candidate.verdict = VERDICT_KILL
        candidate.reason = "no measurable search demand"
        return candidate

    if candidate.difficulty >= DIFFICULTY_CONTESTED:
        candidate.verdict = VERDICT_KILL
        candidate.reason = f"entrenched SERP (difficulty {candidate.difficulty})"
        return candidate

    if candidate.difficulty < DIFFICULTY_WINNABLE:
        candidate.verdict = VERDICT_TARGET
        candidate.reason = (
            f"thin SERP (difficulty {candidate.difficulty})"
            + (f", volume {candidate.search_volume}" if candidate.search_volume else "")
        )
        return candidate

    candidate.verdict = VERDICT_WATCH
    candidate.reason = f"mid difficulty ({candidate.difficulty}) — worth a CPP, not a keyword slot"
    return candidate


def validate(
    keywords: List[str],
    our_app_id: str,
    platform: str = "ios",
    country: str = "us",
    language: str = "en",
    clusters: Optional[Dict[str, str]] = None,
    volumes: Optional[Dict[str, int]] = None,
    depth: int = 30,
) -> tuple[List[Candidate], float]:
    """Pull a live SERP per keyword, attach demand, and return scored candidates.

    Args:
        keywords: Candidate phrases to judge.
        our_app_id: Store app id (Apple numeric id, or Play package name) — used to
            read our own current rank out of each SERP.
        clusters: Optional ``{keyword: cluster_name}`` so the report groups by the
            8 use-case clusters from the ASO playbook.
        volumes: Optional ``{keyword: search_volume}`` harvested from
            :func:`dfs.keywords_for_app` (ours or a competitor's). Keywords with no
            volume entry are scored on winnability alone and flagged as such.

    Returns:
        ``(candidates, cost)`` in input order.
    """
    serps, cost = dfs.serp(
        keywords, platform=platform, country=country, language=language, depth=depth
    )
    by_keyword = {s.keyword: s for s in serps}
    clusters = clusters or {}
    volumes = volumes or {}

    candidates: List[Candidate] = []
    for keyword in keywords:
        result = by_keyword.get(keyword)
        candidate = Candidate(
            keyword=keyword,
            cluster=clusters.get(keyword),
            search_volume=volumes.get(keyword),
            volume_source=dfs.VOLUME_SOURCE_DFS if keyword in volumes else "unmeasured",
            difficulty=result.difficulty() if result else None,
            our_rank=result.rank_of(our_app_id) if result else None,
            top_apps=[a.as_dict() for a in result.apps[:5]] if result else None,
        )
        candidates.append(judge(candidate))

    return candidates, cost


def summarize(candidates: List[Candidate]) -> Dict[str, int]:
    """Count candidates per verdict — the headline of any validation run."""
    counts = {VERDICT_TARGET: 0, VERDICT_WATCH: 0, VERDICT_KILL: 0, VERDICT_UNKNOWN: 0}
    for candidate in candidates:
        counts[candidate.verdict] = counts.get(candidate.verdict, 0) + 1
    return counts
