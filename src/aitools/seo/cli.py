"""CLI for SEO tools (DataForSEO integration)."""

import json

import click

from . import volume


@click.group()
def seo():
    """SEO operations (keyword research via DataForSEO)."""
    pass


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
    """List supported country codes."""
    click.echo("\nSupported country codes:")
    click.echo("-" * 30)
    for code, loc_id in sorted(volume.LOCATION_CODES.items()):
        click.echo(f"  {code:<6} (location_code: {loc_id})")


@seo.command("languages")
def list_languages():
    """List supported language codes."""
    click.echo("\nSupported language codes:")
    click.echo("-" * 20)
    for code in sorted(volume.LANGUAGE_CODES.keys()):
        click.echo(f"  {code}")
