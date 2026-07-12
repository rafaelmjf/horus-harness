"""`.horus/backlog/` card-per-file backlog: parsing, claim, and ship provenance.

Cards are self-contained Markdown files with simple frontmatter (`status`,
`priority`, `tier`, `created`). This module adds two OPTIONAL fields read the
same way:

- `parallel: safe | exclusive` — human-authored intent. `exclusive` means this
  card must not run concurrently with any other in-progress card.
- `surface: <comma-separated globs>` — the code areas the card touches, e.g.
  `surface: horus/dashboard.py, horus/pty_*`.

Both are optional and back-compat: a card with neither field still claims,
same as before this module existed. This is a guardrail (metadata + a
claim-time check + display), not a scheduler — no daemon, no auto-routing.

- `type: bug | feature | chore | task` — one `backlog/` dir instead of a
  separate `bugs/` folder; unset/blank defaults to "task". `horus backlog list
  --type bug` is the query surface, not a folder split.
- `status: shipped` plus `shipped_pr` / `shipped_sha` records immutable merge
  provenance in the card itself. Shipped cards stay in place for git history;
  active views hide them unless explicitly requested.
"""

from __future__ import annotations

import contextlib
import fcntl
import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

from horus import frontmatter
from horus.continuity import Finding

BACKLOG_DIR = "backlog"
_CLAIM_LOCK_FILE = ".claim.lock"

# In-progress for claim-overlap purposes. Cards otherwise use "open" (default)
# and are deleted on completion (see PRD's structure contract).
_IN_PROGRESS_STATUSES = ("claimed",)

# `type` is a free-form-but-conventional field: one `backlog/` dir instead of a
# separate `bugs/` folder, with visibility coming from tooling (this list + the
# `--type` filter) rather than folder separation. Unset/blank defaults to "task".
CARD_TYPES = ("bug", "feature", "chore", "task")
DEFAULT_TYPE = "task"

_LINGERING_DONE_RE = re.compile(
    r"^\s*(?:(?:[-*]|\d+\.)\s*)?(?:\[x\]\s*)?DONE\b\s*(?:$|:|[-—])",
    re.IGNORECASE,
)
_CHECKED_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s*\[x\]", re.IGNORECASE)


@dataclass(frozen=True)
class Card:
    path: Path
    name: str  # filename stem, the identifier used to claim/reference a card
    status: str
    priority: str
    tier: str
    created: str
    parallel: str  # "safe" | "exclusive" | "" (unstated)
    surface: tuple[str, ...]
    type: str  # "bug" | "feature" | "chore" | "task" — defaults to "task" if unstated
    shipped_pr: str
    shipped_sha: str
    shipped: str  # legacy free-text shipped note, used only to detect unflipped drift
    title: str


def _parse_surface(raw: str) -> tuple[str, ...]:
    raw = raw.strip()
    if not raw:
        return ()
    if raw[0] == "[" and raw[-1] == "]":
        raw = raw[1:-1]
    parts = []
    for token in raw.split(","):
        token = token.strip().strip("'\"").strip()
        if token:
            parts.append(token)
    return tuple(parts)


def _title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def backlog_dir(root: Path) -> Path:
    return root / ".horus" / BACKLOG_DIR


def _card_from_path(path: Path) -> Card:
    doc = frontmatter.parse(path.read_text(encoding="utf-8"))
    fm = doc.front_matter
    return Card(
        path=path,
        name=path.stem,
        status=fm.get("status", "open").strip().lower() or "open",
        priority=fm.get("priority", "").strip(),
        tier=fm.get("tier", "").strip(),
        created=fm.get("created", "").strip(),
        parallel=fm.get("parallel", "").strip().lower(),
        surface=_parse_surface(fm.get("surface", "")),
        type=fm.get("type", "").strip().lower() or DEFAULT_TYPE,
        shipped_pr=fm.get("shipped_pr", "").strip(),
        shipped_sha=fm.get("shipped_sha", "").strip(),
        shipped=fm.get("shipped", "").strip(),
        title=_title(doc.body, path.stem),
    )


def load_cards(root: Path) -> list[Card]:
    """All backlog cards, sorted by filename. Empty list if there's no backlog/."""
    hdir = backlog_dir(root)
    if not hdir.is_dir():
        return []
    return [_card_from_path(p) for p in sorted(hdir.glob("*.md")) if p.is_file()]


def find_card(root: Path, name: str) -> Card | None:
    """Look up a card by its filename stem, with or without a trailing `.md`."""
    key = name[:-3] if name.endswith(".md") else name
    for card in load_cards(root):
        if card.name == key:
            return card
    return None


def hygiene_findings(root: Path) -> list[Finding]:
    """Report card lifecycle drift for consolidate and the recurring close gate."""
    findings: list[Finding] = []
    for card in load_cards(root):
        body = frontmatter.parse(card.path.read_text(encoding="utf-8")).body
        lingering_done = card.status == "done" or any(
            _CHECKED_ITEM_RE.match(line) or _LINGERING_DONE_RE.match(line)
            for line in body.splitlines()
        )
        if lingering_done:
            findings.append(Finding(
                "warn",
                f"backlog card '{card.name}' is lingering done — mark it shipped with "
                "`horus backlog ship` (or remove stale data)",
            ))
        if card.status != "shipped" and (card.shipped_pr or card.shipped_sha or card.shipped):
            findings.append(Finding(
                "warn",
                f"backlog card '{card.name}' has shipped provenance but status is "
                f"'{card.status}' — run `horus backlog ship {card.name} --pr … --sha …`",
            ))
    return findings


