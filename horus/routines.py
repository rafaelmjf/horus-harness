"""Agent-delegated maintenance routines over `.horus/`.

Horus runs the deterministic pre-pass (parse the lanes, detect candidates, report)
and the CLI then prints a ritual prompt for the in-loop agent to carry out the
judgement-heavy edits. Like `closure`, nothing is spawned here — the agent already
running in the repo is the LLM. See `docs/routines.md` for the full contracts.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from horus import frontmatter, roadmap, templates
from horus.continuity import (
    HORUS_DIR,
    RECOMMENDED_FILES,
    TEMP_DIR,
    Finding,
    horus_dir,
    recent_sessions,
)

# Lanes consolidate reasons about (sessions/ handled separately).
_LANES = ("project.md", "roadmap.md", "features.md", "decisions.md", "history.md")

# Common source logs `distill-history` can compress, in priority order.
_SOURCE_LOGS = ("docs/HISTORY.md", "CHANGELOG.md", "HISTORY.md", "docs/CHANGELOG.md")

# Root-level canonical docs `infer` distills `.horus/` from (glob prefixes + exact names).
_CANONICAL_DOC_GLOBS = (
    "README*", "ROADMAP*", "TODO*", "PLAN*", "PROJECT_STATUS*", "STATUS*",
    "CHANGELOG*", "HISTORY*", "ARCHITECTURE*",
)
_CANONICAL_DOC_NAMES = ("CLAUDE.md", "AGENTS.md")
_DOC_SUFFIXES = ("", ".md", ".markdown", ".rst", ".txt")

_WORD_RE = re.compile(r"[a-z0-9_]+")
_STOPWORDS = {
    "the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "with", "via",
    "make", "add", "build", "into", "per", "is", "be", "do", "as", "at", "by",
    "new", "use", "from", "that", "this", "it", "its", "our", "we",
}


def _key_tokens(text: str, extra_stop: frozenset[str] = frozenset()) -> set[str]:
    """Significant lowercase tokens for fuzzy cross-lane matching."""
    cleaned = re.sub(r"\*\*|__|`", "", text)
    return {
        w for w in _WORD_RE.findall(cleaned.lower())
        if len(w) > 2 and w not in _STOPWORDS and w not in extra_stop
    }


def _overlap(a: set[str], b: set[str]) -> float:
    """Overlap coefficient: |a ∩ b| / min(|a|, |b|)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _similar(a: set[str], b: set[str], threshold: float, *, min_shared: int = 2) -> bool:
    """Two token sets describe the same item: enough distinctive overlap."""
    return len(a & b) >= min_shared and _overlap(a, b) >= threshold


def _short(text: str, width: int = 48) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"\*\*|__|`", "", text)).strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def feature_capabilities(features_body: str) -> list[str]:
    """First-column (capability) cells from the markdown tables in features.md."""
    caps: list[str] = []
    for raw in features_body.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if not first or set(first) <= set("-: "):  # separator row
            continue
        if first.lower() == "capability":  # header row
            continue
        caps.append(first)
    return caps


def feature_items(features_body: str) -> dict[str, list[str]]:
    """Capability names per section of features.md: shipped / in_progress / planned."""
    items: dict[str, list[str]] = {"shipped": [], "in_progress": [], "planned": []}
    section: str | None = None
    for raw in features_body.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            low = line.lower()
            section = (
                "shipped" if "shipped" in low
                else "in_progress" if "progress" in low
                else "planned" if "planned" in low
                else None
            )
            continue
        if section and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            first = cells[0] if cells else ""
            if not first or set(first) <= set("-: ") or first.lower() == "capability":
                continue
            items[section].append(first)
    return items


def feature_counts(features_body: str) -> dict[str, int]:
    """Capability row counts per section of features.md."""
    return {k: len(v) for k, v in feature_items(features_body).items()}


def _read(hdir: Path, name: str) -> str | None:
    path = hdir / name
    return path.read_text(encoding="utf-8") if path.is_file() else None


# --------------------------------------------------------------------------- #
# consolidate
# --------------------------------------------------------------------------- #

def _name_stopwords(root: Path) -> frozenset[str]:
    """Project-name tokens are low-signal *within* that project — exclude from matching."""
    return frozenset(w for w in _WORD_RE.findall(root.name.lower()) if len(w) > 2)


# Cap how many individual overlap lines we print before summarizing the rest.
_MAX_OVERLAP_LINES = 8


