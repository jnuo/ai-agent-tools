"""Image generation using Google Gemini API.

Two paths, deliberately kept separate:

* ``generate_image`` — Imagen 4.0, text-only. Simple, fast, no reference images.
* ``generate_image_pro`` / ``edit_image_pro`` — Nano Banana Pro
  (``gemini-3-pro-image``) on the ``generate_content`` path. Supports reference
  images for character/style consistency, 1K/2K/4K output, the full aspect-ratio
  set, multiple candidates, and iterative editing of a prior image.
"""

from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from .auth import require_api_key


# Default model - Imagen 4.0 Fast (good quality, faster)
DEFAULT_MODEL = "imagen-4.0-fast-generate-001"

# Nano Banana Pro — GA as gemini-3-pro-image (the -preview suffix still aliases).
# Best character/text/world-knowledge tier; up to 5 characters, 4K, thinking on.
DEFAULT_PRO_MODEL = "gemini-3-pro-image"

# Cheaper/faster generalist + fastest tiers, exposed for callers that don't need Pro.
PRO_MODELS = [
    "gemini-3-pro-image",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image",
]


def get_client() -> genai.Client:
    """Get authenticated Gemini client."""
    api_key = require_api_key()
    return genai.Client(api_key=api_key)


# Aspect ratios the Imagen path accepts.
ASPECT_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]

# Aspect ratios the Gemini (generate_content) path accepts — a superset.
PRO_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
]

# image_size values for the Gemini path (uppercase K is mandatory).
IMAGE_SIZES = ["1K", "2K", "4K"]


def generate_image(
    prompt: str,
    output_path: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
) -> dict:
    """Generate an image from a text prompt (Imagen 4.0, text-only).

    Args:
        prompt: Text description of the image to generate
        output_path: Path to save the image (default: generated_image.png)
        aspect_ratio: Aspect ratio for the image (1:1, 3:4, 4:3, 9:16, 16:9)

    Returns:
        Dict with generation results including file path
    """
    client = get_client()

    # Determine output path
    if not output_path:
        output_path = "generated_image.png"

    file_path = Path(output_path)

    # Build config
    config_kwargs = {"number_of_images": 1}
    if aspect_ratio:
        if aspect_ratio not in ASPECT_RATIOS:
            return {
                "success": False,
                "error": f"Invalid aspect ratio. Must be one of: {ASPECT_RATIOS}",
                "prompt": prompt,
                "model": DEFAULT_MODEL,
            }
        config_kwargs["aspect_ratio"] = aspect_ratio

    # Generate image using Imagen API
    response = client.models.generate_images(
        model=DEFAULT_MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(**config_kwargs),
    )

    # Save the generated image
    if response.generated_images:
        generated_image = response.generated_images[0]

        # Get the image data and save it
        image = generated_image.image

        # Ensure file has correct extension
        if not file_path.suffix:
            file_path = file_path.with_suffix(".png")

        # Save using PIL-like interface
        image.save(str(file_path))

        return {
            "success": True,
            "file": str(file_path),
            "prompt": prompt,
            "model": DEFAULT_MODEL,
            "aspect_ratio": aspect_ratio or "1:1",
        }

    return {
        "success": False,
        "error": "No image generated",
        "prompt": prompt,
        "model": DEFAULT_MODEL,
    }


def _load_reference_images(paths: list[str]) -> tuple[list, Optional[str]]:
    """Open reference-image paths as PIL images.

    Returns (images, error). On any missing/unreadable path, images is empty and
    error is a message — the caller raises it loudly rather than generating a
    frame with silently-dropped references (which would break character locking).
    """
    from PIL import Image

    images = []
    for p in paths:
        fp = Path(p)
        if not fp.exists():
            return [], f"Reference image not found: {p}"
        try:
            images.append(Image.open(fp))
        except Exception as e:  # noqa: BLE001 — surface the real cause
            return [], f"Could not open reference image {p}: {e}"
    return images, None


def _output_paths(output_path: Optional[str], count: int) -> list[Path]:
    """Resolve the save path(s). Multiple candidates get a -1/-2 suffix."""
    base = Path(output_path or "generated_image.png")
    if not base.suffix:
        base = base.with_suffix(".png")
    if count <= 1:
        return [base]
    return [base.with_name(f"{base.stem}-{i + 1}{base.suffix}") for i in range(count)]


