"""Image generation using Google Gemini API."""

from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from .auth import require_api_key


# Default model - Imagen 4.0 Fast (good quality, faster)
DEFAULT_MODEL = "imagen-4.0-fast-generate-001"


def get_client() -> genai.Client:
    """Get authenticated Gemini client."""
    api_key = require_api_key()
    return genai.Client(api_key=api_key)


def generate_image(
    prompt: str,
    output_path: Optional[str] = None,
) -> dict:
    """Generate an image from a text prompt.

    Args:
        prompt: Text description of the image to generate
        output_path: Path to save the image (default: generated_image.png)

    Returns:
        Dict with generation results including file path
    """
    client = get_client()

    # Determine output path
    if not output_path:
        output_path = "generated_image.png"

    file_path = Path(output_path)

    # Generate image using Imagen API
    response = client.models.generate_images(
        model=DEFAULT_MODEL,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
        ),
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
        }

    return {
        "success": False,
        "error": "No image generated",
        "prompt": prompt,
        "model": DEFAULT_MODEL,
    }
