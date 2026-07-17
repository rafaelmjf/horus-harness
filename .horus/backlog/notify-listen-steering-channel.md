---
status: open
priority: high
created: 2026-07-18
vision_facet: "Autonomous dispatch"
phase: converge
tier: opus
type: feature
parallel: safe
created_by: owner
branch: vision-branch-x3-scheduling-and-autonomous-execution
surface: horus/notify.py (inline-keyboard sends), new horus/notify_listen.py (inbound poller + bounded command grammar), horus/cli.py (`horus notify listen`), horus/supervise.py (escalation action buttons)
---

# notify-listen-steering-channel — a deterministic two-way steering channel

**Why (owner, 2026-07-18):** the away loop escalates one-way today (`notify` → phone,
proven live in the X3 e2e rehearsal). The vision is to **interact with the agent to
steer horus projects from the phone, not just receive push notifications**. This adds
the INBOUND half in horus-harness itself — deterministic, no LLM, no hermes — so the
owner can act on an escalation with a tap AND initiate bounded steering commands any
time the listener is running.

This is the harness-owned **Station 1 + the mechanical slice of Station 2** from the
horus-agent messenger-layer assessment (`horus-agent/.horus/research/
2026-07-17-messenger-layer-fresh-assessment.md`), which found the whole "messenger
layer" decomposes into existing owners with **no new product** — Station 1 explicitly
belongs here (extend `notify` + a listener). Conversational stations 2–3 (free-text NL)
remain a future hermes profile, gated on real use (K2); this card is the deterministic
core.

## Design

- **Inbound listener** `horus notify listen [--for <dur>] [--path <repo>]`: long-polls
  the Telegram Bot API `getUpdates` for the configured owner `chat_id` (from
  `[notify]`). Ignores every other chat (`unauthorized_dm_behavior: ignore`). `--for`
  bounds a session (e.g. `8h` for a trip day); default runs until interrupted. For the
  away case it runs as a lingering process.
- **Bounded command grammar → existing deterministic `horus` commands, 1:1.** No free
  shell, no LLM, no new authority.
  - *Read-mostly:* `help`, `sessions`, `schedule`, `backlog`, `usage`.
  - *Bounded mutations:* `cancel <id>` (stop a pending scheduled dispatch),
    `supervise <session>` (re-fire the acceptance gate on a delivery).
  - Unknown input → the help card, never an error, never a shell.
- **Escalation action buttons:** `notify` escalations attach an inline keyboard derived
  from the escalation (Sessions · Schedule · Re-supervise <session>); a button tap is a
  callback handled by the same dispatcher, so a red-gate push is actionable with one tap.

## Security invariants (non-negotiable)

- Owner `chat_id` allowlist only; ignore all other senders.
- Command allowlist only; arguments restricted to a safe charset; commands run as argv
  lists (never a shell string).
- **Never mints authority:** no `envelope create`, nothing `--allow-merge`, nothing
  work-plane (code/diffs/gates). `supervise` re-fire still obeys the run's standing
  envelope (verify+escalate-only unless merge was already granted — the phone cannot
  grant it).
- Token stays machine-local in `[notify]`, never git. Kill switch: `sink = "none"`
  (or just don't run `listen`) disables the whole inbound channel.

## Acceptance

- `horus notify listen` polling, chat_id-locked: an owner text `sessions` returns
  `horus sessions` output; an unknown/other-chat message is ignored.
- A `cancel <id>` round-trip stops a pending dispatch (verified in `horus schedule list`).
- An escalation renders tap buttons; a tap re-fires the mapped command.
- Unit tests cover grammar dispatch, allowlist rejection, chat_id gating, and callback
  mapping with a mocked transport. Live round-trip probed on `@horus_agent_rmjf_bot`.

## Non-goals

- No free-text/NL interpretation (that is the future hermes profile, K2-gated).
- No new work-plane capability; no envelope/merge authority from chat.
- Not a hosted webhook; machine-local long-poll only (matches `notify`'s posture).
