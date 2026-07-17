---
status: open
priority: medium
created: 2026-07-17
tier: sonnet
type: feature
parallel: unsafe
phase: converge
vision_facet: "Autonomous dispatch"
branch: vision-branch-x3-scheduling-and-autonomous-execution
created_by: owner
surface: horus/cli.py; horus/native_hooks.py (band sentinels ~:739-751); new notify wiring (webhook / OS notification / harness PushNotification); machine-local config under ~/.horus/
---

# unattended-escalation-channel — a push channel so a headless supervisor can reach the owner

**Why (owner, 2026-07-17):** for scheduled work the owner wants to be *told* when something
goes wrong ("verify, close and merge the PR, or tell the user if there is a problem"). Today
every escalation surface in `horus` is **pull-based** — a `blocked`/`failed` delivery or a
`*-but-delivered` receipt is only visible if you run `horus sessions`; freshness/divergence
findings only show in `horus close`. There is **no push mechanism** in the codebase
(`PushNotification` belongs to the Claude Code harness, not `horus`). A headless supervisor
(`supervise-verify-merge-close`) that finds a red gate at 05:30 has no way to actively notify.
Part of the `vision-branch-x3-scheduling-and-autonomous-execution` divergence.

## Idea

A thin, machine-local notify channel that unattended runs can call on a terminal problem:

- A configurable sink under `~/.horus/` (never in git): e.g. a webhook URL, an OS
  notification, or delegating to the harness `PushNotification` when running under Claude Code.
- Fires only on **actionable** events: an escalated `horus supervise` failure, a `blocked`/
  `failed` scheduled delivery, or a usage-band closure on an unattended run.
- Message carries the essentials: project, card, session id, which gate failed, the SHA/PR,
  and how to inspect (`horus attach <id>` / PR URL).
- Silent-by-default success (no notification on a clean accept) to avoid alert fatigue.

## Acceptance

- A scheduled `horus supervise` that hits a red required check or failed freshness gate
  delivers a push notification to the owner's configured sink with the failing signal and a
  link to inspect.
- A clean accept produces no push (or an opt-in success ping only).
- No notification config or secret is ever written to git / `fleet.toml`.

## Open questions

- Default sink: OS notification vs webhook vs harness `PushNotification` — and how config is
  declared per machine.
- Which events are escalation-worthy by default vs opt-in.
- Rate-limiting / dedup so a re-firing schedule doesn't spam.

## Reviews

- 2026-07-17 — priority low→medium: `supervise-verify-merge-close` (medium)
  depends on this card for its escalate path, and the away-mode cut line (owner
  trip 2026-07-22) needs escalation in the minimum trustable kit.

## Notes

- Smallest card in the branch; `supervise-verify-merge-close` depends on it for its escalation
  path. `parallel: unsafe` (touches `horus/cli.py`).
