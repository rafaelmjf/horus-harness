---
status: shipped
priority: high
created: 2026-07-17
tier: sonnet
type: feature
parallel: safe
phase: converge
vision_facet: "Continuity core"
created_by: owner
surface: horus/terminal_tui.py (a launch "mode" pick beside account/model/effort), horus/skills.py (a bundled mode skill, e.g. inline-batch-session), the launch prompt/preamble or a SessionStart surface that loads the mode skill, horus/config.py (map mode -> effective continuity granularity)
shipped_pr: 307
shipped_sha: bba6cd5
---

# launch-mode-process-skill — a launch mode attaches a process skill so the working posture holds

**Why (owner, 2026-07-17):** the working posture (e.g. "inline batch: ship several cards in a
row, delay continuity ceremony to closure") currently depends on the model *remembering* a
rule among dozens, or on the owner re-stating it each launch. That is the weakest rung of the
controls ladder and it demonstrably slipped this session (the agent over-closed after one card
until steered). The owner runs Horus across **multiple accounts and models** — a per-account
memory or a per-session steer does NOT propagate, so nothing ensures the process holds. Promote
it: a **launch mode** that attaches a **bundled skill** encoding the posture. A skill is
cross-account + cross-model (projected to `.claude`/`.agents`, travels via git), loads explicitly
at launch (so it isn't buried), and keeps the posture OUT of the PRD.

## How (thin — reuse the launch picker + the bundled-skill mechanism)

1. The TUI launch flow (fresh/resume/card — building on the account/model/effort picker) gains a
   **mode** choice. Start minimal with the demonstrated need: `inline-batch` (and the implicit
   default `standard`). More modes only when a real need appears.
2. Each mode maps to a **bundled skill** (e.g. a new `inline-batch-session` skill) that states
   the posture crisply: ship self-contained cards in a row; per card keep only the delivery-safety
   rungs (branch → PR → reproduce the gate on the exact SHA → one live probe → `backlog ship`);
   DEFER the canonical PRD/continuity write to ONE consolidation at the session boundary; do not
   over-ceremony mid-session. (This is exactly the `handoff` granularity, made explicit + loaded.)
3. Launching in a mode **loads that skill into the session's opening context** — via a launch
   prompt preamble that invokes it (`Skill(<mode-skill>)`) and/or a SessionStart surface. It must
   work for Claude and Codex (both have the projected skill).
4. The mode also sets the session's **effective continuity granularity** so the skill and the
   deterministic gates agree (inline-batch ⇒ handoff), rather than adding a second conflicting
   control.

## Acceptance

- Launching a session in `inline-batch` mode (any account, Claude or Codex) loads the mode skill
  automatically, without the owner re-stating the posture — verifiable that the skill's directives
  are present in the session's opening context.
- The mode is recorded with the session and sets its effective continuity granularity to `handoff`;
  the default/standard mode preserves today's behavior exactly.
- The mode skill is bundled (projected to `.claude` + `.agents`, versioned) so it is identical
  across accounts and models; no PRD/continuity prose carries the posture.
- Tests cover: mode → skill selection, mode → granularity mapping, and back-compat for a launch
  with no mode chosen.

## Non-goals / boundaries

- Not a new continuity concept — `handoff`/`delivery`/`manual` granularity already exists; this
  makes the *inline-batch* posture reliably LOAD, cross-account/model, instead of relying on memory.
- Keep the mode set minimal (start with inline-batch); do not invent a mode taxonomy preemptively.
- If even a loaded skill proves insufficient to hold the posture, the next rung is a hard gate
  (a hook that refuses per-card canonical-continuity churn in inline-batch mode) — not this card.
- Dispatch/worker modes are out of scope here: dispatched workers deliver via git/PR and the
  supervisor owns canonical continuity (workers never edit the PRD — that reintroduces the
  last-writer-wins collision item 5 fixed).

## Notes

- `depends-on` the model/effort launch picker conceptually (same launch surface,
  `tui-launch-model-effort-selection`, already shipped) — the mode pick slots beside it.
- High priority: it is the reliability mechanism behind the inline-preferred finding
  (`research/2026-07-17-delegation-cost-finding.md`); without it, the cost lesson depends on the
  model remembering a rule.
