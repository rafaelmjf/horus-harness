"""Minimal, dependency-free front-matter parsing for `.horus/` files.

Horus controls the format of its own files, so a tiny `key: value` parser is
enough and avoids a PyYAML dependency. It is intentionally conservative: it only
understands the simple scalar front matter Horus writes (quoted or bare scalars).
"""

from __future__ import annotations

from typing import NamedTuple


class Document(NamedTuple):
    front_matter: dict[str, str]
    body: str


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse(text: str) -> Document:
    """Split a Markdown document into front matter and body.

    A document has front matter only when it begins with a line that is exactly
    `---`, followed by `key: value` lines, terminated by another `---` line.
    Anything else is treated as a body with empty front matter.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return Document({}, text)

    front: dict[str, str] = {}
    end_index: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        front[key.strip()] = _strip_quotes(value)

    if end_index is None:
        # No closing fence: not valid front matter, treat whole text as body.
        return Document({}, text)

    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return Document(front, body)
