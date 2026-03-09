"""CLI for SEO tools (Lighthouse, PageSpeed, keyword volume, SERP)."""

import json

import click

from . import volume


@click.group()
def seo():
    """SEO operations (keyword research, Lighthouse, PageSpeed, SERP)."""
    pass


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
