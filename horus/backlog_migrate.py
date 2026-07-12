"""`horus backlog migrate` — convert an inline PRD `## Backlog` section (structure
v3) into one card per item under `.horus/backlog/`, card-per-file being the fleet
standard (see `.horus/backlog/unify-backlog-cards-fleet-standard.md`).

Idempotent and read-safe: once the Backlog section holds no list items (either
because it was already migrated to the thin pointer, or a fresh project never had
any), a re-run is a no-op — nothing is written. Never silently drops content: any
prose in the section that isn't a recognized list item (an intro sentence, notes
between headings, ...) is preserved verbatim in the replacement pointer section
rather than discarded.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import NamedTuple

from horus import backlog, frontmatter, templates
from horus.upgrade import migration_git_safety

_BACKLOG_HEADING_RE = re.compile(r"^##\s+Backlog\s*$", re.IGNORECASE)
_NEXT_HEADING_RE = re.compile(r"^##\s+\S")
_SUBHEADING_RE = re.compile(r"^###\s+(.*)$")
_ITEM_START_RE = re.compile(r"^(?:[-*]\s+|\d+\.\s+)")

_TAG_RE = re.compile(r"\[(\w+)\]", re.IGNORECASE)
_TAG_TO_TYPE = {"bug": "bug", "feature": "feature", "chore": "chore", "ops": "chore", "task": "task"}


class MigrateAction(NamedTuple):
    status: str  # "created" | "would-create" | "updated" | "would-update" | "noop" | "error"
    message: str


class _Item(NamedTuple):
    heading: str | None  # the enclosing `### ` bucket, if any
    text: str  # verbatim item text, leading list marker stripped from line 1


def _priority_for_heading(heading: str | None) -> str:
    if not heading:
        return "medium"
    low = heading.lower()
    if "now" in low or "next" in low:
        return "high"
    if "deferred" in low:
        return "later"
    if "open" in low or "unscheduled" in low:
        return "medium"
    return "medium"


def _infer_type(text: str) -> str:
    m = _TAG_RE.search(text)
    if m:
        return _TAG_TO_TYPE.get(m.group(1).lower(), backlog.DEFAULT_TYPE)
    return backlog.DEFAULT_TYPE


def _strip_marker(line: str) -> str:
    return _ITEM_START_RE.sub("", line, count=1)


def _split_backlog_items(section_body: str) -> tuple[list[_Item], str]:
    """Split a `## Backlog` section body into top-level list items (bullet or
    numbered, at zero indent) plus any leftover prose that isn't part of one
    (an intro sentence, stray notes) — the leftover is never discarded, only
    reported separately so the caller can preserve it."""
    items: list[_Item] = []
    leftover: list[str] = []
    current_heading: str | None = None
    current_lines: list[str] | None = None

    def flush() -> None:
        nonlocal current_lines
        if current_lines is not None:
            text = "\n".join(current_lines).rstrip()
            if text.strip():
                items.append(_Item(current_heading, text))
        current_lines = None

    for line in section_body.splitlines():
        heading_m = _SUBHEADING_RE.match(line)
        if heading_m:
            flush()
            current_heading = heading_m.group(1).strip()
            continue
        if _ITEM_START_RE.match(line):
            flush()
            current_lines = [_strip_marker(line)]
            continue
        if current_lines is not None:
            current_lines.append(line)
        elif line.strip():
            leftover.append(line)
    flush()
    return items, "\n".join(leftover).strip()


def _item_title(text: str) -> str:
    first_line = text.splitlines()[0] if text else ""
    cleaned = re.sub(r"\*\*|\*|`", "", first_line)
    cleaned = _TAG_RE.sub("", cleaned).strip(" -\t")
    cleaned = re.split(r"[.:—\n]", cleaned, maxsplit=1)[0].strip()
    return cleaned or "Migrated backlog item"


def _slugify(title: str, existing: set[str]) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    base = "-".join(words[:6]) or "backlog-item"
    base = base[:60].rstrip("-") or "backlog-item"
    slug = base
    n = 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    existing.add(slug)
    return slug


def _card_text(item: _Item, *, today: str) -> tuple[str, str]:
    """Returns (slug-source title, card file contents)."""
    title = _item_title(item.text)
    priority = _priority_for_heading(item.heading)
    type_ = _infer_type(item.text)
    front = f"---\nstatus: open\npriority: {priority}\ntype: {type_}\ncreated: {today}\n---\n"
    return title, f"{front}\n# {title}\n\n{item.text}\n"


def _find_backlog_section(lines: list[str]) -> tuple[int, int] | None:
    """(section_start_index, section_end_index) of the `## Backlog` section's
    body within `lines` (the *full* PRD.md, frontmatter included — a `## `
    heading regex never matches inside the `key: value` frontmatter fence, so
    scanning the raw file directly is safe and lets the caller splice the
    section back in without reconstructing anything else byte-for-byte). The
    body runs from just after the heading line to the next `## ` heading or EOF."""
    for i, line in enumerate(lines):
        if _BACKLOG_HEADING_RE.match(line):
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if _NEXT_HEADING_RE.match(lines[j]):
                    end = j
                    break
            return i + 1, end
    return None


def migrate_inline_backlog(project_root: Path, *, apply: bool = False) -> list[MigrateAction]:
    """Convert `project_root`'s `.horus/PRD.md` inline `## Backlog` items into
    cards under `.horus/backlog/`. Dry-run (`apply=False`, the default) reports
    what would change without writing anything. Every other line of PRD.md
    (frontmatter, Vision, Shipped, Rules, ...) is left byte-for-byte untouched —
    only the Backlog section's lines are spliced out and replaced."""
    hdir = project_root / ".horus"
    prd_path = hdir / frontmatter.PRD_FILE
    if not prd_path.is_file():
        return [MigrateAction("error", f"no .horus/{frontmatter.PRD_FILE} (backlog migrate needs structure v3)")]

    prd_text = prd_path.read_text(encoding="utf-8")
    lines = prd_text.splitlines()
    located = _find_backlog_section(lines)
    if located is None:
        return [MigrateAction("error", "no '## Backlog' heading found in .horus/PRD.md")]

    start_idx, end_idx = located
    section_body = "\n".join(lines[start_idx:end_idx])

    # Already migrated: the section starts with the pointer block verbatim (a
    # prior run's own output, or a fresh v3 scaffold that never had inline
    # items). Detect this BEFORE splitting into items, else the preserved
    # "Migrated notes" block below would itself be re-classified as leftover
    # prose on every subsequent run and duplicate without bound.
    if section_body.strip().startswith(templates.backlog_pointer_block()):
        return [MigrateAction("noop", "Backlog section already migrated (pointer present) — nothing to do")]

    items, leftover = _split_backlog_items(section_body)
    if not items and not leftover:
        return [MigrateAction("noop", "Backlog section already thin (no items to migrate) — nothing to do")]

    if apply:
        safety = migration_git_safety(project_root)
        if safety:
            return [MigrateAction("error", safety)]

    bdir = backlog.backlog_dir(project_root)
    existing_slugs = {p.stem for p in bdir.glob("*.md")} if bdir.is_dir() else set()
    today = date.today().isoformat()

    actions: list[MigrateAction] = []
    cards: list[tuple[str, str]] = []  # (filename, contents)
    for item in items:
        title, contents = _card_text(item, today=today)
        slug = _slugify(title, existing_slugs)
        cards.append((f"{slug}.md", contents))
        verb = "created" if apply else "would-create"
        actions.append(MigrateAction(verb, f"{verb.split('-')[-1]} .horus/backlog/{slug}.md (from migrated item)"))

    pointer_lines = [templates.backlog_pointer_block()]
    if leftover:
        pointer_lines.append("")
        pointer_lines.append("**Migrated notes (preserved, not converted to a card):**")
        pointer_lines.append("")
        pointer_lines.append(leftover)
    new_section = "\n".join(pointer_lines)

    new_lines = lines[:start_idx] + [""] + new_section.splitlines() + [""] + lines[end_idx:]
    new_prd_text = "\n".join(new_lines)
    if prd_text.endswith("\n"):
        new_prd_text += "\n"

    verb = "updated" if apply else "would-update"
    actions.append(MigrateAction(
        verb,
        f"{'updated' if apply else 'would update'} .horus/{frontmatter.PRD_FILE} — Backlog section replaced with a pointer"
        + (" (leftover prose preserved)" if leftover else ""),
    ))

    if apply:
        bdir.mkdir(parents=True, exist_ok=True)
        for filename, contents in cards:
            (bdir / filename).write_text(contents, encoding="utf-8")
        prd_path.write_text(new_prd_text, encoding="utf-8")

    return actions
