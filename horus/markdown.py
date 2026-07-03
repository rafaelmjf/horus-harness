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
_TABLE_SEP_CELL = re.compile(r"^:?-{1,}:?$")

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


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    cells = _cells(stripped)
    return bool(cells) and all(_TABLE_SEP_CELL.match(c) for c in cells)


_LIST_MARKER_RE = re.compile(r"^(?:[-*]|\d+\.)\s+")
_BOLD_MARK_RE = re.compile(r"\*\*|__")
_SENTENCE_END_RE = re.compile(r"[.!?]$")


def subsection(body: str, heading: str) -> str:
    """Body of a third-level (`### `) markdown section within a section body, until
    the next `### ` or `## ` heading. Mirrors `routines._section` one level deeper."""
    lines = body.splitlines()
    start = None
    target = f"### {heading}".lower()
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s.startswith("### ") or s.startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end])


def subsection_headings(body: str) -> list[str]:
    """Third-level (`### `) heading titles at the top of a markdown section body,
    in document order."""
    return [line.strip()[4:].strip() for line in body.splitlines() if line.strip().startswith("### ")]


def plain_text(text: str) -> str:
    """Strip markdown emphasis/code markers and collapse whitespace to one line."""
    text = _BOLD_MARK_RE.sub("", text)
    text = _INLINE_CODE.sub(r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def first_sentence(text: str, max_len: int = 160) -> str:
    """The first sentence of ``text``, or a hard cutoff at ``max_len`` — always
    ending in an ellipsis when the source was truncated (including when the text
    itself was a hard-wrapped continuation line with no terminal punctuation)."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    m = re.match(r"(.{1,%d}?[.!?])(?:\s|$)" % max_len, text)
    candidate = m.group(1) if m else text
    if len(candidate) > max_len:
        return candidate[: max_len - 1].rstrip() + "…"
    if not _SENTENCE_END_RE.search(candidate):
        return candidate + "…"
    return candidate


def shipped_summary(section_body: str) -> tuple[int, str]:
    """Count shipped entries in a PRD `## Shipped` section body and return the
    latest one as a plain one-liner. Prefers distinct bullet lines (wrap-tolerant);
    falls back to bold-prefixed paragraph blocks (this repo's live PRD groups
    capabilities under `**Category:**` paragraphs rather than one bullet each)."""
    text = section_body.strip()
    if not text:
        return 0, ""

    bullets: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            bullets.append(" ".join(current))
            current.clear()

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if _LIST_MARKER_RE.match(stripped):
            flush()
            current.append(_LIST_MARKER_RE.sub("", stripped, count=1))
        elif not stripped:
            flush()
        elif current:
            current.append(stripped)
    flush()

    if bullets:
        return len(bullets), plain_text(bullets[-1])

    bold_blocks = [
        joined
        for block in re.split(r"\n\s*\n", text)
        if (joined := " ".join(l.strip() for l in block.splitlines() if l.strip())).startswith("**")
    ]
    if bold_blocks:
        return len(bold_blocks), plain_text(bold_blocks[-1])
    return 0, ""


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

    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        # GFM pipe table: a header row followed by a separator row.
        if (
            not in_code
            and line.strip().startswith("|")
            and i + 1 < len(lines)
            and _is_table_separator(lines[i + 1])
        ):
            flush_para()
            close_list()
            header = _cells(line)
            head = "".join(f"<th>{_inline(html.escape(c))}</th>" for c in header)
            rows = [f"<tr>{head}</tr>"]
            i += 2  # skip header + separator
            while i < len(lines) and lines[i].strip().startswith("|"):
                tds = "".join(f"<td>{_inline(html.escape(c))}</td>" for c in _cells(lines[i]))
                rows.append(f"<tr>{tds}</tr>")
                i += 1
            out.append("<table>" + "".join(rows) + "</table>")
            continue

        i += 1
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
