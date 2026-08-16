# aitrending

Automated YouTube → AI-trends watcher for **technical** channels. Runs entirely on GitHub's
servers — nothing of yours needs to be powered on.

Deliberately **separate from [`ytstock`](https://github.com/gbhambha1/ytstock)**: different
channels, different pipeline, different output document, no shared code or history. `ytstock`
tracks financial channels and produces trading commentary; this repo tracks technical channels and
produces [`AI-TRENDS.md`](AI-TRENDS.md). Changing one never affects the other.

## What runs, and when

`.github/workflows/ai-trends-pipeline.yml` runs **daily at 13:00 UTC** and can be run on demand
from the Actions tab (**Run workflow**).

Each run:

1. `fetch_videos.py` — resolves channel IDs, pulls new transcripts from the tracked channels
   (`channels.json`).
2. **Claude** — summarizes any new videos into `AI-TRENDS.md` and rewrites the **Latest themes**
   section.
3. Commits and pushes `AI-TRENDS.md`, `state.json`, `channels.json` and new transcripts.
4. **Emails you the digest** — but only when something new actually landed.

If any step fails, you get a **failure alert email** instead, with a link to the run log.

There is no DST gate and no fixed local time to hit — unlike the financial pipeline, nothing here
keys off a market close, so the exact minute doesn't matter and the schedule never needs a seasonal
edit.

## ⚠️ The proxy is not optional

**YouTube blocks datacenter IP ranges, which includes every GitHub Actions runner.** Without a
proxy, the fetch step will return 0 videos on every run while the workflow reports success — the
pipeline looks healthy and ingests nothing. (This is exactly what happened to `ytstock`, where the
transcripts all arrived via manual commits instead.)

The fix is a **residential proxy**, around $1–3/month. `youtube-transcript-api` has built-in support
for Webshare:

1. Sign up at [webshare.io](https://www.webshare.io/) and buy a residential proxy plan.
2. Copy the **proxy username and password** (not your account login).
3. Add them as repo secrets — `WEBSHARE_PROXY_USERNAME` and `WEBSHARE_PROXY_PASSWORD`.

`fetch_videos.py` picks them up automatically and routes both the RSS feed and the transcript
requests through the proxy. It also supports any generic proxy via a `YT_PROXY_URL` environment
variable.

With no proxy configured, the script prints `DIRECT connection (no proxy configured)` at startup and
the workflow emits a warning — so a silently-empty run is at least a loud one.

## Repository secrets

Settings → Secrets and variables → Actions → **New repository secret**

| Secret | Required | What it is |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (`sk-ant-api...`) |
| `GMAIL_APP_PASSWORD` | Yes | Gmail **app password** — 16 characters, *not* your normal password |
| `WEBSHARE_PROXY_USERNAME` | In practice, yes | Residential proxy username |
| `WEBSHARE_PROXY_PASSWORD` | In practice, yes | Residential proxy password |

Secrets do **not** carry over from other repositories — even if the values are identical to
`ytstock`'s, they must be added here separately.

To create the Gmail app password: Google Account → Security → 2-Step Verification (must be on) →
**App passwords** → generate one for "Mail". Paste it with the spaces removed. The SMTP login
address and the app password must belong to the *same* Google account.

Mail is sent from and to `gbhambha@intelliai.net`; override either with the `EMAIL_TO` / `EMAIL_FROM`
environment variables.

## Adding and removing channels

Edit [`channels.json`](channels.json). **You only need the `@handle`** — leave `channel_id` empty and
`fetch_videos.py` resolves it from the channel page on the next run and caches it back into the file:

```json
{
  "name": "Some Channel",
  "handle": "SomeChannel",
  "channel_id": "",
  "url": "https://www.youtube.com/@SomeChannel"
}
```

`videos_per_channel` (default 5) caps how many recent videos are checked per channel per run.
Videos already in `state.json` are skipped, so raising it is safe.

Entries marked `"unverified": true` were **starter suggestions**, added without network access to
confirm the handle resolves — `@stanfordonline` and `@nvidia` are your own picks and carry no such
marker. Run the workflow once (or `python fetch_videos.py` locally) and check the resolution output
before trusting any of them: a bad handle prints `FAILED` next to its name rather than failing
silently. Delete the ones you don't want.

## Running locally

```bash
pip install -r requirements.txt

python fetch_videos.py                      # resolves IDs, fetches transcripts
python build_digest.py                      # writes digest.txt + digest.html

export GMAIL_APP_PASSWORD="your16charapppassword"
python send_email.py "Test" digest.txt --html digest.html
```

From a home connection you do **not** need the proxy — the block only affects datacenter IPs.

## Files

| File | Purpose |
|---|---|
| `AI-TRENDS.md` | The living document — themes, per-video summaries, coverage log |
| `fetch_videos.py` | Resolves channel IDs and pulls new videos/transcripts |
| `build_digest.py` | Builds the email body from `AI-TRENDS.md` + git history; exits 2 when nothing is new |
| `send_email.py` | Sends it via Gmail SMTP |
| `channels.json` | Tracked channels (handles; IDs auto-resolved) |
| `state.json` | Seen-video state |
| `archive/` | One-off digests the pipeline does not maintain |

These are summaries of public YouTube content — claims belong to the speakers, not to this repo.
