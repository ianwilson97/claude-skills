#!/usr/bin/env python3
"""Render a research archive note (.md) to a standalone styled .html and open it.

The .md file stays the source of truth — it is the inline answer verbatim, with
YAML frontmatter prepended, and it stays greppable. This produces a readable
browser view of that same content: citations styled to stand out, links
clickable, code highlighted-ish, light/dark aware.

Usage:
    python3 archive.py ~/research/2026-07-24-http-409-vs-422.md
    python3 archive.py <file.md> --no-open      # render only
    python3 archive.py --selftest
"""

import html
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

CSS = """
:root {
  --bg: #fbfbfa; --fg: #1f2328; --muted: #6a737d; --rule: #e2e2df;
  --accent: #3b5bdb; --quote-bg: #f2f4f8; --quote-bar: #3b5bdb;
  --code-bg: #f4f4f2; --card: #fff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181c; --fg: #e6e6e3; --muted: #9aa0a6; --rule: #2c2f36;
    --accent: #8ba4ff; --quote-bg: #1d2027; --quote-bar: #8ba4ff;
    --code-bg: #1b1e24; --card: #1a1d22;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  padding: 2.5rem 1.25rem 6rem;
}
main { max-width: 46rem; margin: 0 auto; }
header.meta {
  background: var(--card); border: 1px solid var(--rule); border-radius: 10px;
  padding: 1rem 1.15rem; margin-bottom: 2.5rem;
}
header.meta .q { font-size: 1.15rem; font-weight: 600; line-height: 1.4; }
header.meta dl {
  margin: .75rem 0 0; display: grid; grid-template-columns: auto 1fr;
  gap: .2rem .75rem; font-size: .82rem; color: var(--muted);
}
header.meta dt { font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
header.meta dd { margin: 0; }
h1, h2, h3 { line-height: 1.25; margin: 2.2rem 0 .75rem; }
h1 { font-size: 1.6rem; } h2 { font-size: 1.25rem; }
h2 { padding-bottom: .3rem; border-bottom: 1px solid var(--rule); }
h3 { font-size: 1.02rem; }
a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }
/* Citations are the point of this document — make them unmissable. */
blockquote {
  margin: 1rem 0; padding: .7rem 1rem; background: var(--quote-bg);
  border-left: 3px solid var(--quote-bar); border-radius: 0 6px 6px 0;
  font-style: italic;
}
blockquote p { margin: 0; }
blockquote p + p { margin-top: .5rem; }
code {
  background: var(--code-bg); padding: .12em .35em; border-radius: 4px;
  font: .88em ui-monospace, SFMono-Regular, Menlo, monospace;
}
pre {
  background: var(--code-bg); border: 1px solid var(--rule); border-radius: 8px;
  padding: .9rem 1rem; overflow-x: auto;
}
pre code { background: none; padding: 0; font-size: .84rem; line-height: 1.5; }
table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--rule); padding: .45rem .7rem; text-align: left; }
th { background: var(--quote-bg); }
hr { border: 0; border-top: 1px solid var(--rule); margin: 2rem 0; }
li { margin: .25rem 0; }
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{css}</style></head>
<body><main>
<header class="meta"><div class="q">{question}</div>{dl}</header>
{body}
</main></body></html>
"""


def split_frontmatter(text):
    """Return (dict_of_fields, body). Frontmatter is optional."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip().strip("\"'")
    return fields, m.group(2)


def render(src: Path) -> Path:
    fields, body = split_frontmatter(src.read_text())
    exe = shutil.which("markdown-it")
    if not exe:
        sys.exit("markdown-it not found. Install: npm i -g markdown-it")
    # Pass a real file — markdown-it hangs waiting on stdin otherwise.
    tmp = src.with_suffix(".body.tmp.md")
    tmp.write_text(body)
    try:
        html_body = subprocess.run(
            [exe, str(tmp)], capture_output=True, text=True, check=True
        ).stdout
    finally:
        tmp.unlink(missing_ok=True)

    question = html.escape(fields.get("question", src.stem.replace("-", " ")))
    rows = "".join(
        f"<dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd>"
        for k, v in fields.items()
        if k != "question"
    )
    page = PAGE.format(
        title=question[:80],
        css=CSS,
        question=question,
        dl=f"<dl>{rows}</dl>" if rows else "",
        body=html_body,
    )
    out = src.with_suffix(".html")
    out.write_text(page)
    return out


def selftest():
    f, b = split_frontmatter("---\nquestion: Why?\ndate: 2026-07-24\n---\n# Hi\n")
    assert f == {"question": "Why?", "date": "2026-07-24"}, f
    assert b.strip() == "# Hi"
    f2, b2 = split_frontmatter("# No frontmatter\n")
    assert f2 == {} and b2.startswith("# No")
    src = Path("/tmp/.research-selftest.md")
    src.write_text(
        '---\nquestion: Does it render?\ndate: 2026-07-24\nstack: test\n---\n'
        '# Heading\n\nSee [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110#name-409-conflict)\n\n'
        '> "a quoted line"\n\n```rust\nlet x = 1;\n```\n'
    )
    out = render(src)
    t = out.read_text()
    assert "<blockquote>" in t and "rfc9110#name-409-conflict" in t
    assert "Does it render?" in t and "prefers-color-scheme" in t
    assert "<dt>stack</dt>" in t
    src.unlink()
    out.unlink()
    print("selftest ok")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selftest":
        selftest()
    else:
        out = render(Path(sys.argv[1]).expanduser())
        print(out)
        if "--no-open" not in sys.argv:
            webbrowser.open(out.resolve().as_uri())
