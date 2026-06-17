"""CLI for App Store Connect analytics (downloads + product page views)."""

import csv
import json
import sys

import click

from . import auth, reports


@click.group(name="app-store-connect")
def app_store_connect():
    """App Store Connect analytics — downloads + product page views.

    Auth: ASC_KEY_ID + ASC_ISSUER_ID (env or credentials/app_store_connect/.env);
    the .p8 key defaults to ~/.appstoreconnect/private_keys/AuthKey_<key_id>.p8.

    APP_ID is the numeric App Store id (e.g. 6761076847).

    Reports are generated asynchronously by Apple. Run `setup` once to start
    them, `status` to check readiness, then `downloads` / `page-views`.
    """
    pass


@app_store_connect.command("status")
@click.argument("app_id")
def status_cmd(app_id):
    """Show analytics report requests and whether data is ready."""
    requests_list = reports._list_requests(app_id)
    if not requests_list:
        click.echo("No analytics report requests yet. Run: "
                   f"aitools app-store-connect setup {app_id}")
        return
    click.echo(f"\nApp Store Connect analytics — app {app_id}")
    click.echo("─" * 60)
    for req in requests_list:
        a = req.get("attributes", {})
        click.echo(f"\nrequest {req['id']}")
        click.echo(f"  accessType: {a.get('accessType')}")
        click.echo(f"  stoppedDueToInactivity: {a.get('stoppedDueToInactivity')}")
        for name in (reports.DOWNLOADS_REPORT, reports.ENGAGEMENT_REPORT):
            rid = reports._find_report_id(req["id"], name)
            if not rid:
                click.echo(f"  {name}: (not in this request)")
                continue
            insts = auth.paginate(
                f"/v1/analyticsReports/{rid}/instances",
                {"filter[granularity]": "DAILY", "limit": 200},
            )
            dates = sorted(i["attributes"].get("processingDate", "?") for i in insts)
            if dates:
                click.echo(f"  {name}: {len(dates)} daily instances "
                           f"({dates[0]} → {dates[-1]})")
            else:
                click.echo(f"  {name}: generating (0 instances)")
    click.echo()


@app_store_connect.command("setup")
@click.argument("app_id")
def setup_cmd(app_id):
    """Create the ONGOING + ONE_TIME_SNAPSHOT report requests (idempotent)."""
    ongoing = reports.ensure_request(app_id, "ONGOING")
    snapshot = reports.ensure_request(app_id, "ONE_TIME_SNAPSHOT")
    click.echo(f"ONGOING request:        {ongoing}")
    click.echo(f"ONE_TIME_SNAPSHOT request: {snapshot}")
    click.echo("\nApple is now generating reports. Check with: "
               f"aitools app-store-connect status {app_id}")


def _metric_options(f):
    f = click.option("--json", "as_json", is_flag=True, help="Output as JSON")(f)
    f = click.option("--csv", "as_csv", is_flag=True, help="Output raw report rows as CSV")(f)
    f = click.option("--to", "date_to", required=True, help="End date (YYYY-MM-DD)")(f)
    f = click.option("--from", "date_from", required=True, help="Start date (YYYY-MM-DD)")(f)
    return f


def _emit_metric(result, as_json, as_csv, title):
    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return
    rows = result.get("rows", [])
    if as_csv:
        if not rows:
            return
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return
    rng = result["range"]
    click.echo(f"\n{title} — app {result.get('app_id','?')} ({rng['from']} → {rng['to']})")
    click.echo("─" * 60)
    daily = result.get("daily", {})
    for d, n in daily.items():
        click.echo(f"  {d}: {n}")
    click.echo("─" * 60)
    click.echo(f"  TOTAL: {result.get('total', 0)}")
    click.echo(f"  (columns: {', '.join(result.get('columns', [])) or 'n/a'})\n")


@app_store_connect.command("downloads")
@click.argument("app_id")
@_metric_options
def downloads_cmd(app_id, date_from, date_to, as_csv, as_json):
    """Total app downloads per day."""
    try:
        result = reports.downloads(app_id, date_from, date_to)
    except reports.ReportNotReady as e:
        click.echo(f"Not ready: {e}", err=True)
        raise SystemExit(2)
    result["app_id"] = app_id
    if as_json or as_csv:
        _emit_metric(result, as_json, as_csv, "Downloads")
        return
    rng = result["range"]
    click.echo(f"\nDownloads — app {app_id} ({rng['from']} → {rng['to']})")
    click.echo("(downloads = first-time + redownloads; updates excluded)")
    click.echo("─" * 60)
    daily = result["daily"]
    ft = result["daily_first_time"]
    click.echo(f"  {'date':<14}{'downloads':>11}{'first-time':>12}")
    for d in daily:
        click.echo(f"  {d:<14}{daily[d]:>11}{ft.get(d, 0):>12}")
    click.echo("─" * 60)
    click.echo(f"  total downloads:   {result['total']}")
    click.echo(f"  first-time:        {result['total_first_time']}")
    click.echo(f"  by download type:  {result['by_download_type']}")
    click.echo(f"  by territory:      {result['by_territory']}\n")


@app_store_connect.command("page-views")
@click.argument("app_id")
@_metric_options
def page_views_cmd(app_id, date_from, date_to, as_csv, as_json):
    """Product page views per day (App Store engagement)."""
    try:
        result = reports.page_views(app_id, date_from, date_to)
    except reports.ReportNotReady as e:
        click.echo(f"Not ready: {e}", err=True)
        raise SystemExit(2)
    result["app_id"] = app_id
    if as_json or as_csv:
        _emit_metric(result, as_json, as_csv, "Page views")
        return
    rng = result["range"]
    click.echo(f"\nPage views — app {app_id} ({rng['from']} → {rng['to']})")
    click.echo("(page views = Event 'Page view'; impressions/taps excluded)")
    click.echo("─" * 60)
    for d, n in result["daily"].items():
        click.echo(f"  {d}: {n}")
    click.echo("─" * 60)
    click.echo(f"  total page views:  {result['total']}")
    click.echo(f"  by page type:      {result['by_page_type']}")
    click.echo(f"  by source:         {result['by_source']}")
    click.echo(f"  (impressions:      {result['total_impressions']}; events: {result['by_event']})\n")
