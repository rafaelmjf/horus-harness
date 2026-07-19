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

from horus import backlog, frontmatter, machine_requirements, roadmap, templates
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


def resume_context(root: Path) -> dict[str, str]:
    """Small, read-only handoff for a fresh session.

    This is intentionally narrower than "read every .horus lane": enough current
    state to resume safely, with lazy-load instructions layered on top by
    :func:`resume_prompt`.
    """
    hdir = horus_dir(root)
    if not hdir.is_dir():
        raise FileNotFoundError(f"no {HORUS_DIR}/ directory at {root}")

    context = {
        "project": root.name,
        "current_focus": "",
        "next_action": "",
        "next_prompt": "",
        "execution_recommendation": "",
        "execution_status": "",
        "latest_session": "",
    }

    focus = frontmatter.resolve_focus(root)
    context["current_focus"] = focus["current_focus"]
    context["next_action"] = focus["next_action"]
    context["next_prompt"] = focus["next_prompt"]
    context["execution_recommendation"] = focus["execution_recommendation"]

    execution_md = _read(hdir, "execution.md")
    if execution_md is not None:
        doc = frontmatter.parse(execution_md)
        context["execution_status"] = str(doc.front_matter.get("status", "")).strip()

    sessions = recent_sessions(root, limit=1)
    if sessions:
        doc = frontmatter.parse(sessions[0].read_text(encoding="utf-8"))
        date_text = str(doc.front_matter.get("date", "")).strip()
        summary = str(doc.front_matter.get("summary", "")).strip()
        bits = [sessions[0].name]
        if date_text:
            bits.append(date_text)
        if summary:
            bits.append(summary)
        context["latest_session"] = " - ".join(bits)

    return context


def resume_prompt(root: Path, *, stop_before_execution: bool = True) -> str:
    """Prompt for resuming a project without front-loading every Horus lane.

    Degrades to "" (nothing to resume) when the project has no ``.horus/``
    directory yet, rather than propagating resume_context's FileNotFoundError —
    callers rendering many projects at once (the dashboard) must not have one
    uninitialized/deleted project take down the whole batch."""
    if not horus_dir(root).is_dir():
        return ""
    info = resume_context(root)
    readiness_warning = machine_requirements.warning_text(machine_requirements.inspect(root))
    project = info["project"]
    current_focus = info["current_focus"] or "(not set)"
    next_action = info["next_action"] or "(not set)"
    execution_recommendation = info["execution_recommendation"] or "(not set)"
    execution_status = info["execution_status"] or "(not set)"
    latest_session = info["latest_session"] or "(none)"
    next_prompt = info["next_prompt"]
    continuation = next_prompt or f"Review the next action above for the {project} project."

    if frontmatter.has_prd(root):
        lazy_load = f"""Do not front-load the whole `.horus/` directory. Lazy-load only what this task needs:
- Read `.horus/{frontmatter.PRD_FILE}` before substantial work — vision, backlog, shipped, rules (it is the one maintained continuity file).
- Read `.horus/execution.md` only if the work uses phased worker handoffs or `execution_recommendation` says `plan-execution`.
- Read the latest `.horus/sessions/` summary only if local-only details from the previous session are needed."""
    else:
        lazy_load = """Do not read every `.horus/` lane up front. Lazy-load only what this task needs:
- Read `.horus/execution.md` only if the work uses phased worker handoffs or `execution_recommendation` says `plan-execution`.
- Read `.horus/project.md` only for broader product scope or constraints.
- Read `.horus/features.md`, `.horus/decisions.md`, and `.horus/history.md` only when shipped capability status, durable rules, or prior lessons matter.
- Read the latest `.horus/sessions/` summary only if local-only details from the previous session are needed."""

    if stop_before_execution:
        resume_contract = """Resume contract — orient, then stop:
- The fetch/branch checks and minimum-context reads above are authorized only to
  situate the session. They do not authorize implementation or the rest of the
  authored handoff.
- Treat `next_action`, `execution_recommendation`, and the authored handoff below
  as proposals to explain to the user, not commands to execute.
- Before editing files, running tests, launching workers, scheduling work, merging,
  releasing, deploying, or taking any other state-changing action, summarize the
  actions you inferred and ask the user for permission to proceed.
- A release may be suggested with concrete reasons, but never ordered or chained as
  "and then release". Wait for separate explicit confirmation before releasing."""
        handoff_heading = "Proposed authored handoff (context only — do not execute yet):"
        closing = "Summarize the actions you understood from this handoff and ask permission to proceed."
    else:
        resume_contract = """Direct resume contract — orient, then proceed:
- The explicit All Gas No Breaks launch authorizes direct work on the owner's current
  request and the authored handoff after the fetch/branch checks and minimum reads.
  Do not pause for a preflight summary or permission ceremony.
- Stay within that scope. Do not infer authority to delegate, perform destructive
  operations, merge, release, or deploy when the owner has not granted it.
- A release remains a separately confirmed hard boundary: preserve continuity before
  releasing, and preserve it again when the session closes or hands off."""
        handoff_heading = "Authored handoff:"
        closing = "Proceed directly with the in-scope work."

    prompt = f"""Resume the {project} project.

Before trusting local state:
1. Run `git fetch --all --prune`.
2. Verify the current branch against `origin/<branch>` before acting on local refs or old Horus prose.

Minimum Horus state already loaded:
- `current_focus`: {current_focus}
- `next_action`: {next_action}
- `execution_recommendation`: {execution_recommendation}
- `execution_status`: {execution_status}
- `latest_session`: {latest_session}

{lazy_load}

{resume_contract}

{handoff_heading}
{continuation}

{closing}
"""
    return f"{readiness_warning}\n\n{prompt}" if readiness_warning else prompt


