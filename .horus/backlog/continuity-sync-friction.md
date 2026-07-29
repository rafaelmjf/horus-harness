---
status: open
priority: medium
created: 2026-07-21
created_by: owner
last_refined: 2026-07-29
refine_passes: 3
readiness: shaping
readiness_reason: "Problem and live evidence are clear; the fix space is deliberately left OPEN (cheap auto-fetch vs deeper format changes) to explore before committing. Refine into concrete increments when picked up."
phase: explore
type: chore
vision_facet: "Continuity core"
---

# continuity-sync-friction — reduce cross-session/cross-machine friction in git-synced continuity

## Why — observed live, 2026-07-21

Continuity is git-synced, which has been a good remote-sync option — but this session
hit two **distinct** frictions worth fixing:

1. **Session-start staleness.** Local `main` was 5 commits behind; the SessionStart hook
   *warned* but fetch-first is advisory, so continuity read at start was stale and cards
   left by other sessions (`codex-identity-guard`, `close-check-unclassified-cards-advisory`)
   were not visible until an explicit fetch mid-session.
2. **PRD frontmatter hand-merge.** Because upstream closures had advanced `PRD.md`, this
   session's frontmatter update had to be re-based on the fresh version and hand-merged —
   preserving prior must-not-lose items (the unmapped `codex-codex-work` dir decision, the
   untested `skill install --user`) while appending the new pointer. The single-line
   `next_prompt`/`current_focus`/`next_action` fields make this a whole-line reconciliation
   every time.

Root reads (to validate, not lock): (1) is purely that fetch-first is advisory, not
enacted. (2) is partly that `next_prompt` carries durable *open decisions* that lack
another home — forcing preserve-and-append — and partly that the volatile pointer shares a
file with the rarely-changing PRD body.

## Intended outcome (open — explore before committing)

Less *avoidable* friction reading and updating continuity across sessions/machines, WITHOUT
decoupling continuity from the repo (repo-local + serverless stays the invariant, and the
occasional hand-merge is an acceptable price). Keep the parts that already scale — per-file
backlog cards conflicted zero times.

## Candidate directions (sketches, NOT decisions)

- **Enact fetch-first:** SessionStart hook actually runs `git fetch` (read-only) and
  auto-`ff-only` pulls when the tree is clean with no local commits, instead of only
  warning. Looks cheap + high-value. **Split (2026-07-29):** the *manual* half of this
  — an owner-invoked fast-forward — shipped as `horus sync` (PR #433), and its cockpit
  surface (the TUI "Sync" button + fleet "Sync all") was promoted to its own Ready card
  `cockpit-sync-action`. What remains open here is only the more invasive *automatic*
  form (the hook mutating the tree at session start without an explicit invocation),
  which is contentious — the freshness card explicitly pushes back on auto-pull — and
  stays a `[session]` question below.
- **Give open decisions a durable home** so `next_prompt` becomes a disposable
  last-writer-wins pointer rather than an accreting register (cards, or an "open decisions"
  list under `## Rules`).
- **Split the volatile pointer** out of `PRD.md` into its own small file, so the hot part
  does not drag the cold PRD body into every merge.
- **Tooling:** `horus resume` surfaces exactly what changed in `.horus/` upstream (new
  cards, frontmatter drift) so reconciliation is not hand-diffed.

## Open questions / to explore

- Which directions are worth doing, and in what order.
- Whether open-decisions get their own register or simply become cards.
- Interaction with the freshness gate.
- **Explicitly the sequential on-ramp to `concurrency-safe-continuity`** — design any fix
  here so it does not have to be redone under parallel multi-agent development.

## Open decisions

- Which candidate directions are worth doing, and in what order. [session]
- Whether open decisions get their own register or simply become cards. [session]
- Enact-fetch-first, **automatic form only** (the SessionStart hook mutating a clean
  tree at session start with no explicit invocation). [session] — the *manual* form
  shipped (`horus sync`) and its cockpit surface is now `cockpit-sync-action`; what is
  left is the contentious auto-mutate-on-launch question, which needs an owner working
  session, not refinement.

## Source

In-session process review, 2026-07-21, prompted by the friction during this session's own
landing. Research receipt `.horus/research/2026-07-21-mobile-agent-session-access.md`.
Related: `concurrency-safe-continuity`, `session-process-cadence`,
`cockpit-sync-action` (the promoted manual-sync slice), `tui-remote-freshness-indicator`.

## Reviews

- 2026-07-28 — **Note only, no scope change** (refine pass). `close-check-unclassified-cards-advisory`,
  listed here as related work, **shipped in #409** (v0.0.75) — removed from Related so it stops
  reading as an open blocker. Both of this card's own frictions remain live and unaddressed:
  session-start staleness (fetch-first is still advisory, not enacted) and the `PRD.md`
  frontmatter hand-merge. Tagged its open decisions on the way past; the enact-fetch-first
  direction is the one `[refine]`-class item and is separable from the format work.
- 2026-07-29 — **Manual-sync slice promoted out** (refine pass). The enact-fetch-first
  direction split: its *manual* half shipped as `horus sync` (PR #433) and its cockpit
  surface became the Ready card `cockpit-sync-action` (`order: 40`). The paired see card
  `tui-remote-freshness-indicator` was minted Ready (`order: 30`). This card is now the
  **residual explore card** — the automatic session-start auto-ff question (downgraded to
  `[session]`) plus the two format frictions (`PRD.md` frontmatter hand-merge; a durable
  home for open decisions), all still `[session]`-class. Stays `shaping`/`explore`; nothing
  here is refinement-ready. Also recorded the naming split (Sync = state inward; Horus
  Assets Refresh = assets outward).
