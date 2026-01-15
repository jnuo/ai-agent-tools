---
name: my-productivity
description: Use when user asks about tasks, todo list, calendar events, emails, schedule, inbox, or productivity management. Manages Notion tasks and Google Workspace (Calendar, Gmail).
---

# My Productivity Tools

This skill uses the `ai-agent-tools` library to manage tasks, calendar, and email.

## IMPORTANT: Use This Library, NOT MCPs

**Always use `aitools` CLI commands instead of Notion MCP or other MCPs** for:

- Notion operations (tasks, pages, blocks, search)
- Google Calendar operations
- Gmail operations

The `aitools` library provides:

- Full API access with proper error handling
- Consistent JSON output for parsing
- All block types and page operations
- Task filtering and management

**Do NOT use** `mcp__notion__*` tools when `aitools` can do the same thing.

---

## Setup

### 1. Install the library

```bash
pip install -e "/path/to/ai-agent-tools[all]"
```

### 2. Set up Notion credentials

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the API key
4. Create credentials file:

```bash
mkdir -p /path/to/ai-agent-tools/credentials/notion
echo "NOTION_API_KEY=secret_xxx" > /path/to/ai-agent-tools/credentials/notion/.env
```

5. **Share your Notion pages/databases with the integration** (click "..." menu → "Add connections")

### 3. Set up Google credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Desktop app)
3. Download JSON and save as `/path/to/ai-agent-tools/credentials/google/client_secret.json`
4. Run any Google command to trigger OAuth login:

```bash
aitools google calendar list
```

### 4. Create your skill file

Copy this template to `~/.claude/skills/my-productivity/SKILL.md` and customize it.

---

## My Configuration

<!--
CUSTOMIZE THIS SECTION with your personal settings.
Replace all [PLACEHOLDER] values with your actual IDs and preferences.
-->

**Library location**: `/path/to/ai-agent-tools`

**Timezone**: `Europe/Amsterdam` <!-- e.g., America/New_York, UTC, Asia/Tokyo -->

### My Notion Structure

<!--
DESCRIBE YOUR NOTION SETUP HERE.
This helps Claude understand where to find things and how you organize information.
Examples of what to include:
-->

**Todo Database ID**: `[YOUR_DATABASE_ID]`

- URL: https://notion.so/[YOUR_DATABASE_ID]
- This is where I track all my tasks

**Important Pages**:

- **Work Notes**: `[PAGE_ID]` - Meeting notes and project documentation
- **Personal Journal**: `[PAGE_ID]` - Daily reflections and ideas
- **Reading List**: `[PAGE_ID]` - Books and articles to read

**Project Backlogs**:

- **Project Alpha**: `[DATABASE_ID]` - Main work project backlog
- **Side Project**: `[DATABASE_ID]` - Personal project tasks

<!--
Add any other important context:
- Which databases are for work vs personal?
- Any specific workflows (e.g., "tasks with topic 'urgent' need immediate attention")
- Regular pages you reference often
-->

### Task Database Schema

| Property       | Type   | Values                       |
| -------------- | ------ | ---------------------------- |
| Task           | title  | Task name                    |
| Status         | select | Todo, In Progress, Done      |
| Priority Level | select | High, Medium, Low            |
| topic          | select | work, personal, project-name |
| due date       | date   | YYYY-MM-DD                   |
| URL            | url    | Related link                 |

---

## Commands Reference

### Notion Tasks

#### List all tasks

```bash
aitools notion tasks list [DATABASE_ID] --json
```

#### List filtered tasks

```bash
# By status
aitools notion tasks list [DATABASE_ID] --status "Todo" --json

# By priority
aitools notion tasks list [DATABASE_ID] --priority "High" --json

# By topic
aitools notion tasks list [DATABASE_ID] --topic "work" --json

# Combined filters
aitools notion tasks list [DATABASE_ID] --status "Todo" --priority "High" --json
```

#### Get single task

```bash
aitools notion tasks get [TASK_ID] --json
```

#### Create task

```bash
# Basic
aitools notion tasks create [DATABASE_ID] "Task title"

# With all options
aitools notion tasks create [DATABASE_ID] "Task title" \
  --status "Todo" \
  --priority "High" \
  --topic "work" \
  --due "2026-01-31" \
  --url "https://example.com"
```

#### Update task

```bash
# Update status
aitools notion tasks update [TASK_ID] --status "In Progress"

# Update multiple fields
aitools notion tasks update [TASK_ID] \
  --status "Done" \
  --priority "Low"
```

#### Delete task

```bash
aitools notion tasks delete [TASK_ID] --yes
```

### Notion Pages & Blocks

#### Get a page

```bash
aitools notion page get [PAGE_ID] --json
```

#### Get blocks from a page

