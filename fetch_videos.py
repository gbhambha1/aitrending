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
from urllib.error import HTTPError, URLError
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

# Be gentle with YouTube. This applies after EVERY attempt, successful or not:
# skipping it on failures turns a bad patch into a retry storm, which is what
# escalates into 429s in the first place.
FETCH_DELAY_SECONDS = float(os.environ.get("FETCH_DELAY_SECONDS", "4"))

# Consecutive rate-limit hits before abandoning the run. Progress is saved
# after every success, so stopping early costs nothing -- the next run picks
# up where this one left off, and backing off beats digging the hole deeper.
RATE_LIMIT_GIVE_UP = int(os.environ.get("RATE_LIMIT_GIVE_UP", "4"))
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

# Which username form the proxy actually accepts. None = not yet determined,
# and preflight() settles it by trying both rather than making you guess.
_ROTATE = None

WEBSHARE_CONFIG_URL = "https://proxy.webshare.io/api/v2/proxy/config/"


def load_credentials_from_api():
    """Exchange a Webshare API key for the actual proxy username/password.

    These are two entirely different credentials: the API key talks to
    Webshare's REST API, while the proxy itself authenticates with a short
    generated username/password pair. Sending an API key as the proxy username
    is rejected with 407, which is indistinguishable from any other bad
    credential -- so if WEBSHARE_API_KEY is set, fetch the real pair instead of
    making the user find it by hand.

    Populates the WEBSHARE_PROXY_* env vars in place. Returns an error string
    on failure, or "" on success/not-applicable.
    """
    api_key = (os.environ.get("WEBSHARE_API_KEY") or "").strip()
    if not api_key:
        return ""
    if os.environ.get("WEBSHARE_PROXY_USERNAME"):
        print("  WEBSHARE_API_KEY set but explicit proxy credentials also "
              "present — using the explicit ones")
        return ""

    req = Request(
        WEBSHARE_CONFIG_URL,
        headers={"Authorization": f"Token {api_key}", "User-Agent": UA},
    )
    try:
        with urlopen(req, timeout=30) as r:
            cfg = json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        if e.code in (401, 403):
            return (f"Webshare rejected the API key ({e.code}). Check "
                    f"WEBSHARE_API_KEY against Webshare -> API -> Keys.")
        return f"Webshare API returned {e.code} fetching proxy config."
    except Exception as e:
        return f"could not reach the Webshare API ({type(e).__name__}: {e})."

    user = str(cfg.get("username") or "").strip()
    password = str(cfg.get("password") or "").strip()
    if not user or not password:
        return ("the Webshare API responded but carried no username/password "
                "— check that a proxy plan is active on the account.")

    os.environ["WEBSHARE_PROXY_USERNAME"] = user
    os.environ["WEBSHARE_PROXY_PASSWORD"] = password
    print(f"  fetched proxy credentials from the Webshare API "
          f"(username {len(user)} chars)")
    return ""


def webshare_user(rotate=None):
    """The Webshare username, with the rotating-endpoint suffix if applicable.

    The "-rotate" suffix asks for a different exit IP per request and is what
    Webshare's *rotating residential* endpoint expects. It is NOT valid on
    other plan types -- sending it with a datacenter ("Proxy Server") account
    is rejected with 407, so preflight() tries both forms.
    """
    user = (os.environ.get("WEBSHARE_PROXY_USERNAME") or "").strip()
    if not user:
        return ""
    if rotate is None:
        rotate = _ROTATE
    if rotate is None:  # nothing probed yet -- fall back to the env preference
        rotate = os.environ.get("WEBSHARE_ROTATE", "1").strip() not in (
            "0", "false", "no"
        )
    if not rotate:
        return user
    # Don't double-append if the credential already carries the suffix.
    return user if user.endswith("-rotate") else f"{user}-rotate"


