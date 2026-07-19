---
status: open
priority: low
readiness: deferred
readiness_reason: "X4 branch remains on hold under the 2026-07-18 owner verdict."
created: 2026-07-18
last_refined: 2026-07-19
tier: high
type: feature
parallel: unsafe
phase: explore
created_by: owner
branch: vision-branch-x4-model-harness-plane
surface: horus/codex_usage.py, horus/usage_snapshot.py, horus/statusline.py, horus/cli.py, horus/adapters/claude.py
---

# x4-codex-usage-in-claude-code — live Codex limits while GPT runs in Claude Code

## Why

GPT requests through CLIProxyAPI spend the Codex subscription, but Claude Code's
statusline currently records the selected Claude harness profile's rate limits and
Horus's Codex reading comes from stale native rollout JSONL. The first Claudex
session therefore showed the wrong capacity surface while the real Codex account was
being consumed. Evidence: [[2026-07-18-claudex-first-session-findings]].

## Design

- Use the installed Codex app-server protocol as the authority:
  `initialize` → `initialized` → `account/rateLimits/read` over bounded stdio.
- The read must create no thread, turn, or model call. Horus never calls internal
  ChatGPT endpoints directly and never extracts OAuth tokens into its own client.
- Match the proxy Codex credential to a configured/ambient `CODEX_HOME` by account
  id. No match means **unlinked/unknown**, never a fallback to another account.
- Cache the returned fast/slow windows, reset times, credits, source, and freshness.
  Native rollout JSONL remains a clearly-labelled stale/offline fallback only.
- Inject safe route identity into the Claude process. When its active model is GPT,
  `horus statusline` reads/renders the matched Codex snapshot and does not record the
  Claude profile's pushed limits as if they applied to GPT.
- Refresh only after a short TTL with a hard timeout and stale-on-error behavior;
  statusline rendering must never hang, disappear, or become a background poller.

## Acceptance

- A protocol fixture proves the exact handshake and parses `rateLimits` plus
  `rateLimitsByLimitId` without any model-turn method.
- The native Codex account id and proxy credential are matched deterministically;
  mismatched/unlinked identities produce unknown.
- A live GPT Claude Code statusline agrees with native Codex `/status` for the same
  account's window percentages/resets and names source/freshness.
- A Claude model continues to render/record Claude limits, including after an
  in-session provider switch.
- Timeouts, malformed replies, missing Codex, and stale cache all degrade honestly
  without corrupting the statusline.

## Non-goals

- No exact per-request token attribution through CLIProxyAPI.
- No continuous usage polling or automatic model/account routing.
- No provider credential picker (owned by [[x4-tui-execution-route-axis]]).
