---
status: open
priority: medium
created: 2026-07-18
last_refined: 2026-07-19
tier: high
type: feature
parallel: safe
phase: explore
created_by: owner
branch: vision-branch-x5-safe-execution-boundaries
surface: Horus notify/listener services plus horus-agent Hermes/Telegram runtime boundary and deployment contract
---

# x5-network-bot-isolation — dedicated boundary for Telegram, Hermes, and future inbound services

## Why

Network-facing bots combine persistent credentials, untrusted inbound data, and
always-on resource use. Running them as the same desktop user with broad home access
means one compromised or runaway bot can reach unrelated agent accounts/projects or
pressure the workstation. They deserve a stronger boundary than trusted interactive
development.

## Design questions

- Dedicated Unix identity versus rootless container, informed by
  [[x5-container-execution-spike]].
- Minimal read/write mounts: bot config/token, bounded request registry, required
  Horus command bridge, and nothing else.
- No Docker socket; no ambient Claude/Codex credential directories.
- Scoped secret injection and rotation without committed values.
- Outbound network allow-list where practical; inbound ownership and authentication
  remain deterministic.
- Independent memory/CPU/PID envelope, restart policy, health signal, logs, and kill
  switch.
- Explicit interface to horus-agent/Hermes rather than moving conversational logic
  into horus-harness.

## Acceptance

- A live bot receives and handles the supported bounded command/input flow while
  unable to read unrelated account credentials or project trees.
- Resource stress or process compromise in the bot boundary cannot pressure GNOME,
  the proxy, or agent sessions.
- Tokens remain local/scoped; logs and receipts contain no secrets.
- Stop/revoke removes network authority without impairing native Horus operation.
- The deployment contract names which repo owns each side and works after reboot.

## Non-goals

- No LLM authority minting through inbound chat.
- No multi-user SaaS or distributed bot fleet.
- No redesign of the existing deterministic notify grammar.
