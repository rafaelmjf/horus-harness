"""Managed-block extraction and drift detection for AGENTS.md / CLAUDE.md.

The shared `HORUS:BEGIN/END shared-instructions` blocks in the two files are
intentionally *not* byte-identical: each ends with a line naming the other file
("...aligned with the matching block in `CLAUDE.md`" vs "`AGENTS.md`"). A naive
equality check would therefore report drift on every run. ``normalize_block``
removes that difference so only real divergence is reported.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from horus.templates import BLOCK_BEGIN, BLOCK_END

# Matches the cross-reference line regardless of which file it names.
_CROSSREF_RE = re.compile(
    r"(the matching block in `)(?:AGENTS\.md|CLAUDE\.md)(`)",
)
_CROSSREF_PLACEHOLDER = r"\1<other>\2"


class BlockResult(NamedTuple):
    found: bool
    raw: str | None  # block contents including markers, or None if not found


def extract_block(text: str) -> BlockResult:
    """Pull the managed block (markers included) out of a file's text."""
    start = text.find(BLOCK_BEGIN)
    if start == -1:
        return BlockResult(False, None)
    end = text.find(BLOCK_END, start)
    if end == -1:
        return BlockResult(False, None)
    end += len(BLOCK_END)
    return BlockResult(True, text[start:end])


def normalize_block(raw: str) -> str:
    """Canonicalize a block for comparison: neutralize the cross-reference line
    and ignore trailing whitespace / line-ending differences."""
    neutral = _CROSSREF_RE.sub(_CROSSREF_PLACEHOLDER, raw)
    lines = [line.rstrip() for line in neutral.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()


class DriftReport(NamedTuple):
    status: str  # "aligned" | "drift" | "missing"
    detail: str


def check_drift(text_a: str, name_a: str, text_b: str, name_b: str) -> DriftReport:
    """Compare the managed blocks in two instruction files."""
    a = extract_block(text_a)
    b = extract_block(text_b)

    missing = []
    if not a.found:
        missing.append(name_a)
    if not b.found:
        missing.append(name_b)
    if missing:
        return DriftReport(
            "missing",
            "managed block not found in: " + ", ".join(missing),
        )

    if normalize_block(a.raw) == normalize_block(b.raw):
        return DriftReport("aligned", "shared blocks match (cross-reference aside)")

    import difflib

    diff = difflib.unified_diff(
        normalize_block(a.raw).splitlines(),
        normalize_block(b.raw).splitlines(),
        fromfile=name_a,
        tofile=name_b,
        lineterm="",
    )
    return DriftReport("drift", "\n".join(diff))
