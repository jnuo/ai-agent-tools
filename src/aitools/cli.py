"""AI Agent Tools - Unified CLI.

CLI for AI agents to interact with Google and Notion APIs.
"""

import click

from . import __version__


@click.group()
@click.version_option(version=__version__, prog_name="aitools")
def main():
    """AI Agent Tools - CLI for Google and Notion APIs.

    Use 'aitools <service> --help' for service-specific commands.

    Examples:
        aitools google calendar list --days 7 --json
        aitools notion tasks list DATABASE_ID --json
    """
    pass


# Lazy-load subcommands to avoid import errors if dependencies aren't installed


def _load_google():
    """Load Google CLI if dependencies are installed."""
    try:
        from .google.cli import google
        return google
    except ImportError as e:
        @click.group()
        def google():
            """Google operations (not available - install with: pip install ai-agent-tools[google])"""
            click.echo(f"Google module not available: {e}", err=True)
            click.echo("Install with: pip install ai-agent-tools[google]", err=True)
            raise SystemExit(1)
        return google


def _load_notion():
    """Load Notion CLI if dependencies are installed."""
    try:
        from .notion.cli import notion
        return notion
    except ImportError as e:
        @click.group()
        def notion():
            """Notion operations (not available - install with: pip install ai-agent-tools[notion])"""
            click.echo(f"Notion module not available: {e}", err=True)
            click.echo("Install with: pip install ai-agent-tools[notion]", err=True)
            raise SystemExit(1)
        return notion


def _load_granola():
    """Load Granola CLI (reads local Granola cache - no extra deps needed)."""
    try:
        from .granola.cli import granola
        return granola
    except ImportError as e:
        @click.group()
        def granola():
            """Granola operations (not available)"""
            click.echo(f"Granola module not available: {e}", err=True)
            raise SystemExit(1)
        return granola


def _load_gemini():
    """Load Gemini CLI if dependencies are installed."""
    try:
        from .gemini.cli import gemini
        return gemini
    except ImportError as e:
        @click.group()
        def gemini():
            """Gemini operations (not available - install with: pip install ai-agent-tools[gemini])"""
            click.echo(f"Gemini module not available: {e}", err=True)
            click.echo("Install with: pip install ai-agent-tools[gemini]", err=True)
            raise SystemExit(1)
        return gemini


def _load_resend():
    """Load Resend CLI if dependencies are installed."""
    try:
        from .resend.cli import resend
        return resend
    except ImportError as e:
        @click.group()
        def resend():
            """Resend operations (not available - install with: pip install ai-agent-tools[resend])"""
            click.echo(f"Resend module not available: {e}", err=True)
            click.echo("Install with: pip install ai-agent-tools[resend]", err=True)
            raise SystemExit(1)
        return resend


def _load_analytics():
    """Load Analytics CLI if dependencies are installed."""
    try:
        from .analytics.cli import analytics
        return analytics
    except ImportError as e:
        @click.group()
        def analytics():
            """Analytics operations (not available - install with: pip install ai-agent-tools[analytics])"""
            click.echo(f"Analytics module not available: {e}", err=True)
            click.echo("Install with: pip install ai-agent-tools[analytics]", err=True)
            raise SystemExit(1)
        return analytics


def _load_seo():
    """Load SEO CLI (Lighthouse, PageSpeed, keyword volume, SERP)."""
    try:
        from .seo.cli import seo
        return seo
    except ImportError as e:
        @click.group()
        def seo():
            """SEO operations (not available - install with: pip install ai-agent-tools[seo])"""
            click.echo(f"SEO module not available: {e}", err=True)
            click.echo("Install with: pip install ai-agent-tools[seo]", err=True)
            raise SystemExit(1)
        return seo


def _load_aso():
    """Load ASO CLI (App Store + Play Store keyword/metadata intelligence)."""
    try:
        from .aso.cli import aso
        return aso
    except ImportError as e:
        @click.group()
        def aso():
            """ASO operations (not available)."""
            click.echo(f"ASO module not available: {e}", err=True)
            raise SystemExit(1)
        return aso


def _load_app_store_connect():
    """Load App Store Connect CLI (downloads + product page views)."""
    try:
        from .app_store_connect.cli import app_store_connect
        return app_store_connect
    except ImportError as e:
        @click.group(name="app-store-connect")
        def app_store_connect():
            """App Store Connect operations (not available - missing deps: PyJWT, requests)"""
            click.echo(f"App Store Connect module not available: {e}", err=True)
            raise SystemExit(1)
        return app_store_connect


def _load_play_store():
    """Load Play Store CLI (installs + store-listing performance)."""
    try:
        from .play_store.cli import play_store
        return play_store
    except ImportError as e:
        @click.group(name="play-store")
        def play_store():
            """Play Store operations (not available - missing deps: google-auth)"""
            click.echo(f"Play Store module not available: {e}", err=True)
            raise SystemExit(1)
        return play_store


def _load_appsflyer():
    """Load AppsFlyer CLI (Pull API V2 — aggregate + pulse)."""
    try:
        from .appsflyer.cli import appsflyer
        return appsflyer
    except ImportError as e:
        @click.group()
        def appsflyer():
            """AppsFlyer operations (not available - install with: pip install ai-agent-tools[appsflyer])"""
            click.echo(f"AppsFlyer module not available: {e}", err=True)
            click.echo("Install with: pip install ai-agent-tools[appsflyer]", err=True)
            raise SystemExit(1)
        return appsflyer


# Register subcommands
main.add_command(_load_google())
main.add_command(_load_notion())
main.add_command(_load_granola())
main.add_command(_load_gemini())
main.add_command(_load_resend())
main.add_command(_load_analytics())
main.add_command(_load_seo())
main.add_command(_load_aso())
main.add_command(_load_appsflyer())
main.add_command(_load_app_store_connect())
main.add_command(_load_play_store())


if __name__ == "__main__":
    main()
