---
status: shelved
shelved_on: 2026-08-01
priority: medium
created: 2026-07-29
created_by: owner
readiness: shaping
readiness_reason: "The value is clear and the gap is real. The mechanism is now NARROWED rather than open: herdr-host-probe (2026-07-29) showed a screen-scraper is a maintained treadmill, not a one-off, so prefer agent lifecycle hooks + host-supplied state. Still wants a working session to settle hooks-vs-derived and the Codex path."
topic: dashboard-cockpit
type: feature
tier: medium
parallel: safe
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

### What the probe changed (2026-07-29 — evidence in `herdr-host-probe`)

Mechanism (1) is **more expensive than it looks, and the probe priced it.** herdr does not
ship a heuristic; it ships a **versioned per-agent TOML manifest fetched from the network**
(20 agents, claude `2026.07.13.1`, codex `2026.07.18.1`, auto-updated). Its `claude.toml`
matches Claude's literal UI strings by screen region — `working` from a braille spinner in
the OSC title, `blocked` from "enter to select" + "esc to cancel" + a navigation hint after
the last horizontal rule, `idle` from `^\s*❯` in the prompt box. That is a treadmill
tracking another product's wording, and it is *why* the manifest is remotely updatable.
**Horus should not take that on.** Prefer **(2) lifecycle hooks** as authoritative
(`native_hooks.py` already exists) and **(3) host-supplied state** where a host already
pays the cost. Note the traffic runs both ways: `herdr pane report-agent` accepts *pushed*
state, so Claude hooks could feed herdr's sidebar rather than Horus re-deriving it.

herdr's enum is also wider than this card assumed — `idle` · `working` · `blocked` ·
`done` · `unknown` — and `herdr agent wait <target> --until <status> --timeout <ms>` blocks
on it, which is directly interesting for supervising a dispatched worker.

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

## Reviews

- **2026-07-29 — REAL Claude sessions on the herdr host: detection works, and it has
  a false-idle failure mode worth designing around.** Three live runs (real `claude`,
  `work` account, posture forced to `default` because the owner's `full-auto` default
  bypasses permissions and could never produce a `blocked`), launched through
  `terminal_sessions.launch_on("herdr", …)`.

  **What works.** herdr identifies the process as an agent, not just a pane:
  `agent list` returned `{"agent":"claude","agent_status":"idle","pane_id":"w1:p1",…}`
  with the right cwd. Observed transitions on real work:
  - run 2 (Read tool, auto-allowed): `idle → working → idle`
  - run 3 (Write tool, needs approval): `working → **blocked**` at t+6s, with the pane
    showing "Do you want to create probe-out.txt? ❯ 1. Yes / 2. Yes, allow all edits /
    3. No / Esc to cancel · Tab to amend"

  So `blocked` fires on a genuine tool-permission prompt. That is the state the whole
  feature exists for, and it is real.

  **The false idle.** Run 1 sat on Claude's *trust-folder* dialog — "Is this a project
  you created or one you trust? ❯ 1. Yes, I trust this folder / 2. No, exit / Enter to
  confirm · Esc to cancel" — and herdr reported **`idle`**. `agent explain --json`
  shows why: the `live_blocked_form` rule requires the literal "enter to select", and
  this dialog says "Enter to confirm", so no blocked rule matched and the
  `live_prompt_box` idle rule (`^\s*❯`) won instead.

  That is a blocking prompt reported as idle — precisely the failure that destroys the
  feature's value, because the sidebar's whole claim is "this one needs me". And it is
  not a herdr bug so much as the *structural* cost of screen-scraping: the manifest
  tracks Claude's exact wording, one dialog changed its verb, and the state silently
  inverted. herdr already mitigates this the only way scraping can be mitigated — a
  versioned manifest fetched from the network — which is the treadmill this card
  already decided not to join.

  **Consequences for this card, now evidence-backed rather than argued:**
  1. **Hooks are the primary mechanism**, not a nicety. A lifecycle hook knows it is
     awaiting input; no wording can drift out from under it.
  2. **Host-supplied state is a welcome *secondary*** — genuinely useful (it caught
     `blocked` correctly in run 3, with zero Horus code) but it must be treated as
     advisory, never as the only signal.
  3. **Never render a bare `idle` as "free".** An honest three-way — needs-you /
     working / unknown — beats a confident `idle` that might be a dialog waiting on a
     keypress. This is the same discipline as `activity.py` refusing to guess `✓`.
  4. The trust dialog specifically is worth handling: it is the *first* thing a fresh
     agent in a fresh directory hits, so the very state most likely to be
     mis-reported is also the most common one.

  Probe hygiene: three panes created and all closed, the herdr server left stopped as
  found, the throwaway project removed; three honest `failed` registry rows remain
  (that is what `stop_session` records).