def _pair_overlaps(a: str, b: str) -> bool:
    """Heuristic glob-vs-glob overlap: does either pattern match the other read
    as a literal candidate path? Catches the common cases (equal paths, a glob
    matching a concrete sibling path) without claiming to be a full glob-vs-glob
    intersection solver — this is a guardrail, not a hard scheduler."""
    return fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a)


def surface_overlap(a: tuple[str, ...], b: tuple[str, ...]) -> list[tuple[str, str]]:
    """Pairs of globs (one from `a`, one from `b`) that overlap."""
    return [(x, y) for x in a for y in b if _pair_overlaps(x, y)]


def claim_check(root: Path, name: str) -> list[Finding]:
    """Findings for claiming card `name` against currently in-progress cards.

    Only warns when there is another in-progress card to conflict with — a
    card claimed while nothing else is in progress always claims clean,
    regardless of whether it carries `parallel`/`surface` at all."""
    target = find_card(root, name)
    if target is None:
        return [Finding("fail", f"no backlog card named '{name}'")]

    others = [
        c for c in load_cards(root)
        if c.name != target.name and c.status in _IN_PROGRESS_STATUSES
    ]
    findings: list[Finding] = []
    for other in others:
        if target.parallel == "exclusive" or other.parallel == "exclusive":
            exclusive_one = target.name if target.parallel == "exclusive" else other.name
            findings.append(Finding(
                "warn",
                f"'{exclusive_one}' is marked parallel: exclusive — do not run "
                f"'{target.name}' concurrently with in-progress '{other.name}'",
            ))
            continue
        if not target.surface or not other.surface:
            missing = target.name if not target.surface else other.name
            findings.append(Finding(
                "warn",
                f"'{missing}' has no 'surface' — overlap with in-progress "
                f"'{other.name}' can't be verified",
            ))
            continue
        pairs = surface_overlap(target.surface, other.surface)
        if pairs:
            shown = ", ".join(f"{x} ~ {y}" for x, y in pairs)
            findings.append(Finding(
                "warn",
                f"'{target.name}' surface overlaps in-progress '{other.name}': {shown}",
            ))
    return findings


_STATUS_KEY = "status"


def _set_front_matter(path: Path, updates: dict[str, str]) -> None:
    updates = dict(updates)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: no frontmatter fence to update status in")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError(f"{path}: unterminated frontmatter fence")
    for i in range(1, end):
        key, sep, _ = lines[i].partition(":")
        key = key.strip()
        if sep and key in updates:
            lines[i] = f"{key}: {updates.pop(key)}"
    for key, value in updates.items():
        lines.insert(end, f"{key}: {value}")
        end += 1
    newline = "\n" if text.endswith("\n") else ""
    path.write_text("\n".join(lines) + newline, encoding="utf-8")


def _set_status(path: Path, new_status: str) -> None:
    _set_front_matter(path, {_STATUS_KEY: new_status})


@contextlib.contextmanager
def _claim_lock(root: Path):
    """Serialize the load-check-write critical section across processes.

    Two concurrent `claim()` calls both read the backlog before either writes
    `status: claimed`, so without this lock neither sees the other as
    in-progress and the overlap/exclusive guardrail can be bypassed (TOCTOU).
    `flock` is held for the whole check-then-set-status section below."""
    hdir = backlog_dir(root)
    hdir.mkdir(parents=True, exist_ok=True)
    with open(hdir / _CLAIM_LOCK_FILE, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def claim(root: Path, name: str, *, force: bool = False) -> tuple[bool, list[Finding]]:
    """Attempt to claim card `name`. Returns (claimed, findings).

    Warnings block the claim unless `force=True`; a `fail` (card not found)
    always blocks. On success the card's `status` frontmatter is set to
    `claimed` in place — nothing else about the file changes."""
    with _claim_lock(root):
        findings = claim_check(root, name)
        if any(f.level == "fail" for f in findings):
            return False, findings
        if findings and not force:
            return False, findings
        target = find_card(root, name)
        assert target is not None  # already checked above via claim_check
        _set_status(target.path, "claimed")
        return True, findings


def ship(root: Path, name: str, *, pr: str, sha: str) -> Card | None:
    """Mark a card shipped in place and stamp its merged-PR provenance.

    The card is deliberately retained under ``.horus/backlog/``. Its ``shipped``
    status removes it from active views without losing the work item's context.
    """
    with _claim_lock(root):
        target = find_card(root, name)
        if target is None:
            return None
        _set_front_matter(target.path, {
            "status": "shipped",
            "shipped_pr": pr,
            "shipped_sha": sha,
        })
        return find_card(root, name)
