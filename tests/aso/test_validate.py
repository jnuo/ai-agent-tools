"""Unit tests for the keyword validation gate — difficulty scoring, verdicts, persistence.

No network: every test drives the pure logic that turns a SERP into a target/watch/kill
call. The two things worth guarding are (a) an unwinnable SERP is never scored as easy,
and (b) a *missing* SERP is never scored at all — "no data" and "easy" look identical in
a results table and only one of them is safe to act on.
"""

from pathlib import Path

import pytest

from aitools.aso import dfs, validate as validator
from aitools.aso.aso import AsoDb


def serp_of(*apps: tuple[int, str, int], keyword: str = "kw") -> dfs.Serp:
    """Build a SERP from (rank, app_id, votes) triples."""
    return dfs.Serp(
        keyword=keyword,
        apps=[
            dfs.SerpApp(rank=rank, app_id=app_id, title=f"App {app_id}", votes=votes)
            for rank, app_id, votes in apps
        ],
    )


# ── Difficulty ──────────────────────────────────────────────────────────


def test_difficulty_none_for_empty_serp():
    """An empty SERP scores None, not zero — no data is not the same as easy."""
    assert dfs.Serp(keyword="kw", apps=[]).difficulty() is None


def test_fortress_serp_scores_unwinnable():
    """Ten 50k-review incumbents is the maximum-difficulty case."""
    fortress = serp_of(*[(i, f"app{i}", 80_000) for i in range(1, 11)])
    assert fortress.difficulty() == 100.0
    assert validator.judge(
        validator.Candidate(keyword="kw", difficulty=fortress.difficulty())
    ).verdict == validator.VERDICT_KILL


def test_indie_serp_scores_winnable():
    """A head full of 20-review indie apps is exactly what a near-zero-rank app targets."""
    indie = serp_of(*[(i, f"app{i}", 20) for i in range(1, 11)])
    assert indie.difficulty() == 15.0
    assert validator.judge(
        validator.Candidate(keyword="kw", difficulty=indie.difficulty())
    ).verdict == validator.VERDICT_TARGET


def test_difficulty_ignores_the_tail():
    """Only the head (top 10) decides winnability — nobody scrolls to rank 30."""
    head_light_tail_heavy = serp_of(
        *[(i, f"app{i}", 10) for i in range(1, 11)],
        *[(i, f"app{i}", 500_000) for i in range(11, 31)],
    )
    assert head_light_tail_heavy.difficulty() == 15.0


def test_difficulty_normalizes_short_serps():
    """A 3-result SERP of incumbents is still a fortress, not a third of one."""
    assert serp_of((1, "a", 90_000), (2, "b", 90_000), (3, "c", 90_000)).difficulty() == 100.0


# ── Our rank ────────────────────────────────────────────────────────────


def test_rank_of_finds_us_and_reports_absence_as_none():
    result = serp_of((1, "999", 10), (2, "6761076847", 5))
    assert result.rank_of("6761076847") == 2
    assert result.rank_of(6761076847) == 2, "int app ids must match string ones"
    assert result.rank_of("nope") is None


# ── Verdicts ────────────────────────────────────────────────────────────


def test_zero_volume_is_killed_however_winnable():
    """Ranking #1 on a phrase nobody searches is a wasted metadata slot."""
    candidate = validator.judge(
        validator.Candidate(keyword="kw", difficulty=5.0, search_volume=0)
    )
    assert candidate.verdict == validator.VERDICT_KILL
    assert "demand" in candidate.reason


def test_missing_serp_is_unknown_not_a_verdict():
    candidate = validator.judge(validator.Candidate(keyword="kw", difficulty=None))
    assert candidate.verdict == validator.VERDICT_UNKNOWN
    assert candidate.search_volume is None


def test_mid_difficulty_is_watch():
    candidate = validator.judge(validator.Candidate(keyword="kw", difficulty=50.0))
    assert candidate.verdict == validator.VERDICT_WATCH


def test_summarize_counts_every_verdict():
    candidates = [
        validator.Candidate(keyword="a", verdict=validator.VERDICT_TARGET),
        validator.Candidate(keyword="b", verdict=validator.VERDICT_TARGET),
        validator.Candidate(keyword="c", verdict=validator.VERDICT_KILL),
    ]
    counts = validator.summarize(candidates)
    assert counts == {"target": 2, "watch": 0, "kill": 1, "unknown": 0}


# ── Guards ──────────────────────────────────────────────────────────────


def test_labs_mining_refuses_unsupported_country_with_a_useful_message():
    """TR mining must fail with the reason, not a bare API 'Invalid Field' error."""
    with pytest.raises(ValueError, match="US-only"):
        dfs.keywords_for_app("6761076847", platform="ios", country="tr")


def test_unknown_platform_rejected():
    with pytest.raises(ValueError, match="Unknown platform"):
        dfs.resolve_store("windows")


def test_store_slugs():
    assert dfs.resolve_store("ios") == "apple"
    assert dfs.resolve_store("android") == "google"


# ── Persistence ─────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path: Path) -> AsoDb:
    aso = AsoDb(tmp_path / "aso_test.db")
    yield aso
    aso.close()


def test_candidates_persist_and_reread(db: AsoDb):
    app_row = db.add_app("com.salta.uno", "salta", "ios", "us")
    written = db.save_candidates(
        app_row,
        [
            validator.Candidate(
                keyword="ai weekly planner",
                cluster="3-ai-weekly-planning",
                difficulty=40.0,
                our_rank=None,
                top_apps=[{"rank": 1, "app_id": "x", "title": "T", "rating": 4.5, "votes": 20}],
                verdict=validator.VERDICT_TARGET,
                reason="thin SERP",
            ).as_dict()
        ],
    )
    assert written == 1

    rows = db.list_candidates(app_row)
    assert len(rows) == 1
    assert rows[0]["keyword"] == "ai weekly planner"
    assert rows[0]["cluster"] == "3-ai-weekly-planning"
    assert rows[0]["verdict"] == "target"
    assert rows[0]["our_rank"] is None

    targets = db.list_candidates(app_row, verdict=validator.VERDICT_KILL)
    assert targets == []


def test_same_day_rerun_overwrites_rather_than_duplicating(db: AsoDb):
    """A month's cycle must leave exactly one comparable row per keyword per day."""
    app_row = db.add_app("com.salta.uno", "salta", "ios", "us")
    first = validator.Candidate(keyword="plan my day", verdict=validator.VERDICT_WATCH, difficulty=50.0)
    db.save_candidates(app_row, [first.as_dict()])

    revised = validator.Candidate(keyword="plan my day", verdict=validator.VERDICT_KILL, difficulty=70.0)
    db.save_candidates(app_row, [revised.as_dict()])

    rows = db.list_candidates(app_row)
    assert len(rows) == 1
    assert rows[0]["verdict"] == "kill"
    assert rows[0]["difficulty"] == 70.0
