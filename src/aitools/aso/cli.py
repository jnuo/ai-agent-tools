"""CLI for ASO Intelligence — App Store + Play Store keyword and metadata tracking."""

import json
from pathlib import Path

import click

from .aso import DEFAULT_DB, VALID_PLATFORMS, VALID_REPORT_TYPES, AsoDb


@click.group()
def aso():
    """ASO operations — store, trend, and search App Store / Play Store data.

    Mirrors `aitools seo gsc *` for mobile: register apps, import snapshots
    (search terms, metadata, reviews, rankings), then compute trends.
    """
    pass


# ─── Apps ──────────────────────────────────────────────────────────────


@aso.command("add-app")
@click.argument("bundle_id")
@click.argument("product")
@click.option(
    "--platform",
    type=click.Choice(VALID_PLATFORMS),
    required=True,
    help="ios or android",
)
@click.option("--country", default="us", help="Country code (default: us)")
@click.option("--db", default=str(DEFAULT_DB), help="Path to aso.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def add_app(
    bundle_id: str,
    product: str,
    platform: str,
    country: str,
    db: str,
    as_json: bool,
):
    """Register an app for tracking.

    Examples:
        aitools aso add-app com.jnuo.salta salta --platform ios
        aitools aso add-app com.jnuo.salta salta --platform android --country tr
    """
    aso_db = AsoDb(Path(db))
    app_id = aso_db.add_app(bundle_id, product, platform, country)
    aso_db.close()
    if as_json:
        click.echo(
            json.dumps(
                {
                    "id": app_id,
                    "bundle_id": bundle_id,
                    "product": product,
                    "platform": platform,
                    "country": country.lower(),
                }
            )
        )
    else:
        click.echo(
            f"App registered: {product} → {bundle_id} [{platform}/{country.lower()}] (id={app_id})"
        )


