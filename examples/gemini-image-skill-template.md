---
name: image-generator
description: Use when user wants to generate, create, or make images, logos, icons, illustrations, or visual assets using AI.
---

# AI Image Generator

This skill uses the `ai-agent-tools` library with Google's Gemini/Imagen API to generate images from text prompts.

> **Note**: This is a separate skill from productivity tools. Keep skills focused on a single domain to help Claude Code find the right skill quickly.

---

## ⚠️ COST WARNING - READ FIRST

**This API costs money. NEVER generate images without explicit user confirmation.**

1. **DO NOT** call the generate command until you have gathered ALL requirements
2. **DO NOT** assume defaults - always ask about aspect ratio, style, colors
3. **DO NOT** generate multiple variations without permission
4. **ALWAYS** present the full specification and get a "yes" before generating

**If in doubt, ask more questions. It's cheaper to ask than to generate the wrong image.**

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
aitools gemini generate "PROMPT" [-o OUTPUT_PATH] [-a ASPECT_RATIO] [--json]
```

### Aspect Ratio Options

| Option | Description      | Best for                             |
| ------ | ---------------- | ------------------------------------ |
| `1:1`  | Square (default) | Logos, icons, profile pictures       |
| `4:3`  | Landscape        | Presentations, photos                |
| `3:4`  | Portrait         | Posters, flyers                      |
| `16:9` | Wide landscape   | Banners, headers, YouTube thumbnails |
| `9:16` | Tall portrait    | Phone wallpapers, Instagram stories  |

### Examples

```bash
# Generate a logo (square - default)
aitools gemini generate "A coral orange minimalist logo for a SaaS company called TechFlow" -o logo.png

# Generate a wide banner (16:9)
aitools gemini generate "Abstract gradient banner with purple and blue tones" -o banner.png -a 16:9

# Generate a phone wallpaper (9:16 portrait)
aitools gemini generate "Serene mountain sunset, vibrant colors" -o wallpaper.png -a 9:16

# Generate an icon
aitools gemini generate "A simple flat icon of a calendar, blue color, white background" -o calendar-icon.png

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
  "model": "imagen-4.0-fast-generate-001",
  "aspect_ratio": "1:1"
}
```

---

## IMPORTANT: Understand Context Before Generating

**Image generation costs money (API calls). Never call the API without fully understanding the requirements and getting user confirmation.**

### Step 1: Understand the Context

First, gather context about WHERE and HOW the image will be used:

- Is this for a website, app, presentation, social media, print?
- What's the surrounding design context?
- If for a web project, check the codebase for existing design patterns, color schemes, or dimension requirements
- If dimensions are specified in code (e.g., `width: 800px, height: 400px`), calculate the appropriate aspect ratio

**If building for a frontend project**: Use the `frontend-design` skill to understand design requirements, existing styles, and appropriate dimensions before proceeding.

### Step 2: Determine Specifications

Based on context, figure out:

1. **Aspect ratio / Dimensions**
   - Check if exact pixel dimensions are needed (derive aspect ratio from width:height)
   - Common use cases:
     - Square (1:1): logos, icons, profile pics, app icons
     - Wide (16:9): banners, headers, YouTube thumbnails, hero images
     - Portrait (9:16): phone wallpapers, Instagram stories, mobile splash screens
     - Standard (4:3): presentations, blog images
     - Standard (3:4): posters, flyers, Pinterest pins

2. **Visual style** - Based on existing design language or user preference
   - Minimalist, photorealistic, cartoon, watercolor, flat design, illustrated, etc.

3. **Colors** - Match brand colors or existing design palette

4. **File format and location** - Where should output go?

### Step 3: Confirm with User

**Before generating, present your understanding and get explicit confirmation:**

```
"Based on [context], here's what I'm planning to generate:
  - Prompt: [describe the image]
  - Aspect ratio: [ratio] because [reason]
  - Style: [style]
  - Output: [filename and location]

Should I proceed with this generation?"
```

**Only generate after the user confirms.**

### Example Workflow

```
User: "Create a hero image for the landing page"

Claude: [Checks the codebase for hero section dimensions]
        [Finds: hero section is 1920x1080, uses blue/purple gradient theme]

Claude: "I checked the landing page code. The hero section is 1920x1080 (16:9 ratio)
        and uses a blue/purple gradient theme. Here's what I'll generate:

        - Prompt: Abstract gradient background with flowing blue and purple tones, modern, clean
        - Aspect ratio: 16:9 (matches hero section)
        - Style: Abstract/modern to match site aesthetic
        - Output: ./public/images/hero-bg.png

        Should I proceed?"

User: "Yes, looks good"

Claude: [Now generates with: aitools gemini generate "..." -o ./public/images/hero-bg.png -a 16:9]
```

---

## Usage Patterns

**For ALL patterns below: NEVER skip to generation. Always complete Steps 1-3 above first.**

### When user wants to create a logo

1. **Gather context**: What's the brand/company? What industry? Where will it be used?
2. **Ask about specs**: Aspect ratio (1:1 is typical), style (minimalist, playful, corporate), colors, any symbols/concepts
3. **Confirm**: Present the full prompt and specs, wait for "yes"
4. **Only then**: Generate

### When user wants to create an icon

1. **Gather context**: What's the icon for? App icon, UI element, favicon?
2. **Ask about specs**: Size requirements, style (flat, 3D, outlined), background (transparent, white, colored)
3. **Confirm**: Present the full prompt and specs, wait for "yes"
4. **Only then**: Generate

### When user wants to create a banner/header

1. **Gather context**: Where will it be displayed? Website, social media, email?
2. **Check codebase** (if applicable): Look for existing dimensions, color schemes
3. **Ask about specs**: Confirm 16:9 (or other ratio), style, mood, any concepts to convey
4. **Confirm**: Present the full prompt and specs, wait for "yes"
5. **Only then**: Generate

### When user wants to create illustrations

1. **Gather context**: What's the illustration for? Article, presentation, app?
2. **Ask about specs**: Aspect ratio, style (cartoon, realistic, minimalist, etc.), mood, colors
3. **Confirm**: Present the full prompt and specs, wait for "yes"
4. **Only then**: Generate

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

1. **NEVER generate without explicit confirmation** - This API costs money
2. **Gather full context first** - Understand where/how the image will be used
3. **Ask about ALL specifications** - Aspect ratio, style, colors, output location
4. **Present specs and wait for "yes"** - User must explicitly approve before generation
5. **Use `--json` flag** when you need to parse the output
6. **Save with meaningful filenames** that describe the content
7. **When in doubt, ask more questions** - It's cheaper to clarify than to regenerate

The model used is Imagen 4.0 Fast - good quality with fast generation, but still costs per call.
