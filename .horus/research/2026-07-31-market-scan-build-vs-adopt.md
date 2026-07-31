# Market scan: repo-local agent continuity — 2026-07-31

**Intent:** deepen-own-use (audience = one solo owner-operator) → read as **build-vs-adopt
per capability**, never market saturation.
**Trigger:** pivot / re-baseline (prior bundle 6 releases + 11 days stale).
**Depth:** SHALLOW sweep. Six sources opened; deeper pass offered at the end, not taken.

## Problem / JTBD (hypothesis — not validated by interviews)

"When I return to one of ~20 projects after days away, across two agent CLIs and two
paid accounts on several machines, I want the agent to know what this project is, what
was decided, and what is next — **so I can start work instead of re-explaining it**."

**Current alternatives:** re-explaining by hand each session; `CLAUDE.md`/`AGENTS.md`
instruction files; the agents' own `--resume`/`/resume`; the three tools below.

## Competitive teardown

| Lane | Product | Does well | Gap (vs this owner's job) | Positioning | Evidence |
|---|---|---|---|---|---|
| Continuity | **AICTX** | `.aictx/` repo-local Markdown + Mermaid; CLI **and** MCP server; Codex + Claude Code + Copilot; explicitly local, inspectable | single-project; no accounts/usage; no cockpit; no dispatch | "operational continuity for AI coding agents" | https://aictx.org/ |
| Continuity | **agent-memory** | `.agent-memory/` Markdown as source of truth, git as sync; **MCP is the primary interface**; `staging/` for human-review proposals; FTS5 search; 4 runtimes | v0.5, 7 stars; single-project; no operational plane | "local, git-native project memory" | https://github.com/xChuCx/agent-memory |
| Continuity | **memories.sh** | 4 memory lanes (session/semantic/episodic/procedural); local SQLite free, cloud sync paid; CLI + MCP + SDK | commercial ($15–299/mo); not repo-local Markdown; cloud on paid tiers | "durable state for coding agents" | https://memories.sh/ |
| Cockpit | **Claude Code `claude agents`** | native session dashboard: rows with PR links, `Working` / `Needs input` states, Ctrl+X removal, `/fork` and `/resume` into background sessions | **Claude-only**; no Codex, no accounts, no cross-project fleet | first-party, free | CHANGELOG 2.1.198 / 2.1.203 / 2.1.206 / 2.1.212 |
| Orchestration | **Claude Code Agent Teams** | in-session teammates via the Agent tool | **experimental**, requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | first-party, off by default | CHANGELOG 2.1.178 / 2.1.212 |
| Cockpit | **VS Code Agent Sessions** *(secondary)* | Claude Code + Codex + Copilot side by side in one view | IDE-bound; not terminal/phone | first-party IDE | https://www.developersdigest.tech/blog/vscode-1-128-multi-chat-claude-developer-guide-2026 |

*A claimed `/goal` command from a secondary roundup was **checked against the official
changelog and does not exist**. Rows resting on the changelog are primary; the VS Code
row is secondary and would need verification in a deeper pass.*

## Verdict — build vs adopt, per capability

| Capability | Verdict | Why |
|---|---|---|
| Repo-local continuity files | **KEEP — nothing here is adoptable** | Three teams independently reached the same design, so it is no longer a differentiating *insight* — but none is adoptable for this job (all single-project; agent-memory is v0.5/7 stars, AICTX adoption unmeasured, memories.sh commercial), and the switching cost is 20 managed projects plus the skills, hooks, 62-verb CLI, dashboard and TUI that all key on `.horus/`. What changed is the **justification**, not the verdict: the reason to maintain Horus is now the span, not the file format. |
| **MCP access to continuity** | **ADOPT / COMPOSE** | All three continuity tools expose MCP; two make it the *primary* path. Horus has none. Cheapest capability gap in the scan. |
| Single-agent session list | **ADOPT** | `claude agents` does it natively, and — per today's audit — *more honestly* than Horus, which labels owner-closes `failed`. |
| **Multi-agent × multi-account × multi-project cockpit** | **BUILD / KEEP** | Nothing found spans Claude **and** Codex across accounts, projects and usage. This is the actual differentiator. |
| Session host (tmux / herdr) | **KEEP, THIN** | herdr carried 11 of 26 sessions since v0.0.78. Horus as a thin protocol over someone else's host is the right shape — do not deepen it. |
| Multi-agent orchestration | **DO NOT BUILD** | Already out of scope in the Vision; the platform ships Agent Teams. The boundary holds — this is confirmation, not a gap. |
| Memory segmentation / semantic recall | **DO NOT BUILD** | memories.sh sells lanes + recall as its product. Horus's flat, greppable files are a deliberate different bet. |

## Vision draft (PR-FAQ, one paragraph)

*Horus is the operational plane for one person running many projects across several
coding agents and paid accounts.* Repo-local continuity is no longer a differentiating
idea — three teams reached it independently, and the agent CLIs increasingly ship their
own session views. What nobody ships is the **fleet** view: which of twenty projects is stale, which account
has capacity left, which session on which machine is mid-delivery, and what the next
step is in each — readable from a terminal, a phone, or by the agent itself, with no
vendor lock and no cloud. Horus keeps the files as the contract so any agent can read
them without Horus, and adds the plane the agents deliberately do not: accounts,
usage, fleet state, and owner-gated dispatch.

## Open questions / hard FAQ

1. **Why now?** Three teams independently reached the repo-local-continuity design, and
   the platform shipped its own session view. Horus's differentiator has shifted from
   *what it stores* to *how many things it spans*. **Caveat on this evidence:** what is
   demonstrated is independent reinvention of the idea, NOT a mature category — none of
   the three has measured adoption here, and under a deepen-own-use intent market
   saturation is the wrong yardstick anyway. The adoptability test is what decided the
   verdicts above.
2. **Why us?** Nothing found is multi-agent **and** multi-account **and**
   multi-project. That intersection is the entire remaining moat, and it exists because
   the owner actually has that problem.
3. **Biggest risk?** The platform keeps absorbing upward — `claude agents` already has
   session rows with PR links and honest states. If it adds multi-account and Codex,
   the cockpit's value narrows to fleet-of-projects only.
4. **What does 1M context change?** Opus 5 ships 1M context, which weakens
   continuity-as-token-economy. Continuity-as-durable-cross-session-state is untouched —
   the thesis should be stated that way from now on.
5. **Should MCP replace the CLI?** No — but two competitors treat MCP as the primary
   agent path while Horus requires shelling out. Worth closing as a *read* path only.

## Market-size sanity

Not a market question under this intent — the audience is one owner; the only test is
whether each capability is worth *this* owner's maintenance, and three of seven above say adopt or don't build.

## Candidate backlog items

- **Read-only MCP server over the two contract chokepoints** — from the MCP gap; every
  comparable tool ships one, Horus makes agents shell out. `phase: explore`.
- **Give an owner-initiated close its own terminal status** — from the audit, sharpened
  by `claude agents` showing honest states on the same axis.
- **Restate the continuity thesis as durable cross-session state, not context economy** —
  from the 1M-context finding; a Vision edit, routed to convergence.
- **Evaluate `claude agents` as the single-agent session view** and scope Horus's
  registry to what it uniquely adds (accounts, projects, Codex) — build-vs-adopt.

## Sources

- https://aictx.org/
- https://github.com/xChuCx/agent-memory
- https://memories.sh/
- https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
- https://github.com/Surething-io/cockpit
- https://www.developersdigest.tech/blog/vscode-1-128-multi-chat-claude-developer-guide-2026