@aso.command("apps")
@click.option("--db", default=str(DEFAULT_DB), help="Path to aso.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_apps(db: str, as_json: bool):
    """List tracked apps."""
    aso_db = AsoDb(Path(db))
    apps = aso_db.list_apps()
    aso_db.close()
    if as_json:
        click.echo(json.dumps(apps, indent=2))
        return
    if not apps:
        click.echo("No apps registered. Use 'aitools aso add-app' first.")
        return
    click.echo("\nTracked Apps:")
    click.echo("-" * 60)
    for a in apps:
        click.echo(
            f"  [{a['id']}] {a['product']:<12} {a['platform']:<8} "
            f"{a['country']:<4} {a['bundle_id']}"
        )


# ─── Import ────────────────────────────────────────────────────────────


@aso.command("import")
@click.argument("data_file", type=click.Path(exists=True))
@click.option("--bundle-id", "bundle_id", required=True, help="App bundle id / package name")
@click.option(
    "--platform",
    type=click.Choice(VALID_PLATFORMS),
    required=True,
    help="ios or android",
)
@click.option("--country", default="us", help="Country code (default: us)")
@click.option(
    "--report-type",
    "report_type",
    type=click.Choice(VALID_REPORT_TYPES),
    required=True,
    help="Type of data being imported",
)
@click.option("--start", "start_date", help="Period start (YYYY-MM-DD); for metadata/rankings, use as snapshot date")
@click.option("--end", "end_date", help="Period end (YYYY-MM-DD); ignored for metadata/rankings")
@click.option("--db", default=str(DEFAULT_DB), help="Path to aso.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def import_data(
    data_file: str,
    bundle_id: str,
    platform: str,
    country: str,
    report_type: str,
    start_date: str,
    end_date: str,
    db: str,
    as_json: bool,
):
    """Import a JSON data file for an app + report type.

    Expected JSON shapes:
      search_terms: [{term, impressions, taps, conversions, position}, ...]
      metadata:     [{locale, title, subtitle, keywords_field, description,
                      promotional_text, short_description}, ...]
      reviews:      [{review_id, rating, title, body, version, country, locale, posted_at}, ...]
      rankings:     [{keyword, rank, country?}, ...]

    Examples:
        aitools aso import /tmp/salta_search_terms.json --bundle-id com.jnuo.salta \\
            --platform ios --report-type search_terms --start 2026-04-01 --end 2026-04-30
    """
    if not start_date:
        raise click.UsageError("--start is required")

    aso_db = AsoDb(Path(db))
    with open(data_file) as f:
        rows = json.load(f)

    if report_type == "search_terms":
        if not end_date:
            raise click.UsageError("--end is required for search_terms")
        result = aso_db.import_search_terms(
            bundle_id, platform, start_date, end_date, rows, country
        )
    elif report_type == "metadata":
        result = aso_db.import_metadata(
            bundle_id, platform, start_date, rows, country
        )
    elif report_type == "reviews":
        if not end_date:
            raise click.UsageError("--end is required for reviews")
        result = aso_db.import_reviews(
            bundle_id, platform, start_date, end_date, rows, country
        )
    elif report_type == "rankings":
        result = aso_db.import_rankings(
            bundle_id, platform, start_date, rows, country
        )
    else:  # pragma: no cover — guarded by Click choices
        raise click.UsageError(f"Unknown report-type {report_type!r}")

    aso_db.close()

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if "rows_imported" in result:
            click.echo(
                f"Imported {result['rows_imported']} {report_type} rows for "
                f"{result['app']} ({result.get('period', result.get('snapshot_date'))})"
            )
        else:
            click.echo(
                f"Imported {result.get('locales_imported', 0)} metadata locales for "
                f"{result['app']} ({result.get('snapshot_date')})"
            )


# ─── Trends ────────────────────────────────────────────────────────────


@aso.command("trends")
@click.option("--bundle-id", "bundle_id", required=True, help="App bundle id / package name")
@click.option(
    "--platform",
    type=click.Choice(VALID_PLATFORMS),
    required=True,
    help="ios or android",
)
@click.option("--country", default="us", help="Country code (default: us)")
@click.option(
    "--report-type",
    "report_type",
    type=click.Choice(["search_terms", "rankings"]),
    default="search_terms",
    help="Trend type to compute",
)
@click.option("--limit", default=20, help="Max results per category")
@click.option("--db", default=str(DEFAULT_DB), help="Path to aso.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def trends(
    bundle_id: str,
    platform: str,
    country: str,
    report_type: str,
    limit: int,
    db: str,
    as_json: bool,
):
    """Compare the latest two snapshots and show movers.

    For search_terms: rising/declining/new/lost (by impressions delta).
    For rankings: rising/declining (by rank delta — lower rank is better).
    """
    aso_db = AsoDb(Path(db))
    if report_type == "search_terms":
        result = aso_db.compute_search_term_trends(bundle_id, platform, country, limit)
    else:
        result = aso_db.compute_ranking_trends(bundle_id, platform, country, limit)
    aso_db.close()

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    if "error" in result:
        click.echo(f"⚠ {result['error']}")
        return

    app = result["app"]
    click.echo(
        f"\n{report_type.upper()} TRENDS — {app['product']} "
        f"[{app['platform']}/{app['country']}]"
    )
    click.echo("=" * 60)
    if result.get("mode") == "single_snapshot":
        click.echo(f"Period: {result['period']} (only one snapshot — no trend yet)")
        for r in result.get("top_terms", [])[:limit]:
            click.echo(
                f"  {r['term']:<35} imp={r['impressions']:<6} taps={r['taps']:<5} conv={r['conversions']}"
            )
        return

    click.echo(f"Current:  {result.get('current_period') or result.get('current_date')}")
    click.echo(f"Previous: {result.get('previous_period') or result.get('previous_date')}")
    click.echo(f"\nCounts: {result['counts']}")

    for bucket in ("rising", "declining", "new", "lost"):
        if bucket not in result:
            continue
        items = result[bucket]
        if not items:
            continue
        click.echo(f"\n--- {bucket.upper()} ({len(items)}) ---")
        for r in items[:limit]:
            term = r.get("term") or r.get("keyword", "")
            if "imp_now" in r:
                click.echo(
                    f"  {term:<35} {r.get('imp_prev', 0)} → {r.get('imp_now', 0)} "
                    f"({r.get('imp_change_pct', 0):+}%)"
                )
            elif "rank_now" in r:
                click.echo(
                    f"  {term:<35} rank {r.get('rank_prev')} → {r.get('rank_now')} "
                    f"(Δ{r.get('rank_delta', 0):+})"
                )
            else:
                click.echo(f"  {term:<35} imp={r.get('impressions', 0)}")


# ─── Search ────────────────────────────────────────────────────────────


@aso.command("search")
@click.argument("text")
@click.option(
    "--scope",
    type=click.Choice(["terms", "reviews"]),
    default="terms",
    help="What to search across",
)
@click.option("--bundle-id", "bundle_id", default=None, help="Optional: scope to one app")
@click.option(
    "--platform",
    type=click.Choice(VALID_PLATFORMS),
    default=None,
    help="Required when --bundle-id is set",
)
@click.option("--country", default="us", help="Country code (default: us)")
@click.option("--limit", default=20, help="Max results")
@click.option("--db", default=str(DEFAULT_DB), help="Path to aso.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search_cmd(
    text: str,
    scope: str,
    bundle_id: str,
    platform: str,
    country: str,
    limit: int,
    db: str,
    as_json: bool,
):
    """Full-text search across stored search terms or review bodies.

    Examples:
        aitools aso search "planner" --scope terms
        aitools aso search "crash" --scope reviews --bundle-id com.jnuo.salta --platform ios
    """
    if bundle_id and not platform:
        raise click.UsageError("--platform is required when --bundle-id is provided")

    aso_db = AsoDb(Path(db))
    if scope == "terms":
        rows = aso_db.search_terms_fts(text, bundle_id, platform, country, limit)
    else:
        rows = aso_db.search_reviews_fts(text, bundle_id, platform, country, limit)
    aso_db.close()

    if as_json:
        click.echo(json.dumps(rows, indent=2, default=str))
        return

    if not rows:
        click.echo(f"No matches for '{text}' in {scope}.")
        return

    click.echo(f"\n{len(rows)} matches in {scope}:")
    click.echo("-" * 60)
    for r in rows:
        if scope == "terms":
            click.echo(
                f"  {r['term']:<35} imp={r['impressions']:<6} "
                f"[{r['product']}/{r['platform']}]"
            )
        else:
            click.echo(
                f"  ★{r['rating']} {r.get('title') or '(no title)':<30} "
                f"[{r['product']}/{r['platform']}]"
            )
            if r.get("body"):
                preview = r["body"][:120].replace("\n", " ")
                click.echo(f"      {preview}")


# ─── Stats ─────────────────────────────────────────────────────────────


@aso.command("stats")
@click.option("--db", default=str(DEFAULT_DB), help="Path to aso.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def stats(db: str, as_json: bool):
    """Show per-app coverage across all report types."""
    aso_db = AsoDb(Path(db))
    result = aso_db.stats()
    aso_db.close()

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    if not result["apps"]:
        click.echo("No apps registered. Use 'aitools aso add-app' first.")
        return

    click.echo(f"\nASO Database — {result['total_snapshots']} total snapshots")
    click.echo("=" * 60)
    for app in result["apps"]:
        click.echo(
            f"\n{app['product']} [{app['platform']}/{app['country']}] "
            f"({app['bundle_id']})"
        )
        for rt, info in app["by_report_type"].items():
            if info["snapshots"] > 0:
                click.echo(
                    f"  {rt:<14} {info['snapshots']} snapshots, "
                    f"latest: {info['latest_period']} "
                    f"(pulled {info['last_pulled']})"
                )
            else:
                click.echo(f"  {rt:<14} -")


# ─── DataForSEO: mining + validation ───────────────────────────────────


def _load_keywords(path: Path) -> tuple[list, dict]:
    """Read a keyword file. Accepts a flat list or a {cluster: [keywords]} map."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, list):
        return [str(k) for k in data], {}
    if isinstance(data, dict):
        keywords, clusters = [], {}
        for cluster, terms in data.items():
            for term in terms:
                keywords.append(str(term))
                clusters[str(term)] = cluster
        return keywords, clusters
    raise click.ClickException(
        f"{path}: expected a JSON list of keywords or a {{cluster: [keywords]}} object"
    )


@aso.command("mine")
@click.argument("store_app_id")
@click.option("--platform", type=click.Choice(VALID_PLATFORMS), default="ios")
@click.option("--country", default="us", help="Country code (default: us)")
@click.option("--language", default="en", help="Language code (default: en)")
@click.option("--limit", default=200, help="Max keywords to return (default: 200)")
@click.option("--competitors", is_flag=True, help="Also list apps sharing this keyword footprint")
@click.option("--out", type=click.Path(), help="Write {keyword: volume} JSON here for `validate --volumes`")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def mine(store_app_id, platform, country, language, limit, competitors, out, as_json):
    """Mine the keywords an app ranks for — ours for a baseline, a rival's to steal long-tails.

    STORE_APP_ID is the Apple numeric app id (e.g. 6761076847) or the Play package name.

    Examples:
        aitools aso mine 6761076847 --platform ios              # our baseline
        aitools aso mine 572688855 --competitors --out /tmp/todoist.json
    """
    from . import dfs

    try:
        keywords, cost = dfs.keywords_for_app(
            store_app_id, platform=platform, country=country, language=language, limit=limit
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    payload = {
        "app_id": store_app_id,
        "platform": platform,
        "country": country,
        "cost_usd": round(cost, 4),
        "keyword_count": len(keywords),
        "keywords": [k.as_dict() for k in keywords],
    }

    if competitors:
        rivals, rival_cost = dfs.app_competitors(
            store_app_id, platform=platform, country=country, language=language
        )
        payload["competitors"] = rivals
        payload["cost_usd"] = round(cost + rival_cost, 4)

    if out:
        Path(out).write_text(
            json.dumps({k.keyword: k.search_volume for k in keywords if k.search_volume}, indent=2)
        )

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(f"\n{store_app_id} [{platform}/{country}] — {len(keywords)} keywords (${payload['cost_usd']})")
    click.echo("-" * 60)
    if not keywords:
        click.echo("  No store keywords. The app ranks for nothing here — that IS the finding.")
    for k in keywords[:30]:
        click.echo(f"  {k.search_volume or 0:>7}  {k.keyword}")
    if len(keywords) > 30:
        click.echo(f"  … {len(keywords) - 30} more (use --json)")
    for rival in payload.get("competitors", [])[:10]:
        click.echo(f"  rival: {rival['title']} ({rival['app_id']}) — {rival['intersections']} shared")
    if out:
        click.echo(f"\nVolumes written to {out}")


@aso.command("validate")
@click.option("--keywords-file", required=True, type=click.Path(exists=True),
              help="JSON: a list of keywords, or {cluster: [keywords]}")
@click.option("--store-app-id", required=True, help="Our Apple numeric app id / Play package name")
@click.option("--bundle-id", required=True, help="Registered bundle id (for the DB row)")
@click.option("--product", default="salta", help="Product name if the app isn't registered yet")
@click.option("--platform", type=click.Choice(VALID_PLATFORMS), default="ios")
@click.option("--country", default="us", help="Country code (default: us)")
@click.option("--language", default="en", help="Language code (default: en)")
@click.option("--volumes", type=click.Path(exists=True), help="{keyword: volume} JSON from `aso mine --out`")
@click.option("--max-cost", default=1.00, help="Abort if the run would exceed this (default: $1.00)")
@click.option("--db", default=str(DEFAULT_DB), help="Path to aso.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def validate_cmd(keywords_file, store_app_id, bundle_id, product, platform, country,
                 language, volumes, max_cost, db, as_json):
    """Score candidate keywords on demand + winnability, and call target/watch/kill.

    Pulls a live store SERP per keyword (the only non-modelled signal available),
    reads our own rank out of it, joins any mined volumes, and persists the run so
    next month's cycle can diff against it.

    Example:
        aitools aso validate --keywords-file product/marketing/aso/clusters-en.json \\
          --store-app-id 6761076847 --bundle-id com.salta.uno --platform ios
    """
    from . import dfs, validate as validator

    keywords, clusters = _load_keywords(Path(keywords_file))
    if not keywords:
        raise click.ClickException(f"{keywords_file} contains no keywords")

    # $0.0012 per SERP task — refuse to start a run that would blow the budget.
    estimated = len(keywords) * 0.0012
    if estimated > max_cost:
        raise click.ClickException(
            f"{len(keywords)} keywords ≈ ${estimated:.3f} > --max-cost ${max_cost:.2f}. "
            "Trim the list or raise the cap."
        )

    volume_map = json.loads(Path(volumes).read_text()) if volumes else {}

    click.echo(f"Pulling {len(keywords)} store SERPs (~${estimated:.3f})… this takes a minute.")
    try:
        candidates, cost = validator.validate(
            keywords,
            our_app_id=store_app_id,
            platform=platform,
            country=country,
            language=language,
            clusters=clusters,
            volumes=volume_map,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    aso_db = AsoDb(Path(db))
    app_row = aso_db.add_app(bundle_id, product, platform, country)
    aso_db.save_candidates(app_row, [c.as_dict() for c in candidates])
    aso_db.close()

    counts = validator.summarize(candidates)
    payload = {
        "platform": platform,
        "country": country,
        "cost_usd": round(cost, 4),
        "summary": counts,
        "candidates": [c.as_dict() for c in candidates],
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(f"\nValidated {len(candidates)} keywords [{platform}/{country}] — ${cost:.3f}")
    click.echo(
        f"  target {counts['target']} · watch {counts['watch']} · "
        f"kill {counts['kill']} · unknown {counts['unknown']}"
    )
    click.echo("-" * 78)
    click.echo(f"  {'verdict':<8} {'diff':>5} {'vol':>6} {'rank':>5}  keyword")
    order = {"target": 0, "watch": 1, "unknown": 2, "kill": 3}
    for c in sorted(candidates, key=lambda x: (order[x.verdict], x.difficulty or 999)):
        rank = str(c.our_rank) if c.our_rank else "—"
        vol = str(c.search_volume) if c.search_volume is not None else "?"
        diff = f"{c.difficulty:.0f}" if c.difficulty is not None else "?"
        click.echo(f"  {c.verdict:<8} {diff:>5} {vol:>6} {rank:>5}  {c.keyword}")
    click.echo("\nVolumes are DataForSEO estimates, not store truth — use them to rank")
    click.echo("candidates against each other, never as absolute demand.")