def proxy_url(rotate=None):
    """The proxy URL for plain urllib calls, or '' for a direct connection."""
    user = webshare_user(rotate)
    # .strip() matters: a secret pasted with a trailing newline authenticates
    # as a different user and comes back as an opaque 407.
    password = (os.environ.get("WEBSHARE_PROXY_PASSWORD") or "").strip()
    if user and password:
        host = os.environ.get("WEBSHARE_PROXY_HOST", "p.webshare.io:80").strip()
        return f"http://{user}:{password}@{host}/"
    return os.environ.get("YT_PROXY_URL", "").strip()


def describe_credentials():
    """Report the SHAPE of the proxy credentials without ever printing them.

    CI masks the secret values, so the only way to spot the commonest mistake
    -- pasting the Webshare *account login* instead of the generated proxy
    credentials -- is to describe them. A username containing '@' is an email,
    and an email is never a Webshare proxy username.
    """
    user = (os.environ.get("WEBSHARE_PROXY_USERNAME") or "").strip()
    password = (os.environ.get("WEBSHARE_PROXY_PASSWORD") or "").strip()

    problems = []
    if "@" in user:
        problems.append(
            "username contains '@' — that is an account email, NOT a Webshare "
            "proxy username. Copy the generated pair from Proxy → Settings."
        )
    if len(user) > 20:
        problems.append(
            f"username is {len(user)} chars — Webshare proxy usernames are "
            "short (~8-12). This looks like an API KEY, which is a different "
            "credential and is always rejected by the proxy. Either set it as "
            "WEBSHARE_API_KEY instead (the script will exchange it for the "
            "real proxy credentials), or copy the pair from Proxy → Settings."
        )
    if any(c.isupper() for c in user):
        problems.append("username has uppercase characters — Webshare proxy usernames are lowercase")
    if not user:
        problems.append("username is empty")
    if not password:
        problems.append("password is empty")

    print(f"  credential shape: username {len(user)} chars, password {len(password)} chars")
    for p in problems:
        print(f"  ::warning::{p}")
    return problems


def preflight():
    """Probe the proxy once and settle which username form it accepts.

    Webshare rejects the wrong form with a bare 407 that looks identical to
    bad credentials, so trying both here converts 'guess and re-run' into one
    definite answer printed at the top of the log. Returns an error string if
    the proxy is unusable, or "" if we are good to go.
    """
    global _ROTATE

    # An API key, if supplied, is exchanged for real proxy credentials first.
    problem = load_credentials_from_api()
    if problem:
        return problem

    if not os.environ.get("WEBSHARE_PROXY_USERNAME"):
        return ""  # direct or generic proxy -- nothing to probe

    describe_credentials()

    probe = "https://www.youtube.com/robots.txt"
    last = None
    for rotate in (True, False):
        label = "-rotate" if rotate else "bare"
        url = proxy_url(rotate)
        opener_ = build_opener(ProxyHandler({"http": url, "https": url}))
        try:
            opener_.open(Request(probe, headers={"User-Agent": UA}), timeout=30)
        except HTTPError as e:
            # The DESTINATION answered (403/404/...), so the tunnel and the
            # proxy credentials both worked. That is all this probe tests.
            _ROTATE = rotate
            print(f"  proxy auth OK with {label} username "
                  f"(YouTube replied {e.code} — not an auth failure)")
            return ""
        except URLError as e:
            last = e
            if "407" in str(e):
                print(f"  {label} username rejected (407)")
                continue  # wrong form, or bad credentials — try the other
            # The PROXY refused for some other reason; not a username question,
            # so trying the other form would just repeat the same error.
            return f"could not reach the proxy ({e}). " + explain(e)
        _ROTATE = rotate
        print(f"  proxy OK with {label} username")
        return ""

    # Both forms rejected. Before giving up, test one more cheap explanation:
    # the two secrets being pasted into each other's box. Report it rather
    # than silently adopting it -- a swap is a misconfiguration to fix, not a
    # mode to run in.
    user = (os.environ.get("WEBSHARE_PROXY_USERNAME") or "").strip()
    password = (os.environ.get("WEBSHARE_PROXY_PASSWORD") or "").strip()
    host = os.environ.get("WEBSHARE_PROXY_HOST", "p.webshare.io:80").strip()
    if user and password:
        swapped = f"http://{password}-rotate:{user}@{host}/"
        try:
            build_opener(ProxyHandler({"http": swapped, "https": swapped})).open(
                Request(probe, headers={"User-Agent": UA}), timeout=30
            )
            authed = True
        except HTTPError:
            authed = True  # destination answered => auth succeeded
        except Exception as e:
            authed = "407" not in str(e)
        if authed:
            return (
                "the credentials authenticate when SWAPPED — "
                "WEBSHARE_PROXY_USERNAME holds the password and "
                "WEBSHARE_PROXY_PASSWORD holds the username. Swap the two "
                "secrets and re-run."
            )

    return (
        f"both username forms were rejected with 407 ({last}). " + explain(last)
    )


