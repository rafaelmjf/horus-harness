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
surface: horus/input_bridge.py (new registry), horus/cli.py (`horus ask`), horus/notify_listen.py (answer verb + request push)
shipped_pr: 320
shipped_sha: 505a35e90e5e9c5ee7c98eccf98cd954706897fb
---

# input-bridge-remote-ask — a session asks, the owner answers from the phone

**Why (owner, 2026-07-18):** when a session needs owner input mid-run (a decision,
approval, choice, or free-text guidance) it blocks. For an away/unattended worker
that means it stalls until the owner returns to that terminal. This is the single
biggest gap for genuinely leaving a loop running while away. The deterministic
steering channel (#313) could push escalations and pull a fixed grammar, but it
could not carry a question a session raised nor route the answer back into *that*
session.

## How (the deterministic primitive — Station 1, no LLM)

- `horus/input_bridge.py`: an on-disk request/response registry under
  `~/.horus/input-requests/` (same rendezvous pattern as schedule units / andon
  markers) — the asking process and the single listener meet through files.
- `horus ask "<q>" [--option A --option B] [--free-text] [--default A] [--timeout 1h]`:
  writes a request, blocks polling for the response, prints the answer to stdout.
  Exit 0 = answered; 3 = timed out (prints `--default` so the caller can take the
  safe path, checkpoint, and continue later).
- `notify_listen`: each poll cycle pushes any pending request to the owner with a
  tap button per option (callback `answer <id> #<i>`) + an attach hint; a tap or a
  typed `answer <id> <reply>` (or bare `answer <reply>` for the single open
  request) writes the response the asker is waiting on.
- Transport-only, grants no authority; hermes-ready (a future
  [[hermes-input-relay]] layers a conversation on the same registry).

## Acceptance

- `horus ask` blocks until answered and prints the answer; a tapped option and a
  typed reply both resolve; timeout returns the `--default` with exit 3.
- The listener pushes pending requests with option buttons + attach hint and
  writes the response on a tap/typed answer; double-answers are refused.
- End-to-end proven: ask -> registry -> answer-path -> response -> ask returns.

## Non-goals

- No LLM / hermes here (that is [[hermes-input-relay]] in horus-agent).
- No per-project topic routing yet (that is [[telegram-group-project-topics]]);
  until then a typed reply binds to the single open request or needs `answer <id>`.
- The auto "wrap-up + close the session on timeout" orchestration is the caller's,
  refined later; the primitive supplies the default + timeout signal.

## Reviews

- **2026-07-18 — shipped the primitive** (deterministic Station 1). Follow-ups
  carded: `telegram-group-project-topics` (disambiguation + routing),
  `hermes-input-relay` (horus-agent conversational layer).
