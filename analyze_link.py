"""Fetch a source for one or more user-supplied links, on demand.

The scheduled pipeline watches channels in channels.json. This script handles
the other case: "summarize this specific thing". It fetches the source text and
records it in state.json exactly like the scheduled fetcher does, so the normal
Claude step then writes the synopsis into AI-TRENDS.md and emails it — no
separate summarizing path to keep in sync.

Usage:
  python analyze_link.py <url> [<url> ...]

Supported:
  YouTube video     watch?v=ID · youtu.be/ID · /shorts/ID · /live/ID · /embed/ID
  YouTube channel   /@handle · /channel/UC... · /c/name  (takes its top recent videos)
  X post            x.com/user/status/ID · twitter.com/user/status/ID
  X profile         x.com/user  (requires X_BEARER_TOKEN)

X caveat: X publishes no transcripts. For a post we retrieve the post TEXT
(via the public oEmbed endpoint, no auth needed) — so a text post summarizes
well, while a video post yields only its caption. Transcribing X video would
mean downloading media and running speech-to-text, which this pipeline
deliberately does not do.
"""

import html as html_mod
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request

import fetch_videos as yt

BASE = Path(__file__).parent
STATE_FILE = BASE / "state.json"
ONDEMAND_DIR = BASE / "transcripts" / "_ondemand"

OEMBED = "https://publish.twitter.com/oembed?url={}&omit_script=1&dnt=true"
X_API = "https://api.x.com/2"

YT_VIDEO_PATTERNS = [
    r"[?&]v=([0-9A-Za-z_-]{11})",
    r"youtu\.be/([0-9A-Za-z_-]{11})",
    r"/shorts/([0-9A-Za-z_-]{11})",
    r"/live/([0-9A-Za-z_-]{11})",
    r"/embed/([0-9A-Za-z_-]{11})",
]


# --------------------------------------------------------------------------
# Link classification
# --------------------------------------------------------------------------

def classify(url):
    """Return (kind, identifier). Kinds: yt_video, yt_channel, x_post, x_user."""
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    host = (urlparse(u).hostname or "").lower().removeprefix("www.")
    path = urlparse(u).path

    if host in ("youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"):
        for pat in YT_VIDEO_PATTERNS:
            m = re.search(pat, u)
            if m:
                return "yt_video", m.group(1)
        m = re.search(r"/channel/(UC[0-9A-Za-z_-]{22})", u)
        if m:
            return "yt_channel", m.group(1)
        m = re.search(r"/@([A-Za-z0-9._-]+)", path)
        if m:
            return "yt_channel_handle", m.group(1)
        m = re.search(r"/(?:c|user)/([A-Za-z0-9._-]+)", path)
        if m:
            return "yt_channel_handle", m.group(1)
        return "unknown", u

    if host in ("x.com", "twitter.com", "mobile.x.com", "mobile.twitter.com"):
        m = re.search(r"/status/(\d+)", path)
        if m:
            return "x_post", m.group(1)
        m = re.match(r"^/([A-Za-z0-9_]{1,15})/?$", path)
        if m and m.group(1).lower() not in ("home", "explore", "search", "i"):
            return "x_user", m.group(1)
        return "unknown", u

    return "unknown", u


# --------------------------------------------------------------------------
# Writers
# --------------------------------------------------------------------------

def record(state, key, record_dict):
    state["processed"][key] = record_dict
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def write_source(subdir, name, header_lines, body):
    out_dir = ONDEMAND_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / name
    out_file.write_text(
        "\n".join(header_lines) + "\n" + "-" * 60 + "\n" + body,
        encoding="utf-8",
    )
    return str(out_file.relative_to(BASE))


# --------------------------------------------------------------------------
# YouTube
# --------------------------------------------------------------------------

def do_yt_video(state, api, vid, source_url):
    if vid in state["processed"] and state["processed"][vid].get("transcript_file"):
        print(f"  [skip] already have transcript for {vid} — "
              f"it is already in the ledger")
        return 0
    try:
        text = yt.fetch_transcript(api, vid)
    except Exception as e:
        print(f"  [error] {vid}: {type(e).__name__}: {e}", file=sys.stderr)
        if yt.is_rate_limited(e):
            print("    -> rate limited; try again in a few minutes", file=sys.stderr)
        return 1

    title = f"YouTube video {vid}"
    path = write_source(
        "youtube",
        f"{date.today().isoformat()}_{vid}.txt",
        [
            f"Title: {title}",
            "Channel: (on-demand link)",
            f"Published: {date.today().isoformat()}",
            f"URL: {source_url}",
        ],
        text,
    )
    record(state, vid, {
        "title": title,
        "published": date.today().isoformat(),
        "channel": "On-demand (YouTube)",
        "url": source_url,
        "transcript_file": path,
        "status": "ok",
        "source": "on_demand",
    })
    print(f"  [new]  saved transcript: {path}")
    return 0


def do_yt_channel(state, api, channel_id, label):
    """Fetch this channel's top recent videos, same rules as the scheduled run."""
    config = yt.load_json(yt.CHANNELS_FILE, {}) or {}
    limit = config.get("videos_per_channel", 5)
    max_age = config.get("max_age_days", 30)

    try:
        root = yt.fetch_feed(channel_id)
    except Exception as e:
        print(f"  [error] feed for {label}: {e}", file=sys.stderr)
        return 1

    failures = 0
    for v in yt.feed_videos(root, limit, max_age):
        vid = v["video_id"]
        if vid in state["processed"]:
            print(f"  [skip] already in the ledger: {v['title']}")
            continue
        failures += do_yt_video(
            state, api, vid, f"https://www.youtube.com/watch?v={vid}"
        )
        yt.pause(yt.FETCH_DELAY_SECONDS)
    return 1 if failures else 0


