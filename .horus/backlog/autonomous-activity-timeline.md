---
status: claimed
priority: medium
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/schedule.py or new horus/activity.py (the join), horus/cli.py (schedule status), feeds terminal_tui.py + notify_listen.py + dashboard
---

# autonomous-activity-timeline — one read-out of what's armed + what ran

**Why (owner, 2026-07-18):** with several away workers running, the owner wants one
place that shows both what *will* run (armed/scheduled) and what *did* — successes and
failures with short check marks — instead of stitching it from the head. The data
exists but is scattered: the envelope ledger records what was *dispatched* (`{ts, card,
account, tier, effort, session_id}`) but NOT the outcome; whether a run merged /
escalated / died lives in datums (`datum report` → outcome), the sessions registry
(delivery state), and the supervise verdict. So the "check marks" need a join across
schedule (armed/future) + ledger (dispatched what/when) + datums+registry (outcome).

**TUI-thin constraint:** the join must NOT live in the TUI (it would grow a second
state path — the pane's forbidden rule). It becomes a small CLI primitive the pane,
the phone (`notify listen`'s `schedule` verb), and the dashboard all render.

## How

- **`horus schedule status`** — returns unified rows: armed timers (from `schedule`)
  above, recent dispatched cards with outcome glyphs below. One glyph + one line per
  card: `⧗` armed/running, `✓` merged/shipped, `✗` escalated/failed, `•` no-op.
- Sources: `schedule.load_all()` (armed + andon-halted), `envelope.read_ledger()`
  (dispatched what/when), datums/registry for the outcome. Read-only; no new state.
- Rendered by [[tui-control-settings-pane]] as two bands (Armed / Recent).

## Acceptance

- `schedule status` lists armed dispatches (with andon-halted flagged) and the last N
  dispatched cards each with a correct outcome glyph, joined from the existing readers.
- Deterministic + read-only: no new registry, no outcome inferred it did not observe
  (unknown outcome renders as unknown, never a false ✓).
- One primitive; the pane/phone/dashboard render it without re-parsing.

## Non-goals

- No new telemetry stream or persisted timeline file — it's a join over existing data.
- Not a full scheduler UI — armed management stays in `horus schedule`.
