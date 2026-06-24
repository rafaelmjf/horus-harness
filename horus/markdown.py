"""A deliberately small, safe Markdown-to-HTML renderer.

Covers only what `.horus/` files use: headings, bullet lists (incl. `[ ]`/`[x]`/
`[~]` task items), fenced code blocks, inline code, and paragraphs. All text is
HTML-escaped before rendering, so it is safe for untrusted local content. This is
not a general Markdown engine and intentionally avoids a third-party dependency.
"""

from __future__ import annotations

import html
import re

_INLINE_CODE = re.compile(r"`([^`]+)`")

# task-marker -> (symbol, css class)
_TASK_MARKERS = (
    ("[x]", "&#9745;", "done"),
    ("[X]", "&#9745;", "done"),
    ("[ ]", "&#9744;", "todo"),
    ("[~]", "&#9682;", "partial"),
)


def _inline(escaped: str) -> str:
    # Backticks are not touched by html.escape, so this runs on escaped text.
    return _INLINE_CODE.sub(r"<code>\1</code>", escaped)


def render(md: str) -> str:
    out: list[str] = []
    para: list[str] = []
    in_code = False
    in_list = False

    def flush_para() -> None:
        if para:
            out.append("<p>" + " ".join(para) + "</p>")
            para.clear()

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for line in md.splitlines():
        if line.strip().startswith("```"):
            flush_para()
            close_list()
            if not in_code:
                out.append("<pre><code>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            continue

        if in_code:
            out.append(html.escape(line))
            continue

        stripped = line.strip()
        if not stripped:
            flush_para()
            close_list()
            continue

        if stripped.startswith("#"):
            flush_para()
            close_list()
            level = len(stripped) - len(stripped.lstrip("#"))
            text = _inline(html.escape(stripped[level:].strip()))
            tag = min(level + 1, 6)
            out.append(f"<h{tag}>{text}</h{tag}>")
            continue

        if stripped[:2] in ("- ", "* "):
            flush_para()
            if not in_list:
                out.append("<ul>")
                in_list = True
            content = stripped[2:]
            symbol = ""
            cls = ""
            for token, sym, css in _TASK_MARKERS:
                if content.startswith(token):
                    symbol = sym + " "
                    cls = f' class="task {css}"'
                    content = content[len(token):].strip()
                    break
            out.append(f"<li{cls}>{symbol}{_inline(html.escape(content))}</li>")
            continue

        para.append(_inline(html.escape(stripped)))

    flush_para()
    close_list()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)
