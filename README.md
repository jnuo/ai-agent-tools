# AI Agent Tools

![AI Agent Tools Banner](banner.jpeg)

A Python CLI library for AI agents to interact with Gmail, Google Calendar, Notion, Granola, and Gemini (image generation). Designed to be used with Claude Code, Cursor, and other AI coding assistants.

## Why This Exists

MCPs (Model Context Protocol servers) are often limited by their schemas and don't expose the full power of the underlying APIs. This library takes a different approach:

- **Full API access**: Direct Python wrappers around official APIs
- **CLI-first**: All operations available via command line with `--json` output
- **AI-friendly**: Designed for AI agents to parse and use
- **Secure**: Credentials stored locally, never in the repo

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-agent-tools.git
cd ai-agent-tools

# Install with all dependencies
pip install -e ".[all]"

# Or install only what you need
pip install -e ".[google]"  # Google Calendar + Gmail
pip install -e ".[notion]"  # Notion API
pip install -e ".[gemini]"  # Gemini AI (image generation)
```

## Quick Start

```bash
# Google Calendar
aitools google calendar list --days 7 --json

# Gmail
aitools google mail list --max 10 --json

# Notion Tasks
aitools notion tasks list DATABASE_ID --status "Todo" --json

# Notion Pages
aitools notion page blocks PAGE_ID --json

# Granola Meetings (macOS)
aitools granola list --json
aitools granola transcript MEETING_ID --json

# Gemini Image Generation
aitools gemini generate "A coral orange logo for a SaaS company" -o logo.png
```

## Credentials Setup

### Google (Calendar & Gmail)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or select existing)
3. Enable Calendar API and Gmail API
4. Create OAuth 2.0 Client ID (Desktop app)
5. Download JSON and save as `credentials/google/client_secret.json`

First run will open browser for OAuth login. Token is cached in `credentials/google/token.json`.

### Notion

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create new integration
3. Copy the API key
4. Set environment variable or create file:

```bash
# Option 1: Environment variable
export NOTION_API_KEY=secret_xxx

# Option 2: Create credentials file
echo "NOTION_API_KEY=secret_xxx" > credentials/notion/.env
```

5. Share your Notion pages/databases with the integration

### Gemini (Image Generation)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Set environment variable or create file:

```bash
# Option 1: Environment variable
export GEMINI_API_KEY=your_api_key

# Option 2: Create credentials file
echo "GEMINI_API_KEY=your_api_key" > credentials/gemini/.env
```

## CLI Reference

### Google Calendar

```bash
aitools google calendar list [--days 7] [--max 20] [--json]
aitools google calendar get EVENT_ID [--json]
aitools google calendar create TITLE --start "tomorrow 2pm" [--duration 60]
aitools google calendar delete EVENT_ID [--yes]
aitools google calendar calendars [--json]
```

### Gmail

```bash
aitools google mail list [--max 10] [--label INBOX] [--query "..."] [--json]
aitools google mail read MESSAGE_ID [--json]
aitools google mail draft SUBJECT --to email@example.com [--body "..."]
aitools google mail drafts [--json]
aitools google mail search "from:someone subject:important" [--json]
aitools google mail labels [--json]
aitools google mail label create NAME [--json]
aitools google mail modify MESSAGE_ID [--add-label ID] [--remove-label ID] [--json]
aitools google mail archive MESSAGE_ID [MESSAGE_ID...]
aitools google mail trash MESSAGE_ID
aitools google mail batch-modify --ids "id1,id2,id3" [--add-label ID] [--remove-label ID] [--json]
```

### Notion Tasks

```bash
aitools notion tasks list DATABASE_ID [--status Todo] [--topic work] [--priority High] [--json]
aitools notion tasks get TASK_ID [--json]
aitools notion tasks create DATABASE_ID "Task title" [--status Todo] [--priority High]
aitools notion tasks update TASK_ID [--status "In Progress"] [--priority Low]
aitools notion tasks delete TASK_ID [--yes]
```

### Notion Pages

```bash
aitools notion page get PAGE_ID [--json]
aitools notion page blocks PAGE_ID [--max 100] [--json]
aitools notion page append PAGE_ID --type paragraph --content "Text to add"
aitools notion page update PAGE_ID [--title "New Title"] [--property NAME --value VALUE] [--json]
aitools notion page delete BLOCK_ID [--yes]
aitools notion page search "query" [--type page|database] [--json]
aitools notion verify  # Test API connection
```

### Granola Meetings (macOS only)

Reads from Granola's local cache - no API keys needed. See [docs/granola.md](docs/granola.md) for details.

```bash
aitools granola list [--max 20] [--query "search term"] [--json]
aitools granola get MEETING_ID [--json]
aitools granola transcript MEETING_ID [--json] [--raw]
```

### Gemini Image Generation

Generate images from text prompts using Google's Imagen API.

```bash
aitools gemini generate "prompt text" [-o output.png] [-a ASPECT_RATIO] [--json]
```

**Aspect ratio options**: `1:1` (square, default), `3:4`, `4:3`, `9:16` (portrait), `16:9` (landscape)

Examples:

```bash
# Generate a logo (square)
aitools gemini generate "A coral orange logo for a SaaS company" -o logo.png

