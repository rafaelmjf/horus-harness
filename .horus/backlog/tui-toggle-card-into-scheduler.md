---
status: open
priority: high
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: explore
tier: opus
type: feature
parallel: safe
created_by: owner
surface: horus/terminal_tui.py (backlog pane toggle), horus/schedule.py (arm from the ordered backlog), horus/envelope.py (bind), horus/warmup.py + usage windows (next-window timing), horus/datums.py (model selection)
---

# tui-toggle-card-into-scheduler — arm/disarm a ready card for autonomous execution

**Why (owner, 2026-07-18, "the most bold TUI feature"):** once a card is refined and
ready, a simple selection toggle in the backlog should add it to (or remove it from) the
scheduler, which then runs it on the **next available window** — accounting for
rate-limit reset timers and model selection. This turns the ordered backlog
([[tui-backlog-refine-and-order]]) into actual scheduled autonomous work without hand-
writing `horus schedule run …` / `horus envelope create` each time.

## How (to design in-card)

- A toggle on a backlog card (e.g. a key on the backlog pane) marks it armed/disarmed
  for autonomous execution. Armed cards feed the scheduling machinery that already
  exists: standing **envelope** (bounds accounts/tier/attempts/merge-authority),
  `horus run --unattended --detach` (worker), `horus schedule run … -- supervise <id>`
  (independent verify/merge). The toggle is a thin front-end over that — it must NEVER
  mint authority: arming a card still requires a live owner-approved envelope to actually
  run (per the unattended-dispatch Rule).
- **Next-window timing:** schedule each armed card for the next window where its chosen
  account has capacity, reading the reset timers (`horus usage`/warmup anchors) rather
  than a fixed clock. Multiple armed cards space out across windows in the execution
  order from [[tui-backlog-refine-and-order]].
- **Model selection:** pick the tier/model from the card's `tier` + live calibration
  (`capabilities --models`), owner-gated — never auto-routed silently.
- Mission Control (`m`) already shows armed dispatches + envelope readiness (envelope
  state truthfulness fixed 2026-07-18) — arming a card should surface there.

## Acceptance (draft — refine before actioning)

- Toggling a ready card on/off arms/disarms it for autonomous execution, visible in
  Mission Control's Armed dispatches.
- An armed card runs only under a live owner-approved envelope; with no live envelope,
  arming is inert and says so (never a silent unauthorized run).
- Scheduling honors the next-available-window timing (reset-timer aware) and the ordered
  backlog; the model/tier is owner-visible, never silently auto-routed.
- Disarming before the window removes the pending dispatch (andon/`schedule release`
  semantics reused, not reinvented).

## Non-goals

- Not a new scheduler/orchestrator — thin front-end over envelope + `schedule` +
  `supervise` (reuse, never re-implement).
- Does not mint dispatch authority; the standing-envelope Rule is unchanged.
- The LLM refine/order pass is [[tui-backlog-refine-and-order]], not this card.

## Notes

Pulled forward from the items 5–7 TUI list (2026-07-18). The first autonomous-scheduler
test (hand-picked cards, 2 cards 10 min apart, walk-away 30 min) is the proving ground
for the underlying schedule+supervise loop this toggle will sit on top of — run that
first (decoupled), then build this.
