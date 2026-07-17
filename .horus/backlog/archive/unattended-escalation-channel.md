---
status: shipped
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
shipped_pr: 299
shipped_sha: 6d771ed
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

A thin, machine-local notify channel that unattended runs can call on a terminal problem.
Horus owns the **event wiring only** — never a transport, never a token:

- **A sink abstraction with pluggable implementations**, configured machine-locally in
  `~/.horus/config.toml` `[notify]` (never in git, never `fleet.toml`):
  - `hermes` — shells out to `hermes send` (see the 2026-07-17 investigation below).
    Preferred where present; the owner already runs it.
  - `webhook` — POST JSON to a URL, for anyone without Hermes.
  - `none` (default) — no sink configured; escalations stay pull-based as today.
- **Hermes is OPTIONAL, by construction** (owner, 2026-07-17): a machine without it must
  still schedule, supervise and escalate — falling back to `webhook`, else degrading to
  today's pull-only behaviour with a visible note. Horus must never require a second tool
  to be installed.
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
- **With no sink configured, and on a machine with no Hermes at all, every other command
  behaves exactly as it does today** — the channel is additive, never a dependency.
- A sink that fails (Hermes absent, webhook 500, no network) never fails the run it was
  reporting on: the escalation is best-effort and says so.

## Open questions

- Which events are escalation-worthy by default vs opt-in.
- Rate-limiting / dedup so a re-firing schedule doesn't spam.
- Does the `hermes` sink target the home channel (bare `telegram`) or a dedicated
  Horus target/topic? A dedicated one keeps away-mode dispatch noise out of DMs.

## Reviews

- 2026-07-17 — **scoped around `hermes send` (owner-directed investigation).** The owner
  already runs Hermes: three always-on `hermes-gateway-*` systemd services, profiles in
  `~/.hermes/profiles/`, Telegram targets live (`hermes send --list`). `hermes send` is a
  one-shot messenger — its own help: *"no LLM, no agent loop, no running gateway required
  for bot-token platforms like Telegram/Discord/Slack/Signal"* — so Horus shells out one
  line, owns no token, embeds no client, and it works even if the gateway is down. That is
  exactly "Hermes is the messenger, not the cockpit": TUI + horus-agent stay the work
  surface (faster response times), Hermes only carries the escalation. Two owner
  constraints baked into Acceptance above: (1) Hermes is OPTIONAL — a machine without it
  must still schedule/supervise/escalate (webhook, else pull-only); Horus never requires a
  second tool. (2) best-effort — a failing sink never fails the run it reports on. NOT yet
  dispatch-ready: the DM-vs-dedicated-topic open question and the default-events question
  are unresolved design forks. A separate future card could add a TWO-WAY steer-from-phone
  mode (the `terminal`+`skills` Hermes profile pattern from the travel app), but that is
  not this card and not needed for the away-mode cut line.
- 2026-07-17 — priority low→medium: `supervise-verify-merge-close` (medium)
  depends on this card for its escalate path, and the away-mode cut line (owner
  trip 2026-07-22) needs escalation in the minimum trustable kit.

## Notes

- Smallest card in the branch; `supervise-verify-merge-close` depends on it for its escalation
  path. `parallel: unsafe` (touches `horus/cli.py`).
