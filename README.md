# AI Agent Tools

![AI Agent Tools Banner](banner.jpeg)

A Python CLI library for AI agents to interact with Gmail, Google Calendar, YouTube (channel comments + video upload), Notion, Granola, Gemini (image generation), Resend (email), Google Analytics 4, GitHub analytics, and SEO tools (Lighthouse, PageSpeed, Google Autocomplete, Serper SERP, DataForSEO keyword volume + Labs/Backlinks/AI-GEO/On-Page, GSC Intelligence). Designed to be used with Claude Code, Cursor, and other AI coding assistants.

## Why This Exists

MCPs (Model Context Protocol servers) are often limited by their schemas and don't expose the full power of the underlying APIs. This library takes a different approach:

- **Full API access**: Direct Python wrappers around official APIs
- **CLI-first**: All operations available via command line with `--json` output
- **AI-friendly**: Designed for AI agents to parse and use
- **Secure**: Credentials stored locally, never in the repo

## Installation

```bash
# Clone the repository
git clone https://github.com/jnuo/ai-agent-tools.git
cd ai-agent-tools

# Install with all dependencies
pip install -e ".[all]"

# Or install only what you need
pip install -e ".[google]"     # Google Calendar + Gmail
pip install -e ".[notion]"     # Notion API
pip install -e ".[gemini]"     # Gemini AI (image generation)
pip install -e ".[resend]"     # Resend (email inbox + send)
pip install -e ".[analytics]"  # Google Analytics 4 + GitHub stats
pip install -e ".[seo]"        # Lighthouse, PageSpeed, Autocomplete, Serper, DataForSEO
```

## Quick Start

```bash
# Google Calendar
aitools google calendar list --days 7 --json

# Gmail
aitools google mail list --max 10 --json

# YouTube channel comments (reply as the channel)
aitools google youtube comments --handle salta_app --days 7 --unanswered --json

# YouTube upload (public by default; --privacy unlisted for internal link-only shares)
aitools google youtube upload out.mp4 --title "Release v1.27" --description-file notes.md --json

# Notion Tasks
aitools notion tasks list DATABASE_ID --status "Todo" --json

# Notion Pages
aitools notion page blocks PAGE_ID --json

# Granola Meetings (macOS)
aitools granola list --json
aitools granola transcript MEETING_ID --json

# Gemini Image Generation
aitools gemini generate "A coral orange logo for a SaaS company" -o logo.png

# Resend Email
aitools resend inbox --json
aitools resend read EMAIL_ID --json
aitools resend send --from "noreply@example.com" --to "user@example.com" --subject "Hi" --body "Hello"

# Google Analytics 4
aitools analytics ga4 report PROPERTY_ID -d date -m sessions,activeUsers --start 7daysAgo --json

# GitHub Analytics
aitools analytics github stats owner/repo --json
aitools analytics github traffic owner/repo --json

# SEO — Lighthouse Audit
aitools seo lighthouse https://example.com --json

# SEO — PageSpeed Insights (no API key required, optional for higher rate limits)
aitools seo pagespeed https://example.com --strategy desktop --json

# SEO — Google Autocomplete (free, no API key)
aitools seo autocomplete "blood test tracking" --json

# SEO — Serper SERP Analysis
aitools seo serper "kan tahlili takip" --country tr --lang tr --json

# SEO — DataForSEO Keyword Volume
aitools seo volume "buy laptop" "cheap laptops" --json
aitools seo volume "laptop kaufen" -c de -l de --json

# SEO — DataForSEO Labs (competitor keywords, difficulty, ideas, intent)
aitools seo ranked-keywords todoist.com -c us -l en          # keywords a domain ranks for
aitools seo kd "daily planner" "todo list app" --json        # real keyword difficulty 0-100
aitools seo keyword-ideas "daily planner" --limit 30         # broad ideas + volume
aitools seo keyword-suggestions "daily planner" --json       # long-tails containing the seed
aitools seo intent "daily planner" "buy planner app"         # info/nav/commercial/transactional

# SEO — DataForSEO Backlinks (authority pillar; rank ≈ DR)
aitools seo backlinks todoist.com                            # domain rank, backlinks, ref domains
aitools seo referring-domains todoist.com --limit 20 --json

# SEO — DataForSEO AI Optimization (GEO / AI-search visibility)
aitools seo ai-answer "best daily planner app"               # does an LLM mention you?
aitools seo ai-volume "daily planner" --json                 # how often a keyword is asked in AI chats

# SEO — DataForSEO On-Page (instant single-page technical audit)
aitools seo onpage https://getsalta.app --json

# SEO — GSC Intelligence (store, trend, search Google Search Console data)
aitools seo gsc add-site "sc-domain:example.com" "my-product"
aitools seo gsc import /tmp/gsc_data.json --site "sc-domain:example.com" --start 2026-02-19 --end 2026-03-19
aitools seo gsc trends --site "sc-domain:example.com" --json
aitools seo gsc search "keyword" --json
aitools seo gsc stats
```