def campaign_prompt(*, outcome: str, cockpit: str, targets: list[str]) -> str:
    """Compose a bounded campaign brief for the optional TUI Campaign entry point.

    Unlike ``resume_prompt``, the outcome and target set are owner-authored at
    launch time — this never invents a project archetype or a target list."""
    target_lines = (
        "\n".join(f"- {name}" for name in targets)
        if targets
        else "- (none named — this campaign is scoped to the cockpit project only)"
    )
    return f"""Supervise this campaign from {cockpit}. Desired outcome:
{outcome}

Named target projects:
{target_lines}

Apply need-first judgment separately for each bounded unit of work: default to working
inline, and only dispatch a worker when a concrete context, parallelism, or price
dividend exceeds the brief/review/gate/merge/closure tax. Cross-project scope or
multiple named targets alone are never a dispatch dividend. Never auto-select a model
or account, auto-spawn a worker, or fall back to a different envelope without renewed
approval. Every named target project retains its own branch/PR/gate/continuity
authority — land changes there through its normal review path. Direct per-project
launch stays the default way to work; use this campaign framing only to keep the
cross-project outcome coherent.
"""


# --------------------------------------------------------------------------- #
# consolidate
# --------------------------------------------------------------------------- #

def _name_stopwords(root: Path) -> frozenset[str]:
    """Project-name tokens are low-signal *within* that project — exclude from matching."""
    return frozenset(w for w in _WORD_RE.findall(root.name.lower()) if len(w) > 2)


# Cap how many individual overlap lines we print before summarizing the rest.
_MAX_OVERLAP_LINES = 8

# --------------------------------------------------------------------------- #
# consolidate — structure v3 (PRD.md + sessions/): backlog hygiene only, no
# lane-purity/overlap warnings (there are no lanes to route between).
# --------------------------------------------------------------------------- #

_PRD_SOFT_CAP = 235
_PRD_HARD_CAP = 250
_MAX_UNDISTILLED_SESSIONS = 12

# A top-level markdown list item: "- text", "* text", or "1. text".
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(.*)$")
_CHECKBOX_RE = re.compile(r"^\[([ xX])\]\s*(.*)$")
_BOLD_TITLE_RE = re.compile(r"^\*\*(.+?)\*\*")

_PRD_SKELETON_SECTIONS = ("Vision", "Backlog", "Shipped", "Rules")
_PRD_PLACEHOLDER_MARKERS = ("describe ", "todo", "tbd", "fill in", "placeholder", "one-paragraph")


def _section(body: str, heading: str) -> str:
    """Body of a top-level (`## `) markdown section, until the next `## ` heading."""
    lines = body.splitlines()
    start = None
    target = f"## {heading}".lower()
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end])


