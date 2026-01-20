---
name: image-generator
description: Use when user wants to generate, create, or make images, logos, icons, illustrations, or visual assets using AI.
---

# AI Image Generator

This skill uses the `ai-agent-tools` library with Google's Gemini/Imagen API to generate images from text prompts.

> **Note**: This is a separate skill from productivity tools. Keep skills focused on a single domain to help Claude Code find the right skill quickly.

---

## Setup

### 1. Install the library

```bash
pip install -e "/path/to/ai-agent-tools[gemini]"
```

### 2. Set up Gemini API credentials

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Set up credentials:

```bash
# Option 1: Environment variable
export GEMINI_API_KEY=your_api_key

# Option 2: Create credentials file
mkdir -p /path/to/ai-agent-tools/credentials/gemini
echo "GEMINI_API_KEY=your_api_key" > /path/to/ai-agent-tools/credentials/gemini/.env
```

### 3. Create your skill file

Copy this template to `~/.claude/skills/image-generator/SKILL.md` and customize it.

---

## My Configuration

**Library location**: `/path/to/ai-agent-tools`

**Default output directory**: `~/Pictures/generated` (customize as needed)

---

## Commands Reference

### Generate an image

```bash
aitools gemini generate "PROMPT" [-o OUTPUT_PATH] [--json]
```

### Examples

```bash
# Generate a logo
aitools gemini generate "A coral orange minimalist logo for a SaaS company called TechFlow" -o logo.png

# Generate an icon
aitools gemini generate "A simple flat icon of a calendar, blue color, white background" -o calendar-icon.png

# Generate a background image
aitools gemini generate "Abstract gradient background with purple and blue tones" -o background.png

# Generate with default filename (generated_image.png)
aitools gemini generate "Modern electric vehicle charging station, photorealistic"

# Get JSON output for parsing
aitools gemini generate "Cute cartoon cat" -o cat.png --json
```

### JSON Output Format

When using `--json`, the output looks like:

```json
{
  "success": true,
  "file": "logo.png",
  "prompt": "A coral orange minimalist logo...",
  "model": "imagen-4.0-fast-generate-001"
}
```

---

## Usage Patterns

### When user wants to create a logo

1. Ask for company/project name and style preferences if not specified
2. Generate with descriptive prompt including style, colors, and composition
3. Save to meaningful filename
4. Show the result path

### When user wants to create an icon

1. Determine the icon purpose and style (flat, 3D, outlined, etc.)
2. Include background preference in prompt (transparent, white, colored)
3. Generate and save

### When user wants to create illustrations

1. Get context about the illustration purpose
2. Include style keywords (cartoon, realistic, minimalist, etc.)
3. Generate and provide the file path

---

## Tips for Better Results

**Be specific in prompts**:

- Include style: "minimalist", "photorealistic", "cartoon", "watercolor"
- Include colors: "coral orange", "blue and white", "monochrome"
- Include composition: "centered", "with white background", "as a logo"

**Good prompt examples**:

- "A minimalist coral orange logo for a tech startup, simple geometric shapes, white background"
- "Photorealistic image of a modern electric car charging at a sleek charging station, daytime, urban setting"
- "Cute cartoon mascot of a friendly robot, flat design, vibrant colors"

**Less effective prompts**:

- "A logo" (too vague)
- "Picture of car" (lacks style and detail)

---

## Key Principles

- Always use `--json` flag when you need to parse the output
- Save images with meaningful filenames that describe the content
- Ask clarifying questions if the user's request is vague
- The model used is Imagen 4.0 Fast - good quality with fast generation