## Credentials Setup

### Google (Calendar & Gmail)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or select existing)
3. Enable Calendar API and Gmail API
4. Create OAuth 2.0 Client ID (Desktop app)
5. Download JSON and save as `credentials/google/client_secret.json`

First run will open browser for OAuth login. Token is cached in `credentials/google/token.json`.

### YouTube

Reuses the same `client_secret.json`, but authenticates **separately** — the YouTube
channel is usually owned by a different Google account than Calendar/Gmail.

1. Enable **YouTube Data API v3** in the same Google Cloud project
2. Run any `aitools google youtube ...` command
3. A browser opens **once** — sign in as the **channel owner**, not your personal account

Token is cached in `credentials/google/token_youtube.json`. Scope is
`youtube.force-ssl`, which covers read, reply, **and upload** — one consent, no
re-auth needed to start uploading. Re-authenticate with `aitools google logout --youtube`.

**Multiple channels.** Every command takes `--account NAME` to select a channel owned
by a different Google account (e.g. one per product, or a work channel):

```bash
aitools google youtube upload demo.mp4 --title "Demo" --account work   # token_youtube_work.json
aitools google logout --youtube --account work                         # re-auth just that one
```

Each name gets its own token file and its own browser consent. Without `--account`,
the default `token_youtube.json` is used.

### Google Analytics 4

Uses the same Google Cloud project but requires a separate OAuth scope. Three authentication methods:

1. **OAuth (interactive)** -- uses the same `credentials/google/client_secret.json`, stores a separate `token_analytics.json`
2. **Service account JSON string** (CI/automated):
   ```bash
   export GA4_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
   ```
3. **Service account file** (CI/automated):
   ```bash
   export GA4_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
   ```

**Setup:**