def explain(exc):
    """Turn an opaque tunnel error into something actionable."""
    text = str(exc)
    if "407" in text:
        return (
            "407 = the proxy REJECTED the credentials (it was reached, so the "
            "host is right). If BOTH username forms were tried, the suffix is "
            "not the problem. Check, in order: (1) Webshare Proxy -> Settings, "
            "'Authentication method' must be Username/Password -- if it is set "
            "to IP Authorization, every username/password request 407s no "
            "matter what. (2) the secrets hold the generated *proxy* "
            "credentials from that same page, not your Webshare account login. "
            "(3) the plan is activated and still has bandwidth. (4) on a "
            "non-rotating plan set WEBSHARE_ROTATE=0, and for a datacenter "
            "plan set WEBSHARE_PROXY_HOST to one of your IP:port endpoints."
        )
    if "403" in text:
        return "403 = the request was refused outright, which usually means an IP block rather than a credential problem."
    if "Name or service not known" in text or "getaddrinfo" in text:
        return "DNS failure -- check WEBSHARE_PROXY_HOST."
    return ""


def opener():
    """A urllib opener that honours the proxy settings, if any."""
    url = proxy_url()
    if not url:
        return build_opener()
    return build_opener(ProxyHandler({"http": url, "https": url}))


def transcript_api():
    """A YouTubeTranscriptApi configured with the proxy, if one is set."""
    user = (os.environ.get("WEBSHARE_PROXY_USERNAME") or "").strip()
    password = (os.environ.get("WEBSHARE_PROXY_PASSWORD") or "").strip()
    if user and password:
        # WebshareProxyConfig appends "-rotate" itself, so it is only correct
        # when preflight found that form works. Otherwise drive the same URL
        # we proved good through the generic config, keeping both code paths
        # on identical credentials.
        if _ROTATE is False and GenericProxyConfig is not None:
            url = proxy_url()
            return YouTubeTranscriptApi(
                proxy_config=GenericProxyConfig(http_url=url, https_url=url)
            )
        if WebshareProxyConfig is not None:
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
        user = webshare_user()
        host = os.environ.get("WEBSHARE_PROXY_HOST", "p.webshare.io:80").strip()
        # Show the username shape (never the password) -- the commonest 407
        # cause is the "-rotate" suffix being wrong for the plan, and you
        # cannot diagnose that without seeing which form was sent.
        return f"Webshare proxy — user='{user}' host={host}"
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
            if failures == 0:  # explain once, on the first failure only
                hint = explain(e)
                if hint:
                    print(f"    -> {hint}")
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


def pause(seconds):
    if seconds > 0:
        time.sleep(seconds)


def is_rate_limited(exc):
    """True when YouTube/Google threw us at the 429 'sorry' interstitial."""
    text = str(exc)
    return "429" in text or "/sorry/" in text or "too many" in text.lower()


def is_not_yet_available(exc):
    """True for premieres and live streams that have no captions *yet*.

    Distinct from a permanent failure: these get captions once the broadcast
    finishes, so they should be retried on a later run rather than recorded
    as processed.
    """
    text = str(exc).lower()
    return (
        "live event will begin" in text
        or "premiere" in text
        or "live stream recording is not available" in text
        or ("unplayable" in text and "live" in text)
    )