def _backlog_item_texts(section_body: str) -> list[str]:
    """Marker-stripped text of each top-level list item in a section (sub-bullets
    included; wrapped continuation lines without a marker are not list items)."""
    items = []
    for line in section_body.splitlines():
        m = _LIST_ITEM_RE.match(line)
        if m:
            items.append(m.group(1))
    return items


def _item_title(text: str) -> str | None:
    """The bold **title** at the start of a backlog item's text, if any."""
    m = _BOLD_TITLE_RE.match(text.strip())
    return m.group(1).rstrip(" .:").strip() if m else None


def _prd_skeleton_gaps(prd_body: str) -> list[str]:
    """PRD skeleton sections (Vision/Backlog/Shipped/Rules) that are missing, empty,
    or still carry generic placeholder wording."""
    gaps: list[str] = []
    for heading in _PRD_SKELETON_SECTIONS:
        section = _section(prd_body, heading).strip()
        if not section:
            gaps.append(f"{heading} (missing/empty)")
            continue
        low = section.lower()
        if any(marker in low[:120] for marker in _PRD_PLACEHOLDER_MARKERS):
            gaps.append(heading)
    return gaps


def _vision_facets(prd_body: str) -> list[str]:
    """Facet names from the markdown table under `## Vision` — the bold text of each
    row's first column. Header/separator rows carry no bold and are skipped."""
    facets: list[str] = []
    for line in _section(prd_body, "Vision").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        first = line.strip("|").split("|", 1)[0].strip()
        m = _BOLD_TITLE_RE.match(first)
        if m:
            facets.append(m.group(1).strip())
    return facets


def _norm_facet(name: str) -> str:
    """Whitespace/case-insensitive key so a card's `vision_facet` matches a Vision
    facet without demanding byte-exact casing/spacing."""
    return " ".join(name.lower().split())


def convergence_findings(root: Path, prd_body: str) -> list[Finding]:
    """Phase-aware convergence read-out: map active backlog cards onto `## Vision`
    facets via their `vision_facet` frontmatter and report coverage. Advisory and
    read-only. `converge`-phase cards (the default) must name a known facet; `explore`
    cards are exempt and reported in a separate bucket. No facet table ⇒ no read-out."""
    facets = _vision_facets(prd_body)
    if not facets:
        return []
    facet_by_key = {_norm_facet(f): f for f in facets}
    counts: dict[str, int] = {f: 0 for f in facets}
    explore: list[str] = []
    flags: list[Finding] = []

    for card in backlog.load_active_cards(root):
        if card.phase == backlog.EXPLORE_PHASE:
            explore.append(card.name)
            continue
        if not card.vision_facet:
            flags.append(Finding(
                "warn",
                f"convergence: card '{card.name}' is converge-phase with no vision_facet — "
                f"link it to a Vision facet or set `phase: explore`",
            ))
            continue
        matched = facet_by_key.get(_norm_facet(card.vision_facet))
        if matched is None:
            flags.append(Finding(
                "warn",
                f"convergence: card '{card.name}' targets unknown facet "
                f"'{card.vision_facet}' — fix the name or add the facet to the Vision",
            ))
            continue
        counts[matched] += 1

    findings: list[Finding] = []
    with_work = [f"{f} ({n})" for f, n in counts.items() if n]
    no_work = [f for f, n in counts.items() if not n]
    if with_work:
        findings.append(Finding("ok", "convergence: facets with open work — " + ", ".join(with_work)))
    if no_work:
        findings.append(Finding(
            "ok",
            "convergence: no open cards (converged or untouched — judge vs the facet's "
            "definition of done) — " + ", ".join(no_work),
        ))
    if explore:
        findings.append(Finding(
            "ok",
            f"convergence: {len(explore)} exploratory card(s), Ready-gate exempt — "
            + ", ".join(sorted(explore)),
        ))
    findings.extend(flags)
    return findings


