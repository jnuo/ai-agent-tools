"""CLI for AppsFlyer Pull API operations."""

import csv
import json
import sys

import click

from . import aggregate
from . import pulse as pulse_mod


@click.group()
def appsflyer():
    """AppsFlyer Pull API V2 (aggregate + pulse).

    Auth: APPSFLYER_API_TOKEN env var, or credentials/appsflyer/.env.
    Generate a V2 token in: Account → Security Center → API Tokens (V2).

    All commands need an APP-ID:
      iOS: "id6761076847" (numeric App Store ID prefixed with "id")
      Android: "com.salta.dos" (package name)
    """
    pass


# ---------- pulse (daily / weekly rollup) ----------


@appsflyer.command("pulse")
@click.argument("app_id")
@click.option("--day", help="ISO date (YYYY-MM-DD). Default: yesterday.")
@click.option("--weekly", is_flag=True, help="7-day rollup ending on --day (default yesterday).")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def pulse_cmd(app_id: str, day: str, weekly: bool, as_json: bool):
    """One-shot product pulse: installs + top media sources."""
    if weekly:
        result = pulse_mod.weekly_pulse(app_id, end_day=day)
    else:
        result = pulse_mod.daily_pulse(app_id, day=day)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    _print_pulse(result, weekly=weekly)


# ---------- aggregate reports ----------


@appsflyer.group()
def agg():
    """Aggregate Pull API V2 reports (partners, daily, geo)."""
    pass


def _agg_options(f):
    """Shared options decorator for aggregate commands."""
    f = click.option("--media-source", help="Filter by single media source")(f)
    f = click.option("--geo", help="Filter by single country code (e.g., TR, US)")(f)
    f = click.option("--timezone", help="Override report timezone (default: app TZ)")(f)
    f = click.option("--currency", help="'preferred' or 'USD'")(f)
    f = click.option("--json", "as_json", is_flag=True, help="Output as JSON")(f)
    f = click.option("--csv", "as_csv", is_flag=True, help="Output as raw CSV")(f)
    f = click.option("--to", "date_to", required=True, help="End date (YYYY-MM-DD)")(f)
    f = click.option("--from", "date_from", required=True, help="Start date (YYYY-MM-DD)")(f)
    return f


@agg.command("partners")
@click.argument("app_id")
@_agg_options
def agg_partners(app_id, date_from, date_to, as_csv, as_json, **kwargs):
    """Partners report — one row per media source."""
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    rows = aggregate.partners_report(app_id, date_from, date_to, **kwargs)
    _emit_rows(rows, as_json, as_csv, label="partners")


@agg.command("partners-daily")
@click.argument("app_id")
@_agg_options
def agg_partners_daily(app_id, date_from, date_to, as_csv, as_json, **kwargs):
    """Partners by date — one row per (partner, date)."""
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    rows = aggregate.partners_by_date_report(app_id, date_from, date_to, **kwargs)
    _emit_rows(rows, as_json, as_csv, label="partners-by-date")


@agg.command("daily")
@click.argument("app_id")
@_agg_options
def agg_daily(app_id, date_from, date_to, as_csv, as_json, **kwargs):
    """Daily report — one row per date."""
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    rows = aggregate.daily_report(app_id, date_from, date_to, **kwargs)
    _emit_rows(rows, as_json, as_csv, label="daily")


@agg.command("geo")
@click.argument("app_id")
@_agg_options
def agg_geo(app_id, date_from, date_to, as_csv, as_json, **kwargs):
    """Geo report — one row per country."""
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    rows = aggregate.geo_report(app_id, date_from, date_to, **kwargs)
    _emit_rows(rows, as_json, as_csv, label="geo")


@agg.command("geo-daily")
@click.argument("app_id")
@_agg_options
def agg_geo_daily(app_id, date_from, date_to, as_csv, as_json, **kwargs):
    """Geo by date — one row per (country, date)."""
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    rows = aggregate.geo_by_date_report(app_id, date_from, date_to, **kwargs)
    _emit_rows(rows, as_json, as_csv, label="geo-by-date")


# ---------- output helpers ----------


def _emit_rows(rows: list[dict], as_json: bool, as_csv: bool, label: str):
    """Emit a list of CSV-derived dicts in the requested format."""
    if as_json:
        click.echo(json.dumps(rows, indent=2, default=str))
        return

    if as_csv:
        if not rows:
            return
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return

    # Human-readable summary
    if not rows:
        click.echo(f"No {label} rows returned.")
        return

    click.echo(f"\n{label} — {len(rows)} rows")
    click.echo("─" * 60)

    # Print up to 20 rows in a compact key:value layout
    for i, row in enumerate(rows[:20]):
        click.echo(f"\n[{i + 1}]")
        for k, v in row.items():
            click.echo(f"  {k}: {v}")

    if len(rows) > 20:
        click.echo(f"\n... +{len(rows) - 20} more rows. Use --json or --csv for full output.")


def _print_pulse(result: dict, weekly: bool):
    """Human-readable pulse output."""
    app_id = result.get("app_id", "?")

    if weekly:
        rng = result.get("range", {})
        click.echo(f"\nAppsFlyer weekly pulse — {app_id} ({rng.get('from')} → {rng.get('to')})")
        click.echo("─" * 60)
        daily = result.get("daily", [])
        if daily:
            click.echo(f"\nDaily ({len(daily)} days):")
            for row in daily:
                d = row.get("Date") or row.get("date") or "?"
                inst = row.get("Installs", "?")
                click.echo(f"  {d}: {inst} installs")
        else:
            click.echo("\nNo daily data.")
    else:
        day = result.get("date", "?")
        click.echo(f"\nAppsFlyer daily pulse — {app_id} ({day})")
        click.echo("─" * 60)
        totals = result.get("totals") or {}
        if totals:
            click.echo("\nTotals:")
            for k, v in totals.items():
                click.echo(f"  {k}: {v}")
        else:
            click.echo("\nNo data for this day.")

    top = result.get("top_partners") or []
    if top:
        click.echo(f"\nTop {len(top)} partners by installs:")
        for i, row in enumerate(top, 1):
            partner = row.get("Media Source (pid)") or row.get("Media Source") or "?"
            installs = row.get("Installs", "?")
            click.echo(f"  {i}. {partner}: {installs}")
    click.echo()