```bash
aitools notion page blocks [PAGE_ID] --json

# Limit results
aitools notion page blocks [PAGE_ID] --max 50 --json
```

#### Search Notion

```bash
# Search all
aitools notion page search "query" --json

# Search only pages
aitools notion page search "query" --type page --json

# Search only databases
aitools notion page search "query" --type database --json
```

#### Append blocks to a page

```bash
# Paragraph (default)
aitools notion page append [PAGE_ID] --text "My paragraph text"

# Headings
aitools notion page append [PAGE_ID] --type heading1 --text "Main Heading"
aitools notion page append [PAGE_ID] --type heading2 --text "Section Heading"
aitools notion page append [PAGE_ID] --type heading3 --text "Subsection"

# Lists
aitools notion page append [PAGE_ID] --type bullet --text "Bullet point"
aitools notion page append [PAGE_ID] --type numbered --text "Numbered item"

# To-do
aitools notion page append [PAGE_ID] --type todo --text "Task to do"
aitools notion page append [PAGE_ID] --type todo --text "Completed task" --checked

# Toggle (collapsible)
aitools notion page append [PAGE_ID] --type toggle --text "Click to expand"

# Divider
aitools notion page append [PAGE_ID] --type divider

# Insert after specific block
aitools notion page append [PAGE_ID] --type bullet --text "New item" --after [BLOCK_ID]

# Advanced: Raw JSON blocks
aitools notion page append [PAGE_ID] --json-blocks '[{"type": "paragraph", ...}]'
```

**Available block types**: `paragraph`, `heading1`, `heading2`, `heading3`, `bullet`, `numbered`, `todo`, `toggle`, `divider`

#### Delete a block

```bash
aitools notion page delete [BLOCK_ID] --yes
```

#### Verify Notion connection

```bash
aitools notion verify
```

### Google Calendar

#### List events

```bash
# Next 7 days (default)
AITOOLS_TIMEZONE=[YOUR_TIMEZONE] aitools google calendar list --json

# Custom range
AITOOLS_TIMEZONE=[YOUR_TIMEZONE] aitools google calendar list --days 14 --max 50 --json
```

#### Get single event

```bash
aitools google calendar get [EVENT_ID] --json
```

#### Create event

```bash
# Basic (1 hour default)
aitools google calendar create "Meeting title" --start "tomorrow 2pm"

# With duration (minutes)
aitools google calendar create "Quick sync" --start "tomorrow 10am" --duration 30

# With end time
aitools google calendar create "Workshop" --start "Friday 9am" --end "Friday 12pm"

# With details
aitools google calendar create "Team standup" \
  --start "Monday 9:30am" \
  --duration 15 \
  --desc "Daily sync" \
  --location "Zoom"
```

#### Delete event

```bash
aitools google calendar delete [EVENT_ID] --yes
```

#### List calendars

```bash
aitools google calendar calendars --json
```

### Gmail

#### List recent emails

```bash
# Inbox (default)
aitools google mail list --json

# With options
aitools google mail list --max 20 --label "INBOX" --json

# With search query
aitools google mail list --query "from:someone@example.com" --json
```

#### Read email

```bash
aitools google mail read [MESSAGE_ID] --json
```

#### Search emails

```bash
aitools google mail search "subject:invoice has:attachment" --max 10 --json
```

#### Create draft (never sends automatically)

```bash
aitools google mail draft "Subject line" \
  --to "recipient@example.com" \
  --body "Email body text" \
  --cc "cc@example.com"
```

#### List drafts

```bash
aitools google mail drafts --json
```

#### List labels

```bash
aitools google mail labels --json
```

---

## Key Principles

- **Use `aitools` instead of MCPs** for Notion and Google operations
- Always use `--json` flag for structured output
- Parse JSON and present results in a readable format
- Gmail only creates drafts - it never sends automatically
- Notion items are archived (not permanently deleted) on delete
- Google OAuth will prompt for login on first use if needed

---

## Usage Patterns

### When user asks about tasks

1. List tasks with appropriate filters based on what they're asking
2. Parse JSON output
3. Present in readable format with status icons

### When user wants to create a task

1. Extract: title, status, priority, topic, due date from their request
2. Infer appropriate topic from context
3. Run create command with appropriate options
4. Confirm creation with task details

### When user asks about calendar

1. List events for requested time range
2. Parse and format event details
3. Highlight time, location, and important info

### When user asks about email

1. List or search emails based on request
2. Read specific messages if needed
3. Summarize content without exposing sensitive details

### When user wants to add content to Notion

1. Identify the target page ID (ask if unclear)
2. Use `aitools notion page append` with appropriate block type
3. Confirm the block was added

### When user wants to search Notion

1. Use `aitools notion page search` with user's query
2. Filter by type if they specify pages or databases
3. Present results with titles and IDs