def _consolidate_signals_v3(root: Path, hdir: Path) -> list[Finding]:
    """Backlog-hygiene checks for structure v3 (PRD.md + sessions/). Read-only."""
    findings: list[Finding] = []
    prd_text = _read(hdir, frontmatter.PRD_FILE) or ""
    doc = frontmatter.parse(prd_text)

    # 1. PRD size vs the ~250-line cap.
    line_count = len(prd_text.splitlines())
    if line_count > _PRD_HARD_CAP:
        findings.append(Finding(
            "warn",
            f"{HORUS_DIR}/{frontmatter.PRD_FILE} is {line_count} lines — over the ~250-line cap: "
            f"distill one-line shipped entries, delete done backlog items (git remembers)",
        ))
    elif line_count > _PRD_SOFT_CAP:
        findings.append(Finding(
            "warn",
            f"{HORUS_DIR}/{frontmatter.PRD_FILE} is {line_count} lines — approaching the ~250-line "
            f"cap — distill: one-line shipped entries, delete done backlog items (git remembers)",
        ))

    # 2. Stale frontmatter: PRD last_updated older than the newest session note.
    sessions = recent_sessions(root, limit=999)
    newest_session_date = None
    for s in sessions:
        d = _as_date(frontmatter.parse(s.read_text(encoding="utf-8")).front_matter.get("date"))
        if d and (newest_session_date is None or d > newest_session_date):
            newest_session_date = d
    if newest_session_date:
        prd_updated = _as_date(doc.front_matter.get("last_updated"))
        if prd_updated is None or prd_updated < newest_session_date:
            stamp = prd_updated.isoformat() if prd_updated else "unset"
            findings.append(Finding(
                "warn",
                f"{HORUS_DIR}/{frontmatter.PRD_FILE} last_updated ({stamp}) is older than the "
                f"newest session note ({newest_session_date.isoformat()}) — refresh it and bump last_updated",
            ))

    # 3. Undistilled session notes.
    if len(sessions) > _MAX_UNDISTILLED_SESSIONS:
        findings.append(Finding(
            "warn",
            f"{len(sessions)} session notes in {HORUS_DIR}/sessions/ — distill older ones to "
            f"{HORUS_DIR}/sessions/archive/",
        ))

    # 4 & 5. Backlog hygiene: duplicate titles + lingering done items.
    backlog_items = _backlog_item_texts(_section(doc.body, "Backlog"))
    seen_titles: dict[str, str] = {}
    warned_dupes: set[str] = set()
    for raw in backlog_items:
        cb = _CHECKBOX_RE.match(raw)
        checked = bool(cb and cb.group(1).lower() == "x")
        text = cb.group(2) if cb else raw
        title = _item_title(text)

        if title:
            key = title.lower()
            if key in seen_titles:
                if key not in warned_dupes:
                    findings.append(Finding(
                        "warn", f"duplicate backlog title '{seen_titles[key]}' — merge or rename"
                    ))
                    warned_dupes.add(key)
            else:
                seen_titles[key] = title

        if checked or text.startswith("DONE") or text.startswith("Done:"):
            findings.append(Finding(
                "warn",
                f"backlog item '{title or _short(text)}' is done — delete it (git remembers)",
            ))

    findings.extend(backlog.hygiene_findings(root))

    # 6. Phase-aware convergence read-out (advisory): where the backlog sits against
    # the Vision facets. Its "ok" lines are a report and always print; only off-vision
    # or unknown-facet cards raise a warn.
    findings.extend(convergence_findings(root, doc.body))

    if not any(f.level in ("warn", "fail") for f in findings):
        findings.append(Finding(
            "ok", "PRD backlog hygiene looks clean — size, freshness, duplicates, done items"
        ))
    return findings