1. In [Google Cloud Console](https://console.cloud.google.com), enable the **Google Analytics Data API**
2. Grant the service account (or your OAuth user) **Viewer** access in GA4 Admin > Property Access
3. Create a free Google Cloud account -- the GA4 Data API includes **25,000 requests/day free** (no billing required)

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

### Resend

1. Go to [Resend API Keys](https://resend.com/api-keys)
2. Create a full-access API key
3. Set environment variable or create file:

```bash
# Option 1: Environment variable
export RESEND_API_KEY=re_xxx

# Option 2: Create credentials file
echo "RESEND_API_KEY=re_xxx" > credentials/resend/.env
```

### SEO — PageSpeed Insights

PageSpeed Insights works **without an API key** but has low rate limits. For higher rate limits:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable the **PageSpeed Insights API** (APIs & Services > Library)
3. Create an API key (APIs & Services > Credentials)
4. Free tier: **25,000 queries/day** at no cost

```bash
# Option 1: Pass via CLI
aitools seo pagespeed https://example.com --api-key YOUR_KEY

# Option 2: Environment variable
export PAGESPEED_API_KEY=your_key
```

### SEO — Lighthouse

Requires the Lighthouse CLI installed locally:

```bash
npm install -g lighthouse
```

### SEO — Serper (SERP Analysis)

1. Go to [Serper.dev](https://serper.dev/api-key)
2. Create an API key (2,500 free queries included)
3. Set up:

```bash
# Option 1: Environment variable
export SERPER_API_KEY=your_key

# Option 2: Config file
mkdir -p ~/.config/aitools
echo "your_key" > ~/.config/aitools/serper_api_key
```

### SEO — Google Autocomplete

Free, no API key needed. Uses Google's public autocomplete endpoint.

### SEO — DataForSEO (Keyword Volume)

1. Go to [DataForSEO](https://app.dataforseo.com/api-access)
2. Get your login email and API password
3. Set up:

```bash
# Option 1: Environment variables
export DATAFORSEO_LOGIN='your-login'
export DATAFORSEO_PASSWORD='your-password'

# Option 2: Credentials file
mkdir -p credentials/seo
echo 'DATAFORSEO_LOGIN=your-login' > credentials/seo/.env
echo 'DATAFORSEO_PASSWORD=your-password' >> credentials/seo/.env
```

### App Store Connect (downloads + page views)

1. App Store Connect → Users and Access → Integrations → App Store Connect API → create a key (Admin/Finance/Sales role for analytics).
2. Save the `.p8` at `~/.appstoreconnect/private_keys/AuthKey_<KEY_ID>.p8`.
3. Set up:

```bash
mkdir -p credentials/app_store_connect
echo 'ASC_KEY_ID=XXXXXXXXXX' > credentials/app_store_connect/.env
echo 'ASC_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' >> credentials/app_store_connect/.env
# Optional: ASC_PRIVATE_KEY_PATH if the .p8 lives elsewhere.
```

### Play Store (installs + store-listing performance)

1. Play Console → Download reports → Statistics → "Copy Cloud Storage URI" (`pubsite_prod_...`).
2. A service account with read access to that bucket (Play auto-grants linked accounts; else grant Storage Object Viewer).
3. Set up:

```bash
mkdir -p credentials/play_store
cp /path/to/service-account.json credentials/play_store/service-account.json
echo 'PLAY_REPORTS_BUCKET=pubsite_prod_XXXXXXXXXXXXXXXXXXX' > credentials/play_store/.env
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

### YouTube (channel comments + video upload)

```bash
aitools google youtube comments --handle salta_app [--days 7] [--max-videos 25] [--unanswered] [--json]
aitools google youtube reply COMMENT_ID "Reply text"     # posts immediately, as the channel
aitools google youtube upload VIDEO_PATH --title "..."   # see below
aitools google logout --youtube                          # re-authenticate the YouTube account only
```

Comments are marked answered when a reply on the thread is authored by the channel
itself. `reply` posts publicly and immediately — there is no draft step.

Uses a **separate OAuth token** (`credentials/google/token_youtube.json`) because the
YouTube channel is usually owned by a different Google account than Calendar/Gmail.
Add `--account NAME` to any command to use a second channel.

#### Upload a video

Uploads to whichever channel the cached token owns. Nothing about the video is
hardcoded — title, description, tags, category, and privacy all come from flags.

```bash
aitools google youtube upload VIDEO_PATH \
  --title "..." \
  [--description "..." | --description-file NOTES.md] \
  [--tags "a,b,c"] \
  [--privacy public|private|unlisted] \
  [--category-id 28] \
  [--made-for-kids | --not-made-for-kids] \
  [--playlist "Releases"] \
  [--account NAME] \
  [--json]
```

| Flag                 | Default                     | Notes                                                                                                        |
| -------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `--privacy`          | `public`                    | `unlisted` = link-only, for internal shares. `private` = only you.                                           |
| `--category-id`      | `28` (Science & Technology) | Any id from [`videoCategories.list`](https://developers.google.com/youtube/v3/docs/videoCategories/list).    |
| `--made-for-kids`    | `--not-made-for-kids`       | Self-declared COPPA status.                                                                                  |
| `--description-file` | —                           | For long, multiline descriptions. Overrides `--description`.                                                 |
| `--playlist`         | —                           | Playlist **name or id**. A playlist miss never fails the upload — the URL is still returned, with a warning. |

**The upload publishes immediately** at the chosen privacy. It is resumable and
chunked (5 MB), so a dropped connection retries the current chunk rather than
restarting a 60 MB transfer; progress is printed as it goes.

```bash
# Public release video, description from a file
aitools google youtube upload out.mp4 \
  --title "Salta v1.27 — what's new" \
  --description-file release-notes.md \
  --tags "productivity,ai" --json

# Unlisted internal video — share the link with colleagues
aitools google youtube upload demo.mp4 \
  --title "Q3 demo (internal)" \
  --privacy unlisted --account work
```

On success it prints the **video id and URL** (structured under `--json`):

```json
{
  "status": "ok",
  "video_id": "abc123",
  "url": "https://youtube.com/watch?v=abc123",
  "privacy": "public"
}
```

**Quota.** Since June 2026 `videos.insert` has its **own daily quota bucket** —
**100 uploads/day** by default, separate from the 10,000-unit pool the read endpoints
share. (Before December 2025 an upload cost 1600 units of that shared pool, i.e. only
~6/day. That is no longer the case.)

**Scopes.** Upload needs one of `youtube.upload`, `youtube.force-ssl`, `youtube`, or
`youtubepartner`. The cached token is checked **before** any bytes are sent, so an
under-scoped token fails in a second with re-auth instructions instead of a 403
partway through the transfer.

**Shorts.** There is no "this is a Short" API flag. YouTube classifies a video as a
Short automatically from the file itself — **vertical (9:16) aspect ratio and a
duration of 3 minutes or less**. Upload a vertical clip with this same command and it
becomes a Short. (`#Shorts` in the title/description is not required for
classification; it historically only helped discovery.)

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

Reads from Granola's local cache -- no API keys needed. See [docs/granola.md](docs/granola.md) for details.

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

# Get JSON output
aitools gemini generate "Abstract art in blue tones" -o art.png --json
```

### Resend Email

```bash
aitools resend inbox [--limit 20] [--json]
aitools resend read EMAIL_ID [--json]
aitools resend send --from "noreply@example.com" --to "user@example.com" --subject "Subject" --body "Body"
```

### Google Analytics 4

Requires GA4 Data API enabled in Google Cloud (free, 25K requests/day).

```bash
# Run a report with dimensions and metrics
aitools analytics ga4 report PROPERTY_ID -d date -m sessions,activeUsers --start 7daysAgo --end yesterday --json

# Traffic by source over 90 days
aitools analytics ga4 report PROPERTY_ID -d date,sessionSource,sessionMedium -m sessions,activeUsers --start 90daysAgo --json
```

### GitHub Analytics

Uses `gh` CLI (must be authenticated via `gh auth login`).

```bash
# Repository stats (stars, forks, watchers)
aitools analytics github stats owner/repo --json

# Traffic data (views + clones, last 14 days)
aitools analytics github traffic owner/repo --json

# Popular referrers
aitools analytics github referrers owner/repo --json
```

### SEO — Lighthouse

Run local Lighthouse audits (requires `npm install -g lighthouse`).

```bash
# Full audit (performance, SEO, accessibility, best practices)
aitools seo lighthouse https://example.com --json

# Desktop-only, performance only
aitools seo lighthouse https://example.com --device desktop --category performance,seo
```

Output includes scores, Core Web Vitals, and failing audits.

### SEO — PageSpeed Insights

Run Google's PageSpeed Insights API (includes both lab data and CrUX field data).

```bash
# Mobile analysis (default)
aitools seo pagespeed https://example.com --json

# Desktop with specific categories
aitools seo pagespeed https://example.com --strategy desktop --category performance

# With API key for higher rate limits
aitools seo pagespeed https://example.com --api-key YOUR_KEY --json
```

Output includes Lighthouse scores, Core Web Vitals (LCP, TBT, CLS, FCP, SI, TTI), CrUX field data, and performance opportunities with estimated savings.

### SEO — Google Autocomplete

Free keyword research using Google's autocomplete suggestions.

```bash
# English suggestions
aitools seo autocomplete "blood test tracking" --json

# Turkish suggestions, Turkey region
aitools seo autocomplete "kan tahlili" --lang tr --country TR

# German suggestions, Germany region
aitools seo autocomplete "bluttest ergebnisse" --lang de --country DE
```

### SEO — Serper (SERP Analysis)

Search Google via Serper.dev API. Returns organic results, People Also Ask, and related searches.

```bash
# Basic search
aitools seo serper "blood test app" --num 5

# Localized search
aitools seo serper "kan tahlili takip" --country tr --lang tr --json

# News search
aitools seo serper "health tracking app" --type news --json
```

### SEO — DataForSEO (Keyword Volume)

Get search volume, CPC, and competition data for keywords using DataForSEO's Google Ads API.

```bash
# Get volume for multiple keywords
aitools seo volume "buy laptop" "cheap laptops" --json

# Localized volume (Germany, German)
aitools seo volume "laptop kaufen" -c de -l de --json

# Include SERP features info
aitools seo volume "blood test app" -s --json

# List supported countries
aitools seo countries

# List supported languages
aitools seo languages
```

Output includes search volume, CPC, competition level, competition index, and monthly search trends.

### SEO — DataForSEO (Labs, Backlinks, AI/GEO, On-Page)

Deeper DataForSEO coverage for the content, authority, GEO, and technical pillars.
All share the same credentials as `volume`. Add `--json` to any command for the
full structured output. Labs/backlinks calls cost ~$0.012–0.024 each; `ai-answer`
~$0.001; `onpage` ~$0.0002.

```bash
# Content pillar — Labs
# Keywords a competitor domain already ranks for (position, volume, KD, URL)
aitools seo ranked-keywords todoist.com -c us -l en --limit 50
# Real keyword difficulty (0-100)
aitools seo kd "daily planner" "todo list app" --json
# Category-related keyword ideas with volume
aitools seo keyword-ideas "daily planner" --limit 30
# Long-tail suggestions containing the seed phrase
aitools seo keyword-suggestions "daily planner" -c tr -l tr --json
# Search intent classification (informational/navigational/commercial/transactional)
aitools seo intent "daily planner" "buy planner app"

# Authority pillar — Backlinks (rank 0-1000 ≈ Ahrefs DR / Moz DA proxy)
aitools seo backlinks todoist.com
aitools seo referring-domains todoist.com --limit 20 --json

# GEO pillar — AI Optimization
# What an LLM actually answers to a prompt (does it mention your brand?)
aitools seo ai-answer "best daily planner app" --web-search
# How often a keyword is searched inside AI assistants
aitools seo ai-volume "daily planner" --json

# Technical pillar — On-Page (instant single-page audit)
aitools seo onpage https://getsalta.app --json
```

Labs endpoints require numeric location + language codes (handled by the same
`-c`/`-l` country/language flags as `volume`; `aitools seo countries` /
`languages` list what's supported).

### SEO — GSC Intelligence

Store Google Search Console performance data in a local SQLite database, compute month-over-month trends, and search across your properties. Inspired by [metehan777/vectordb-gsc](https://github.com/metehan777/vectordb-gsc) — thanks to Metehan for the approach of turning GSC data into a queryable local database. This implementation uses SQLite + FTS5 instead of vector embeddings for simplicity.

```bash
# Register a GSC property
aitools seo gsc add-site "sc-domain:example.com" "my-product"

# Import performance data from a JSON file (exported from GSC API/MCP)
aitools seo gsc import /tmp/gsc_data.json --site "sc-domain:example.com" --start 2026-02-19 --end 2026-03-19

# Compute month-over-month trends (rising, declining, new, lost queries)
aitools seo gsc trends --site "sc-domain:example.com"
aitools seo gsc trends --site "sc-domain:example.com" --limit 10 --json

# Full-text search across stored queries
aitools seo gsc search "blood test" --site "sc-domain:example.com"
aitools seo gsc search "etkinlik"  # search across all sites

# Database overview
aitools seo gsc stats

# List tracked sites
aitools seo gsc sites
```

The database path defaults to `~/Documents/code/RoboPM/scripts/data/gsc.db` but can be overridden with `--db /path/to/gsc.db` on any command.

**Data flow:** Pull GSC data via the Google Search Console API or MCP tool → save as JSON → import into SQLite → query trends and search.

### App Store Connect

```bash
# One-time: start the async analytics reports for an app (idempotent)
aitools app-store-connect setup 6761076847

# Check whether Apple has finished generating report instances
aitools app-store-connect status 6761076847

# Downloads + product page views per day
aitools app-store-connect downloads  6761076847 --from 2026-06-01 --to 2026-06-14
aitools app-store-connect page-views 6761076847 --from 2026-06-01 --to 2026-06-14 --json
```

App Store Connect generates these reports asynchronously; the first snapshot can take up to ~a day, and recent days lag ~1-2 days behind.

### Play Store

```bash
# Daily installs (device + user)
aitools play-store installs com.salta.dos --from 2026-06-01 --to 2026-06-14

# Store-listing visitors (page views) + acquisitions
aitools play-store store-performance com.salta.dos --from 2026-06-01 --to 2026-06-14 --json

# List report objects in the bucket (discovery)
aitools play-store ls --prefix stats/
```

Play exports monthly CSVs with a ~2-3 day lag.

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
      "Bash(*aitools gemini*)",
      "Bash(*aitools resend inbox*)",
      "Bash(*aitools resend read*)",
      "Bash(*aitools analytics*)",
      "Bash(*aitools seo*)",
      "Bash(*aitools appsflyer*)",
      "Bash(*aitools app-store-connect status*)",
      "Bash(*aitools app-store-connect downloads*)",
      "Bash(*aitools app-store-connect page-views*)",
      "Bash(*aitools play-store*)"
    ]
  }
}
```

**What this allows (no prompts):**

| Service           | Auto-allowed operations                                                                |
| ----------------- | -------------------------------------------------------------------------------------- |
| Gmail             | search, read, list, draft, labels, drafts, label create, modify, archive, batch-modify |
| Calendar          | list, get, calendars                                                                   |
| Notion            | tasks list/get/update, page get/blocks/append/update/search                            |
| Granola           | all (read-only)                                                                        |
| Gemini            | all (image generation)                                                                 |
| Resend            | inbox, read                                                                            |
| Analytics         | all GA4 reports, all GitHub stats (read-only)                                          |
| SEO               | all (lighthouse, pagespeed, autocomplete, serper, dataforseo volume — all read-only)   |
| AppsFlyer         | all (pulse, aggregate reports — read-only)                                             |
| App Store Connect | status, downloads, page-views (read-only; `setup` requires approval)                   |
| Play Store        | installs, store-performance, ls (read-only)                                            |
| Help              | all --help commands                                                                    |

**What still requires approval:**

| Service  | Requires confirmation            |
| -------- | -------------------------------- |
| Gmail    | send (if implemented), trash     |
| Calendar | create, delete                   |
| Notion   | tasks create/delete, page delete |
| Resend   | send                             |

This keeps read operations fast while protecting against accidental creates/deletes.

### Skill Setup

Create Claude Code skills for different capabilities. **Keep skills focused** -- don't put everything in one skill.

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

| Variable                   | Description                           | Default            |
| -------------------------- | ------------------------------------- | ------------------ |
| `AITOOLS_CREDENTIALS_DIR`  | Override credentials directory        | `./credentials`    |
| `AITOOLS_TIMEZONE`         | Timezone for calendar operations      | `UTC`              |
| `NOTION_API_KEY`           | Notion API key                        | (from .env file)   |
| `GEMINI_API_KEY`           | Gemini API key for image gen          | (from .env file)   |
| `RESEND_API_KEY`           | Resend API key for email              | (from .env file)   |
| `GA4_SERVICE_ACCOUNT_JSON` | GA4 service account JSON string (CI)  | --                 |
| `GA4_SERVICE_ACCOUNT_FILE` | Path to GA4 service account JSON file | --                 |
| `PAGESPEED_API_KEY`        | Google PageSpeed API key (optional)   | --                 |
| `SERPER_API_KEY`           | Serper.dev API key                    | (from config file) |
| `DATAFORSEO_LOGIN`         | DataForSEO login email                | (from .env file)   |
| `DATAFORSEO_PASSWORD`      | DataForSEO API password               | (from .env file)   |

## Security Notes

- **Never commit credentials**: The `credentials/` directory is gitignored
- **OAuth tokens are local**: Google tokens stored only on your machine
- **API keys stay private**: Notion key in env var or local .env file
- **No auto-send**: Gmail only creates drafts, never sends automatically

## Development

### Setup

```bash
# Clone and install with dev dependencies
git clone https://github.com/jnuo/ai-agent-tools.git
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

- **Unit tests** (`tests/notion/`, `tests/google/`, `tests/seo/`): Fast, mocked, run automatically in CI
- **Integration tests** (`tests/integration/`): Real API calls, run locally before PRs
- **Fixtures**: Shared test data in `tests/conftest.py`

### CI/CD

GitHub Actions runs unit tests automatically on every push and PR. Integration tests are **local-only** -- run them manually before creating PRs.

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
│   │   ├── youtube.py      # YouTube Data API (channel comments + video upload)
│   │   └── cli.py          # Google CLI commands
│   ├── notion/
│   │   ├── auth.py         # API key handling
│   │   ├── tasks.py        # Task database ops
│   │   ├── pages.py        # Page/block ops
│   │   └── cli.py          # Notion CLI commands
│   ├── granola/
│   │   ├── meetings.py     # Meeting/transcript reading
│   │   └── cli.py          # Granola CLI commands
│   ├── gemini/
│   │   ├── auth.py         # API key handling
│   │   ├── image.py        # Image generation
│   │   └── cli.py          # Gemini CLI commands
│   ├── resend/
│   │   ├── auth.py         # API key handling
│   │   ├── mail.py         # Inbox + send operations
│   │   └── cli.py          # Resend CLI commands
│   ├── analytics/
│   │   ├── auth.py         # GA4 OAuth/service account + gh CLI
│   │   ├── ga4.py          # GA4 Data API reports
│   │   ├── github.py       # GitHub traffic, stars, referrers
│   │   └── cli.py          # Analytics CLI commands
│   └── seo/
│       ├── auth.py         # DataForSEO credentials
│       ├── volume.py       # DataForSEO keyword volume
│       ├── lighthouse.py   # Local Lighthouse audit runner
│       ├── pagespeed.py    # PageSpeed Insights API v5
│       ├── autocomplete.py # Google Autocomplete suggestions
│       ├── serper.py       # Serper.dev SERP API
│       ├── gsc.py          # GSC Intelligence (SQLite storage, trends, FTS5 search)
│       ├── gsc_schema.sql  # GSC database schema
│       └── cli.py          # SEO CLI commands
├── tests/
│   ├── conftest.py         # Shared fixtures
│   ├── google/             # Google module tests
│   ├── notion/             # Notion module tests
│   ├── granola/            # Granola module tests
│   ├── seo/                # SEO module tests
│   └── integration/        # Integration tests (real API calls)
├── docs/
│   └── granola.md          # Granola setup & usage
├── .github/workflows/
│   └── test.yml            # CI workflow
├── credentials/            # (gitignored)
│   ├── google/
│   ├── notion/
│   ├── gemini/
│   ├── resend/
│   └── seo/
└── examples/
    ├── claude-skill-template.md        # Productivity skill (tasks, calendar, email)
    └── gemini-image-skill-template.md  # Image generation skill
```

## Credits

- **GSC Intelligence** module inspired by [metehan777/vectordb-gsc](https://github.com/metehan777/vectordb-gsc) — the idea of turning Google Search Console data into a local queryable database with trend detection. Our implementation swaps ChromaDB + embeddings for SQLite + FTS5 for simplicity, but the core concept of persisting GSC snapshots and computing month-over-month trends comes from Metehan's work.

## License

MIT
