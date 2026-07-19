---
status: open
priority: medium
created: 2026-07-19
last_refined: 2026-07-19
vision_facet: "PO lifecycle"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: owner
surface: horus/backlog.py (deferred + last_refined field parse), horus/backlog_tree.py, horus/cli.py (backlog list sections), horus/terminal_tui.py (backlog pane), horus/skills.py (grooming mode + cockpit ready-gate consume it), horus/routines.py (consolidate read-out counts)
---

# backlog-deferred-disposition — machine-readable "deliberately waiting", honest ready counts

**Why (owner, 2026-07-19 refine pass):** "backlog" reads as active work waiting to be
done, but at the time of carding 14 of 35 open cards were deliberately waiting — branch
holds, missing external evidence, unsettled upstream behavior, observe-first periods.
Nothing machine-readable separated them, so counts misled ("26 of 35 need nothing" read
as 26 work-ready, which was false — the honest split was ~15 ready / ~14 deferred /
5 gated / 1 done-pending-ship), the TUI showed watch-cards beside actionable ones, and a
scheduler or refine pass had no way to skip them. The refine pass stamped the field by
hand; this card makes the tooling consume it.

**The contract (decided in-pass, owner-approved):**

- `deferred: "<reason/until>"` — optional frontmatter. **Presence** is the machine
  signal; the reason is prose for humans and should name what un-defers the card.
- **Ready = `status: open` ∧ no `deferred:` ∧ `depends-on` satisfied.** Gating via
  `depends-on`/events is distinct from deferral — do not conflate them.
- `priority` returns to meaning **importance-when-active**; it is never again used as a
  deferral workaround (demote-to-low for waiting cards is the anti-pattern this
  replaces).
- `last_refined: <date>` — optional frontmatter stamped by refine passes; a future pass
  skips cards whose stamp is newer than their last substantive edit.

## How

- `backlog.py`: parse both fields into the Card dataclass (raw passthrough already
  keeps unknown fields; this promotes them to named fields).
- `horus backlog list` + TUI backlog pane: render deferred cards in a separate section
  (or dimmed with the reason), never interleaved with ready work; counts report
  ready/deferred/gated separately.
- Cockpit ready-gate (`cockpit-autonomous-dispatch-contract` skill) auto-skips
  deferred cards as dispatch candidates — a deferred card is not thin, it is waiting;
  do not route it to grooming.
- Grooming mode (`scope-cards`): skip deferred cards unless the pass holds un-defer
  evidence; skip cards whose `last_refined` postdates their last substantive edit.
- `horus consolidate` read-out: report the disposition split so PRD counts stay honest.

## Acceptance

- A card stamped `deferred:` never renders among ready work in `backlog list` or the
  TUI pane, and appears with its reason in a separate deferred section; counts split
  ready/deferred.
- The cockpit ready-gate refuses a deferred card as a dispatch candidate, naming the
  reason.
- Cards without either new field behave exactly as today (no forced migration).
- Gate: full suite green on the exact SHA. Probe: in this repo (14 live stamped
  cards), `horus backlog list` shows the split with real reasons; stamp/unstamp one
  card and it moves between sections.

## Non-goals

- No auto-undefer: a human or an evidence-holding session removes the stamp.
- No new status enum value — `status:` stays open/claimed/shipped/done; deferral is
  orthogonal disposition.
- No date-based expiry; reasons name conditions, not timers.

## Source

Backlog refine pass, 2026-07-19 (this repo) — owner-designed during the first live
grooming run; the 14 hand-stamped cards are the live fixture.