def consolidate_signals(root: Path, *, overlap_threshold: float = 0.5) -> list[Finding]:
    """Detect what a consolidation pass should route/prune/distill. Read-only."""
    hdir = horus_dir(root)
    if not hdir.is_dir():
        return [Finding("fail", f"no {HORUS_DIR}/ directory (run `horus init`)")]

    if frontmatter.has_prd(root):
        return _consolidate_signals_v3(root, hdir)

    findings: list[Finding] = []
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
            "warn", f"{len(sessions)} local recovery note(s) to distill into the lanes"
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

    # v3 (PRD.md + sessions/): the PRD frontmatter is the one fresh surface; the
    # shared resolver still honors transitional shims per-field.
    v3 = frontmatter.has_prd(root)
    fresh_lanes = (frontmatter.PRD_FILE,) if v3 else _FRESH_LANES

    sessions = recent_sessions(root, limit=1)
    session_date = None
    if sessions:
        session_date = _as_date(frontmatter.parse(sessions[0].read_text(encoding="utf-8")).front_matter.get("date"))

    # 1) Lanes that should track every session, but weren't updated since the last one.
    if session_date:
        for lane in fresh_lanes:
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
    focus = frontmatter.resolve_focus(root)
    next_action = focus["next_action"]
    next_home = frontmatter.PRD_FILE if v3 else "roadmap.md"
    if v3 or _read(hdir, "roadmap.md") is not None:
        if not next_action:
            findings.append(Finding(
                "warn", f"{next_home} next_action is empty — the dashboard NEXT shows 'not set'; author it at closure"
            ))
        if not focus["next_prompt"]:
            findings.append(Finding(
                "warn", f"{next_home} next_prompt is empty — the dashboard's resume prompt is blank; author it"
            ))
        if not focus["execution_recommendation"]:
            findings.append(Finding(
                "warn",
                f"{next_home} execution_recommendation is empty — analyze whether the NEXT needs execution.md/subagents",
            ))

    focus_home = frontmatter.PRD_FILE if v3 else "project.md"
    if (v3 or _read(hdir, "project.md") is not None) and not focus["current_focus"]:
        findings.append(Finding(
            "warn", f"{focus_home} current_focus is empty — the dashboard shows it; set it at closure"
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
            generated = templates.instruction_file(
                "Agent Instructions" if name == "AGENTS.md" else "Claude Code Instructions",
                "CLAUDE.md" if name == "AGENTS.md" else "AGENTS.md",
                "Codex Notes" if name == "AGENTS.md" else "Claude Notes",
            )
            if p.read_text(encoding="utf-8") != generated:
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
    is_v3 = hdir.is_dir() and frontmatter.has_prd(root)
    if docs:
        names = ", ".join(d.name if d.parent == root else f"docs/{d.name}" for d in docs)
        findings.append(Finding("ok", f"{len(docs)} canonical doc(s) to distill from: {names}"))
    elif is_v3:
        findings.append(Finding(
            "ok", "no useful canonical docs found; the blank PRD scaffold may remain blank until a real use case"
        ))
    else:
        findings.append(Finding(
            "warn", "no canonical docs found (README/ROADMAP/STATUS/…); infer has little to distill from"
        ))

    if is_v3:
        prd_body = frontmatter.parse(_read(hdir, frontmatter.PRD_FILE) or "").body
        gaps = _prd_skeleton_gaps(prd_body)
        if gaps and docs:
            findings.append(Finding(
                "warn",
                f"PRD skeleton section(s) empty/placeholder: {', '.join(gaps)} — distill from the "
                f"canonical docs above",
            ))
        elif not gaps:
            findings.append(Finding(
                "ok", "PRD skeleton sections (Vision/Backlog/Shipped/Rules) are populated"
            ))
        else:
            findings.append(Finding(
                "ok", "PRD skeleton is intentionally blank; infer only after useful source truth exists"
            ))
    elif hdir.is_dir():
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

    if frontmatter.has_prd(root):
        # Structure v3: the curated history lives in archive/, not a top-level lane.
        history_body = _read(hdir, "archive/history.md")
        if history_body is None:
            findings.append(Finding(
                "ok",
                f"no {HORUS_DIR}/archive/history.md yet — the first distill pass creates it",
            ))
        else:
            lines, heads = _log_stats(frontmatter.parse(history_body).body)
            findings.append(Finding(
                "ok", f"current archive/history.md: {lines} line(s), {heads} curated entry/entries"
            ))
        return findings

    history_body = _read(hdir, "history.md")
    if history_body is None:
        findings.append(Finding("warn", f"{HORUS_DIR}/history.md missing — run `horus init` to scaffold it"))
    else:
        lines, heads = _log_stats(frontmatter.parse(history_body).body)
        findings.append(Finding("ok", f"current history.md: {lines} line(s), {heads} curated entry/entries"))
    return findings
