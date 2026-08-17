"""Track which videos have been ANALYZED, separately from which were fetched.

`state.json` holds two ledgers:

  processed  — every video the fetcher has seen (transcript saved, or a reason
               why not). Stops the fetcher re-downloading.
  analyzed   — every video that has been written into AI-TRENDS.md. Stops the
               summarizer re-analyzing.

They are deliberately separate. A transcript can be fetched in one run and
summarized in a later one (a rate-limited or time-capped run stops early), and
inferring "already analyzed" by parsing the document is fragile — a reworded
heading would silently cause a duplicate. This ledger is the single source of
truth, and it is queried and updated by explicit commands rather than by
pattern-matching prose.

Usage:
  python ledger.py pending            # transcripts awaiting analysis (one path per line)
  python ledger.py pending --json     # same, as JSON with titles and metadata
  python ledger.py mark ID [ID ...]   # record video IDs as analyzed
  python ledger.py status             # counts
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
STATE_FILE = BASE / "state.json"


def load():
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    else:
        state = {}
    state.setdefault("processed", {})
    state.setdefault("analyzed", {})
    return state


def save(state):
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def pending(state):
    """Videos with a transcript on disk that have not been analyzed yet."""
    out = []
    for vid, rec in state["processed"].items():
        if vid in state["analyzed"]:
            continue
        path = rec.get("transcript_file")
        if not path:
            continue  # no transcript (disabled/unavailable) — nothing to analyze
        if not (BASE / path).exists():
            continue  # recorded but the file is gone; don't claim it's pending
        out.append({
            "video_id": vid,
            "title": rec.get("title", ""),
            "channel": rec.get("channel", ""),
            "published": rec.get("published", ""),
            "url": rec.get("url", ""),
            "transcript_file": path,
        })
    out.sort(key=lambda r: (r["channel"], r["published"]))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    state = load()

    if cmd == "pending":
        items = pending(state)
        if "--json" in sys.argv:
            print(json.dumps(items, indent=2))
        else:
            for it in items:
                print(it["transcript_file"])
        # Exit 1 when there is nothing to do, so callers can branch on it.
        sys.exit(0 if items else 1)

    if cmd == "mark":
        ids = [a for a in sys.argv[2:] if not a.startswith("-")]
        if not ids:
            print("usage: ledger.py mark ID [ID ...]", file=sys.stderr)
            sys.exit(1)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        marked, unknown = [], []
        for vid in ids:
            if vid not in state["processed"]:
                unknown.append(vid)
                continue
            if vid in state["analyzed"]:
                continue  # already marked; marking twice is not an error
            rec = state["processed"][vid]
            state["analyzed"][vid] = {
                "analyzed_at": stamp,
                "title": rec.get("title", ""),
                "channel": rec.get("channel", ""),
            }
            marked.append(vid)
        save(state)
        print(f"marked {len(marked)} analyzed; {len(state['analyzed'])} total")
        if unknown:
            print(f"::warning::not in the processed ledger, ignored: {', '.join(unknown)}")
        sys.exit(0)

    if cmd == "status":
        p = len(state["processed"])
        a = len(state["analyzed"])
        q = len(pending(state))
        print(f"processed: {p}\nanalyzed:  {a}\npending:   {q}")
        sys.exit(0)

    print(f"unknown command: {cmd}\n{__doc__}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