def consolidate_signals(root: Path, *, overlap_threshold: float = 0.5) -> list[Finding]:
    """Detect what a consolidation pass should route/prune/distill. Read-only."""
    findings: list[Finding] = []
    hdir = horus_dir(root)
    if not hdir.is_dir():
        return [Finding("fail", f"no {HORUS_DIR}/ directory (run `horus init`)")]

    for name in RECOMMENDED_FILES:
        if not (hdir / name).is_file():
            findings.append(Finding("warn", f"{HORUS_DIR}/{name} missing — run `horus init` to scaffold it"))

    stop = _name_stopwords(root)
    roadmap_body = _read(hdir, "roadmap.md")
    features_body = _read(hdir, "features.md")

    tasks = roadmap.parse_tasks(frontmatter.parse(roadmap_body).body) if roadmap_body else []
    caps = feature_capabilities(features_body) if features_body else []
    cap_tokens = [(c, _key_tokens(c, stop)) for c in caps]

    def matched_cap(task_tokens: set[str]) -> str | None:
        for cap, c_tokens in cap_tokens:
            if _similar(task_tokens, c_tokens, overlap_threshold):
                return cap
        return None

    # Rule 2: roadmap items that overlap a features row → split (action vs status).
    # A roadmap item that already points back at features.md is treated as an
    # intentional, reconciled split (the cross-reference is the split marker), so the
    # warning clears once the agent adds the pointer — otherwise in-progress/planned
    # items that legitimately live in both lanes would warn forever.
    overlaps: list[tuple[str, str]] = []
    reconciled = 0
    done = [t for t in tasks if t.state == "done"]
    unshipped_done = 0
    for t in tasks:
        cap = matched_cap(_key_tokens(t.text, stop))
        if cap:
            if "features.md" in t.text.lower():
                reconciled += 1
            else:
                overlaps.append((t.text, cap))
        elif t.state == "done":
            unshipped_done += 1

    for text, cap in overlaps[:_MAX_OVERLAP_LINES]:
        findings.append(Finding(
            "warn",
            f"overlap: roadmap '{_short(text)}' ↔ features '{_short(cap)}' — split: keep "
            f"action points in roadmap, status in features, and cross-reference both",
        ))
    if len(overlaps) > _MAX_OVERLAP_LINES:
        findings.append(Finding("warn", f"… and {len(overlaps) - _MAX_OVERLAP_LINES} more roadmap↔features overlap(s) to split"))
    if reconciled:
        findings.append(Finding("ok", f"{reconciled} roadmap↔features pair(s) already split (cross-referenced)"))
    if not overlaps and not reconciled:
        findings.append(Finding("ok", "no roadmap↔features overlap detected"))

    # Rule 1: done roadmap items without a matching capability row → maybe ship to ledger.
    if done:
        findings.append(Finding(
            "warn",
            f"{len(done)} done roadmap item(s); {unshipped_done} without a features row — "
            f"move shipped capabilities to features.md, then prune the done items",
        ))

    # Rule 5: sessions waiting to be distilled upward.
    sessions = recent_sessions(root, limit=999)
    if sessions:
        findings.append(Finding(
            "warn", f"{len(sessions)} session summary(ies) to distill into the lanes"
        ))
    temp_notes = _temp_notes(root)
    if temp_notes:
        findings.append(Finding(
            "warn", f"{len(temp_notes)} temp worker handoff note(s) to review/distill"
        ))

    if not any(f.level in ("warn", "fail") for f in findings):
        findings.append(Finding("ok", "lanes look consolidated — no routing/pruning candidates"))
    return findings


def _temp_notes(root: Path) -> list[Path]:
    temp = horus_dir(root) / TEMP_DIR
    if not temp.is_dir():
        return []
    files = [p for p in temp.glob("*.md") if p.is_file()]
    files.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return files


# --------------------------------------------------------------------------- #
# freshness — is the dashboard's read-surface current with the work + this session?
# --------------------------------------------------------------------------- #

# The exact fields the dashboard renders as a project's *current* state. The closure
# ritual must keep these fresh; these checks detect (never author) when it didn't.
# project.md/roadmap.md should track every project-moving session; features.md only
# changes on a ship (covered by the consolidate ship→ledger signal), so it's not here.
_FRESH_LANES = ("project.md", "roadmap.md")


