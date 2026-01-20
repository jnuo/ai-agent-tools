"""CLI for Gemini image generation."""

import json

import click

from . import image


@click.group()
def gemini():
    """Gemini AI operations (image generation)."""
    pass


@gemini.command("generate")
@click.argument("prompt")
@click.option("--output", "-o", default="generated_image.png", help="Output file path")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def generate(prompt: str, output: str, as_json: bool):
    """Generate an image from a text prompt.

    Examples:
        aitools gemini generate "A coral orange logo for a SaaS company"
        aitools gemini generate "Modern EV charging station" -o charging.png
    """
    try:
        result = image.generate_image(
            prompt=prompt,
            output_path=output,
        )

        if as_json:
            click.echo(json.dumps(result, indent=2))
            return

        if result["success"]:
            click.echo(f"\nGenerated: {result['file']}")
            click.echo(f"Model: {result['model']}")
        else:
            click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
            raise SystemExit(1)

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Generation failed: {e}", err=True)
        raise SystemExit(1)
