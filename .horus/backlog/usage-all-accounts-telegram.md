---
status: open
priority: medium
created: 2026-07-18
vision_facet: "Accounts & isolation"
tier: low
type: feature
parallel: safe
created_by: owner
surface: horus/usage_snapshot.py (all-accounts roll-up + renderer), horus/cli.py (`horus usage all`), horus/notify_listen.py (usage verb)
---

# usage — capacity across all accounts from Telegram

**Why (owner, 2026-07-18):** the steering channel's `usage` read showed only one
target's window. The owner wants to see, from the phone, the capacity of **every**
account at once — which one still has headroom before dispatching there. Pairs
with `warmup` (start a window) and the away-loop (route to the account with room).

## How

- `horus/usage_snapshot.py`: a fleet roll-up over every configured account (each
  Claude `CLAUDE_CONFIG_DIR` + each Codex `CODEX_HOME`, or an agent's default
  when it has no aliases), both windows (5h + weekly), reusing the existing
  cache/read path. Best-effort — an unreadable account renders `unknown`, never
  raises. Reset-past windows blank so a stale percent never misleads.
- `horus usage all [--cached] [--stdout]`: a compact per-account table.
- Point the `notify_listen` `usage` verb at `usage all`.

## Acceptance

- `horus usage all` renders one row per configured account with its 5h + weekly
  percents + resets; `unknown` where unreadable.
- `--cached` never touches the network; `--stdout` emits JSON.
- The phone's `usage` verb surfaces the all-accounts view.

## Non-goals

- No new usage source or metering — reuses the existing snapshot cache/reads.
- No auto-routing off the readout (the delegation hard boundary is unchanged).
