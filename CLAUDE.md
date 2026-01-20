# AI Agent Tools - Development Guidelines

This file contains guidelines for Claude Code and contributors working on this repository.

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
│   └── gemini/             # Image generation
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
