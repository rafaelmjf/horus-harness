---
status: open
priority: high
tier: sonnet
created: 2026-07-14
type: feature
parallel: safe
surface: horus/terminal_tui.py
---

> Narrowed 2026-07-14 (owner triage): items 1–2 are the valuable next slice and belong
> in the pre-release batch only after the correctness bugs. Items 3–4 are deferred
> polish; do not let timers/age display expand the first implementation.

# TUI cockpit state gaps: PRD focus on project screen and claimed badge

Four gaps found reviewing the TUI as a cockpit (2026-07-14 owner brainstorm),
roughly in value order:

1. **PRD frontmatter on the project screen** — show `current_focus` and
   `next_action` above Resume/Fresh/Backlog. Today you choose "Resume" blind;
   these are the two highest-value lines in continuity and the dashboard
   already reads them PRD-first.
2. **Claimed badge on backlog cards** — `_open_cards` includes
   `status: claimed` cards but renders them identically to open ones, hiding
   exactly the in-progress state the claim guard exists to surface.
Deferred follow-ups (re-prioritize only after observed pain):

3. **Idle refresh** — data loads only when a frame is (re)created, so the
   sessions/usage view goes stale while watched. A refresh key is the cheap
   rung; a background invalidate timer the nicer one.
4. **Session age on the sessions screen** — `updated_at` is in the registry
   record but unrendered; "running 3h, idle 40m" changes attach-vs-kill.

Keep the invariant: every TUI action stays a thin wrapper over a CLI-callable
primitive — the TUI is the human surface, agents use the CLI/JSON.
