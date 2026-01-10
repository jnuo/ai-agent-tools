---
name: my-productivity
description: Use when user asks about tasks, todo list, calendar events, emails, schedule, or productivity management. This skill provides access to Notion task databases and Google Workspace (Calendar, Gmail).
---

# My Productivity Tools

This skill uses the `ai-agent-tools` library to manage tasks, calendar, and email.

## Setup

**Library location**: [YOUR_PATH_TO_AI_AGENT_TOOLS]

Ensure the library is installed:

```bash
pip install -e "[YOUR_PATH]/ai-agent-tools[all]"
```

## My Configuration

### Notion

- **Todo Database ID**: [YOUR_DATABASE_ID]
- **Database URL**: https://notion.so/[YOUR_DATABASE_ID]

### Google

- **Timezone**: [YOUR_TIMEZONE] # e.g., Europe/Amsterdam, America/New_York, UTC
- **Primary Calendar**: primary

### Task Database Schema

| Property       | Type   | Values                  |
| -------------- | ------ | ----------------------- |
| Task           | title  | Task name               |
| Status         | select | Todo, In Progress, Done |
| Priority Level | select | High, Medium, Low       |
| topic          | select | [YOUR_TOPICS]           |
| due date       | date   | YYYY-MM-DD              |
| URL            | url    | Related link            |

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
  --due "2024-12-31" \
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

# With duration
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
aitools google mail list --query "from:boss@company.com" --json
```

#### Read email

```bash
aitools google mail read [MESSAGE_ID] --json
```

#### Search emails

```bash
aitools google mail search "subject:invoice has:attachment" --max 10 --json
```

#### Create draft

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

## Usage Patterns

### When user asks about tasks

1. List tasks with appropriate filters
2. Parse JSON output
3. Present in readable format

### When user wants to create a task

1. Extract: title, status, priority, topic, due date
2. Run create command
3. Confirm creation with task ID

### When user asks about calendar

1. List events for requested time range
2. Parse and format event details
3. Highlight important info (time, location, attendees)

### When user asks about email

1. List or search emails
2. Read specific messages if needed
3. Summarize content, never expose full sensitive details

---

## Notes

- All commands support `--json` flag for structured output
- Gmail only creates drafts (never sends automatically)
- Notion tasks are archived (not permanently deleted) on delete
- Google OAuth will prompt for login on first use
