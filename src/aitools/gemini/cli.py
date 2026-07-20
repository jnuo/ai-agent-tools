"""CLI for Gemini image generation."""

import json

import click

from . import image


def _emit(result: dict, as_json: bool) -> None:
    """Print a result dict and exit non-zero on failure."""
    if as_json:
        click.echo(json.dumps(result, indent=2))
        if not result.get("success"):
            raise SystemExit(1)
        return

    if result.get("success"):
        files = result.get("files") or [result["file"]]
        for f in files:
            click.echo(f"\nGenerated: {f}")
        click.echo(f"Model: {result['model']}")
        click.echo(f"Aspect ratio: {result.get('aspect_ratio')}")
        if result.get("image_size"):
            click.echo(f"Size: {result['image_size']}")
        if result.get("text"):
            click.echo(f"Note: {result['text']}")
    else:
        click.echo(f"Error: {result.get('error', 'Unknown error')}", err=True)
        raise SystemExit(1)


@click.group()
def gemini():
    """Gemini AI operations (image generation)."""
    pass


@gemini.command("generate")
@click.argument("prompt")
@click.option("--output", "-o", default="generated_image.png", help="Output file path")
@click.option(
    "--aspect-ratio",
    "-a",
    type=click.Choice(image.ASPECT_RATIOS),
    default=None,
    help="Aspect ratio (default: 1:1 square)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def generate(prompt: str, output: str, aspect_ratio: str, as_json: bool):
    """Generate an image from a text prompt (Imagen 4.0, text-only).

    Examples:
        aitools gemini generate "A coral orange logo for a SaaS company"
        aitools gemini generate "Wide landscape banner" -o banner.png -a 16:9
    """
    try:
        result = image.generate_image(
            prompt=prompt,
            output_path=output,
            aspect_ratio=aspect_ratio,
        )
        _emit(result, as_json)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:  # noqa: BLE001
        click.echo(f"Generation failed: {e}", err=True)
        raise SystemExit(1)


@gemini.command("generate-pro")
@click.argument("prompt")
@click.option("--output", "-o", default="generated_image.png", help="Output file path")
@click.option(
    "--model",
    "-m",
    type=click.Choice(image.PRO_MODELS),
    default=image.DEFAULT_PRO_MODEL,
    help="Gemini image model (default: gemini-3-pro-image / Nano Banana Pro)",
)
@click.option(
    "--aspect-ratio",
    "-a",
    type=click.Choice(image.PRO_ASPECT_RATIOS),
    default=None,
    help="Aspect ratio (default: 1:1)",
)
@click.option(
    "--image-size",
    type=click.Choice(image.IMAGE_SIZES),
    default=None,
    help="Resolution: 1K, 2K, 4K (default: 1K)",
)
@click.option(
    "--ref",
    "reference_images",
    multiple=True,
    help="Reference image path for character/style consistency (repeatable)",
)
@click.option("--number", "-n", type=int, default=None, help="Number of candidates")
@click.option(
    "--thinking/--no-thinking",
    default=None,
    help="Force the model's thinking on/off (default: model default)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def generate_pro(
    prompt: str,
    output: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    reference_images: tuple,
    number: int,
    thinking: bool,
    as_json: bool,
):
    """Generate with Nano Banana Pro — reference images, 1K/2K/4K, character locking.

    Examples:
        aitools gemini generate-pro "two people in bed, front-on" -a 9:16 --image-size 2K
        aitools gemini generate-pro "Maria at the fish tank" --ref maria.png --ref room.png -a 9:16
        aitools gemini generate-pro "logo studies" -n 4 -o study.png
    """
    try:
        result = image.generate_image_pro(
            prompt=prompt,
            output_path=output,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            reference_images=list(reference_images) or None,
            candidate_count=number,
            thinking=thinking,
        )
        _emit(result, as_json)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:  # noqa: BLE001
        click.echo(f"Generation failed: {e}", err=True)
        raise SystemExit(1)


@gemini.command("edit")
@click.argument("prompt")
@click.option(
    "--input",
    "input_images",
    multiple=True,
    required=True,
    help="Image to edit (repeatable — first is edited, rest are extra references)",
)
@click.option("--output", "-o", default="edited_image.png", help="Output file path")
@click.option(
    "--model",
    "-m",
    type=click.Choice(image.PRO_MODELS),
    default=image.DEFAULT_PRO_MODEL,
    help="Gemini image model (default: gemini-3-pro-image)",
)
@click.option(
    "--aspect-ratio",
    "-a",
    type=click.Choice(image.PRO_ASPECT_RATIOS),
    default=None,
    help="Aspect ratio (default: keep source)",
)
@click.option(
    "--image-size",
    type=click.Choice(image.IMAGE_SIZES),
    default=None,
    help="Resolution: 1K, 2K, 4K",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def edit(
    prompt: str,
    input_images: tuple,
    output: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
    as_json: bool,
):
    """Iteratively edit / refine an existing image with a prompt.

    Examples:
        aitools gemini edit "give her a red scarf" --input frame.png -o frame-v2.png
        aitools gemini edit "same room, but morning light" --input scene.png -a 9:16
    """
    try:
        result = image.edit_image_pro(
            prompt=prompt,
            input_images=list(input_images),
            output_path=output,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        )
        _emit(result, as_json)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:  # noqa: BLE001
        click.echo(f"Generation failed: {e}", err=True)
        raise SystemExit(1)
