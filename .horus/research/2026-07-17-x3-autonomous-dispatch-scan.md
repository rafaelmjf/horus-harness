# Mini market scan: X3 scheduled/autonomous dispatch + supervision — 2026-07-17

Trigger: owner-requested quick check (light sweep, ~6 searches + 1 primary doc fetch;
no deep-research fan-out) to close the blind spot in the vision-branch-x3 session,
which filed the branch without a Step-2 outward pass. Intent lens: deepen-own-use
(build-vs-adopt). Scope: the owner's loop — schedule a card's worker on THIS machine
under own accounts → attachable worker → independent supervisor verifies → merge/close
→ escalate on red.

## Candidates

| Candidate | Does | Misses (vs the X3 loop) |
|---|---|---|
| **Claude Code native scheduling** (3 tiers, Routines shipped Apr'26) | `/loop`+Cron tools: session-scoped, local, 7-day expiry. **Desktop scheduled tasks: local, persistent, no open session, 1-min interval.** Routines: Anthropic cloud, fires with machine off, GitHub-event triggers, autonomous perms, ≥1h | Claude-only; no account routing (isolated config dirs), no `horus run` envelope/receipts/datums, no worktree+attach posture, no independent supervisor, no fleet; Routines = cloud clone, no local files |
| **OpenAI Codex cloud** | Delegated cloud tasks; scheduled pickup of routine work (triage, CI); auto PR review culture internally | Codex-only, cloud sandboxes (not this machine/accounts), no cross-project continuity, merge still human/GitHub-side |
| **GitHub Copilot coding agent** (GA'26) | Assign issue → autonomous branch+PR in Actions, self-iterates on tests, 3-layer security scan | Explicitly STOPS at human review — no unattended merge; per-issue, GitHub-hosted, single-vendor, no fleet/continuity |
| **Devin (Cognition)** | **Closest to the whole loop:** scheduled sessions + playbooks, managed-Devins orchestration (child VMs, recurring, parallel test+report), auto-merge toggle once checks pass | SaaS on their VMs/ACU pricing — not your machine or subscriptions; worker verifies ITSELF (no independent supervisor process); no repo-local agent-neutral continuity; vendor lock |
| **OpenHands + resolver** | OSS, self-hosted, headless from cron/CI; label an issue → sandboxed run → tests → PR | Its own agent (doesn't drive Claude Code/Codex under your plans); human merges; no fleet plane; verification = worker's own tests |
| **Vibe Kanban (BloopAI)** | Local, orchestrates Claude Code/Codex/etc in parallel git worktrees, kanban UI, diff review → PR | Human-in-the-loop by design (review column); no scheduler, no unattended supervisor/merge, no continuity/receipts; a HUMAN kanban for agents — the exact model the agent-first boundary declines |

## Verdict: YELLOW (same shape as the memory finding)

**The scheduling primitive is commoditized** — local persistent scheduling ships native
(Claude Desktop tasks), cloud scheduling ships twice (Routines, Codex cloud), and Devin
sells the full scheduled-orchestration loop. A generic "cron for agents" wrapper is
table stakes; do not build one for its own sake.

**What remains uncovered — the X3 triad nobody has:**
1. **Independent deterministic supervision.** Every candidate either keeps a human at
   merge (Copilot, OpenHands, Vibe Kanban) or lets the worker bless its own work
   (Devin children "verify their own changes"). Nobody runs a *separate* supervisor
   process that re-derives the gate (required CI on the exact SHA + freshness + live
   probe) and refuses worker self-report. `supervise-verify-merge-close` is the
   genuinely novel card.
2. **Own machine, own subscriptions, multi-agent multi-account.** All autonomous loops
   run on vendor infra with vendor metering, single-vendor. Routing scheduled work
   across claude-personal/claude-work/codex under existing plans on this machine is
   unserved — it is exactly the `horus run` envelope (accounts, receipts, datums,
   worktrees) no native scheduler knows about.
3. **Continuity-closing loop.** No candidate closes the loop back into durable
   repo-local state (ship the card, close the PRD boundary, feed the next pick).

**Build-vs-adopt per card:** `schedule-local-dispatcher` — build wrapper-THIN
(systemd/cron backend as carded; revisit Desktop scheduled tasks as an alternative
trigger for claude-only cases, but account routing + receipts force the wrapper);
`supervise-verify-merge-close` — BUILD, it is the differentiator; escalation channel —
adopt native transports (PushNotification/webhook), own only the event wiring (as
carded); attachable/worktree defaults — internal, no market question; cockpit contract
— Horus-specific, build. Capacity-pull dispatch (usage-window reset pulls the next
ready card) appears nowhere in the field — candidate novel addition.

**Risk echo:** natives keep absorbing from below (Desktop tasks are already local +
persistent + 1-min). Anything X3 builds that is *just scheduling* will be subsumed;
the durable part is the envelope + supervisor + continuity closure. Devin's existence
is the value proof — the same loop, sold at ACU pricing, minus neutrality and locality.

## Sources

- https://code.claude.com/docs/en/scheduled-tasks (primary; comparison table local/desktop/cloud)
- https://makerkit.dev/blog/tutorials/claude-code-routines-guide
- https://github.blog/ai-and-ml/github-copilot/assigning-and-completing-issues-with-coding-agent-in-github-copilot/
- https://docs.github.com/copilot/concepts/agents/coding-agent/about-coding-agent
- https://developers.openai.com/codex/cloud · https://openai.com/codex/
- https://docs.devin.ai/release-notes/overview · https://cognition.ai/blog/devin-can-now-manage-devins
- https://github.com/OpenHands/OpenHands · https://www.openhands.dev/product/cli
- https://github.com/BloopAI/vibe-kanban
