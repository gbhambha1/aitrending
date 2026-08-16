"""Build the email digest from AI-TRENDS.md and the run's git history.

Writes two files next to the repo root:
  digest.txt   plain-text body (always readable)
  digest.html  HTML alternative (tables render properly in Gmail)

and prints the subject line to stdout.

Usage:
  python build_digest.py [BASE_SHA]

BASE_SHA is the commit the run started at; commits after it are reported as
"what changed". Omit it to skip the changelog section.

Exit code 2 means "nothing new this run" — the workflow uses that to skip the
email entirely rather than sending an empty daily notification.
"""

import html
import re
import subprocess
import sys
from pathlib import Path

DOC = Path("AI-TRENDS.md")
REPO_URL = "https://github.com/gbhambha1/aitrending"
NEW_SINCE_HEADING = "## 🆕 What's new this run"


def run_git(*args):
    """Return git stdout, or '' if the command fails (shallow clone, etc.)."""
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=30
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def meta(text, label):
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else "unknown"


def changes(base_sha):
    """New video entries and transcripts added since base_sha."""
    if not base_sha:
        return [], [], []
    rng = f"{base_sha}..HEAD"
    commits = [ln for ln in run_git("log", "--format=%h %s", rng).splitlines() if ln]

    videos = []
    diff = run_git("diff", rng, "--unified=0", "--", str(DOC))
    for line in diff.splitlines():
        # Added lines only, and only video-entry headings (level 3).
        if line.startswith("+### "):
            videos.append(line[5:].strip())

    transcripts = [
        ln.split("\t")[-1]
        for ln in run_git("diff", "--name-status", rng, "--", "transcripts/").splitlines()
        if ln.startswith("A")
    ]
    return commits, videos, transcripts


def md_to_html(md):
    """Minimal Markdown → HTML: headings, tables, bold, links, lists, quotes.

    Deliberately small — the digest only ever contains the subset of Markdown
    the pipeline itself writes.
    """
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return s

    out, rows, in_list = [], [], False

    def flush_table():
        if not rows:
            return
        out.append('<table cellspacing="0" cellpadding="6">')
        for i, cells in enumerate(rows):
            tag = "th" if i == 0 else "td"
            tds = "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells)
            out.append(f"<tr>{tds}</tr>")
        out.append("</table>")
        rows.clear()

    def flush_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in md.splitlines():
        stripped = line.strip()

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue  # separator row
            flush_list()
            rows.append(cells)
            continue
        flush_table()

        if not stripped:
            flush_list()
            continue

        if stripped.startswith("#"):
            flush_list()
            level = len(stripped) - len(stripped.lstrip("#"))
            out.append(f"<h{min(level, 4)}>{inline(stripped.lstrip('# '))}</h{min(level, 4)}>")
        elif stripped.startswith(("- ", "* ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
        elif stripped.startswith("> "):
            flush_list()
            out.append(f"<blockquote>{inline(stripped[2:])}</blockquote>")
        elif set(stripped) == {"-"} and len(stripped) >= 3:
            flush_list()
            out.append("<hr>")
        else:
            flush_list()
            out.append(f"<p>{inline(stripped)}</p>")

    flush_table()
    flush_list()
    return "\n".join(out)


STYLE = """
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       font-size: 14px; line-height: 1.5; color: #1a1a1a; max-width: 760px; }
table { border-collapse: collapse; margin: 12px 0; font-size: 13px; }
th, td { border: 1px solid #d0d7de; text-align: left; vertical-align: top; }
th { background: #f6f8fa; }
h1 { font-size: 20px; } h2 { font-size: 17px; } h3 { font-size: 15px; }
blockquote { margin: 8px 0; padding: 4px 12px; border-left: 3px solid #d0d7de; color: #57606a; }
code { background: #f6f8fa; padding: 1px 4px; border-radius: 3px; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 16px 0; }
.footer { color: #57606a; font-size: 12px; margin-top: 20px; }
"""


def summary_excerpt(text):
    """The 'Latest themes' section, if the doc has one — the part worth reading
    in the email body rather than clicking through for."""
    heading = "## 🎯 Latest themes"
    start = text.find(heading)
    if start == -1:
        return ""
    rest = text[start + len(heading):]
    end = re.search(r"^## ", rest, re.M)
    body = rest[: end.start()] if end else rest
    return (heading + body).strip()


def main():
    base_sha = sys.argv[1] if len(sys.argv) > 1 else ""
    text = DOC.read_text(encoding="utf-8") if DOC.exists() else ""

    updated = meta(text, "Last updated")
    covered = meta(text, "Videos covered")
    commits, videos, transcripts = changes(base_sha)

    # Unlike the financial pipeline this was forked from, there is no daily
    # market data to refresh — so a run with no new videos has nothing to say.
    # Signal that to the workflow instead of emailing noise.
    #
    # Only when a BASE_SHA was supplied, though: without one we genuinely
    # cannot tell what is new, and exiting 2 would make a plain local
    # `python build_digest.py` refuse to produce anything.
    if base_sha and not videos and not transcripts:
        print("NOTHING_NEW", file=sys.stderr)
        sys.exit(2)

    parts = [f"# 🤖 AI trends update — {updated}", ""]

    parts.append(NEW_SINCE_HEADING)
    for v in videos:
        parts.append(f"- **New summary:** {v}")
    for t in transcripts:
        parts.append(f"- **New transcript:** {t}")
    parts.append("")

    themes = summary_excerpt(text)
    if themes:
        parts += [themes.rstrip("- \n"), ""]

    parts.append("---")
    parts.append(f"Videos covered: {covered}")
    if commits:
        parts.append("")
        parts.append("Commits this run:")
        for c in commits:
            parts.append(f"- {c}")
    parts.append("")
    parts.append(f"Full document: {REPO_URL}/blob/main/AI-TRENDS.md")
    parts.append("Summaries of public YouTube content — claims are the speakers', not verified.")

    body = "\n".join(parts)
    Path("digest.txt").write_text(body, encoding="utf-8")
    Path("digest.html").write_text(
        f"<html><head><meta charset='utf-8'><style>{STYLE}</style></head>"
        f"<body>{md_to_html(body)}</body></html>",
        encoding="utf-8",
    )

    bits = []
    if videos:
        bits.append(f"{len(videos)} new video{'s' if len(videos) != 1 else ''}")
    elif transcripts:
        bits.append(f"{len(transcripts)} new transcript{'s' if len(transcripts) != 1 else ''}")
    suffix = f" — {', '.join(bits)}" if bits else ""
    print(f"🤖 AI trends update — {updated}{suffix}")


if __name__ == "__main__":
    main()
