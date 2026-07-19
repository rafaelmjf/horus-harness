---
status: open
priority: high
created: 2026-07-18
last_refined: 2026-07-19
tier: frontier
type: feature
parallel: safe
phase: explore
created_by: owner
branch: vision-branch-x4-model-harness-plane
depends-on: x5-linux-agent-cgroup-containment
surface: run the PI coding-agent harness through Horus via the CLIProxyAPI proxy
---

# x4 — experiment with PI as a harness via the proxy

> **Carved-out priority (2026-07-18).** The X4 harness-switch branch is on hold after a
> poor first live GPT-in-Claude-Code trial (see [[vision-branch-x4-model-harness-plane]]).
> The one thread the owner still wants to pursue is running **PI** through the system via
> the same API-proxy path. This card is explicitly prioritized *ahead of* any further
> GPT-in-Claude-Code work.

## Why

The harness axis (X4 stage 2) always named `opencode / pi / codex` as adapters to
register. Of those, PI is the one the owner wants to try next. It is a distinct harness
from the GPT-in-Claude-Code experiment that went badly — a different runtime, so its
speed/safety/usefulness must be judged on its own evidence, not tarred by that trial.

Reusing the shipped CLIProxyAPI wiring (v0.0.65, mode B) means PI can potentially ride
the same subscription-backed proxy with per-launch env injection and no `settings.json`
rewrite — the safe integration contract already proven for the Claude adapter.

## Scope (to be refined in a fresh session before actioning)

- Confirm what "PI" is as a launchable harness and how it takes a model endpoint /
  base-URL + credential, so it can be pointed at the local CLIProxyAPI gateway.
- Decide whether PI integrates as a first-class Horus harness adapter (like the
  Claude/Codex adapters) or as a thinner launch profile.
- Reuse the existing optional/off-by-default/guided-and-live-verified proxy contract;
  never a documentation-only setup.
- Preserve the X4 principles: every launch names the actual harness + provider
  credential; unknown usage/account/context is labelled unknown, never borrowed.
- Test in a **low-risk context** (the host-freeze lesson): do not evaluate model benefit
  until the host cannot be taken down by one child process — depends on X5 progress
  ([[vision-branch-x5-safe-execution-boundaries]]) for anything unattended.

## Acceptance (draft)

- PI launches through Horus pointed at the local proxy, with the route (harness +
  profile + provider credential) named truthfully in the launch surface.
- Continuity survives a PI-harness session the same as a native one.
- The owner can evaluate whether PI-via-proxy is fast enough and useful enough to keep,
  on real evidence, without a host-safety incident.
- The integration is optional and removable; native agent use still works without it.

## Notes

The exact plan should be (re)drafted in a fresh, unhurried session — consistent with the
owner's intent to revise all X4/X5 planning cards before actioning them.
