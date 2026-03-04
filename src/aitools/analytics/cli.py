"""CLI for analytics commands."""

import json

import click


@click.group()
def analytics():
    """Analytics operations (GA4, GitHub)."""
    pass


# =============================================================================
# GA4 COMMANDS
# =============================================================================


@analytics.group()
def ga4():
    """Google Analytics 4 operations."""
    pass


@ga4.command("report")
@click.argument("property_id")
@click.option("--dimensions", "-d", required=True, help="Comma-separated dimensions (e.g., date,sessionSource)")
@click.option("--metrics", "-m", required=True, help="Comma-separated metrics (e.g., sessions,activeUsers)")
@click.option("--start", "start_date", default="28daysAgo", help="Start date (YYYY-MM-DD or relative)")
@click.option("--end", "end_date", default="yesterday", help="End date (YYYY-MM-DD or relative)")
@click.option("--limit", "-n", default=10000, help="Max rows")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def ga4_report(property_id: str, dimensions: str, metrics: str, start_date: str, end_date: str, limit: int, as_json: bool):
    """Run a GA4 report.

    Examples:

        aitools analytics ga4 report 506362940 -d date -m sessions,activeUsers --start 7daysAgo --end yesterday --json

        aitools analytics ga4 report 506362940 -d date,sessionSource,sessionMedium -m sessions,activeUsers --start 90daysAgo --json
    """
    from .ga4 import run_report

    dims = [d.strip() for d in dimensions.split(",")]
    mets = [m.strip() for m in metrics.split(",")]

    result = run_report(
        property_id=property_id,
        dimensions=dims,
        metrics=mets,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    # Pretty print
    click.echo(f"\nGA4 Report — property {property_id}")
    click.echo(f"Dimensions: {', '.join(dims)}")
    click.echo(f"Metrics: {', '.join(mets)}")
    click.echo(f"Rows: {result['row_count']}\n")

    for row in result["rows"][:20]:
        dim_str = " | ".join(row["dimension_values"])
        met_str = " | ".join(row["metric_values"])
        click.echo(f"  {dim_str}  →  {met_str}")

    if result["row_count"] > 20:
        click.echo(f"\n  ... and {result['row_count'] - 20} more rows (use --json for full output)")


# =============================================================================
# GITHUB COMMANDS
# =============================================================================


@analytics.group()
def github():
    """GitHub repository analytics."""
    pass


@github.command("stats")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def github_stats(repo: str, as_json: bool):
    """Get repository stats (stars, forks, watchers).

    Example: aitools analytics github stats jnuo/ai-agent-tools --json
    """
    from .github import get_repo_stats

    data = get_repo_stats(repo)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    click.echo(f"\n{repo}")
    click.echo(f"  Stars: {data['stars']}")
    click.echo(f"  Forks: {data['forks']}")
    click.echo(f"  Watchers: {data['watchers']}")
    click.echo(f"  Open Issues: {data['open_issues']}")


@github.command("traffic")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def github_traffic(repo: str, as_json: bool):
    """Get traffic data (views + clones, last 14 days).

    Example: aitools analytics github traffic jnuo/ai-agent-tools --json
    """
    from .github import get_traffic

    data = get_traffic(repo)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    click.echo(f"\n{repo} — Traffic (last 14 days)")
    click.echo("\n  Views:")
    for v in data["views"]:
        date = v["timestamp"][:10]
        click.echo(f"    {date}: {v['count']} ({v['uniques']} unique)")
    click.echo("\n  Clones:")
    for c in data["clones"]:
        date = c["timestamp"][:10]
        click.echo(f"    {date}: {c['count']} ({c['uniques']} unique)")


@github.command("referrers")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def github_referrers(repo: str, as_json: bool):
    """Get popular referrers.

    Example: aitools analytics github referrers jnuo/ai-agent-tools --json
    """
    from .github import get_referrers

    data = get_referrers(repo)

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    click.echo(f"\n{repo} — Top Referrers")
    for ref in data:
        click.echo(f"  {ref['referrer']}: {ref['count']} views ({ref['uniques']} unique)")
