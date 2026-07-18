---
status: open
priority: medium
created: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: owner
surface: horus/schedule.py (fired-entry → session/receipt link) + horus/terminal_tui.py (Mission Control) + horus/cli.py (schedule status/list)
---

# schedule-status-outcome-not-just-fired — Mission Control shows the outcome, not just "fired"

**Why (owner, 2026-07-19, away-mode drill read-out):** `horus schedule status` /
`schedule list` and the TUI Mission Control render a fired one-shot as `fired` and stop
there — they report that the timer *ran*, not what the dispatched worker *did*. Reading
the light drill's outcomes meant reconstructing them by hand from three places: the run
receipts (`~/.horus/logs/runs/*.log`), the systemd journal
(`journalctl --user -u horus-sched-<id>`), and the input-request registry. For an
away-mode owner opening Mission Control on a phone, "fired" is not an outcome. This is
the observability leg of the autonomous loop, alongside
[[schedule-supervise-resolve-target-at-fire-time]] and [[notify-schedule-batch-complete]].

## How (thin, read-only projection)

A fired schedule entry links to its launched session/run receipt, and `schedule status`
+ Mission Control render the deterministic outcome already on disk: exit status, whether
a branch/commit/PR was produced (the `--expect-delivery` signal), and PR/CI state when a
PR exists — reusing `horus supervise`'s verification read, never re-deriving it or
trusting a worker self-report. Unknown stays unknown, never a false ✓ (the `schedule
status` glyph contract, #324).

## Acceptance

- When a fired dispatch entry is shown in `schedule status` / Mission Control, the tool
  should show an outcome beyond `fired`: at least exit result + delivery (branch/PR
  produced or not), and PR/CI state when a PR exists.
- The outcome is read from durable receipts (run log / registry / gh), not a worker's
  prose; an unreadable signal renders unknown, never a green pass.
- No new always-on polling — the read is on-demand when the pane/command renders.

## Non-goals

- Not auto-merge or auto-supervise (that stays `horus supervise` under envelope authority).
- Not a live activity stream; a render-time projection of on-disk state is enough.
