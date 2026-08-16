"""Fetch the latest videos + transcripts for the channels in channels.json.

- Reads channels.json for the channel list
- Resolves each channel's ID from its @handle if not already cached
- Pulls each channel's RSS feed (no API key needed)
- Downloads transcripts for videos not yet in state.json
- Saves transcripts to transcripts/<handle>/<date>_<title>_<video_id>.txt
- Records everything in state.json so videos are only processed once

Run:  python fetch_videos.py

PROXY
-----
YouTube blocks datacenter IP ranges, which includes every GitHub Actions
runner. Without a proxy this script will fetch nothing in CI. Set either:

  WEBSHARE_PROXY_USERNAME / WEBSHARE_PROXY_PASSWORD   (residential, recommended)
  YT_PROXY_URL                                        (any http(s) proxy URL)

With neither set, it connects directly — correct for running on your own
machine, useless on a cloud runner.
"""

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen, Request, ProxyHandler, build_opener

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

try:  # present in youtube-transcript-api >= 1.0
    from youtube_transcript_api.proxies import WebshareProxyConfig, GenericProxyConfig
except ImportError:  # pragma: no cover - older library, proxy simply unavailable
    WebshareProxyConfig = GenericProxyConfig = None

BASE = Path(__file__).parent
CHANNELS_FILE = BASE / "channels.json"
STATE_FILE = BASE / "state.json"
TRANSCRIPTS_DIR = BASE / "transcripts"

ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"

FETCH_DELAY_SECONDS = 3  # be gentle with YouTube
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# A channel ID is always "UC" + 22 chars from the URL-safe base64 alphabet.
CHANNEL_ID_RE = re.compile(r"UC[0-9A-Za-z_-]{22}")


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


# --------------------------------------------------------------------------
# Proxy plumbing
# --------------------------------------------------------------------------

def proxy_url():
    """The proxy URL for plain urllib calls, or '' for a direct connection."""
    user = os.environ.get("WEBSHARE_PROXY_USERNAME")
    password = os.environ.get("WEBSHARE_PROXY_PASSWORD")
    if user and password:
        # Webshare's rotating residential endpoint. The "-rotate" suffix asks
        # for a different exit IP per request, which is what keeps YouTube from
        # rate-limiting the whole run after a few videos.
        return f"http://{user}-rotate:{password}@p.webshare.io:80/"
    return os.environ.get("YT_PROXY_URL", "")


def opener():
    """A urllib opener that honours the proxy settings, if any."""
    url = proxy_url()
    if not url:
        return build_opener()
    return build_opener(ProxyHandler({"http": url, "https": url}))


def transcript_api():
    """A YouTubeTranscriptApi configured with the proxy, if one is set."""
    user = os.environ.get("WEBSHARE_PROXY_USERNAME")
    password = os.environ.get("WEBSHARE_PROXY_PASSWORD")
    if user and password and WebshareProxyConfig is not None:
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=user, proxy_password=password
            )
        )
    generic = os.environ.get("YT_PROXY_URL")
    if generic and GenericProxyConfig is not None:
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(http_url=generic, https_url=generic)
        )
    return YouTubeTranscriptApi()


def describe_proxy():
    if os.environ.get("WEBSHARE_PROXY_USERNAME"):
        return "Webshare residential proxy"
    if os.environ.get("YT_PROXY_URL"):
        return "generic proxy (YT_PROXY_URL)"
    return "DIRECT connection (no proxy configured)"


# --------------------------------------------------------------------------
# Channel resolution
# --------------------------------------------------------------------------

def resolve_channel_id(handle):
    """Turn an @handle into a UC... channel ID by reading the channel page.

    Saves you ever having to hunt for a channel ID by hand — declare the
    handle in channels.json and this fills in the rest, once.
    """
    url = f"https://www.youtube.com/@{handle}"
    req = Request(url, headers={"User-Agent": UA})
    with opener().open(req, timeout=30) as r:
        body = r.read().decode("utf-8", errors="replace")

    # Most reliable first: the explicit externalId field in the page's JSON.
    m = re.search(r'"externalId"\s*:\s*"(UC[0-9A-Za-z_-]{22})"', body)
    if m:
        return m.group(1)
    m = re.search(r"youtube\.com/channel/(UC[0-9A-Za-z_-]{22})", body)
    if m:
        return m.group(1)
    # Last resort: any well-formed ID on the page.
    m = CHANNEL_ID_RE.search(body)
    if m:
        return m.group(0)
    raise ValueError(f"no channel ID found on the page for @{handle}")


