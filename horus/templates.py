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

Before substantial work:

- Read `.horus/project.md`.
- Read `.horus/roadmap.md`.
- Read `.horus/decisions.md`.
- Review recent local session summaries in `.horus/sessions/` when available.

After work that contributes to the project state:

- Add a concise session summary under `.horus/sessions/`.
- Update `.horus/roadmap.md` when roadmap status or current focus changes.
- Update `.horus/decisions.md` only for durable decisions and their reasoning.
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
last_updated: {date}
---

# Roadmap

## Now

- [ ] First task.

## Later

- [ ] Deferred task.
"""


def readme_md() -> str:
    return """# `.horus/` — project continuity

Horus keeps a concise, vendor-neutral record of project state here so any agent
(Claude, Codex, ...) can pick up continuity across machines — even without Horus
installed. Read this first.

- `project.md` — what this project is, current focus, shape, boundaries.
- `roadmap.md` — current focus + a checklist of planned / in-progress / done items.
- `decisions.md` — durable decisions and their reasoning, dated.
- `sessions/` — local session summaries (gitignored; per-machine context that
  distills into the files above).

**This is the single concise source of "what is this, and what's next."** If the
project already has rich docs (README, a status/roadmap file, and anything they
point to), distill the essentials here and treat those as the source — do not
maintain two hand-written roadmaps that will drift. Mark a superseded doc as such
once its content lives here.

Durable state (`project.md` / `roadmap.md` / `decisions.md`) is committed and
travels via git; session summaries stay local per machine.

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
2. Roadmap: update .horus/roadmap.md if status or current focus changed.
3. Decisions: record durable decisions in .horus/decisions.md, with reasoning.
4. Instructions: keep the AGENTS.md / CLAUDE.md shared blocks aligned
   (check with `horus doctor instructions`; fix with `horus reconcile instructions`).
5. Do not continue editing source code as part of closure.
"""
