"""Templates for files created by `horus init`.

The managed instruction block is the single source of the shared-instructions
content. The only intended difference between the `AGENTS.md` and `CLAUDE.md`
copies is the cross-reference line naming the *other* file; see
``instructions.normalize_block`` which accounts for that when checking drift.
"""

from __future__ import annotations

BLOCK_BEGIN = "<!-- HORUS:BEGIN shared-instructions -->"
BLOCK_END = "<!-- HORUS:END shared-instructions -->"

_SHARED_BODY = """## Horus Project Continuity

This repository uses `.horus/` for project continuity.

**You — the agent in this session — maintain the `.horus/` lanes, filling them from the
context you hold in this conversation.** The `horus` CLI only scaffolds templates and
emits deterministic signals/checks; it never parses files to write lane content for you,
because it cannot see this session. Update the lanes by invoking the **`horus-consolidate`**
skill (it can see this conversation) and writing in what actually happened — decisions and
why, what shipped, dead ends, the next step.

Before substantial work, read the `.horus/` lanes (each stays in its lane):

- `project.md` — vision, shape, boundaries, current focus.
- `roadmap.md` — open action points (the *what's next*).
- `features.md` — capability ledger (shipped / in-progress / planned packages).
- `decisions.md` — durable rules and their reasoning.
- `history.md` — carried-forward lessons ("bumps in the road").
- Review recent local session summaries in `.horus/sessions/` when available.

After work that contributes to the project state, close the session by invoking the
`horus-consolidate` skill and folding in this session's context:

- Add a concise session summary under `.horus/sessions/` (scaffold with
  `horus session new "<title>"`, then write what actually happened — not just a date).
- Keep facts in their lane: open action points in `roadmap.md`, shipped/planned
  capabilities in `features.md`, durable rules in `decisions.md`, lessons in
  `history.md`. Don't maintain the same fact in two files.
- `horus consolidate` / `horus close` are signal + verification only — you supply the
  content from the session; they never rewrite the lanes for you.
- Do not store secrets or full transcripts in `.horus/`.

Instruction synchronization:

- Keep this shared Horus-managed block aligned with the matching block in `{other}`.
- Agent-specific instructions may live outside the Horus-managed block."""


def shared_block(other_file: str) -> str:
    """Return the full managed block (markers included) cross-referencing ``other_file``."""
    return f"{BLOCK_BEGIN}\n{_SHARED_BODY.format(other=other_file)}\n{BLOCK_END}"


def instruction_file(title: str, other_file: str, agent_notes_heading: str) -> str:
    """A fresh AGENTS.md / CLAUDE.md containing the managed block plus an agent-notes stub."""
    return (
        f"# {title}\n\n"
        f"{shared_block(other_file)}\n\n"
        f"## {agent_notes_heading}\n\n"
        "- Keep the project lightweight and shaped around current user needs.\n"
    )


def project_md(project_name: str, date: str) -> str:
    return f"""---
project: {project_name}
status: planning
current_focus: "Describe the immediate focus here."
last_updated: {date}
---

# {project_name}

One-paragraph description of what this project is. If the repo already has a
README or status doc, distill the essentials here (see `.horus/README.md`).

## Current Shape

What the project looks like right now.

## Boundaries

What is intentionally out of scope.
"""


def roadmap_md(date: str) -> str:
    return f"""---
status: active
current_focus: "Describe the current focus here."
next_prompt: ""
last_updated: {date}
---

# Roadmap

## Now

- [ ] First task.

## Later

- [ ] Deferred task.
"""


def features_md(date: str) -> str:
    return f"""---
status: active
last_updated: {date}
---

# Features — capability ledger

Complete **capabilities** (shippable packages), status-tracked. A feature is a
shippable unit of behaviour, not a task — bug fixes, corrections, and chores live
in `roadmap.md` and never appear here. The action points to build a planned or
in-progress feature live in `roadmap.md`; the *why* behind a shipped one is in
`decisions.md` / `history.md`.

Status: **Shipped** · **In progress** · **Planned**

## Shipped

| Capability | Since | Notes |
|---|---|---|

## In progress

| Capability | Notes |
|---|---|

## Planned

| Capability | Notes |
|---|---|
"""


def history_md(date: str) -> str:
    return f"""---
status: active
last_updated: {date}
---

# History — bumps in the road

Curated, durable context: the problems that bit us and the lessons that shaped the
design. **Not** a timeline and **not** open issues (those live in `roadmap.md`) —
just the war stories worth carrying forward. Compress a large existing changelog
into this curated subset with `horus distill-history`.
"""


def readme_md() -> str:
    return """# `.horus/` — project continuity

Horus keeps a concise, vendor-neutral record of project state here so any agent
(Claude, Codex, ...) can pick up continuity across machines — even without Horus
installed. Read this first.

- `project.md` — what this project is, current focus, shape, boundaries (overview + vision).
- `roadmap.md` — open **action points** (any type: feature work, bug fix, chore),
  pruned when done. The *what's next*, not a completed log.
- `features.md` — the **capability ledger**: complete packages tracked
  shipped / in-progress / planned. A capability, not a task — distinct from roadmap.
- `decisions.md` — durable decisions / rules to follow and their reasoning, dated.
- `history.md` — curated bumps in the road: problems that bit us and the lessons
  that shaped the design. Relevant context, **not** a timeline and **not** open issues.
- `sessions/` — local session summaries (gitignored; per-machine context that
  distills into the files above).

**This is the single concise source of "what is this, and what's next."** If the
project already has rich docs (README, a status/roadmap file, and anything they
point to), distill the essentials here and treat those as the source — do not
maintain two hand-written roadmaps that will drift. Mark a superseded doc as such
once its content lives here.

Keep each lane in its lane; run `horus consolidate` to route facts to the right
file, prune what's done, and distill session summaries upward.

Durable state (`project.md` / `roadmap.md` / `features.md` / `decisions.md` /
`history.md`) is committed and travels via git; session summaries stay local per
machine.

These files are scaffolded by `horus init` and maintained by the agents working in
this repo. A future `horus infer` will populate them automatically (LLM-based).
"""


