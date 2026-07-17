---
status: open
priority: medium
created: 2026-07-17
tier: opus
type: feature
parallel: safe
phase: explore
created_by: owner
surface: .horus/backlog/ (divergence umbrella); may inform a future PRD Vision facet; links five explore cards
---

# vision-branch-x3 — scheduling & autonomous execution

> **New card type (owner, 2026-07-17): a "vision branch".** This is a divergence
> umbrella the owner is testing and will refine in future sessions — it captures a
> coherent *direction* (a roadmap branch, in the `roadmap-branches` sense) plus the
> concrete cards that would realise it, so the branch can be judged and either
> converged (promoted into a Vision facet) or dropped as a unit. It is deliberately
> `phase: explore` and carries **no `vision_facet`**, because the direction is not yet
> in the product's Vision (see the scope note below).

## Why (owner, 2026-07-17)

Born from a live dogfood: a scheduled, one-shot `horus run` dispatched on this machine
(claude-personal, opus, in a worktree) autonomously shipped `PR #287` (the TUI backlog
field picker) end-to-end — cron → worker → branch → CI-green → PR. The test worked, but
exposed that the *full* loop the owner wants is only ~70% built, and that the missing
70%→100% glue lives in the **execution/orchestration plane** the harness Vision currently
declares **out of scope**.

**The end-goal loop** (owner's words): start a cockpit session → check backlog across
projects via fleet commands → pick a card (act directly if it is already scoped; otherwise
use the scoping skills to make it dispatch-ready) → decide model + account + mode → launch
a worker that is **attachable by default** (so the owner can inspect or intervene) → do it
now if requested, or **schedule** it (this machine, never cloud; non-recurring — a card is
done once) under a chosen account (claude-personal / claude-work / codex-personal) → and,
because scheduled work has no live supervisor, **schedule a supervisor run** that
independently verifies, then closes + merges the PR, or escalates a problem to the owner.

## Scope tension (the reason this is a *branch*, not accepted scope)

The harness Vision's **Out of scope** line names *"the execution/orchestration plane
(distributed worker control, agent marketplace)"*. This direction is squarely that plane,
so its cards are filed as a **divergence**, not accepted product scope. Nuance: the
*primitives* already exist in-scope (`horus run`, `horus sessions`, `horus merge-watch`,
`--worktree`, the delivery classifier); what is genuinely new is **scheduling** and the
**auto-merge / escalation glue**. horus-agent cannot host it either — that repo is an
instruction rung that "never grows Python or a service". So **no repo currently owns an
orchestration daemon**; converging this branch means an explicit owner decision to promote
it (a new facet, e.g. "PO execution loop"), with the boundary drawn tightly (single machine,
one-shot, owner-consent-gated — not distributed worker control).

## What already exists vs. the gaps (findings, 2026-07-17)

Mapped from horus-harness source. Flow step → status → mechanism:

1. **Discover cards across projects** — EXISTS — `horus fleet --backlog [--stdout] [--type]`
   (local disk roll-up, `horus/fleet_backlog.py`) or `horus fleet --review` (remote shipped
   truth via `fleet.toml`, `horus/fleet_review.py`).
2. **Pick a card** — EXISTS — JSON roll-up carries status/priority/tier/type/surface,
   priority-sorted (`horus/fleet_backlog.py:30`).
3. **Scoped enough?** — EXISTS as *judgment* (no boolean) — the "Ready gate": a
   `phase: converge` card with `vision_facet` + a testable acceptance line + `surface`/
   `parallel` = dispatch-ready; `phase: explore` = exempt probe. The self-sufficiency test
   lives in the `scope-cards` skill.
4. **Scope a thin card** — EXISTS — `pathfinder` → `roadmap-branches` → `scope-cards` skills.
5. **Decide model + account + mode** — EXISTS — `dispatch-decision` skill emits mode
   (`inline-here`/`dispatched-worker`/`dispatched-plan`) + isolated account (gated on
   `horus usage check`) + tier→model + verification depth + a consent envelope. Card `tier:`
   is advisory input; the skill translates it to a concrete `--model` (nothing auto-selects).
6. **Well-scoped-for-agent vs needs-owner** — EXISTS as judgment — Ready-gate + rubric
   verification depth (proven tier + clear acceptance → autonomous; ambiguous/unproven →
   supervised).
7. **Dispatch now** — EXISTS — `horus run --account --path --worker --model --worktree
   --expect-delivery` (`horus/cli.py:995`, `horus/run_executor.py:72`).
8. **Attachable by default** — **GAP** — attachable *only* with `--target tmux --detach`
   (requires `--worker`); `horus run` defaults to `--target current` = not attachable
   (`horus/cli.py:1073-1087`, `horus/terminal_sessions.py:55-57`). → `unattended-dispatch-attachable-worktree-defaults`.
9. **Schedule it (this machine, not cloud, one-shot)** — **GAP** — no built-in scheduler;
   `horus run` is immediate. → `schedule-local-dispatcher`.
10. **Scheduled supervisor: verify → merge/close, else escalate** — **PARTIAL** — *verify*
    exists unattended (`horus merge-watch` required-CI-on-exact-SHA 0/1/2, `horus close
    --check` freshness 0/1, `horus sessions --json` delivery status + post-hoc receipt), but
    there is **no `horus merge`** (actual merge = `gh pr merge`; `integration.integrate()`
    auto-merge is wired to onboarding only), and **escalation is pull-based only** (no push
    channel in `horus`). → `supervise-verify-merge-close` + `unattended-escalation-channel`.

## The branch's cards (proposed together)

- `schedule-local-dispatcher` — a first-class local one-shot/cron scheduler wrapping
  `horus run` (this machine, never cloud).
- `unattended-dispatch-attachable-worktree-defaults` — make scheduled/detached dispatch
  attachable + worktree-isolated by default (fixes step 8).
- `supervise-verify-merge-close` — an unattended verify → merge → close → escalate command
  (the missing step-10 glue).
- `unattended-escalation-channel` — a push channel so a headless supervisor can tell the
  owner about a problem.
- `cockpit-autonomous-dispatch-contract` — a cockpit skill (+ horus-agent PRD reference)
  wiring the existing skills into this loop, with the owner-consent gate pinned.

## Acceptance (for the branch, not the individual cards)

- The owner can read this one card and understand the whole direction, what already works,
  what is missing, and which cards would close each gap.
- A convergence decision is explicit: either promote to a Vision facet with a tightly-drawn
  boundary, or drop the branch (and its cards) as a unit.

## Notes

- Delivery evidence from the originating dogfood: `PR #287` (merged, `horus-harness`),
  worker opus/claude-personal, 7m55s, in worktree `horus-harness-wt-feat-tui-backlog-field-picker`.
- The hand-rolled crontab wrapper used for the dogfood is a stopgap that
  `schedule-local-dispatcher` would replace.
- "branch x3" is the owner's working identifier for this vision branch; refine the card-type
  conventions (naming, frontmatter, how a branch converges) in a future session.
