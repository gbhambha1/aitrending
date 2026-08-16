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

## 🌐 The IP problem — why this repo uses a proxy

YouTube aggressively blocks **datacenter IP ranges**, which includes every GitHub Actions runner.
Two requests happen per video and only one is at risk:

| Request | Endpoint | At risk? |
|---|---|---|
| Discovery — what's new on a channel | `youtube.com/feeds/videos.xml` | Generally no — static XML, no bot detection |
| Transcript — the actual text | `youtube.com/watch` + timedtext | **Yes.** This is where the blocking happens |

The evidence that this bites is the sibling repo: `ytstock`'s fetch step reports 0 new transcripts
on cloud runners, and its transcripts all arrived via manual commits instead. But the blocking is a
heuristic, not a published rule, and it varies by IP range.

Given that evidence, this repo is set up to use a residential proxy — see below.

If you ever want to check whether it's still needed, running with no proxy secrets set costs
nothing: `fetch_videos.py` falls back to a direct connection, prints
`DIRECT connection (no proxy configured)` at startup, and the run emits a loud warning if every
request failed.

### Setting up the proxy

You need a **residential IP**. `youtube-transcript-api` has built-in support for Webshare
(~$1–3/month), which is why it's the documented path.

> ⚠️ **Buy the right plan.** Webshare sells several proxy types and only one works here:
>
> | Plan | Works? |
> |---|---|
> | **Residential** (rotating) | ✅ **Buy this one** |
> | "Proxy Server" (datacenter) | ❌ Datacenter IPs — blocked exactly like the GitHub runner |
> | "Static Residential" | ❌ Fixed IP, gets flagged quickly under repeated use |
>
> The datacenter plan is the cheapest and most prominent on their site, so it is easy to buy by
> mistake and then wonder why nothing changed.

1. Sign up at [webshare.io](https://www.webshare.io/) and buy a **Residential** plan.
2. Go to the dashboard's **Proxy → Settings** page and copy the **proxy username and password**.
   These are *not* your Webshare account login — they're a separate generated credential pair.
3. Add them as repo secrets: `WEBSHARE_PROXY_USERNAME` and `WEBSHARE_PROXY_PASSWORD`.

**If the run fails with `407 Proxy Authentication Required`,** the proxy was reached and rejected
your credentials. In order of likelihood:

1. **Wrong plan.** The rotating-residential endpoint expects the username with a `-rotate` suffix,
   which `fetch_videos.py` appends automatically. A datacenter "Proxy Server" plan does *not* accept
   it and answers exactly this 407. Either switch to the Residential plan, or set a repo **variable**
   `WEBSHARE_ROTATE=0` (Settings → Secrets and variables → Actions → *Variables*) to send the bare
   username.
2. **Wrong credentials.** The secrets must hold the generated proxy username/password from
   Webshare's Proxy → Settings page, not your account login.
3. **Bandwidth exhausted** on the plan.

The fetch step prints `Webshare proxy — user='...' host=...` at startup so you can see exactly which
username form was sent. Override the endpoint with `WEBSHARE_PROXY_HOST` if your plan uses a
different one.

`fetch_videos.py` picks the secrets up automatically and routes both the feed and the transcript
requests through the proxy.

**Bandwidth:** residential plans bill per GB. This pipeline is light — 7 channels × 5 videos checked
per day, with everything already in `state.json` skipped, so only genuinely new videos transfer.
Expect well under 1 GB/month, i.e. the smallest plan.

Any other provider (Bright Data, IPRoyal, Oxylabs, Smartproxy) works too — set `YT_PROXY_URL` to its
proxy URL instead. `fetch_videos.py` routes everything through whichever is configured.

**What won't work:** the official YouTube Data API v3 is unblocked but only downloads captions for
videos *you own*, so it can't help here; a cheap VPS is another datacenter IP; free proxy lists are
unreliable. The only genuinely free option is running the fetch from a residential connection —
i.e. your own machine.

## Repository secrets

Settings → Secrets and variables → Actions → **New repository secret**

| Secret | Required | What it is |
|---|---|---|
| `ANTHROPIC_API_KEY_AI` | Yes | Anthropic API key (`sk-ant-api...`) — note the `_AI` suffix |
| `GMAIL_APP_PASSWORD` | Yes | Gmail **app password** — 16 characters, *not* your normal password |
| `WEBSHARE_PROXY_USERNAME` | Yes | Webshare **Residential** proxy username — see the IP section above |
| `WEBSHARE_PROXY_PASSWORD` | Yes | Webshare Residential proxy password |

Secrets do **not** carry over from other repositories — even if the values are identical to
`ytstock`'s, they must be added here separately.

The Anthropic key is named **`ANTHROPIC_API_KEY_AI`**, not `ANTHROPIC_API_KEY`, so it can never be
confused with the financial pipeline's key. The two repos can hold entirely separate API keys —
useful for billing them apart, or revoking one without touching the other.

### The Gmail app password

Mail is sent **from and to `gbhambha@intelliai.net`** — that address is the default for both in
`send_email.py`, and SMTP logs in as it.

> ⚠️ **Generate the app password while signed in as `gbhambha@intelliai.net`.** The SMTP login
> address and the app password must belong to the *same* Google account. An app password created
> under a different account fails with `535 BadCredentials` even though it is perfectly valid —
> and being signed into several Google accounts at once is the usual way this goes wrong. Check the
> account switcher before generating.

1. Sign in as `gbhambha@intelliai.net`.
2. Google Account → Security → **2-Step Verification** (must already be on).
3. **App passwords** → generate one for "Mail".
4. Paste it into the `GMAIL_APP_PASSWORD` secret **with the spaces removed** — it should be 16
   lowercase letters, no digits.

`intelliai.net` is a **Google Workspace** account, so app passwords additionally require that the
Workspace admin has not disabled them.

To send somewhere else, set the `EMAIL_TO` / `EMAIL_FROM` environment variables — but note that
changing `EMAIL_FROM` means the app password must belong to *that* account instead.
`send_email.py` prints `SMTP login as: <address>` before connecting and warns if it is sending as
anything other than `gbhambha@intelliai.net`, so a mismatch shows up in the run log rather than as
an opaque 535.

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
