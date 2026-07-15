# intern_pos_emailer

A bot that **runs daily on GitHub Actions** and sends Discord alerts for **new US
software engineering internship openings** (Summer & Spring / off-cycle).
It pulls from community internship aggregators and directly from company career
sites (via their ATS APIs), filters to what you care about, remembers what it has
already shown you, and only alerts on **new** postings.

```
sources (github lists + Greenhouse/Lever/Ashby/Workday)
   → normalize → filter (internship · season · category · US)
   → dedup vs data/seen_jobs.json
   → Discord webhook alert
   → commit updated state back to the repo
```

## What it tracks
- **Roles:** internships only — Summer & Spring / off-cycle / co-op (configurable).
- **Categories:** software engineering and software development. Quant, trading,
  business, and consulting internships are excluded.
- **Location:** United States (incl. US-remote).

All of this is tunable in `config/` — no code changes needed.

## Layout
```
config/        # all tunables (no code): companies, github lists, filters, settings
src/sources/   # one module per source type (github lists + 4 ATS APIs)
src/filters.py # internship / season / category / US-location rules
src/dedup.py   # seen-jobs state (data/seen_jobs.json)
src/notify/    # Discord webhook formatting and delivery
src/apply/     # FUTURE auto-apply scaffold (not yet implemented)
src/main.py    # orchestrator + CLI
.github/workflows/daily.yml  # the daily cron
tests/         # pytest: filters + dedup
```

## Quick start (local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# See what it would send today — fetches live sources, no Discord alert or state write:
python -m src.main --dry-run
```

Add your Discord webhook URL to the gitignored `config/settings.local.yaml`:
```yaml
discord:
  webhook_url: "https://discord.com/api/webhooks/..."
```

Then test and run it:
```bash
python -m src.main --test-notify   # sends one sample Discord alert
python -m src.main                 # full run
```

**First-run tip:** with an empty `data/seen_jobs.json`, the first real run will
alert the *entire current backlog* (~hundreds of postings). If you'd
rather start clean and only get *new* postings from then on, seed the state once:
```bash
python -m src.main --seed   # marks everything currently open as "seen", sends nothing
```

Run the tests:
```bash
pytest
```

## Discord webhook
In Discord, open the target channel's **Edit Channel → Integrations → Webhooks**,
create a webhook, and copy its URL into `config/settings.local.yaml` under
`discord.webhook_url`. Local settings override `config/settings.yaml`. A webhook
URL grants permission to post in that channel, so never commit or share it.

## Deploy (private repo + daily cron)
1. Create a **private** GitHub repo and push this project.
2. Add a GitHub Actions repository secret named `DISCORD_WEBHOOK_URL`. The local
   `config/settings.local.yaml` override is used when running on your machine.
3. (Optional) Run `python -m src.main --seed` locally once and commit the updated
   `data/seen_jobs.json`, so your first scheduled alert is a small delta rather than
   the whole backlog.
4. The workflow `.github/workflows/daily.yml` runs at **13:00 UTC daily** and also
   on-demand from the **Actions tab** (`workflow_dispatch`, with a dry-run toggle).
5. Each run commits the updated `data/seen_jobs.json` back to the repo, so the bot
   remembers what it already sent.

Notes:
- Private-repo Actions get 2,000 free minutes/month; a run is ~1–2 min → effectively free.
- GitHub disables scheduled workflows after **60 days of no repo activity** — the daily
  state commit normally counts, but you can also re-trigger manually to keep it alive.
- Adjust the time by editing the `cron:` line (it's in UTC).

## Tuning
- **`config/companies.yaml`** — add companies by ATS + token. Some seed tokens are
  best-effort — run `--dry-run` and disable any that 404 (`enabled: false`).
- **`config/github_lists.yaml`** — the community `listings.json` URLs. These repos
  roll names each cycle (`Summer2026` → `Summer2027`); update the URL when the new
  cycle's repo appears.
- **`config/filters.yaml`** — keywords, allowed seasons/years, and US location terms.
- **`config/settings.yaml`** — Discord webhook and alert format, state pruning,
  suppression.

## Auto-apply (local) — implemented
`src/apply/` is a working local tool that applies to the jobs the bot finds:
opens each Greenhouse / Lever / Ashby application form in a real browser, fills
your details, generates a tailored cover letter via Gemini 2.5 Flash, and
**auto-submits simple forms while pausing for your review on forms with custom
questions**.

```bash
pip install -r requirements.txt -r requirements-apply.txt
python -m playwright install chromium
python -m src.apply --prepare-only      # safe first run: fills but never submits
python -m src.apply                     # real run (visible browser)
```

Runs on your machine (not CI) so you can watch, solve CAPTCHAs, and review before
submit. It needs your resume in `resumes/`, a filled `config/profile.yaml` (copy
`config/profile.example.yaml`), and optionally `GEMINI_API_KEY` for cover letters.
Every attempt is logged to `data/applications.json` so re-runs never double-apply.

**See [APPLYING.md](APPLYING.md) for the full guide, modes, and what to provide.**

## Legal / etiquette
Uses official public JSON APIs (Greenhouse, Lever, Ashby, Workday) and open,
community-maintained data — no scraping of LinkedIn/Indeed or other anti-bot sites.
Requests are rate-limited and retried politely. Respect each site's Terms of Service.