# Generate a wide banner (16:9 landscape)
aitools gemini generate "Abstract gradient banner" -o banner.png -a 16:9

# Generate a phone wallpaper (9:16 portrait)
aitools gemini generate "Mountain sunset wallpaper" -o wallpaper.png -a 9:16

# Generate with default filename (generated_image.png)
aitools gemini generate "Modern EV charging station"

# Get JSON output
aitools gemini generate "Abstract art in blue tones" -o art.png --json
```

## Using with Claude Code

The best way to use this library is with Claude Code. Below are recommended permission settings and skill setup.

### Recommended Permissions

To avoid being prompted for every read operation, add these to your `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(*aitools google mail search*)",
      "Bash(*aitools google mail read*)",
      "Bash(*aitools google mail list*)",
      "Bash(*aitools google mail draft*)",
      "Bash(*aitools google mail labels*)",
      "Bash(*aitools google mail label create*)",
      "Bash(*aitools google mail modify*)",
      "Bash(*aitools google mail archive*)",
      "Bash(*aitools google mail batch-modify*)",
      "Bash(*aitools google mail drafts*)",
      "Bash(*aitools google calendar list*)",
      "Bash(*aitools google calendar get*)",
      "Bash(*aitools google calendar calendars*)",
      "Bash(*aitools notion tasks list*)",
      "Bash(*aitools notion tasks get*)",
      "Bash(*aitools notion tasks update*)",
      "Bash(*aitools notion page get*)",
      "Bash(*aitools notion page blocks*)",
      "Bash(*aitools notion page append*)",
      "Bash(*aitools notion page update*)",
      "Bash(*aitools notion page search*)",
      "Bash(*aitools notion verify*)",
      "Bash(*aitools granola*)",
      "Bash(*aitools*--help*)",
      "Bash(*aitools gemini*)"
    ]
  }
}
```

**What this allows (no prompts):**
| Service | Auto-allowed operations |
|---------|------------------------|
| Gmail | search, read, list, draft, labels, drafts, label create, modify, archive, batch-modify |
| Calendar | list, get, calendars |
| Notion | tasks list/get/update, page get/blocks/append/update/search |
| Granola | all (read-only) |
| Gemini | all (image generation) |
| Help | all --help commands |

**What still requires approval:**
| Service | Requires confirmation |
|---------|----------------------|
| Gmail | send (if implemented), trash |
| Calendar | create, delete |
| Notion | tasks create/delete, page delete |

This keeps read operations fast while protecting against accidental creates/deletes.

### Skill Setup

Create Claude Code skills for different capabilities. **Keep skills focused** - don't put everything in one skill.

### 1. Install the library

```bash
pip install -e /path/to/ai-agent-tools[all]
```

### 2. Create skill files

Use the templates in `examples/`:

| Skill               | Template                         | Use Case                                |
| ------------------- | -------------------------------- | --------------------------------------- |
| **Productivity**    | `claude-skill-template.md`       | Tasks, calendar, email                  |
| **Image Generator** | `gemini-image-skill-template.md` | AI image generation (has cost warnings) |

**Example: Productivity skill**

Create `~/.claude/skills/my-productivity/SKILL.md`:

```markdown
---
name: my-productivity
description: Use when user asks about tasks, calendar, emails, or managing their schedule
---

# My Productivity Tools

This skill uses the ai-agent-tools library for Google and Notion operations.

## Configuration

- **Notion Todo Database ID**: YOUR_DATABASE_ID_HERE
- **Timezone**: Europe/Amsterdam

## Available Commands

### List my tasks

