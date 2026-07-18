---
status: shipped
priority: high
created: 2026-07-17
tier: opus
type: chore
parallel: unsafe
phase: converge
vision_facet: "Autonomous dispatch"
branch: vision-branch-x3-scheduling-and-autonomous-execution
created_by: owner
surface: no code — a live rehearsal of the shipped kit (horus envelope/schedule/run/supervise/notify) on a real small card + isolated account
shipped_pr: 312
shipped_sha: dc1a18b636b0e5558336da687a00f794e8a1a109
---

# x3-away-mode-kit-e2e-rehearsal — dogfood the whole away loop once, end-to-end

**Why (owner, 2026-07-17):** the X3 away-mode kit (items 0–6) shipped fully this
session — each piece verified in isolation (unit tests + a single live probe each) —
but the full chain has NOT been exercised as one loop. Before relying on it during the
2026-07-22 trip, run it once for real. High priority, but **not necessarily the next
item** (deferred deliberately; the owner is first measuring the dispatch mechanism on
other well-scoped cards). This is a validation chore, not a feature — no code expected;
if it surfaces a defect, that becomes its own bug card.

## What to exercise (one real small card, isolated account)

1. `horus envelope create` a bounded, expiring envelope for one small real card on an
   isolated account (e.g. claude-personal), **without** `--allow-merge` first.
2. `horus schedule run --at '+Nm'` a `horus run --unattended --envelope ... --card ...
   --expect-delivery` dispatch, and confirm the on-disk timer + linger.
3. Pair a scheduled `horus supervise <session> --path <repo>` after the worker's finish.
4. **Observe the full loop:** worker delivers (attachable + `auto/<card>` worktree) →
   supervise verifies (required CI on the exact SHA + freshness) → since no merge
   authority, it lands `verified` (no merge) OR, on a deliberately-broken gate,
   escalates to **@horus_agent_rmjf_bot** and **halts a dependent** scheduled dispatch
   (add a throwaway card that `depends-on` the first to see the andon fire).
5. Then repeat once **with** `--allow-merge` + a real `--probe`, and watch it merge +
   close + ship unattended.

## Acceptance

- The full envelope→schedule→dispatch→supervise→(escalate|merge) chain runs unattended
  on a real card with no human in the loop mid-run, and every gate is observed to behave
  as designed (verify+escalate-only by default; merge only with authority + a passing probe).
- A deliberately red gate produces a Telegram escalation AND a visible dependent halt in
  `horus schedule list`.
- Any divergence from designed behavior is filed as a bug card (this rehearsal's real output).

## Notes

- `parallel: unsafe` only in the sense that it drives live systemd timers + real
  dispatch on this machine; it touches no source. Do it on a low-stakes real card so a
  merge is genuinely acceptable.

## Reviews

### 2026-07-18 — Rafael Figueiredo (agent)
Verdict: complete

COMPLETE 2026-07-18: both passes dogfooded live. Pass A (escalate): red gate on PR #311, supervise verified red on exact head, escalated to the telegram bot + andon halted rehearsal-dependent. Pass B (merge): PR #312 green, supervise --allow-merge + probe merged/closed/shipped unattended. Findings carded: scheduled-dispatch-launch-failure-escalates + config-dir-guard-advisory (shipped #310) + supervise session-resolution gap (Rules).
