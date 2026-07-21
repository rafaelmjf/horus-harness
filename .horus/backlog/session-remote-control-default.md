---
status: open
priority: high
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: ready
autonomy: attended
order: 10
phase: build
type: feature
tier: low
parallel: safe
surface: "Horus session-launch path (Claude adapter/launch) + global TUI toggle + per-launch override for remote-control-on-launch"
vision_facet: "Dashboard / cockpit"
---

# session-remote-control-default — launch Horus sessions with remote control enabled by default

## Why

The owner uses Claude Code **remote control** to reach live CLI sessions from the
phone (confirmed working on the Windows box this session). Today it has to be
remembered/enabled, so a session you forgot to enable it on is unreachable from
mobile. Making Horus enable it at launch — with a toggle — means Horus-launched
sessions are phone-attachable immediately, without the papercut. The owner expects
to lean on this heavily over the next few days, so it's the intended next build.

## Intended outcome

Horus-launched **Claude** sessions are remote-control-enabled by default,
controllable via a **global TUI toggle** plus a **per-launch override** — reachable
from the native app without remembering to turn it on.

## Broad boundaries

- **Claude-only for now.** Codex has no equivalent native remote control, and the
  Codex mobile app is Mac-worker-only regardless (see research receipt 2026-07-21).
  Do not block this on Codex parity; the owner explicitly accepts Claude-only until
  Codex's Windows/Linux worker support lands (if ever).
- **A setting with a sensible default + per-launch override, NOT hardcoded
  always-on.** Interactive sessions being cloud-attachable is pure upside; an
  *unattended dispatched worker* being cloud-attachable by default is a posture
  choice the owner must be able to flip. The launch path must read the setting (the
  whole point is catching the sessions you *forgot* about).
- **Scope guard — what this does NOT do:** it makes sessions *reachable*; it does
  **not** remove the phone account-switch step. A session under account B is still
  only attachable when the phone is authed to B — that friction is server-side and
  unfixable client-side (see research). Don't let the card be oversold as "fixes
  switching." It fixes "forgot to enable."

## First step / open decision (verify before building)

- **The exact enable mechanism.** Is Claude Code remote control enabled via a launch
  flag, a `settings.json` key, or only as an in-session action? This determines
  whether Horus can flip it at spawn time or needs a different approach entirely, and
  it sets the pass/fail bar. Quick claude-code-guide check is the first task.

## Acceptance

- **Step 0 (owner-attended):** confirm the remote-control enable mechanism (launch
  flag vs `settings.json` key vs in-session-only); the wiring follows from it.
- With the global toggle on, Horus-launched Claude sessions are remote-control-enabled
  at spawn (no manual in-session step), with a per-launch override; the launch path
  reads the setting so forgotten sessions are covered.
- Gate: full suite green on the exact SHA. Probe: launch a Claude session via Horus
  with the toggle on → confirm it is attachable from the native app with no manual
  enablement; toggle off / per-launch override → not auto-enabled.

## Non-goals

- Not Codex. Not a fix for account-switch friction. Not the self-hosted chat
  frontend (see `horus-phone-chat-poc`).

## Source

In-session discussion 2026-07-21 (owner-directed, "definitely, to be done next").
Research receipt: `.horus/research/2026-07-21-mobile-agent-session-access.md`
(suggested idea #1). Cross-links `native-app-account-launch-spike` (adjacent
account/session-reach work) and `windows-native-horus-setup` (the machine this
serves).

## Reviews

- 2026-07-21 — **Minted Ready (attended)** (owner, refine pass): decision-complete and
  the owner-driven #1 next build; the enable-mechanism unknown is an implementation
  lookup folded into Acceptance step 0, not a design gap. Ordered first (`order: 10`).
  Facet corrected `Distribution → Dashboard / cockpit` (phone-reach-of-sessions).