def ensure_channel_ids(config):
    """Fill in any missing channel_id values and persist them.

    Returns the number of handles that could NOT be resolved, so the caller can
    tell "quiet week" apart from "every request is being refused".
    """
    changed = False
    failures = 0
    for ch in config["channels"]:
        if ch.get("channel_id"):
            continue
        handle = ch["handle"]
        print(f"  resolving @{handle} ...", end=" ", flush=True)
        try:
            ch["channel_id"] = resolve_channel_id(handle)
            print(ch["channel_id"])
            changed = True
        except Exception as e:
            print(f"FAILED ({type(e).__name__}: {e})")
            failures += 1
    if changed:
        CHANNELS_FILE.write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )
    return failures


# --------------------------------------------------------------------------
# Feed + transcripts
# --------------------------------------------------------------------------

def fetch_feed(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = Request(url, headers={"User-Agent": UA})
    with opener().open(req, timeout=30) as r:
        return ET.fromstring(r.read())


def feed_videos(root, limit):
    videos = []
    for entry in root.findall(f"{ATOM}entry")[:limit]:
        videos.append({
            "video_id": entry.find(f"{YT}videoId").text,
            "title": entry.find(f"{ATOM}title").text,
            "published": entry.find(f"{ATOM}published").text[:10],
        })
    return videos


def safe_name(text):
    return re.sub(r"[^\w\- ]", "", text).strip()[:80]


def fetch_transcript(api, video_id):
    fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
    return " ".join(s.text for s in fetched.snippets)


def main():
    config = load_json(CHANNELS_FILE, None)
    if config is None:
        print("ERROR: channels.json not found", file=sys.stderr)
        sys.exit(1)
    if not config.get("channels"):
        print("ERROR: channels.json has no channels — add at least one", file=sys.stderr)
        sys.exit(1)

    print(f"Network: {describe_proxy()}")

    print("\n=== Resolving channel IDs ===")
    blocked = ensure_channel_ids(config)

    state = load_json(STATE_FILE, {"processed": {}})
    state.setdefault("processed", {})
    per_channel = config.get("videos_per_channel", 5)
    api = transcript_api()
    new_files = []

    for ch in config["channels"]:
        handle = ch["handle"]
        print(f"\n=== {ch['name']} (@{handle}) ===")
        if not ch.get("channel_id"):
            print("  [skip] no channel_id — resolution failed above", file=sys.stderr)
            continue
        try:
            root = fetch_feed(ch["channel_id"])
        except Exception as e:
            print(f"  feed error: {e}", file=sys.stderr)
            blocked += 1
            continue

        for v in feed_videos(root, per_channel):
            vid = v["video_id"]
            if vid in state["processed"]:
                print(f"  [skip] already have: {v['title']}")
                continue

            out_dir = TRANSCRIPTS_DIR / handle
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{v['published']}_{safe_name(v['title'])}_{vid}.txt"

            record = {
                "title": v["title"],
                "published": v["published"],
                "channel": ch["name"],
                "url": f"https://www.youtube.com/watch?v={vid}",
            }
            try:
                text = fetch_transcript(api, vid)
                header = (
                    f"Title: {v['title']}\n"
                    f"Channel: {ch['name']}\n"
                    f"Published: {v['published']}\n"
                    f"URL: {record['url']}\n"
                    f"{'-' * 60}\n"
                )
                out_file.write_text(header + text, encoding="utf-8")
                record["transcript_file"] = str(out_file.relative_to(BASE))
                record["status"] = "ok"
                new_files.append(str(out_file.relative_to(BASE)))
                print(f"  [new]  saved transcript: {v['title']}")
            except (TranscriptsDisabled, NoTranscriptFound):
                record["status"] = "no_transcript"
                print(f"  [warn] no transcript available: {v['title']}")
            except VideoUnavailable:
                record["status"] = "unavailable"
                print(f"  [warn] video unavailable: {v['title']}")
            except Exception as e:
                # Leave it out of state so we retry next run.
                print(f"  [error] {v['title']}: {type(e).__name__}: {e}", file=sys.stderr)
                blocked += 1
                continue

            state["processed"][vid] = record
            STATE_FILE.write_text(
                json.dumps(state, indent=2) + "\n", encoding="utf-8"
            )
            time.sleep(FETCH_DELAY_SECONDS)

    print(f"\nDone. {len(new_files)} new transcript(s).")

    # Say the quiet part out loud: a run that fetched nothing AND hit errors
    # with no proxy configured is almost certainly an IP block, not a quiet
    # week on YouTube. Silence here is what let ytstock look healthy for weeks.
    if blocked and not new_files and not proxy_url():
        print(
            "\n::warning::Every request failed and no proxy is configured. "
            "YouTube blocks datacenter IPs, so this is the expected result on a "
            "cloud runner. Set WEBSHARE_PROXY_USERNAME / WEBSHARE_PROXY_PASSWORD."
        )

    if new_files:
        print("NEW_TRANSCRIPTS:")
        for f in new_files:
            print(f"  {f}")


if __name__ == "__main__":
    main()
