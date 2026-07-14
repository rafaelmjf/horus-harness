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
- a `## Reviews` body section holds free-text review/comment entries, appended
  by :func:`add_review` (`horus backlog review`, also the TUI's `r` key).
  Append-only by convention: entries accumulate as history and end-of-section
  appends keep cross-machine merges conflict-free. Tooling never parses entry
  contents — reviews are for humans and agents to read, not a schema — and the
  lingering-done hygiene scan skips this section so a review saying
  "DONE looks wrong" or quoting a `[x]` checklist can't flag the card.
"""

from __future__ import annotations

import contextlib
import datetime
import fnmatch
import getpass
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from horus import frontmatter
from horus.continuity import Finding

BACKLOG_DIR = "backlog"
_CLAIM_LOCK_FILE = ".claim.lock"
REVIEWS_HEADING = "## Reviews"
REVIEW_SOURCES = ("manual", "agent")

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


def _reviews_span(lines: list[str]) -> tuple[int, int] | None:
    """(start, end) line indices of the `## Reviews` section — `start` is the
    heading line, `end` the next `## ` heading (or EOF). None if absent."""
    start = next(
        (i for i, line in enumerate(lines) if line.strip().casefold() == REVIEWS_HEADING.casefold()),
        None,
    )
    if start is None:
        return None
    end = next(
        (j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
        len(lines),
    )
    return start, end


def _lines_outside_reviews(body: str) -> list[str]:
    lines = body.splitlines()
    span = _reviews_span(lines)
    if span is None:
        return lines
    start, end = span
    return lines[:start] + lines[end:]


def hygiene_findings(root: Path) -> list[Finding]:
    """Report card lifecycle drift for consolidate and the recurring close gate."""
    findings: list[Finding] = []
    for card in load_cards(root):
        body = frontmatter.parse(card.path.read_text(encoding="utf-8")).body
        # Review entries are free text — a reviewer writing "DONE" or quoting a
        # checked item must not read as lifecycle drift of the card itself.
        lingering_done = card.status == "done" or any(
            _CHECKED_ITEM_RE.match(line) or _LINGERING_DONE_RE.match(line)
            for line in _lines_outside_reviews(body)
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
    # fcntl is Unix-only; a top-level import broke `horus` entirely on Windows
    # (install-smoke: ModuleNotFoundError on any CLI invocation). There the
    # claim guard degrades to advisory (msvcrt locking isn't equivalent and
    # single-user Windows overlap is theoretical), which matches the guard's
    # intent — best-effort TOCTOU protection, not a correctness invariant.
    try:
        import fcntl
    except ImportError:
        with open(hdir / _CLAIM_LOCK_FILE, "w", encoding="utf-8"):
            yield
        return
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


def default_author(root: Path) -> str:
    """Reviewer attribution when none is given: git identity, then OS user."""
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "config", "user.name"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return getpass.getuser()


def review_entry(*, author: str, source: str = "manual", verdict: str = "", note: str = "") -> str:
    """One `### <date> — <author> (<source>)` entry for the `## Reviews` section."""
    lines = [f"### {datetime.date.today().isoformat()} — {author} ({source})"]
    if verdict:
        lines.append(f"Verdict: {verdict}")
    if note.strip():
        lines.extend(["", note.strip()])
    return "\n".join(lines)


def add_review(
    root: Path,
    name: str,
    *,
    author: str,
    source: str = "manual",
    verdict: str = "",
    note: str = "",
) -> Card | None:
    """Append a review entry to card `name`'s `## Reviews` section, creating the
    section at the end of the card when absent. Returns the card, or None if no
    card matches. The file changes only by insertion — frontmatter and the rest
    of the body are untouched, so this composes with claim/ship provenance."""
    with _claim_lock(root):
        target = find_card(root, name)
        if target is None:
            return None
        text = target.path.read_text(encoding="utf-8")
        entry = review_entry(author=author, source=source, verdict=verdict, note=note).splitlines()
        lines = text.splitlines()
        span = _reviews_span(lines)
        if span is None:
            while lines and not lines[-1].strip():
                lines.pop()
            lines.extend(["", REVIEWS_HEADING, "", *entry])
        else:
            start, end = span
            while end > start + 1 and not lines[end - 1].strip():
                end -= 1
            lines[end:end] = ["", *entry]
        target.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return find_card(root, name)


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