\`\`\`bash
aitools notion tasks list YOUR_DATABASE_ID --json
\`\`\`

### Create a task

\`\`\`bash
aitools notion tasks create YOUR_DATABASE_ID "Task title" --status Todo --priority High
\`\`\`

### Update task status

\`\`\`bash
aitools notion tasks update TASK_ID --status "In Progress"
\`\`\`

### List calendar events

\`\`\`bash
AITOOLS_TIMEZONE=Europe/Amsterdam aitools google calendar list --days 7 --json
\`\`\`

### Check recent emails

\`\`\`bash
aitools google mail list --max 10 --json
\`\`\`

## Task Database Schema

- Task (title): Task name
- Status: Todo, In Progress, Done
- Priority Level: High, Medium, Low
- topic: work, personal, etc.
- due date: YYYY-MM-DD
- URL: Related link
```

### 3. Use it

Now when you ask Claude "what's on my calendar?" or "add a task to buy groceries", it will use the skill to execute the appropriate commands.

## Configuration

Environment variables:

| Variable                  | Description                      | Default          |
| ------------------------- | -------------------------------- | ---------------- |
| `AITOOLS_CREDENTIALS_DIR` | Override credentials directory   | `./credentials`  |
| `AITOOLS_TIMEZONE`        | Timezone for calendar operations | `UTC`            |
| `NOTION_API_KEY`          | Notion API key                   | (from .env file) |
| `GEMINI_API_KEY`          | Gemini API key for image gen     | (from .env file) |

## Security Notes

- **Never commit credentials**: The `credentials/` directory is gitignored
- **OAuth tokens are local**: Google tokens stored only on your machine
- **API keys stay private**: Notion key in env var or local .env file
- **No auto-send**: Gmail only creates drafts, never sends automatically

## Development

### Setup

```bash
# Clone and install with dev dependencies
git clone https://github.com/yourusername/ai-agent-tools.git
cd ai-agent-tools
pip install -e ".[all,dev]"
```

### Running Tests

```bash
# Run unit tests only (fast, no API calls)
pytest -m "not integration"

# Run with coverage
pytest -m "not integration" --cov

# Run specific module tests
pytest tests/notion/test_auth.py

# Run specific test by name
pytest -k "test_create_paragraph"
```

### Integration Tests (Local Only)

Integration tests make real API calls and should be run locally before creating PRs.
Test resources are created and cleaned up automatically.

```bash
# Load credentials and run Notion integration tests
export $(cat credentials/notion/.env | xargs)
pytest -m integration tests/integration/test_notion_integration.py -v

# Run Google integration tests (requires OAuth setup first)
pytest -m integration tests/integration/test_google_integration.py -v

# Run ALL tests (unit + integration)
export $(cat credentials/notion/.env | xargs)
pytest
```

### Test Structure

- **Unit tests** (`tests/notion/`, `tests/google/`): Fast, mocked, run automatically in CI
- **Integration tests** (`tests/integration/`): Real API calls, run locally before PRs
- **Fixtures**: Shared test data in `tests/conftest.py`

### CI/CD

GitHub Actions runs unit tests automatically on every push and PR. Integration tests are **local-only** - run them manually before creating PRs.

```bash
# CI runs this automatically
pytest -m "not integration" --cov

# Run locally before PRs (requires credentials)
pytest -m integration -v
```

## Project Structure

```
ai-agent-tools/
├── src/aitools/
│   ├── cli.py              # Main entry point
│   ├── config.py           # Configuration
│   ├── google/
│   │   ├── auth.py         # OAuth handling
│   │   ├── calendar.py     # Calendar API
│   │   ├── gmail.py        # Gmail API
│   │   └── cli.py          # Google CLI commands
│   ├── notion/
│   │   ├── auth.py         # API key handling
│   │   ├── tasks.py        # Task database ops
│   │   ├── pages.py        # Page/block ops
│   │   └── cli.py          # Notion CLI commands
│   ├── granola/
│   │   ├── meetings.py     # Meeting/transcript reading
│   │   └── cli.py          # Granola CLI commands
│   └── gemini/
│       ├── auth.py         # API key handling
│       ├── image.py        # Image generation
│       └── cli.py          # Gemini CLI commands
├── tests/
│   ├── conftest.py         # Shared fixtures
│   ├── google/             # Google module tests
│   └── notion/             # Notion module tests
├── .github/workflows/
│   └── test.yml            # CI workflow
├── credentials/            # (gitignored)
│   ├── google/
│   ├── notion/
│   └── gemini/
└── examples/
    ├── claude-skill-template.md        # Productivity skill (tasks, calendar, email)
    └── gemini-image-skill-template.md  # Image generation skill
```

## License

MIT
