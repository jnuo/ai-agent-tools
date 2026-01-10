# AI Agent Tools

A Python CLI library for AI agents to interact with Google and Notion APIs. Designed to be used with Claude Code, Cursor, and other AI coding assistants.

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
aitools notion page search "query" [--type page|database] [--json]
aitools notion verify  # Test API connection
```

## Using with Claude Code

The best way to use this library is with a Claude Code skill that contains your personal configuration.

### 1. Install the library

```bash
pip install -e /path/to/ai-agent-tools[all]
```

### 2. Create a skill file

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

## Security Notes

- **Never commit credentials**: The `credentials/` directory is gitignored
- **OAuth tokens are local**: Google tokens stored only on your machine
- **API keys stay private**: Notion key in env var or local .env file
- **No auto-send**: Gmail only creates drafts, never sends automatically

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
│   └── notion/
│       ├── auth.py         # API key handling
│       ├── tasks.py        # Task database ops
│       ├── pages.py        # Page/block ops
│       └── cli.py          # Notion CLI commands
├── credentials/            # (gitignored)
│   ├── google/
│   └── notion/
└── examples/
    └── claude-skill-template.md
```

## License

MIT
