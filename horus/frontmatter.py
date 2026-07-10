"""Minimal, dependency-free front-matter parsing for `.horus/` files.

Horus controls the format of its own files, so a tiny `key: value` parser is
enough and avoids a PyYAML dependency. It is intentionally conservative: it only
understands the simple scalar front matter Horus writes (quoted or bare scalars).
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

PRD_FILE = "PRD.md"

# Where each focus/handoff field lives in the legacy v2 lanes, in fallback order.
# `resolve_focus` prefers `.horus/PRD.md` frontmatter (structure v3) the moment a
# field is present there; these are the per-field fallbacks for v2 projects and
# for v3 projects still carrying transitional shims.
_SHIM_HOMES: dict[str, tuple[str, ...]] = {
    "status": ("project.md",),
    "current_focus": ("project.md", "roadmap.md"),
    "next_action": ("roadmap.md",),
    "next_prompt": ("roadmap.md",),
    "execution_recommendation": ("roadmap.md",),
    "last_updated": ("project.md", "roadmap.md"),
}


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


def prd_path(project_root: Path) -> Path:
    return project_root / ".horus" / PRD_FILE


def has_prd(project_root: Path) -> bool:
    """True when the project uses the v3 continuity structure (PRD.md + sessions/)."""
    return prd_path(project_root).is_file()


def continuity_source(project_root: Path) -> str:
    """Which continuity file `resolve_focus` reads, for display attribution.

    Fleet/status views render this so a stale local PRD is attributable to a
    specific file rather than presented as if it were fetched-remote truth — this
    is always the *working-checkout* copy, never a fetched remote's version.
    """
    if has_prd(project_root):
        return f".horus/{PRD_FILE} (working checkout)"
    return ".horus/project.md+roadmap.md (working checkout, v2)"


def parse_file(path: Path) -> Document | None:
    """Parse a Markdown file into a Document, or None when it doesn't exist."""
    if not path.is_file():
        return None
    return parse(path.read_text(encoding="utf-8"))


def resolve_focus(project_root: Path) -> dict[str, str]:
    """Resolve the focus/handoff frontmatter fields for a project, PRD-first.

    v3 projects carry `current_focus` / `next_action` / `next_prompt` /
    `execution_recommendation` (plus `status` / `last_updated`) in `.horus/PRD.md`
    frontmatter; v2 projects keep them in the `project.md` / `roadmap.md` lanes.
    Per field, a non-empty PRD.md value wins the moment it exists; otherwise the
    legacy lane value is used — so v2 projects behave exactly as before, and a v3
    project may delete the shims entirely once PRD.md carries the fields.
    """
    hdir = project_root / ".horus"
    prd = parse_file(hdir / PRD_FILE)
    shims: dict[str, Document | None] = {}
    result: dict[str, str] = {}
    for field, homes in _SHIM_HOMES.items():
        value = ""
        if prd is not None:
            value = str(prd.front_matter.get(field, "")).strip()
        if not value:
            for home in homes:
                if home not in shims:
                    shims[home] = parse_file(hdir / home)
                doc = shims[home]
                if doc is not None:
                    value = str(doc.front_matter.get(field, "")).strip()
                if value:
                    break
        result[field] = value
    return result