# --------------------------------------------------------------------------
# X
# --------------------------------------------------------------------------

def strip_tags(markup):
    """oEmbed returns the post as an HTML blockquote; recover the plain text."""
    markup = re.sub(r"<br\s*/?>", "\n", markup, flags=re.I)
    markup = re.sub(r"</p>", "\n\n", markup, flags=re.I)
    text = re.sub(r"<[^>]+>", "", markup)
    # html.unescape handles the full entity set, not just the common few.
    text = html_mod.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def do_x_post(state, post_id, source_url):
    key = f"x:{post_id}"
    if key in state["processed"]:
        print(f"  [skip] already in the ledger: {source_url}")
        return 0

    # oEmbed is public and needs no credentials, which keeps single posts
    # working without anyone provisioning an X API token.
    req = Request(OEMBED.format(quote(source_url, safe="")),
                  headers={"User-Agent": yt.UA})
    try:
        with yt.opener().open(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        hint = " (post may be deleted, private, or age-restricted)" if e.code in (403, 404) else ""
        print(f"  [error] X oEmbed returned {e.code}{hint}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"  [error] X oEmbed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    author = data.get("author_name") or "unknown"
    text = strip_tags(data.get("html", ""))
    if not text:
        print("  [warn] no text in the post — nothing to summarize", file=sys.stderr)
        return 1

    title = f"X post by {author}"
    slug = re.sub(r"[^\w]", "", author)[:40] or "x"
    path = write_source(
        "x",
        f"{date.today().isoformat()}_{slug}_{post_id}.txt",
        [
            f"Title: {title}",
            f"Channel: X / @{author}",
            f"Published: {date.today().isoformat()}",
            f"URL: {source_url}",
            "NOTE: X publishes no transcripts. This is the post text only — if the "
            "post is a video, its spoken content is NOT included.",
        ],
        text,
    )
    record(state, key, {
        "title": title,
        "published": date.today().isoformat(),
        "channel": f"On-demand (X / @{author})",
        "url": source_url,
        "transcript_file": path,
        "status": "ok",
        "source": "on_demand",
    })
    print(f"  [new]  saved post text: {path}")
    return 0


def do_x_user(state, handle):
    token = (os.environ.get("X_BEARER_TOKEN") or "").strip()
    if not token:
        print(
            f"  [error] listing an X profile (@{handle}) needs X_BEARER_TOKEN — "
            f"X has no public feed equivalent to YouTube's RSS. Add the secret, "
            f"or pass individual post links instead.",
            file=sys.stderr,
        )
        return 1

    hdrs = {"Authorization": f"Bearer {token}", "User-Agent": yt.UA}
    try:
        req = Request(f"{X_API}/users/by/username/{quote(handle)}", headers=hdrs)
        with yt.opener().open(req, timeout=30) as r:
            uid = json.loads(r.read().decode("utf-8"))["data"]["id"]
        req = Request(
            f"{X_API}/users/{uid}/tweets?max_results=10"
            f"&tweet.fields=created_at,public_metrics",
            headers=hdrs,
        )
        with yt.opener().open(req, timeout=30) as r:
            posts = json.loads(r.read().decode("utf-8")).get("data", [])
    except HTTPError as e:
        note = " — token lacks read access or the tier does not allow this" if e.code in (401, 403) else ""
        print(f"  [error] X API returned {e.code}{note}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"  [error] X API: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if not posts:
        print(f"  [warn] no posts returned for @{handle}")
        return 0

    # Same selection philosophy as the YouTube side: most engaged-with first.
    posts.sort(key=lambda p: (p.get("public_metrics") or {}).get("like_count", 0),
               reverse=True)
    config = yt.load_json(yt.CHANNELS_FILE, {}) or {}
    limit = config.get("videos_per_channel", 5)

    failures = 0
    for p in posts[:limit]:
        failures += do_x_post(
            state, p["id"], f"https://x.com/{handle}/status/{p['id']}"
        )
    return 1 if failures else 0


# --------------------------------------------------------------------------

def main():
    urls = [a for a in sys.argv[1:] if a.strip()]
    if not urls:
        print(__doc__)
        sys.exit(1)

    problem = yt.preflight()
    if problem:
        print(f"Proxy preflight FAILED: {problem}", file=sys.stderr)
        sys.exit(3)

    state = yt.load_json(STATE_FILE, {"processed": {}})
    state.setdefault("processed", {})
    state.setdefault("analyzed", {})
    api = yt.transcript_api()

    failures = 0
    for url in urls:
        kind, ident = classify(url)
        print(f"\n=== {url}  [{kind}] ===")

        if kind == "yt_video":
            failures += do_yt_video(state, api, ident, url)
        elif kind == "yt_channel":
            failures += do_yt_channel(state, api, ident, ident)
        elif kind == "yt_channel_handle":
            try:
                cid = yt.resolve_channel_id(ident)
                print(f"  resolved @{ident} -> {cid}")
            except Exception as e:
                print(f"  [error] could not resolve @{ident}: {e}", file=sys.stderr)
                failures += 1
                continue
            failures += do_yt_channel(state, api, cid, ident)
        elif kind == "x_post":
            failures += do_x_post(state, ident, url)
        elif kind == "x_user":
            failures += do_x_user(state, ident)
        else:
            print(f"  [error] unrecognised link. Supported: YouTube video or "
                  f"channel, X post or profile.", file=sys.stderr)
            failures += 1

    print(f"\nDone. {failures} of {len(urls)} link(s) failed.")
    # Fail the step only when nothing at all was retrieved; a partial success
    # still has something worth summarizing.
    sys.exit(1 if failures >= len(urls) else 0)


if __name__ == "__main__":
    main()
