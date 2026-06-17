"""CLI for Google Play reporting (installs + store-listing performance)."""

import json

import click

from . import auth, reports

_PKG_HELP = "Android package name (e.g. com.salta.dos)"


@click.group(name="play-store")
def play_store():
    """Google Play reporting — installs + store-listing visitors/acquisitions.

    Auth: service-account JSON at credentials/play_store/service-account.json
    (or PLAY_SERVICE_ACCOUNT_PATH) + PLAY_REPORTS_BUCKET (the pubsite_prod_...
    bucket from Play Console -> Download reports -> Statistics).
    """
    pass


def _date_options(f):
    f = click.option("--json", "as_json", is_flag=True, help="Output as JSON")(f)
    f = click.option("--to", "date_to", required=True, help="End date (YYYY-MM-DD)")(f)
    f = click.option("--from", "date_from", required=True, help="Start date (YYYY-MM-DD)")(f)
    return f


@play_store.command("installs")
@click.argument("package")
@_date_options
def installs_cmd(package, date_from, date_to, as_json):
    """Daily installs (device + user)."""
    result = reports.installs(package, date_from, date_to)
    if as_json:
        click.echo(json.dumps(result, indent=2))
        return
    rng = result["range"]
    click.echo(f"\nPlay installs — {package} ({rng['from']} → {rng['to']})")
    click.echo("─" * 60)
    click.echo(f"  {'date':<14}{'device':>10}{'user':>10}{'active':>10}")
    dd = result["daily_device_installs"]
    du = result["daily_user_installs"]
    ad = result["active_device_installs"]
    for d in dd:
        click.echo(f"  {d:<14}{dd[d]:>10}{du.get(d,0):>10}{ad.get(d,0):>10}")
    click.echo("─" * 60)
    click.echo(f"  total device installs: {result['total_device_installs']}")
    click.echo(f"  total user installs:   {result['total_user_installs']}\n")


@play_store.command("store-performance")
@click.argument("package")
@_date_options
def store_perf_cmd(package, date_from, date_to, as_json):
    """Daily store-listing visitors (page views) + acquisitions."""
    result = reports.store_performance(package, date_from, date_to)
    if as_json:
        click.echo(json.dumps(result, indent=2))
        return
    rng = result["range"]
    click.echo(f"\nPlay store performance — {package} ({rng['from']} → {rng['to']})")
    click.echo("─" * 60)
    click.echo(f"  {'date':<14}{'visitors':>10}{'acquisit.':>12}")
    v = result["daily_visitors"]
    a = result["daily_acquisitions"]
    for d in sorted(set(v) | set(a)):
        click.echo(f"  {d:<14}{v.get(d,0):>10}{a.get(d,0):>12}")
    click.echo("─" * 60)
    click.echo(f"  total visitors:     {result['total_visitors']}")
    click.echo(f"  total acquisitions: {result['total_acquisitions']}")
    click.echo(f"  conversion rate:    {result['conversion_rate']}\n")


@play_store.command("ls")
@click.option("--prefix", default="stats/", help="Object name prefix to list")
def ls_cmd(prefix):
    """List report objects in the bucket (debugging / discovery)."""
    for name in auth.list_objects(prefix):
        click.echo(name)