def decisions_md() -> str:
    return """# Decisions

Durable decisions and their reasoning. Dated entries. No ephemeral chatter.
"""


def session_summary(
    *,
    title: str,
    date: str,
    project: str,
    agent: str,
    account: str,
    environment: str,
) -> str:
    return f"""---
date: {date}
agent: {agent}
account: {account}
environment: {environment}
project: {project}
status: in-progress
summary: "{title}"
---

# {title}

## Summary

What this session set out to do and what happened.

## Key Points

- ...

## Next

- ...
"""


CLOSURE_PROMPT = """Closure ritual - update project continuity before ending this session:

1. Session summary: ensure a summary for this session exists under .horus/sessions/
   (create one with `horus session new "<title>"` if this session moved the project forward).
2. Roadmap: update .horus/roadmap.md if status or current focus changed, and refresh
   its `next_prompt` frontmatter — a natural-language prompt to paste into a fresh
   Claude/Codex session to resume the single best next step (the dashboard shows it
   with a copy button). Write it for a cold reader: name the next step + point at .horus/.
3. Decisions: record durable decisions in .horus/decisions.md, with reasoning.
4. Instructions: keep the AGENTS.md / CLAUDE.md shared blocks aligned
   (check with `horus doctor instructions`; fix with `horus reconcile instructions`).
5. Do not continue editing source code as part of closure.
"""


USAGE_CLOSURE_INSTRUCTION = (
    "You are close to your 5-hour usage limit and risk being cut off mid-task. Stop the "
    "current work now and close the session cleanly so nothing in your head is lost. "
    "Use the horus-consolidate skill — it can see THIS conversation, which a file-only "
    "script cannot — and fold the session's *context* into .horus, not just what files "
    "changed: the decisions made and why, what shipped, dead ends worth remembering, "
    "and the next step. Concretely: (1) run the horus-consolidate skill to update the "
    ".horus lanes from this session's context (the skill uses `horus consolidate` for "
    "signals, but you supply the context a script can't); (2) write a concise handover "
    "summary under `.horus/sessions/` with what shipped and the next step; (3) commit "
    "with `horus close --commit`. Then stop — do not resume the main task."
)


CONSOLIDATE_PROMPT = """Consolidation routine - reshape .horus/ so each lane stays in its lane.
Act on the signals above. Edit .horus/** ONLY (not source, not AGENTS.md/CLAUDE.md).
Never invent status, dates, or versions; when intent is unclear, leave it and flag it.

1. Ship -> ledger: for each done roadmap action point that completed a shippable
   capability, close it in roadmap.md and add/update the matching row in features.md
   (Planned/In-progress -> Shipped; stamp the version if the repo records one, else blank).
2. De-duplicate across lanes: where the same item sits in both roadmap.md and
   features.md, keep the *action points* in roadmap.md and the *capability status* in
   features.md, each pointing at the other. No fact maintained in two places.
3. Prune: drop done/obsolete roadmap items (they live in features/history/git now).
4. Distill sessions: fold durable content from sessions/*.md into the lanes, then
   remove or mark the distilled summary.
5. Keep lanes pure: no tasks in features.md; no shipped packages lingering in
   roadmap.md; no open issues in history.md; no changelog in project.md.

Re-run `horus consolidate` afterward; the candidates above should be resolved.
"""


DISTILL_HISTORY_PROMPT = """Distill-history routine - compress a large log into the curated history.md subset.
Act on the signals above. Edit .horus/history.md (and freeze the source log); never
invent incidents - only compress what the log already records.

Signal test for each entry:
- KEEP: a real problem the project hit + the durable lesson/design change it forced.
- DROP: routine changelog/version-bump noise, resolved-and-irrelevant incidents,
  anything already captured as a rule in decisions.md (cross-reference instead).
- history.md is carried-forward context: NOT a timeline, NOT open issues (those are roadmap.md).

1. Read the source log identified above.
2. Write the high-signal "bumps in the road" into history.md (curated, deduplicated).
3. Mark the source log as superseded/frozen at the top - do not delete it.
"""


INFER_PROMPT = """Infer routine - bootstrap/refresh .horus/ by distilling the project's own docs.
Act on the signals above. The goal is a single concise source of "what is this and
what's next", distilled FROM the canonical docs - not a second copy of them.

1. If .horus/ doesn't exist yet, run `horus init` to scaffold the lanes first.
2. Read the canonical docs found above and follow their pointers (README -> status/
   roadmap -> CLAUDE.md -> linked docs like docs/*.md). Build a model of the project.
3. Distill into the lanes, each in its lane:
   - project.md - what it is, current shape, boundaries, current focus.
   - roadmap.md - open action points (what's next), grouped.
   - features.md - shipped / in-progress / planned capabilities.
   - decisions.md - durable decisions + reasoning, dated.
   - history.md - curated lessons / bumps in the road.
4. Don't duplicate: where a canonical doc stays the deep reference, point at it from
   .horus/ instead of copying it wholesale. Distill the essentials.
5. Mark superseded docs: if a doc's "current state / next steps" role now lives in
   .horus/, add a one-line pointer at its top (e.g. "Current state: see .horus/").
   Ask before substantially rewriting any source doc.
6. When intent is genuinely unclear (status, priorities), ask the user rather than
   guess. Never invent decisions, dates, or versions.

Edit scope: .horus/** (plus, with care and consent, a one-line pointer atop a
superseded source doc).
"""
