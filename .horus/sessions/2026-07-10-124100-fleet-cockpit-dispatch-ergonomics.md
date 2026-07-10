---
date: 2026-07-10T12:41:00
agent: codex
account: ambient
environment: host
project: horus-harness
status: closed
summary: "fleet cockpit dispatch ergonomics"
---

# fleet cockpit dispatch ergonomics

## Summary

Shipped the three dispatch-ergonomics fixes observed in horus-agent's first real
fleet session as independent green checkpoints. Each ticket used a card with an
open→claimed history and an early pushed claim, then landed by auto-merged PR.

## Evidence

- PR #134 added the read-only `horus fleet` command. A live call against the real
  registry printed six non-cockpit projects on one line each with git freshness,
  latest session, and PRD-resolved focus/action/prompt; `horus-agent` was excluded.
- PR #135 made `horus run --worker codex|claude` infer the matching adapter when
  `--agent` is omitted. The CLI-boundary test observed `codex` adapter selection;
  explicit agent and posture precedence stayed intact.
- PR #136 kept Codex's safe `auto-edit` default and made its network/socket limits
  discoverable in `horus run --help` and the adapter docstring. The help regression
  test requires the `--posture full-auto` guidance and bypass warning.
- Full local suites passed after every ticket: 961, 962, then 963 tests. Required
  freshness and Python 3.12/3.13 checks were green on all three PRs before merge.
- All three completed cards were deleted and routed to one-line Shipped entries.

## Next

- Cut the next patch release with Sonnet, do not deploy manually, and observe the
  hosted webhook update `/health` to the published target. Then resume the Opus
  LaunchBackend + LocalBackend seam freeze.
