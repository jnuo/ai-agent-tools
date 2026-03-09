# AI Agent Tools

Python CLI library providing AI agents access to Google Calendar, Gmail, Notion, Granola, and Gemini.

## On Session Start

1. Use `/notion` skill to check tasks with topic `aitools`
2. Show pending tasks and ask: "Work on these or something else?"

---

# Development Guidelines

This file contains guidelines for Claude Code and contributors working on this repository.

## CRITICAL: Keep Documentation In Sync

**This is a library meant for discovery and use by others.** The README and CLI help must accurately reflect ALL available features. Users should be able to see the full capabilities at a glance.

**Before completing ANY feature addition:**

1. Run `aitools --help` and all subcommand helps to verify CLI documentation
2. Ensure README.md lists ALL commands with examples
3. Update the Claude Code permissions section if new commands are added
4. Verify the Quick Start section shows the new capability

## When Adding New Features or Integrations

**Documentation Checklist** - When adding a new integration or feature, ensure you update:

1. **README.md**
   - Add to the description line at the top
   - Add installation option (if new dependency group)
   - Add to Quick Start section with example commands
   - Add Credentials Setup section (if API keys needed)
   - Add CLI Reference section with all commands
   - Update Environment Variables table
   - Update Project Structure diagram

2. **Skill Templates** (in `examples/`)
   - Create a **separate skill template** for unrelated capabilities (don't cram everything into one skill)
   - Update existing skill templates to reference the new skill
   - Keep skills focused on a single domain (productivity, image generation, meeting notes, etc.)

3. **Tests**
   - Add unit tests for the new module
   - Add integration tests if the feature makes API calls

## Skill Organization Best Practice

**Avoid putting too many capabilities into a single skill.** Claude Code works better when skills are:

- **Focused**: One domain per skill (tasks, images, meetings)
- **Discoverable**: Clear description that matches user intent
- **Lightweight**: Smaller context means faster responses

Example structure:

```
~/.claude/skills/
├── my-productivity/     # Tasks, calendar, email
│   └── SKILL.md
├── image-generator/     # Gemini image generation
│   └── SKILL.md
└── meeting-notes/       # Granola transcripts
    └── SKILL.md
```

## Project Structure

```
ai-agent-tools/
├── src/aitools/
│   ├── cli.py              # Main entry point
│   ├── config.py           # Configuration
│   ├── google/             # Gmail & Calendar
│   ├── notion/             # Tasks & Pages
│   ├── granola/            # Meeting notes (macOS)
│   ├── gemini/             # Image generation
│   ├── resend/             # Email inbox + send
│   ├── analytics/          # GA4 reports, GitHub stats
│   └── seo/                # Lighthouse, PageSpeed, Autocomplete, Serper, DataForSEO
├── tests/
│   ├── google/
│   ├── notion/
│   ├── granola/
│   └── integration/
├── docs/                   # Extended documentation
├── examples/               # Skill templates
│   ├── claude-skill-template.md        # Productivity skill
│   └── gemini-image-skill-template.md  # Image generation skill
└── credentials/            # API keys (gitignored)
```

## Claude Code Permissions Section

When adding new CLI commands, update the **"Recommended Permissions"** section in README.md:

1. **Read-only commands** (list, get, search, read) → Add to `permissions.allow`
2. **Safe write commands** (draft, update) → Add to `permissions.allow`
3. **Destructive commands** (delete, send, create) → Leave OUT of allow list (requires user approval)

This ensures Claude Code users have a smooth experience without constant permission prompts for safe operations.

## Code Style

- Use Click for CLI commands
- Return JSON with `--json` flag for AI parsing
- Handle errors gracefully with informative messages
- Keep CLI commands consistent across modules

## Testing

```bash
# Unit tests only (fast, no API calls)
pytest -m "not integration"

# Integration tests (requires credentials)
pytest -m integration -v
```