def _run_generate_content(
    *,
    client: genai.Client,
    model: str,
    contents: list,
    output_path: Optional[str],
    aspect_ratio: Optional[str],
    image_size: Optional[str],
    candidate_count: Optional[int],
    output_mime_type: Optional[str],
    thinking: Optional[bool],
    prompt: str,
) -> dict:
    """Shared generate_content → save-images path for the Pro functions.

    Nano Banana Pro rejects ``candidate_count > 1`` ("Multiple candidates is not
    enabled for this model"), so we produce N outputs by running N independent
    calls rather than asking the API for N candidates — which also gives more
    variation between them.
    """
    if aspect_ratio and aspect_ratio not in PRO_ASPECT_RATIOS:
        return {
            "success": False,
            "error": f"Invalid aspect ratio. Must be one of: {PRO_ASPECT_RATIOS}",
            "prompt": prompt,
            "model": model,
        }
    if image_size and image_size not in IMAGE_SIZES:
        return {
            "success": False,
            "error": f"Invalid image_size. Must be one of: {IMAGE_SIZES}",
            "prompt": prompt,
            "model": model,
        }

    image_config = None
    if aspect_ratio or image_size or output_mime_type:
        image_config = types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            output_mime_type=output_mime_type,
        )

    config_kwargs = {"response_modalities": ["IMAGE"]}
    if image_config is not None:
        config_kwargs["image_config"] = image_config
    if thinking is not None:
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=(-1 if thinking else 0)
        )
    config = types.GenerateContentConfig(**config_kwargs)

    count = max(1, candidate_count or 1)
    paths = _output_paths(output_path, count)
    saved: list[str] = []
    text_parts: list[str] = []

    for path in paths:
        response = client.models.generate_content(
            model=model, contents=contents, config=config
        )
        wrote = False
        for part in response.parts or []:
            if getattr(part, "inline_data", None) and not wrote:
                part.as_image().save(str(path))
                saved.append(str(path))
                wrote = True
            elif getattr(part, "text", None):
                text_parts.append(part.text)

    if not saved:
        return {
            "success": False,
            "error": "No image returned" + (f" — {' '.join(text_parts)}" if text_parts else ""),
            "prompt": prompt,
            "model": model,
        }

    return {
        "success": True,
        "file": saved[0],
        "files": saved,
        "prompt": prompt,
        "model": model,
        "aspect_ratio": aspect_ratio or "1:1",
        "image_size": image_size or "1K",
        "text": " ".join(text_parts) or None,
    }


def generate_image_pro(
    prompt: str,
    output_path: Optional[str] = None,
    *,
    model: str = DEFAULT_PRO_MODEL,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
    reference_images: Optional[list[str]] = None,
    candidate_count: Optional[int] = None,
    output_mime_type: Optional[str] = None,
    thinking: Optional[bool] = None,
) -> dict:
    """Generate an image with Nano Banana Pro (Gemini image models).

    Unlike ``generate_image`` (Imagen), this path accepts reference images for
    character/style consistency and exposes image_size + the full aspect set.

    Args:
        prompt: Text description of the image to generate.
        output_path: Where to save (default: generated_image.png). With
            candidate_count > 1, files get a -1/-2 suffix.
        model: One of PRO_MODELS (default: gemini-3-pro-image).
        aspect_ratio: One of PRO_ASPECT_RATIOS.
        image_size: "1K" | "2K" | "4K".
        reference_images: File paths whose subjects/style the output should
            match (Pro supports up to 5 characters / 6 objects).
        candidate_count: How many images to return (>1 saves multiple files).
        output_mime_type: "image/png" | "image/jpeg".
        thinking: True/False to force the model's thinking on/off (default: model default).

    Returns:
        Dict with success, file, files[], model, aspect_ratio, image_size.
    """
    client = get_client()

    contents: list = [prompt]
    if reference_images:
        images, err = _load_reference_images(reference_images)
        if err:
            return {"success": False, "error": err, "prompt": prompt, "model": model}
        contents.extend(images)

    return _run_generate_content(
        client=client,
        model=model,
        contents=contents,
        output_path=output_path,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        candidate_count=candidate_count,
        output_mime_type=output_mime_type,
        thinking=thinking,
        prompt=prompt,
    )


def edit_image_pro(
    prompt: str,
    input_images: list[str],
    output_path: Optional[str] = None,
    *,
    model: str = DEFAULT_PRO_MODEL,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
    candidate_count: Optional[int] = None,
    output_mime_type: Optional[str] = None,
    thinking: Optional[bool] = None,
) -> dict:
    """Iteratively edit / refine one or more existing images with a prompt.

    The input images carry the state to edit — pass the prior generated image
    (plus any extra reference images) and describe the change.

    Args:
        prompt: The change to make ("give her a red scarf", "same room, morning").
        input_images: File paths — the image(s) to edit, plus any references.
        (remaining args as in generate_image_pro)
    """
    if not input_images:
        return {
            "success": False,
            "error": "edit_image_pro requires at least one input image",
            "prompt": prompt,
            "model": model,
        }

    client = get_client()

    images, err = _load_reference_images(input_images)
    if err:
        return {"success": False, "error": err, "prompt": prompt, "model": model}

    # Prompt first, then the images to edit.
    contents: list = [prompt, *images]

    return _run_generate_content(
        client=client,
        model=model,
        contents=contents,
        output_path=output_path,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        candidate_count=candidate_count,
        output_mime_type=output_mime_type,
        thinking=thinking,
        prompt=prompt,
    )
