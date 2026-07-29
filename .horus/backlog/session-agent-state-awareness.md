---
status: open
priority: medium
created: 2026-07-29
created_by: owner
readiness: shaping
readiness_reason: "The value is clear and the gap is real, but the detection mechanism is deliberately open (pane-buffer heuristic vs agent lifecycle hooks vs host-supplied state) — needs a working session to pick one, ideally informed by what herdr-host-probe observes."
phase: explore
type: feature
tier: medium
parallel: safe
vision_facet: "Dashboard / cockpit"
surface: horus/registry.py, horus/terminal_tui.py (Sessions view), possibly horus/activity.py, horus/native_hooks.py
---

# session-agent-state-awareness — surface working / idle / blocked for running sessions

## Why — owner, 2026-07-29

Evaluating herdr, exactly one of its four attractive features turned out to be a genuine
Horus gap: **per-agent state in a sidebar** — `working`, `idle`, `blocked`. The other
three did not survive comparison:

- **Mouse** — already there: the TUI runs `mouse_support=True`
  (`terminal_tui.py:289`) and every launched tmux session gets `set-option mouse on`
  (`terminal_sessions._enable_mouse_mode`). Only click/drag pane-resize is missing.
- **Notifications** — Horus is ahead: `horus notify` → Telegram with away-mode and
  `notify listen` verbs beats local sound/desktop for the actual use case.
- **Plugins** — Horus's extension point is skills, which is closer to what the product is.

What Horus knows today is coarse: `registry.SessionRecord.status` is
`running`/`exited`/`failed` plus a `last_activity_at` timestamp. Nothing knows *"this
agent is sitting on a permission prompt waiting for you"* — which is precisely the state
worth surfacing when several agents run in parallel, because it is the one that costs
wall-clock while looking identical to "busy".

`activity.py` is **not** this: it joins armed schedules, the dispatch ledger, and run
outcomes (the autonomous-dispatch read-out). It is about dispatch history, not live
attention.

## What to build (shape, not yet settled)

A per-session state, computed cheaply, rendered in the TUI Sessions view (and available
to the dashboard and `notify listen`, which already have session rows to hang it on).

Three candidate mechanisms, in rough order of cost:

1. **Pane-buffer heuristic** — hash/snapshot the pane's visible buffer on a timer; no
   change ⇒ idle. Cheap, host-specific, and weak at distinguishing `idle` from `blocked`.
2. **Agent lifecycle hooks** — Claude Code hooks already exist in this repo
   (`native_hooks.py`); a hook that reports "awaiting input" is authoritative rather than
   inferred, but is per-agent work and does not cover Codex without its own path.
3. **Host-supplied state** — if the herdr probe shows `herdr agent explain --json` is
   good, the `state` capability from `session-host-protocol` carries it for free on that
   host, and tmux keeps whichever of (1)/(2) is chosen.

herdr's own approach is worth copying in one respect: it layers them (hooks when
installed, else screen-manifest matching) and keeps **blocked detection deliberately
strict** — only visible approval/permission prompts. A false `blocked` is worse than
none, because the whole value is "this one needs me".

## Acceptance (draft — sharpen when the mechanism is chosen)

- A running session renders a state that is honest: an unknown state renders as unknown,
  never as a confident `idle`. (Same discipline as `activity.py`'s `?` glyph, which
  refuses to guess `✓`.)
- The Sessions view shows it for every running row, and it costs no continuous polling
  loop that runs when nobody is looking at it.
- `blocked` fires only on positively observed evidence of a waiting prompt.
- Whatever is chosen works for both Claude and Codex, or declares which agents it covers.

## Open decisions

- Which mechanism (1/2/3, or a layered combination). [session] — this is the card's whole
  question; wants a working session and preferably the herdr probe's observation of what
  `agent explain --json` reports for a Claude pane on a permission prompt.
- Whether state belongs in `registry.SessionRecord` (durable, and every reader gets it) or
  is computed on read (no schema change, no staleness risk). [session] — it is the same
  durable-vs-derived question the repo has answered both ways; decide with the mechanism.
- Whether `blocked` should escalate through `horus notify` — the away-mode case is
  genuinely "an agent needs you and you are not at the terminal". [refine] once the
  detection is trustworthy; premature while it can false-positive.

## Source

Owner session, 2026-07-29 — the one herdr feature with real pull, kept as an additive
Horus feature rather than a reason to adopt herdr wholesale. Related:
`herdr-host-probe` (may supply the state for free on that host),
`session-host-protocol` (the `state` capability), `activity.py` (deliberately a different
thing).