def _as_date(value: object) -> date | None:
    """Coerce a frontmatter ``last_updated`` / ``date`` value to a date, tolerantly."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def freshness_signals(root: Path) -> list[Finding]:
    """Detect when the dashboard would show *stale* state after a close — read-only.

    The drift this catches (and what closure must fix): lanes not refreshed since the
    latest session, an empty/placeholder NEXT or focus, or a `next_action` that points
    at work already shipped. Detection only — the agent authors the fix in the skill."""
    findings: list[Finding] = []
    hdir = horus_dir(root)
    if not hdir.is_dir():
        return findings

    sessions = recent_sessions(root, limit=1)
    session_date = None
    if sessions:
        session_date = _as_date(frontmatter.parse(sessions[0].read_text(encoding="utf-8")).front_matter.get("date"))

    # 1) Lanes that should track every session, but weren't updated since the last one.
    if session_date:
        for lane in _FRESH_LANES:
            body = _read(hdir, lane)
            if body is None:
                continue
            lu = _as_date(frontmatter.parse(body).front_matter.get("last_updated"))
            if lu is None or lu < session_date:
                stamp = lu.isoformat() if lu else "unset"
                findings.append(Finding(
                    "warn",
                    f"{HORUS_DIR}/{lane} last_updated ({stamp}) is older than the latest session "
                    f"({session_date.isoformat()}) — refresh it (the dashboard shows it) and bump last_updated",
                ))

    # 2) The dashboard's NEXT + focus must be authored (it never infers them).
    rm = _read(hdir, "roadmap.md")
    next_action = ""
    if rm is not None:
        fm = frontmatter.parse(rm).front_matter
        next_action = (fm.get("next_action") or "").strip()
        if not next_action:
            findings.append(Finding(
                "warn", "roadmap.md next_action is empty — the dashboard NEXT shows 'not set'; author it at closure"
            ))
        if not (fm.get("next_prompt") or "").strip():
            findings.append(Finding(
                "warn", "roadmap.md next_prompt is empty — the dashboard's resume prompt is blank; author it"
            ))
        if not (fm.get("execution_recommendation") or "").strip():
            findings.append(Finding(
                "warn",
                "roadmap.md execution_recommendation is empty — analyze whether the NEXT needs execution.md/subagents",
            ))

    pj = _read(hdir, "project.md")
    if pj is not None and not (frontmatter.parse(pj).front_matter.get("current_focus") or "").strip():
        findings.append(Finding(
            "warn", "project.md current_focus is empty — the dashboard shows it; set it at closure"
        ))

    # 3) NEXT pointing at already-shipped work. Fuzzy, so require a *strong* match
    # (≥3 shared distinctive tokens) — next_action often *mentions* shipped capabilities
    # as context ("…makes the Control tab multi-agent"); only a heavy overlap is a real flag.
    fb = _read(hdir, "features.md")
    if next_action and fb is not None:
        stop = _name_stopwords(root)
        na_tokens = _key_tokens(next_action, stop)
        for cap in feature_items(fb)["shipped"]:
            if _similar(na_tokens, _key_tokens(cap, stop), 0.6, min_shared=3):
                findings.append(Finding(
                    "warn",
                    f"next_action may point at already-shipped work ('{_short(cap)}') — confirm it's still the next step",
                ))
                break

    if not any(f.level in ("warn", "fail") for f in findings):
        findings.append(Finding("ok", "dashboard lanes are fresh (NEXT + focus authored, lanes updated this session)"))
    return findings


# --------------------------------------------------------------------------- #
# distill-history
# --------------------------------------------------------------------------- #

def find_source_log(root: Path, explicit: str | None = None) -> Path | None:
    """The large log to compress: explicit arg, else the first known candidate."""
    if explicit:
        p = (root / explicit) if not Path(explicit).is_absolute() else Path(explicit)
        return p if p.is_file() else None
    for rel in _SOURCE_LOGS:
        p = root / rel
        if p.is_file():
            return p
    return None


def _log_stats(text: str) -> tuple[int, int]:
    """(non-blank lines, heading count) — a cheap size signal."""
    lines = text.splitlines()
    nonblank = sum(1 for ln in lines if ln.strip())
    headings = sum(1 for ln in lines if ln.lstrip().startswith("#"))
    return nonblank, headings


def discover_canonical_docs(root: Path) -> list[Path]:
    """Project docs `infer` can distill `.horus/` from: root status/roadmap/readme
    files, the instruction files, and anything under docs/. De-duplicated, sorted."""
    found: dict[str, Path] = {}
    for pattern in _CANONICAL_DOC_GLOBS:
        for p in root.glob(pattern):
            if p.is_file() and p.suffix.lower() in _DOC_SUFFIXES:
                found[p.name] = p
    for name in _CANONICAL_DOC_NAMES:
        p = root / name
        if p.is_file():
            found[name] = p
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        for p in sorted(docs_dir.glob("*.md")):
            found[f"docs/{p.name}"] = p
    return [found[k] for k in sorted(found)]


def _placeholder_lanes(hdir: Path) -> list[str]:
    """Lanes that are missing or still carry `horus init` placeholder content."""
    out: list[str] = []

    proj = _read(hdir, "project.md")
    if proj is None:
        out.append("project.md (missing)")
    else:
        doc = frontmatter.parse(proj)
        focus = doc.front_matter.get("current_focus", "").strip().lower()
        if focus.startswith("describe ") or "one-paragraph description" in doc.body.lower():
            out.append("project.md")

    rm = _read(hdir, "roadmap.md")
    if rm is None:
        out.append("roadmap.md (missing)")
    elif "first task." in rm.lower() or "describe the current focus" in rm.lower():
        out.append("roadmap.md")

    fb = _read(hdir, "features.md")
    if fb is None:
        out.append("features.md (missing)")
    elif sum(feature_counts(fb).values()) == 0:
        out.append("features.md")

    # Placeholder = body unchanged from the shipped template (reachable: any real
    # content clears it — no need to add a particular heading).
    hb = _read(hdir, "history.md")
    if hb is None:
        out.append("history.md (missing)")
    else:
        body = frontmatter.parse(hb).body.strip()
        if not body or body == frontmatter.parse(templates.history_md("")).body.strip():
            out.append("history.md")

    return out


def infer_signals(root: Path) -> list[Finding]:
    """What an `infer` pass has to work with: canonical docs to distill from, and
    which `.horus/` lanes still need populating. Read-only."""
    findings: list[Finding] = []
    hdir = horus_dir(root)
    if not hdir.is_dir():
        findings.append(Finding("warn", "no .horus/ yet — run `horus init`, then infer populates it"))

    docs = discover_canonical_docs(root)
    if docs:
        names = ", ".join(d.name if d.parent == root else f"docs/{d.name}" for d in docs)
        findings.append(Finding("ok", f"{len(docs)} canonical doc(s) to distill from: {names}"))
    else:
        findings.append(Finding(
            "warn", "no canonical docs found (README/ROADMAP/STATUS/…); infer has little to distill from"
        ))

    if hdir.is_dir():
        placeholders = _placeholder_lanes(hdir)
        if placeholders:
            findings.append(Finding("warn", f"placeholder/empty lanes to populate: {', '.join(placeholders)}"))
        else:
            findings.append(Finding("ok", "all lanes already populated (infer would refine, not bootstrap)"))
        # decisions.md is judgement-only — surface it, but don't pressure invention.
        db = _read(hdir, "decisions.md")
        if db is not None and db.strip() == templates.decisions_md().strip():
            findings.append(Finding(
                "ok", "decisions.md is empty — add entries only if the docs record real dated decisions (don't invent)"
            ))
    return findings


def distill_signals(root: Path, source: Path | None) -> list[Finding]:
    """Report the compression target: source-log size vs current history.md size."""
    findings: list[Finding] = []
    hdir = horus_dir(root)
    if not hdir.is_dir():
        return [Finding("fail", f"no {HORUS_DIR}/ directory (run `horus init`)")]

    if source is None:
        findings.append(Finding(
            "warn",
            "no source log found (looked for docs/HISTORY.md, CHANGELOG.md, …) — "
            "pass one explicitly, or distill the archive inside history.md",
        ))
    else:
        lines, heads = _log_stats(source.read_text(encoding="utf-8"))
        rel = source.relative_to(root) if source.is_relative_to(root) else source
        findings.append(Finding(
            "ok" if lines else "warn",
            f"source log {rel}: {lines} non-blank line(s), {heads} heading(s) to compress",
        ))

    history_body = _read(hdir, "history.md")
    if history_body is None:
        findings.append(Finding("warn", f"{HORUS_DIR}/history.md missing — run `horus init` to scaffold it"))
    else:
        lines, heads = _log_stats(frontmatter.parse(history_body).body)
        findings.append(Finding("ok", f"current history.md: {lines} line(s), {heads} curated entry/entries"))
    return findings
