---
status: open
priority: medium
readiness: ready
autonomy: attended
created: 2026-07-18
last_refined: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: owner
surface: horus/notify.py (send with message_thread_id), horus/notify_listen.py (thread-aware routing + owner-lock), horus/config.py ([notify] group chat_id + project->topic map)
---

# telegram-group-project-topics — a topic per project in one steering group

**Why (owner, 2026-07-18):** with several away workers running, escalations and
input-requests from different projects all land in one DM and blur together, and
a typed reply is ambiguous about which project's open request it answers. A
Telegram **forum group with one topic per project** separates them: each
project's messages go to its own thread, and a reply *in that thread* binds to
that project unambiguously. It fits the single-consumer constraint (one bot, one
`notify listen` loop still serves every topic) and pairs naturally with both the
input bridge ([[input-bridge-remote-ask]]) and the future hermes relay.

## How

- `[notify]` config gains a group `chat_id` + a `project -> topic (message_thread_id)`
  map (auto-create a topic on first message for a project, or configured).
- Outbound `notify.escalate` / input-request pushes carry `message_thread_id` so
  each project's messages land in its own thread.
- `notify_listen` reads the incoming `message_thread_id` and uses it to bind a
  typed reply / `answer` to that project's open input-request — replacing the
  "single open request or require id" disambiguation the primitive ships with.
- Owner-lock moves from a single DM `chat_id` to the group `chat_id` (optionally
  restrict to the owner's user id within the group). Still owner-only.

## Acceptance

- Each registered project's escalations + input-requests post to its own topic.
- A reply in a project's topic answers that project's open input-request with no
  id needed; cross-topic replies never bind to the wrong project.
- One `notify listen` loop still serves all topics (getUpdates single-consumer).
- DM mode still works when no group is configured (back-compatible).
- Probe (added 2026-07-19 refine pass): `horus notify test` from a repo registered
  to a topic lands in that project's topic, not the DM; with open input-requests in
  topics A and B, a reply typed in topic A binds only to A's request. Reply-binding
  needs an owner tap → dispatch under **verify+escalate** (no auto-merge); the owner
  probes reply-binding at release.

## Non-goals

- No per-project bot (still one bot, one consumer).
- No LLM/hermes here — this is deterministic routing; hermes layers on top later.
