# Granola Integration

Read meeting notes and transcripts from [Granola](https://granola.so), the AI-powered meeting notes app.

## How It Works

Granola stores meeting data locally on your Mac in a cache file. This integration reads directly from that cache - no API keys or authentication required.

**Cache location**: `~/Library/Application Support/Granola/cache-v3.json`

## Requirements

- macOS (Granola is Mac-only)
- Granola app installed and used at least once
- No additional dependencies needed

## Commands

### List Meetings

```bash
# List recent meetings
aitools granola list --json

# Limit results
aitools granola list --max 10 --json

# Search by title
aitools granola list --query "interview" --json
```

Output includes:

- Meeting ID (needed for other commands)
- Title
- Date
- Whether transcript is available
- Whether notes are available

### Get Meeting Details

```bash
# Get meeting with notes
aitools granola get MEETING_ID --json
```

Returns:

- Title and date
- Notes (plain text)
- Overview/summary
- Whether transcript exists

### Get Transcript

```bash
# Get formatted transcript
aitools granola transcript MEETING_ID --json

# Include raw segments (for detailed analysis)
aitools granola transcript MEETING_ID --json --raw
```

The transcript is formatted with speaker labels:

- `[Me]` - Your speech (microphone audio)
- `[Them]` - Other participants (speaker audio)

## Example Workflow

```bash
# 1. Find your meeting
aitools granola list --query "standup" --json

# 2. Get meeting details
aitools granola get 690fccca-650d-44bf-a66c-8be43bfd03c5 --json

# 3. Get full transcript
aitools granola transcript 690fccca-650d-44bf-a66c-8be43bfd03c5 --json
```

## Data Available

| Field         | Source     | Description                                |
| ------------- | ---------- | ------------------------------------------ |
| `title`       | Document   | Meeting title (from calendar)              |
| `created_at`  | Document   | When meeting started                       |
| `notes`       | Document   | Formatted meeting notes                    |
| `notes_plain` | Document   | Plain text notes                           |
| `overview`    | Document   | AI-generated summary                       |
| `transcript`  | Transcript | Full conversation text                     |
| `segments`    | Transcript | Individual speech segments with timestamps |

## Using with Claude Code

Add to your productivity skill to enable meeting transcript access:

```markdown
### Granola Meetings

#### List recent meetings

\`\`\`bash
aitools granola list --max 10 --json
\`\`\`

#### Search for specific meeting

\`\`\`bash
aitools granola list --query "interview" --json
\`\`\`

#### Get meeting transcript

\`\`\`bash
aitools granola transcript MEETING_ID --json
\`\`\`
```

## Limitations

- **Mac only**: Granola is macOS-exclusive
- **Local data only**: Only accesses meetings that have been synced to your local cache
- **Read-only**: Cannot create, edit, or delete meetings through this interface
- **Speaker detection**: Granola labels speakers as "microphone" vs "speaker" audio sources, not by name

## Troubleshooting

### "Granola cache not found"

The cache file doesn't exist. Make sure:

1. Granola is installed
2. You've attended at least one meeting with Granola active
3. Granola has had time to sync

### "No transcript available"

Not all meetings have transcripts. Check:

- Was Granola actively recording during the meeting?
- Has Granola finished processing the audio?

### Meeting not appearing in list

- The meeting may be marked as deleted
- Try searching with `--query` to filter
- Check that Granola has synced (open the app)
