---
status: shipped
priority: high
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: opus
type: feature
parallel: safe
created_by: owner
branch: vision-branch-x3-scheduling-and-autonomous-execution
surface: horus/schedule.py (release/re-arm + a persistent listen unit), horus/notify_listen.py (grammar + service loop), horus/cli.py (`horus notify listen --service`, `horus schedule release`)
shipped_pr: 317
shipped_sha: 47ab52ebec0c1b94b0c05446f27002503c370ebf
---

# notify-listen — trip-mode service + andon-reply (release) completion

**Why (owner, 2026-07-18):** the deterministic steering channel shipped
(`notify-listen-steering-channel`, PR #313) — read-mostly + `cancel`/`supervise`, live
round-trip proven. Two gaps remain before it is genuinely usable **unattended for the
2026-07-22 trip**, both continuations of that work:

## 1. Andon-reply loop — `release` a halted dependent from the phone

`horus supervise` halts every dependent scheduled dispatch when a base goes red (the
andon), and the steering channel shows it — but there is **no way to re-arm** a halted
dispatch once the base is fixed. `horus schedule` today has `run|list|cancel` only; a
halt disables the timer (`schedule.halt`) with no inverse.

- Add `horus schedule release <id>` — re-arm a halted (not cancelled, not fired)
  dispatch: re-enable its timer, clear the halted marker, restore its `pending` state.
  Refuse to release a cancelled/fired one (only an andon-halted dispatch is releasable).
- Add `release <id>` to the `notify_listen` grammar (bounded mutation) and a **Release**
  button on escalations that halted dependents (the escalation knows the halted card
  names). Tap → base fixed → dependents re-armed, all from the phone.

## 2. Trip-mode persistent listener

`horus notify listen` runs `--for <window>` or until interrupted — it dies when the
terminal closes, so it cannot cover a week away. Give it the same on-disk `systemd
--user` posture the scheduler already uses (survives reboot, needs linger):

- `horus notify listen --service` (or `horus schedule listen`) writes a persistent
  `--user` unit that runs the poller and restarts on exit; `--stop` tears it down.
- One listener per bot (getUpdates is single-consumer): refuse a second, name the live
  one — mirror the config-dir/one-consumer discipline.
- It reuses `horus notify listen` wholesale (no second poll loop), exactly as
  `horus schedule` passes through to `horus run`.

## Acceptance

- `horus schedule release <id>` re-arms an andon-halted dispatch (verified: halt →
  release → `pending` again in `schedule list`, timer re-enabled on disk); refuses
  cancelled/fired.
- A halted-dependent escalation renders a **Release** button; a tap re-arms it.
- `horus notify listen --service` survives a terminal close (and reboot under linger);
  `--stop` removes it; a second listener is refused with the live one named.

## Non-goals

- Still no free-text NL / LLM (future hermes profile, K2-gated).
- No new work-plane authority; `release` only re-arms an already-authorized dispatch,
  never mints an envelope.
