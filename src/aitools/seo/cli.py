"""CLI for SEO tools (Lighthouse, PageSpeed, keyword volume, SERP, GSC Intelligence)."""

import json
from pathlib import Path

import click

from . import ai_optim, backlinks, labs, onpage, volume
from .gsc import DEFAULT_DB, GscDb


@click.group()
def seo():
    """SEO operations (keyword research, Lighthouse, PageSpeed, SERP, GSC)."""
    pass


# =============================================================================
# GSC Intelligence
# =============================================================================

@seo.group("gsc")
def gsc_group():
    """GSC Intelligence — store, trend, and search Google Search Console data."""
    pass


@gsc_group.command("add-site")
@click.argument("url")
@click.argument("product")
@click.option("--db", default=str(DEFAULT_DB), help="Path to gsc.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gsc_add_site(url: str, product: str, db: str, as_json: bool):
    """Register a GSC property for tracking.

    Examples:
        aitools seo gsc add-site "sc-domain:viziai.app" viziai
        aitools seo gsc add-site "https://etko.app/" etko
    """
    gsc = GscDb(Path(db))
    site_id = gsc.add_site(url, product)
    gsc.close()
    if as_json:
        click.echo(json.dumps({"id": site_id, "url": url, "product": product}))
    else:
        click.echo(f"Site registered: {product} → {url} (id={site_id})")


@gsc_group.command("sites")
@click.option("--db", default=str(DEFAULT_DB), help="Path to gsc.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gsc_sites(db: str, as_json: bool):
    """List tracked GSC sites."""
    gsc = GscDb(Path(db))
    sites = gsc.list_sites()
    gsc.close()
    if as_json:
        click.echo(json.dumps(sites, indent=2))
    else:
        if not sites:
            click.echo("No sites registered. Use 'aitools seo gsc add-site' first.")
            return
        click.echo("\nTracked GSC Sites:")
        click.echo("-" * 50)
        for s in sites:
            click.echo(f"  [{s['id']}] {s['product']:<12} {s['url']}")


@gsc_group.command("import")
@click.argument("data_file", type=click.Path(exists=True))
@click.option("--site", required=True, help="GSC property URL")
@click.option("--start", "start_date", required=True, help="Period start (YYYY-MM-DD)")
@click.option("--end", "end_date", required=True, help="Period end (YYYY-MM-DD)")
@click.option("--db", default=str(DEFAULT_DB), help="Path to gsc.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gsc_import(data_file: str, site: str, start_date: str, end_date: str, db: str, as_json: bool):
    """Import GSC performance data from a JSON file.

    The JSON file should contain an array of objects with keys:
    query, page, clicks, impressions, ctr, position.

    Examples:
        aitools seo gsc import /tmp/gsc_data.json --site "sc-domain:viziai.app" --start 2026-02-19 --end 2026-03-19
    """
    gsc = GscDb(Path(db))
    with open(data_file) as f:
        rows = json.load(f)

    result = gsc.import_data(site, start_date, end_date, rows)
    gsc.close()

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"Imported {result['rows_imported']} rows for {result['site']} ({result['period']})")


@gsc_group.command("trends")
@click.option("--site", required=True, help="GSC property URL")
@click.option("--limit", default=20, help="Max results per category")
@click.option("--db", default=str(DEFAULT_DB), help="Path to gsc.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gsc_trends(site: str, limit: int, db: str, as_json: bool):
    """Show month-over-month trends for a site.

    Compares the latest two snapshots and classifies queries as:
    rising, declining, new, or lost.

    Examples:
        aitools seo gsc trends --site "sc-domain:viziai.app"
        aitools seo gsc trends --site "sc-domain:etko.app" --limit 10 --json
    """
    gsc = GscDb(Path(db))
    result = gsc.compute_trends(site, limit=limit)
    gsc.close()

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    if "error" in result:
        click.echo(f"Error: {result['error']}")
        return

    if result["mode"] == "single_snapshot":
        click.echo(f"\n{result['site']} — Single snapshot ({result['period']})")
        click.echo(f"Total rows: {result['total_rows']}")
        click.echo(f"\nTop queries by impressions:")
        click.echo(f"{'Query':<45} {'Clicks':>7} {'Impr':>8} {'Pos':>6}")
        click.echo("-" * 70)
        for r in result["top_queries"]:
            q = r["query"][:44]
            click.echo(f"{q:<45} {r['clicks']:>7} {r['impressions']:>8} {r['position']:>6.1f}")
        return

    click.echo(f"\n{result['site']} — Trends")
    click.echo(f"Current:  {result['current_period']}")
    click.echo(f"Previous: {result['previous_period']}")
    click.echo(f"Rising: {result['counts']['rising']} | Declining: {result['counts']['declining']} | New: {result['counts']['new']} | Lost: {result['counts']['lost']}")

    for category, label, extra_cols in [
        ("rising", "RISING", True),
        ("declining", "DECLINING", True),
        ("new", "NEW QUERIES", False),
        ("lost", "LOST QUERIES", False),
    ]:
        items = result[category]
        if not items:
            continue
        click.echo(f"\n{'─' * 70}")
        click.echo(f"  {label} ({len(items)})")
        click.echo(f"{'─' * 70}")

        if extra_cols:
            click.echo(f"  {'Query':<35} {'Impr Now':>9} {'Impr Prev':>10} {'Change':>8} {'Pos':>6}")
            for r in items:
                q = r["query"][:34]
                click.echo(
                    f"  {q:<35} {r['imp_now']:>9} {r['imp_prev']:>10} "
                    f"{r['imp_change_pct']:>+7.1f}% {r['pos_now']:>5.1f}"
                )
        else:
            click.echo(f"  {'Query':<40} {'Clicks':>7} {'Impr':>8} {'Pos':>6}")
            for r in items:
                q = r["query"][:39]
                click.echo(f"  {q:<40} {r['clicks']:>7} {r['impressions']:>8} {r['position']:>6.1f}")


@gsc_group.command("search")
@click.argument("text")
@click.option("--site", default=None, help="Filter by GSC property URL")
@click.option("--limit", default=20, help="Max results")
@click.option("--db", default=str(DEFAULT_DB), help="Path to gsc.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gsc_search(text: str, site: str, limit: int, db: str, as_json: bool):
    """Full-text search over stored GSC queries.

    Examples:
        aitools seo gsc search "blood test" --site "sc-domain:viziai.app"
        aitools seo gsc search "etkinlik" --json
    """
    gsc = GscDb(Path(db))
    results = gsc.search(text, site_url=site, limit=limit)
    gsc.close()

    if as_json:
        click.echo(json.dumps(results, indent=2))
        return

    if not results:
        click.echo(f"No results for '{text}'")
        return

    click.echo(f"\nSearch: '{text}' ({len(results)} results)")
    click.echo(f"{'Query':<35} {'Page':<25} {'Clicks':>7} {'Impr':>8} {'Product':<10}")
    click.echo("-" * 90)
    for r in results:
        q = r["query"][:34]
        pg = r["page"].split("/")[-1][:24] if r["page"] else ""
        click.echo(f"{q:<35} {pg:<25} {r['clicks']:>7} {r['impressions']:>8} {r['product']:<10}")


@gsc_group.command("stats")
@click.option("--db", default=str(DEFAULT_DB), help="Path to gsc.db")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def gsc_stats(db: str, as_json: bool):
    """Show database statistics."""
    gsc = GscDb(Path(db))
    result = gsc.stats()
    gsc.close()

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    if not result["sites"]:
        click.echo("Database is empty. Add sites first.")
        return

    click.echo(f"\nGSC Intelligence Database")
    click.echo(f"Total: {result['total_snapshots']} snapshots, {result['total_rows']} rows")
    click.echo("-" * 70)
    for s in result["sites"]:
        click.echo(f"  {s['product']:<12} {s['url']}")
        click.echo(f"    Snapshots: {s['snapshots']}  |  Rows: {s['total_rows']}  |  Latest: {s['latest_period']}")
        click.echo(f"    Last pulled: {s['last_pulled']}")
    click.echo()


# =============================================================================
# DataForSEO - Keyword Volume
# =============================================================================

@seo.command("volume")
@click.argument("keywords", nargs=-1, required=True)
@click.option(
    "--country", "-c",
    default="us",
    help="Country code (us, uk, de, es, tr, etc.)"
)
@click.option(
    "--language", "-l",
    default="en",
    help="Language code (en, de, es, tr, etc.)"
)
@click.option(
    "--serp-info", "-s",
    is_flag=True,
    help="Include SERP features info"
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search_volume(keywords: tuple, country: str, language: str, serp_info: bool, as_json: bool):
    """Get search volume for keywords.

    Examples:
        aitools seo volume "buy laptop" "cheap laptops"
        aitools seo volume "comprar portatil" -c es -l es --json
        aitools seo volume "laptop kaufen" -c de -l de
    """
    try:
        result = volume.get_search_volume(
            keywords=list(keywords),
            country=country,
            language=language,
            include_serp_info=serp_info,
        )

        if as_json:
            click.echo(json.dumps(result, indent=2))
            return

        if result["success"]:
            click.echo(f"\nKeyword Search Volume ({country.upper()}, {language})")
            click.echo(f"API Cost: ${result.get('cost', 0):.4f}")
            click.echo("-" * 70)

            # Header
            click.echo(f"{'Keyword':<35} {'Volume':>10} {'CPC':>8} {'Competition':>12}")
            click.echo("-" * 70)

            for kw in result["keywords"]:
                keyword = kw["keyword"][:34] if kw["keyword"] else "N/A"
                vol = kw.get("search_volume") or 0
                cpc = kw.get("cpc") or 0
                comp = kw.get("competition") or "N/A"

                click.echo(f"{keyword:<35} {vol:>10,} ${cpc:>7.2f} {comp:>12}")

            click.echo("-" * 70)
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            raise SystemExit(1)

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Failed: {e}", err=True)
        raise SystemExit(1)


# =============================================================================
# DataForSEO Labs — competitor keywords, difficulty, ideas, suggestions, intent
# =============================================================================

def _run(fn, as_json, pretty):
    """Call an API fn, handle errors, and either emit JSON or run a pretty printer."""
    try:
        result = fn()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:  # noqa: BLE001 - surface any unexpected failure to the CLI
        click.echo(f"Failed: {e}", err=True)
        raise SystemExit(1)
    if as_json:
        click.echo(json.dumps(result, indent=2))
        return
    pretty(result)


@seo.command("ranked-keywords")
@click.argument("domain")
@click.option("--country", "-c", default="us", help="Country code (us, tr, de, ...)")
@click.option("--language", "-l", default="en", help="Language code (en, tr, de, ...)")
@click.option("--limit", default=50, help="Max keywords to return")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def ranked_keywords_cmd(domain: str, country: str, language: str, limit: int, as_json: bool):
    """Keywords a domain/URL already ranks for (competitor keyword research).

    Feed a competitor's domain to mine their winnable long-tails.

    Examples:

        aitools seo ranked-keywords todoist.com -c us -l en

        aitools seo ranked-keywords notion.so --limit 100 --json
    """
    def pretty(r):
        click.echo(f"\nRanked Keywords — {r['target']} ({country.upper()}, {language})")
        click.echo(f"Total ranking keywords: {r.get('total_count'):,}  |  API Cost: ${r.get('cost', 0):.4f}")
        click.echo("-" * 90)
        click.echo(f"{'Keyword':<38} {'Pos':>4} {'Volume':>9} {'KD':>4} {'CPC':>7}")
        click.echo("-" * 90)
        for kw in r["keywords"]:
            k = (kw["keyword"] or "")[:37]
            pos = kw.get("rank_group") or 0
            vol = kw.get("search_volume") or 0
            kd = kw.get("keyword_difficulty")
            kd_s = f"{kd}" if kd is not None else "-"
            cpc = kw.get("cpc") or 0
            click.echo(f"{k:<38} {pos:>4} {vol:>9,} {kd_s:>4} ${cpc:>6.2f}")

    _run(lambda: labs.ranked_keywords(domain, country, language, limit), as_json, pretty)


@seo.command("kd")
@click.argument("keywords", nargs=-1, required=True)
@click.option("--country", "-c", default="us", help="Country code (us, tr, de, ...)")
@click.option("--language", "-l", default="en", help="Language code (en, tr, de, ...)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def kd_cmd(keywords: tuple, country: str, language: str, as_json: bool):
    """Real keyword difficulty (0-100) for one or more keywords.

    Examples:

        aitools seo kd "daily planner" "todo list app"

        aitools seo kd "gunluk planlayici" -c tr -l tr --json
    """
    def pretty(r):
        click.echo(f"\nKeyword Difficulty ({country.upper()}, {language})  |  Cost: ${r.get('cost', 0):.4f}")
        click.echo("-" * 55)
        click.echo(f"{'Keyword':<45} {'KD':>6}")
        click.echo("-" * 55)
        for kw in r["keywords"]:
            k = (kw["keyword"] or "")[:44]
            kd = kw.get("keyword_difficulty")
            click.echo(f"{k:<45} {(kd if kd is not None else '-'):>6}")

    _run(lambda: labs.keyword_difficulty(list(keywords), country, language), as_json, pretty)


def _pretty_kw_volume_table(title):
    def pretty(r):
        click.echo(f"\n{title} — {r.get('country', '').upper()}/{r.get('language', '')}")
        tc = r.get("total_count")
        tc_s = f"  |  Total available: {tc:,}" if tc else ""
        click.echo(f"API Cost: ${r.get('cost', 0):.4f}{tc_s}")
        click.echo("-" * 70)
        click.echo(f"{'Keyword':<42} {'Volume':>9} {'Comp':>8} {'CPC':>7}")
        click.echo("-" * 70)
        for kw in r["keywords"]:
            k = (kw["keyword"] or "")[:41]
            vol = kw.get("search_volume") or 0
            comp = kw.get("competition_level") or "-"
            cpc = kw.get("cpc") or 0
            click.echo(f"{k:<42} {vol:>9,} {comp:>8} ${cpc:>6.2f}")
    return pretty


@seo.command("keyword-ideas")
@click.argument("keywords", nargs=-1, required=True)
@click.option("--country", "-c", default="us", help="Country code (us, tr, de, ...)")
@click.option("--language", "-l", default="en", help="Language code (en, tr, de, ...)")
@click.option("--limit", default=50, help="Max ideas to return")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def keyword_ideas_cmd(keywords: tuple, country: str, language: str, limit: int, as_json: bool):
    """Broad, category-related keyword ideas with volume.

    Examples:

        aitools seo keyword-ideas "daily planner" --limit 30

        aitools seo keyword-ideas "kan tahlili" -c tr -l tr --json
    """
    _run(
        lambda: labs.keyword_ideas(list(keywords), country, language, limit),
        as_json, _pretty_kw_volume_table("Keyword Ideas"),
    )


@seo.command("keyword-suggestions")
@click.argument("seed")
@click.option("--country", "-c", default="us", help="Country code (us, tr, de, ...)")
@click.option("--language", "-l", default="en", help="Language code (en, tr, de, ...)")
@click.option("--limit", default=50, help="Max suggestions to return")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def keyword_suggestions_cmd(seed: str, country: str, language: str, limit: int, as_json: bool):
    """Long-tail suggestions containing the seed phrase, with volume.

    Examples:

        aitools seo keyword-suggestions "daily planner" --limit 30

        aitools seo keyword-suggestions "gunluk plan" -c tr -l tr --json
    """
    _run(
        lambda: labs.keyword_suggestions(seed, country, language, limit),
        as_json, _pretty_kw_volume_table("Keyword Suggestions"),
    )


@seo.command("intent")
@click.argument("keywords", nargs=-1, required=True)
@click.option("--language", "-l", default="en", help="Language code (en, tr, de, ...)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def intent_cmd(keywords: tuple, language: str, as_json: bool):
    """Classify keywords by search intent (info/nav/commercial/transactional).

    Examples:

        aitools seo intent "daily planner" "buy planner app"

        aitools seo intent "gunluk planlayici" -l tr --json
    """
    def pretty(r):
        click.echo(f"\nSearch Intent ({language})  |  Cost: ${r.get('cost', 0):.4f}")
        click.echo("-" * 70)
        click.echo(f"{'Keyword':<40} {'Intent':<16} {'Prob':>6}")
        click.echo("-" * 70)
        for kw in r["keywords"]:
            k = (kw["keyword"] or "")[:39]
            intent = kw.get("intent") or "-"
            prob = kw.get("probability") or 0
            click.echo(f"{k:<40} {intent:<16} {prob:>6.2f}")

    _run(lambda: labs.search_intent(list(keywords), language), as_json, pretty)


# =============================================================================
# DataForSEO Backlinks — authority pillar (domain rank ≈ DR)
# =============================================================================

@seo.command("backlinks")
@click.argument("domain")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def backlinks_cmd(domain: str, as_json: bool):
    """Backlink profile summary: domain rank, backlinks, referring domains.

    'rank' (0-1000) is DataForSEO's domain-rank — the DR/DA proxy.

    Examples:

        aitools seo backlinks todoist.com

        aitools seo backlinks getsalta.app --json
    """
    def pretty(r):
        click.echo(f"\nBacklink Profile — {r['target']}  |  Cost: ${r.get('cost', 0):.4f}")
        click.echo("-" * 55)
        click.echo(f"  Domain rank (DR proxy):   {r.get('rank')}")
        click.echo(f"  Total backlinks:          {(r.get('backlinks') or 0):,}")
        click.echo(f"  Referring domains:        {(r.get('referring_domains') or 0):,}")
        click.echo(f"  Referring main domains:   {(r.get('referring_main_domains') or 0):,}")
        click.echo(f"  Referring pages:          {(r.get('referring_pages') or 0):,}")
        click.echo(f"  Broken backlinks:         {(r.get('broken_backlinks') or 0):,}")
        click.echo(f"  Spam score:               {r.get('backlinks_spam_score')}")
        click.echo(f"  First seen:               {r.get('first_seen')}")

    _run(lambda: backlinks.summary(domain), as_json, pretty)


@seo.command("referring-domains")
@click.argument("domain")
@click.option("--limit", default=50, help="Max referring domains to return")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def referring_domains_cmd(domain: str, limit: int, as_json: bool):
    """Top referring domains for a target, ranked by domain rank.

    Examples:

        aitools seo referring-domains todoist.com --limit 20

        aitools seo referring-domains getsalta.app --json
    """
    def pretty(r):
        click.echo(f"\nReferring Domains — {r['target']}")
        click.echo(f"Total: {(r.get('total_count') or 0):,}  |  Cost: ${r.get('cost', 0):.4f}")
        click.echo("-" * 70)
        click.echo(f"{'Domain':<42} {'Rank':>5} {'Backlinks':>10} {'Spam':>5}")
        click.echo("-" * 70)
        for d in r["domains"]:
            dom = (d["domain"] or "")[:41]
            click.echo(f"{dom:<42} {(d.get('rank') or 0):>5} {(d.get('backlinks') or 0):>10,} {(d.get('spam_score') or 0):>5}")

    _run(lambda: backlinks.referring_domains(domain, limit), as_json, pretty)


# =============================================================================
# DataForSEO AI Optimization — GEO / AI-search visibility
# =============================================================================

@seo.command("ai-answer")
@click.argument("prompt")
@click.option("--model", default="gpt-4o-mini", help="LLM model name")
@click.option("--max-tokens", default=400, help="Max output tokens")
@click.option("--web-search", is_flag=True, help="Let the model use web search")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def ai_answer_cmd(prompt: str, model: str, max_tokens: int, web_search: bool, as_json: bool):
    """Get an LLM's actual answer to a prompt — the GEO 'does it mention us?' check.

    Examples:

        aitools seo ai-answer "best daily planner app"

        aitools seo ai-answer "AI life planner apps" --web-search --json
    """
    def pretty(r):
        click.echo(f"\nAI Answer ({r.get('model_name')})  |  Cost: ${r.get('cost', 0):.4f}"
                   f"  |  tokens in/out: {r.get('input_tokens')}/{r.get('output_tokens')}")
        click.echo("-" * 70)
        click.echo(r.get("answer") or "(no answer returned)")

    _run(
        lambda: ai_optim.ai_answer(prompt, model, max_tokens, web_search),
        as_json, pretty,
    )


@seo.command("ai-volume")
@click.argument("keywords", nargs=-1, required=True)
@click.option("--country", "-c", default="us", help="Country code (us, tr, de, ...)")
@click.option("--language", "-l", default="en", help="Language code (en, tr, de, ...)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def ai_volume_cmd(keywords: tuple, country: str, language: str, as_json: bool):
    """AI-assistant search volume — how often a keyword is asked inside AI chats.

    Examples:

        aitools seo ai-volume "daily planner" "todo app"

        aitools seo ai-volume "gunluk planlayici" -c tr -l tr --json
    """
    def pretty(r):
        click.echo(f"\nAI Search Volume ({country.upper()}, {language})  |  Cost: ${r.get('cost', 0):.4f}")
        click.echo("-" * 55)
        click.echo(f"{'Keyword':<42} {'AI Volume':>10}")
        click.echo("-" * 55)
        for kw in r["keywords"]:
            k = (kw["keyword"] or "")[:41]
            click.echo(f"{k:<42} {(kw.get('ai_search_volume') or 0):>10,}")

    _run(lambda: ai_optim.ai_search_volume(list(keywords), country, language), as_json, pretty)


# =============================================================================
# DataForSEO On-Page — technical pillar (instant single-page audit)
# =============================================================================

# On-page 'checks' keys where a True value reliably signals an SEO problem.
_ONPAGE_PROBLEM_CHECKS = (
    "no_title",
    "no_description",
    "no_h1_tag",
    "no_favicon",
    "no_image_alt",
    "no_doctype",
    "no_encoding_meta_tag",
    "title_too_long",
    "title_too_short",
    "duplicate_title_tag",
    "duplicate_meta_tags",
    "deprecated_html_tags",
    "is_broken",
    "is_4xx_code",
    "is_5xx_code",
    "is_redirect",
    "is_www",
    "high_loading_time",
    "has_render_blocking_resources",
    "low_content_rate",
    "small_page_size",
    "canonical_to_broken",
    "recursive_canonical",
    "has_meta_refresh_redirect",
    "https_to_http_links",
)

@seo.command("onpage")
@click.argument("url")
@click.option("--js", "enable_js", is_flag=True, help="Render JavaScript before auditing")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def onpage_cmd(url: str, enable_js: bool, as_json: bool):
    """Instant single-page technical SEO audit (title, meta, htags, checks).

    Examples:

        aitools seo onpage https://getsalta.app

        aitools seo onpage https://todoist.com --js --json
    """
    def pretty(r):
        if not r.get("success"):
            click.echo(f"\n{url}: {r.get('error')}")
            return
        click.echo(f"\nOn-Page Audit — {r['url']}  |  Cost: ${r.get('cost', 0):.4f}")
        click.echo("-" * 70)
        click.echo(f"  HTTP status:      {r.get('status_code')}")
        click.echo(f"  On-page score:    {r.get('onpage_score')}")
        click.echo(f"  Title:            {r.get('title')}")
        click.echo(f"  Description:      {(r.get('description') or '')[:100]}")
        click.echo(f"  Canonical:        {r.get('canonical')}")
        h1 = r.get("h1") or []
        click.echo(f"  H1:               {h1[0][:80] if h1 else '(none)'}")
        click.echo(f"  Internal links:   {r.get('internal_links_count')}")
        click.echo(f"  External links:   {r.get('external_links_count')}")
        click.echo(f"  Images:           {r.get('images_count')}")
        # Surface only checks whose True value is unambiguously a problem
        # (DataForSEO 'checks' semantics vary per key, so use a curated set
        # rather than guessing from the name). Full checks are in --json.
        checks = r.get("checks") or {}
        problems = [k for k in _ONPAGE_PROBLEM_CHECKS if checks.get(k) is True]
        if problems:
            click.echo(f"  Issues:           {', '.join(problems)}")

    _run(lambda: onpage.instant_page(url, enable_js), as_json, pretty)


@seo.command("countries")
def list_countries():
    """List supported country codes for volume lookup."""
    click.echo("\nSupported country codes:")
    click.echo("-" * 30)
    for code, loc_id in sorted(volume.LOCATION_CODES.items()):
        click.echo(f"  {code:<6} (location_code: {loc_id})")


@seo.command("languages")
def list_languages():
    """List supported language codes for volume lookup."""
    click.echo("\nSupported language codes:")
    click.echo("-" * 20)
    for code in sorted(volume.LANGUAGE_CODES.keys()):
        click.echo(f"  {code}")


# =============================================================================
# Lighthouse
# =============================================================================

@seo.command("lighthouse")
@click.argument("url")
@click.option("--device", type=click.Choice(["mobile", "desktop"]), default="mobile", help="Device type")
@click.option("--category", default="performance,seo,accessibility,best-practices", help="Comma-separated categories")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def lighthouse_cmd(url: str, device: str, category: str, as_json: bool):
    """Run a Lighthouse audit on a URL.

    Requires lighthouse CLI: npm install -g lighthouse

    Examples:

        aitools seo lighthouse https://example.com --json

        aitools seo lighthouse https://example.com --device desktop --category performance,seo
    """
    from .lighthouse import run_lighthouse

    categories = [c.strip() for c in category.split(",")]

    try:
        result = run_lighthouse(url=url, device=device, categories=categories)
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)

    if as_json:
        # Output everything except the raw lighthouse data
        output = {k: v for k, v in result.items() if k != "raw"}
        click.echo(json.dumps(output, indent=2))
        return

    # Pretty print
    click.echo(f"\nLighthouse Report — {result['url']}")
    click.echo(f"Device: {device}")
    click.echo(f"Fetched: {result['fetch_time']}\n")

    # Category scores
    click.echo("Scores:")
    for cat_id, cat_data in result["scores"].items():
        score = cat_data["score"]
        indicator = _score_indicator(score)
        click.echo(f"  {indicator} {cat_data['title']}: {score}")

    # Core Web Vitals
    if result["metrics"]:
        click.echo("\nCore Web Vitals & Metrics:")
        for label, metric in result["metrics"].items():
            indicator = _score_indicator(metric["score"])
            click.echo(f"  {indicator} {label}: {metric['display']}")

    # Failing audits
    if result["failing_audits"]:
        click.echo(f"\nFailing Audits ({len(result['failing_audits'])}):")
        for audit in result["failing_audits"][:15]:
            display = f" ({audit['display']})" if audit["display"] else ""
            click.echo(f"  [{audit['score']:>3}] {audit['title']}{display}")

        if len(result["failing_audits"]) > 15:
            click.echo(f"\n  ... and {len(result['failing_audits']) - 15} more (use --json for full output)")


# =============================================================================
# PageSpeed Insights
# =============================================================================

@seo.command("pagespeed")
@click.argument("url")
@click.option("--strategy", type=click.Choice(["mobile", "desktop"]), default="mobile", help="Analysis strategy")
@click.option("--category", default="performance,seo,accessibility,best-practices", help="Comma-separated categories")
@click.option("--api-key", default=None, envvar="PAGESPEED_API_KEY", help="Google API key (optional, for higher rate limits)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def pagespeed_cmd(url: str, strategy: str, category: str, api_key: str | None, as_json: bool):
    """Run PageSpeed Insights analysis on a URL.

    No API key required (optional for higher rate limits).

    Examples:

        aitools seo pagespeed https://example.com --json

        aitools seo pagespeed https://example.com --strategy desktop --category performance
    """
    from .pagespeed import run_pagespeed

    categories = [c.strip() for c in category.split(",")]

    try:
        result = run_pagespeed(
            url=url,
            strategy=strategy,
            categories=categories,
            api_key=api_key,
        )
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)

    if as_json:
        output = {k: v for k, v in result.items() if k != "raw"}
        click.echo(json.dumps(output, indent=2))
        return

    # Pretty print
    click.echo(f"\nPageSpeed Insights — {result['url']}")
    click.echo(f"Strategy: {strategy}\n")

    # Lighthouse scores
    click.echo("Scores:")
    for cat_id, cat_data in result["scores"].items():
        score = cat_data["score"]
        indicator = _score_indicator(score)
        click.echo(f"  {indicator} {cat_data['title']}: {score}")

    # Core Web Vitals
    if result["metrics"]:
        click.echo("\nLab Data (Core Web Vitals):")
        for label, metric in result["metrics"].items():
            indicator = _score_indicator(metric["score"])
            click.echo(f"  {indicator} {label}: {metric['display']}")

    # CrUX field data
    if result["field_data"]:
        click.echo(f"\nField Data (CrUX) — Overall: {result['field_overall']}")
        for metric_name, fd in result["field_data"].items():
            category_label = fd["category"]
            p = fd["percentile"]
            good_pct = round(fd["good"] * 100, 1)
            click.echo(f"  {metric_name}: p75={p} ({category_label}) — {good_pct}% good")
    else:
        click.echo("\nField Data: not available (insufficient real-user data)")

    # Opportunities
    if result["opportunities"]:
        click.echo(f"\nTop Opportunities ({len(result['opportunities'])}):")
        for opp in result["opportunities"][:10]:
            savings = ""
            if opp["savings_ms"]:
                savings = f" (save ~{opp['savings_ms']:.0f}ms)"
            click.echo(f"  - {opp['title']}{savings}")

        if len(result["opportunities"]) > 10:
            click.echo(f"\n  ... and {len(result['opportunities']) - 10} more (use --json for full output)")


# =============================================================================
# Google Autocomplete
# =============================================================================

@seo.command("autocomplete")
@click.argument("query")
@click.option("--lang", default="en", help="Language code (e.g., tr, en, es)")
@click.option("--country", default="US", help="Country code (e.g., TR, US, DE)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def autocomplete_cmd(query: str, lang: str, country: str, as_json: bool):
    """Get Google Autocomplete suggestions for a query.

    Free, no API key needed. Great for keyword research.

    Examples:

        aitools seo autocomplete "kan tahlili" --lang tr --country TR

        aitools seo autocomplete "blood test tracking" --json
    """
    from .autocomplete import get_autocomplete

    try:
        suggestions = get_autocomplete(query=query, lang=lang, country=country)
    except RuntimeError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps({"query": query, "suggestions": suggestions}, indent=2))
        return

    click.echo(f"\nAutocomplete — \"{query}\" (lang={lang}, country={country})\n")
    if suggestions:
        for i, s in enumerate(suggestions, 1):
            click.echo(f"  {i:>2}. {s}")
    else:
        click.echo("  No suggestions found.")


# =============================================================================
# Serper (Google SERP)
# =============================================================================

@seo.command("serper")
@click.argument("query")
@click.option("--country", default="us", help="Country code (e.g., tr, us, de)")
@click.option("--lang", default="en", help="Language code (e.g., tr, en, es)")
@click.option("--num", default=10, help="Number of results")
@click.option("--type", "search_type", type=click.Choice(["search", "news", "images"]), default="search", help="Search type")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def serper_cmd(query: str, country: str, lang: str, num: int, search_type: str, as_json: bool):
    """Search Google via Serper.dev API.

    Requires SERPER_API_KEY env var or ~/.config/aitools/serper_api_key file.

    Examples:

        aitools seo serper "kan tahlili takip" --country tr --lang tr --json

        aitools seo serper "blood test app" --num 5
    """
    from .serper import SerperAuthError, search_serp

    try:
        result = search_serp(
            query=query, country=country, lang=lang, num=num, search_type=search_type,
        )
    except SerperAuthError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    except (RuntimeError, ValueError) as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    # Pretty print organic results
    click.echo(f"\nSERP — \"{query}\" ({search_type}, country={country})\n")

    organic = result.get("organic", [])
    if organic:
        click.echo("Organic Results:")
        for i, r in enumerate(organic, 1):
            click.echo(f"  {i:>2}. {r.get('title', '')}")
            click.echo(f"      {r.get('link', '')}")
            snippet = r.get("snippet", "")
            if snippet:
                click.echo(f"      {snippet[:120]}")
            click.echo()

    paa = result.get("peopleAlsoAsk", [])
    if paa:
        click.echo("People Also Ask:")
        for q in paa:
            click.echo(f"  - {q.get('question', '')}")
        click.echo()

    related = result.get("relatedSearches", [])
    if related:
        click.echo("Related Searches:")
        for r in related:
            click.echo(f"  - {r.get('query', '')}")


# =============================================================================
# Helpers
# =============================================================================

def _score_indicator(score: int) -> str:
    """Return a text indicator based on score (0-100)."""
    if score >= 90:
        return "[PASS]"
    elif score >= 50:
        return "[AVG ]"
    else:
        return "[FAIL]"