def backoff(attempt):
    """Exponential wait after a rate-limit hit: 15s, 30s, 60s, capped at 120s."""
    delay = min(15 * (2 ** (attempt - 1)), 120)
    print(f"    backing off {delay}s before continuing")
    pause(delay)


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

    # Settle the proxy question once, up front. Without this the same 407 is
    # repeated per channel and the real answer is buried.
    print("\n=== Proxy preflight ===")
    problem = preflight()
    if problem:
        print(f"  FAILED: {problem}")
        print(
            "\n::error::Proxy authentication failed — the run reached nothing. "
            "Fix the proxy credentials or plan type, then re-run."
        )
        sys.exit(3)

    print("\n=== Resolving channel IDs ===")
    channels_failed = ensure_channel_ids(config)

    state = load_json(STATE_FILE, {"processed": {}})
    state.setdefault("processed", {})
    per_channel = config.get("videos_per_channel", 5)
    api = transcript_api()
    new_files = []
    video_errors = 0
    rate_limited = 0
    stop = False

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
            channels_failed += 1
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
                pause(FETCH_DELAY_SECONDS)  # never retry-storm past a failure
                if is_not_yet_available(e):
                    # A premiere or live stream that hasn't finished. It will
                    # have captions later, so deliberately do NOT record it --
                    # a future run should pick it up.
                    print(f"  [wait] not available yet (live/premiere): {v['title']}")
                    continue
                if is_rate_limited(e):
                    rate_limited += 1
                    print(f"  [429]  rate limited on: {v['title']}", file=sys.stderr)
                    if rate_limited >= RATE_LIMIT_GIVE_UP:
                        print(
                            f"\n::warning::Stopping early — rate limited "
                            f"{rate_limited} times. Progress so far is saved; "
                            f"the next run resumes where this one stopped.",
                            file=sys.stderr,
                        )
                        stop = True
                        break
                    backoff(rate_limited)
                    continue
                # Leave it out of state so we retry next run.
                print(f"  [error] {v['title']}: {type(e).__name__}: {e}", file=sys.stderr)
                video_errors += 1
                continue

            state["processed"][vid] = record
            STATE_FILE.write_text(
                json.dumps(state, indent=2) + "\n", encoding="utf-8"
            )
            pause(FETCH_DELAY_SECONDS)

        if stop:
            break

    print(f"\nDone. {len(new_files)} new transcript(s).")

    if new_files:
        print("NEW_TRANSCRIPTS:")
        for f in new_files:
            print(f"  {f}")

    if rate_limited:
        print(f"Rate limited {rate_limited} time(s).")
    if video_errors:
        print(f"{video_errors} video(s) failed for other reasons.")

    # Anything actually fetched is worth summarizing, so a partial run is a
    # success -- the transcripts are on disk and state.json has advanced.
    if new_files:
        return

    # Nothing fetched. Distinguish a genuinely quiet day (fine) from a run
    # that reached nothing (not fine). Reporting the second as success is
    # exactly how a broken pipeline stays green for weeks.
    total = len(config["channels"])
    if channels_failed >= total:
        print(
            f"\n::error::All {total} channels failed to connect — this run "
            f"reached nothing, so it is NOT evidence of a quiet day."
        )
        if not proxy_url():
            print(
                "::error::No proxy is configured. YouTube blocks datacenter "
                "IPs, so this is the expected result on a cloud runner. Set "
                "WEBSHARE_PROXY_USERNAME / WEBSHARE_PROXY_PASSWORD."
            )
        sys.exit(3)

    if rate_limited or video_errors:
        print(
            f"\n::error::No transcripts retrieved — {rate_limited} rate-limit "
            f"and {video_errors} other failure(s). Not a quiet day; the "
            f"channels were listed but no transcript could be downloaded."
        )
        sys.exit(3)

    # Zero new, zero errors: everything was already in state.json. Correct.


if __name__ == "__main__":
    main()
