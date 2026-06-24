# Codex Plan Review

Reviewed: 2026-06-24

Scope: validation of `plan.md` only. This file does not modify the plan.

## Refined Core Concept

After the follow-up clarification, the core concept is narrower and stronger than "remote control coding agents":

> A lightweight local gateway that lets one project be driven by different official CLI identities/accounts, while exposing those sessions through one unified chat surface, starting with Telegram topics.

The important differentiators are:

- same project, multiple account identities;
- real Claude Code / Codex CLI sessions, not a new agent loop;
- Telegram topic -> session routing;
- small local process, not a full agent platform;
- explicit account choice per task/session;
- low setup burden for one person using personal and work subscriptions.

This changes the competitive read. Several alternatives overlap with remote control, memory, multi-agent orchestration, or messaging gateways, but very few target this exact account-routing problem in a tiny wrapper.

## Decision Table

| Alternative | What it is | Overlap with Horus | Account switching in same project | Real Claude/Codex CLI session? | Telegram/unified chat? | Lightweight fit | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| Claude Code Remote Control | Official Claude local-session remote UI through Claude web/mobile | Medium | Weak: tied to the logged-in Claude identity for that local session | Yes, Claude only | No Telegram; Claude surfaces only | High | Use alongside Horus, not instead of it |
| GitHub Agent HQ / Copilot Agents | GitHub-hosted agent sessions for Claude/Codex via GitHub, mobile, VS Code, issues, PRs | Medium | Weak: tied to GitHub/Copilot account and enabled repos | Probably not your local subscription CLI session; GitHub-managed agent session | No Telegram | Medium/low for this goal | Watch, but do not build around it |
| Claw Orchestrator / OpenClaw | Multi-engine runtime/orchestrator over Claude, Codex, Gemini, Cursor, OpenCode, etc. | High technically | Possible in theory, but not the small central use case | Claw Orchestrator docs explicitly support CLIs as subprocess engines | Depends on surrounding OpenClaw/gateway setup | Low | Too much platform for MVP; steal patterns only |
| Hermes Agent | Broad self-improving agent platform with memory, skills, providers, gateway, cron, terminal backends | High in surface area | Not the focused primitive; per-topic external runtime binding is/was a requested feature, not the simple default | Mixed: primary model providers can be API/OAuth-backed; Codex CLI exists as a bundled skill/delegation path | Yes, includes Telegram gateway | Low | Too heavy; useful proof that the need exists |
| kube-coder | Kubernetes workspace platform with tmux, browser IDE, dashboards, isolated pods | Low/medium | Not focused on account routing | Integrates coding CLIs in workspace pods | No Telegram found | Very low | Not a substitute; validates "session infrastructure" ideas only |
| PACE | Local persistent memory for Claude using Markdown + SQLite FTS5 + MCP | Low for control plane, medium for later memory | No | Not a session router; targets Claude/PACE memory via MCP/plugin | No | High | Complementary later, not a competitor to MVP |
| claude-code-telegram | Telegram bot for Claude Code with session persistence, sandboxing, audit logging | Medium/high for Claude-only Telegram | Not focused on multi-account/multi-agent per project | Uses Claude Code integration, including SDK/CLI fallback | Yes, Telegram | Medium | Closest implementation reference, but too Claude-specific |

## Alternative Notes

### Claude Code Remote Control

Re-check: the official docs say Remote Control continues a local Claude Code session from phone/tablet/browser, works with `claude.ai/code` and Claude mobile apps, and keeps the session running locally. It is available on Pro, Max, Team, and Enterprise plans, and it is explicitly Claude-only.

This is excellent for what it does. It does not solve the key Horus problem:

- no Codex;
- no Telegram topic routing;
- no unified multi-agent surface;
- no first-class "choose personal vs work account for this project/session" layer.

Decision: keep using it. Horus is for the cases where Claude Remote Control's single-vendor, single-account surface gets in the way.

Source: https://code.claude.com/docs/en/remote-control

### GitHub Agent HQ / Copilot Agents

Re-check: GitHub says Claude and Codex coding agents are available for Copilot Pro+ and Copilot Enterprise customers. GitHub's changelog says sessions can be started from github.com, GitHub Mobile, VS Code, issues, PRs, the Agents tab, and the VS Code agent sessions view. GitHub says no additional Claude/Codex subscription is required during preview and each session consumes one premium request.

Pricing check: GitHub lists Copilot Pro+ at $39/user/month and Copilot Enterprise at $39/user/month. So yes, this is a paid GitHub/Copilot feature, not a lightweight local wrapper over your existing Claude/Codex CLI subscriptions.

This overlaps in "multi-agent control room" but not in the core Horus wedge:

- it is GitHub/repo/PR centered;
- it is GitHub account and Copilot billing centered;
- it is not Telegram-first;
- it is not about local `CODEX_HOME` / `CLAUDE_CONFIG_DIR` account routing;
- it may be very useful for PR-producing tasks, but not as a local personal/work account switchboard.

Decision: watch it, but do not treat it as a replacement.

Sources:
- https://github.blog/changelog/2026-02-04-claude-and-codex-are-now-available-in-public-preview-on-github/
- https://github.com/features/copilot/plans

### Claw Orchestrator / OpenClaw

Correction to the earlier review: Claw Orchestrator is closer mechanically than I first framed it. Its README says it supports Claude Code `claude`, Codex `codex`, Gemini, Cursor Agent, OpenCode, and custom CLIs, and that any coding CLI running as a subprocess can be wired as a custom engine.

So the answer to "does it use true sessions or APIs?" is: for Claw Orchestrator specifically, the documented engine model is real CLI subprocesses.

The reason not to use it for Horus MVP is not "wrong mechanism"; it is product mass. It is a multi-engine runtime with persistent sessions, multi-agent council behavior, isolated git worktrees, and OpenClaw plugin support. Powerful, but Horus needs a much smaller control plane:

```text
Telegram topic -> (agent, account_home, cwd, session_id) -> official CLI resume
```

Decision: study its adapter/session patterns, but do not adopt it until Horus has proven the two-account, one-project Telegram loop.

Source: https://github.com/Enderfga/claw-orchestrator

### Hermes Agent

Hermes is important because it shows the same direction exists: persistent agent, messaging gateway, Telegram, memory, skills, scheduling, and multiple backends. But it is intentionally a broad agent platform.

Re-check:

- Hermes README advertises Telegram/Discord/Slack/WhatsApp/Signal/CLI through one gateway, memory, skills, cron, terminal backends, subagents, and provider switching.
- Hermes provider docs describe Anthropic routes that may use Claude Code credential storage under specific plan/credit conditions, or API keys.
- Hermes has a bundled Codex CLI skill that delegates to the real Codex CLI, but its own docs also distinguish Hermes-managed Codex OAuth/provider behavior from standalone Codex CLI auth.
- A Hermes issue explicitly asks for Telegram topics to be bound to persistent external runtimes like Codex/Claude/Gemini, which is very close to Horus' desired UX. The issue says Hermes had topic-scoped conversations but not the direct "this topic is attached to an external agent runtime/session" workflow at that time.

So Hermes is not "just API-only." It can invoke real CLIs in places. But it is also not a tiny account/session router. It is a full agent operating environment.

Decision: too heavy for Horus' personal MVP; useful validation that Telegram-topic-bound external agent sessions are a real itch.

Sources:
- https://github.com/NousResearch/hermes-agent
- https://hermes-agent.nousresearch.com/docs/integrations/providers
- https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-codex
- https://github.com/NousResearch/hermes-agent/issues/5394

### kube-coder

Re-check: kube-coder is explicitly Kubernetes/Helm/workspace-pod oriented. Its README describes per-user isolated development environments with VS Code in browser, persistent tmux terminals, dashboard, in-pod browser sessions, GitHub OAuth, per-user subdomains, namespaces, ingress rules, and persistent volumes.

That is almost the opposite of Horus' desired mass. It validates some session ideas, especially tmux/persistent workspaces, but it is not the right shape.

Decision: ignore for MVP.

Source: https://github.com/imran31415/kube-coder/blob/main/README.md

### PACE

PACE is not a replacement for Horus. It is a good later companion.

Re-check: PACE describes itself as a local, human-readable memory system: Markdown files, SQLite FTS5, MCP server, no cloud, no vector DB, no API keys. It is aimed at giving Claude persistent memory across sessions. Its README explicitly says it is not a coding assistant memory tool and is more about soft context: decisions, preferences, identifiers, people, relationships, project summaries.

PACE does not solve:

- Telegram control;
- Codex support;
- account switching;
- per-topic session routing;
- official CLI process management.

But PACE is philosophically aligned with Horus: local-first, low infrastructure, human-readable state, SQLite where useful. The plan should keep PACE as a later memory layer, not as part of the MVP.

Decision: complementary. Do not build PACE-like memory until session routing works.

Source: https://github.com/jagbanana/PACE

## Updated Recommendation

The concept survives the re-check.

The sharper framing is:

> Horus is not an agent platform. Horus is a tiny session/account switchboard for official coding CLIs, exposed through Telegram topics.

The MVP should optimize for this single proof:

1. A project can be registered once by name.
2. The same project can be opened under `personal` or `work`.
3. The same Telegram group can have separate topics for those sessions.
4. Each topic is bound to one real CLI session ID.
5. The bot can resume the right session without guessing account, project, or agent.
6. Manual takeover cannot race the bot.

Everything else is optional.

## Product Boundary Decision

Build Horus if the desired tool is:

- personal/local;
- Telegram-first;
- less than a few thousand lines;
- no Kubernetes;
- no dashboard-first workflow;
- no agent marketplace;
- no generic self-improving memory loop;
- no cloud-hosted runtime requirement;
- built around `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, cwd, and session IDs.

Do not build Horus if the real goal becomes:

- multi-user team workspaces;
- scheduled autonomous employees;
- dozens of tools and providers;
- skill marketplaces;
- cloud execution;
- GitHub PR automation as the main surface;
- long-term memory as the primary product.

## Skills And Rules Compatibility Layer

This is a promising feature, but it should be framed carefully.

There are already two emerging common formats:

- `AGENTS.md` for repo/project instructions.
- Agent Skills / `SKILL.md` for reusable task workflows.

So Horus should not invent a new custom standard. The better wedge is:

> Horus can be the local compatibility manager that installs, projects, audits, and activates the right instruction/skill surfaces for each agent/account/session it launches.

### Why this matters

The current ecosystem is converging, but not fully unified:

- Codex uses `AGENTS.md`, `.agents/skills`, Codex plugins, `~/.codex/config.toml`, hooks, MCP config, and `CODEX_HOME`.
- Claude Code uses `CLAUDE.md`, `.claude/skills`, Claude plugins, commands-as-skills, settings, hooks, MCP config, and `CLAUDE_CONFIG_DIR` / Claude config state.
- Cursor uses `.cursor/rules/*.mdc` plus `AGENTS.md`.
- GitHub Copilot uses `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `AGENTS.md`, and Agent Skills.
- Gemini CLI uses `GEMINI.md`, but can configure alternate context filenames such as `AGENTS.md`.
- Windsurf/Devin Cascade supports `AGENTS.md` and its own rules engine.

The real user pain is not just file conversion. It is knowing which instructions and skills are active for this project, under this account, in this agent.

### Relevant standards and docs

`AGENTS.md` is now a real common convention. The official site describes it as a simple open format for guiding coding agents, and says it is used by over 60k open-source projects.

Source: https://agents.md/

Codex officially reads `AGENTS.md`, including global files under `CODEX_HOME`, repo files, nested directory files, `AGENTS.override.md`, fallback names, and byte limits. Codex also has an official import flow that can import instructions, settings, skills, plugins, projects, chat sessions, MCP config, hooks, slash commands, and subagents from other agents into Codex.

Sources:
- https://developers.openai.com/codex/guides/agents-md
- Codex manual, `Import to Codex`

Agent Skills are an open standard. The spec defines a skill as a directory containing `SKILL.md`, optional `scripts/`, `references/`, and `assets/`, with required `name` and `description` frontmatter. Codex, Claude Code, and GitHub Copilot/VS Code all now document Agent Skills support.

Sources:
- https://agentskills.io/specification
- https://code.claude.com/docs/en/skills
- https://code.visualstudio.com/docs/agent-customization/agent-skills

Claude Code explicitly says its skills follow the Agent Skills open standard but extend it with extra behavior such as invocation control, subagent execution, dynamic context injection, allowed/disallowed tools, paths, hooks, and model/effort options. This means a skill can be portable in the common subset but still need target-specific metadata for full fidelity.

Source: https://code.claude.com/docs/en/skills

### Existing tools going in this direction

| Tool | What it does | Relevance | Gap for Horus |
|---|---|---|---|
| `rulesync` | Generates configs for many AI coding tools from unified rule files. Supports rules, commands, MCP, ignore files, subagents, skills, hooks, and permissions across many targets. | Very relevant. It is the strongest existing "compatibility layer" found. | It is a generator/sync tool, not a Telegram/session/account runtime. |
| `instruct-sync` | Installs and syncs instruction packs for Copilot, Cursor, Claude Code, Windsurf, Cline, and `AGENTS.md`. | Relevant for instruction packs and registry-style installs. | Smaller scope; mostly instruction files, not session routing. |
| `ds-agent-rules` / Sync AI Agent Rules | One source of truth for data science / ML rules, synced into `CLAUDE.md`, `AGENTS.md`, Copilot, Gemini, Cursor, Windsurf, etc. | Shows domain-specific rule packs are a real pattern. | Domain-specific and sync-oriented. |
| AI Rules Converter | VS Code extension/CLI to convert rules between Cursor, Windsurf, Kiro, Antigravity, Claude Code, Gemini CLI, and GitHub Copilot; claims skills/MCP/hooks migration too. | Validates demand for conversion UX. | Young/small install base; not tied to actual running sessions. |
| Codex import | Official one-way import into Codex from other agents. | Important because OpenAI is already solving "bring setup into Codex." | Codex-centered, not a neutral multi-agent manager. |

Sources:
- https://github.com/dyoshikawa/rulesync
- https://github.com/zekariasasaminew/instruct-sync
- https://github.com/marketplace/actions/sync-ai-agent-rules
- https://marketplace.visualstudio.com/items?itemName=skezu.ai-rules-converter

### Decision table for Horus

| Possible Horus feature | Build now? | Why |
|---|---:|---|
| Read and display active instruction sources per session | Yes | Fits the UI/control-room idea and directly reduces confusion. |
| Use `AGENTS.md` as the canonical project instruction file | Yes | Existing open convention; no need to invent. |
| Use Agent Skills `SKILL.md` as the canonical portable skill format | Yes | Existing open standard; portable across Codex, Claude, VS Code/Copilot. |
| Install repo-scoped skills into `.agents/skills` | Yes, later MVP+ | Codex and VS Code support it; it is agent-neutral. |
| Generate `.claude/skills` and `.agents/skills` projections | Maybe | Useful if Claude/Codex discovery differs in practice; keep generated files marked as generated. |
| Generate `CLAUDE.md`, `GEMINI.md`, `.cursor/rules`, Copilot instructions from one source | Maybe, but consider delegating to `rulesync` | Existing tools already do this well. Horus should not compete unless runtime integration matters. |
| Translate every Claude plugin/hook/skill into Codex plugin/hook/skill | No for MVP | Too lossy and security-sensitive. Use common subset first. |
| Create a Horus-specific package standard | No | Would add another format to an ecosystem already trying to converge. |

### Recommended design

Use a "canonical plus projections" model:

```text
Canonical repo surfaces:
  AGENTS.md
  .agents/skills/<skill>/SKILL.md
  .horus/compat.toml

Generated / target-specific projections:
  CLAUDE.md
  .claude/skills/<skill>/SKILL.md
  GEMINI.md
  .cursor/rules/*.mdc
  .github/copilot-instructions.md
  .github/instructions/*.instructions.md
```

`AGENTS.md` should hold durable repo conventions: setup, commands, tests, architecture, code style, boundaries, and verification expectations.

Agent Skills should hold repeatable workflows: "review PR", "run app", "debug failing CI", "release checklist", "migrate component", "generate docs", etc.

`.horus/compat.toml` should not become a new instruction language. It should only declare projection policy:

```toml
[canonical]
instructions = "AGENTS.md"
skills = ".agents/skills"

[targets.codex]
enabled = true

[targets.claude]
enabled = true
generate_claude_md = true
skill_projection = "copy"

[targets.cursor]
enabled = false
```

### Compatibility boundaries

Some fields are portable; some are not.

Portable common subset:

- skill directory with `SKILL.md`;
- `name`;
- `description`;
- `scripts/`;
- `references/`;
- `assets/`;
- relative links from `SKILL.md`;
- repo instructions in plain Markdown.

Target-specific or risky:

- Claude `allowed-tools`, `disallowed-tools`, `hooks`, `paths`, `context: fork`, dynamic `!command` injection;
- Codex plugin manifests, marketplaces, app metadata, `agents/openai.yaml`, hooks;
- Cursor `.mdc` frontmatter such as `alwaysApply`, `globs`, and `description`;
- Copilot `applyTo` frontmatter and `.github/instructions/*.instructions.md`;
- Gemini import syntax and context filename settings;
- MCP auth and environment variables;
- permissions and approval rules.

Horus should surface these as warnings rather than pretending conversion is lossless.

### Security note

Skills are executable-adjacent. A skill can include scripts, tool approvals, hooks, MCP config, or instructions that cause an agent to run commands. Installing third-party skills into both Claude and Codex doubles the blast radius.

The compatibility layer should therefore include:

- provenance: where a skill came from;
- target projections generated from which canonical version;
- diff before install/update;
- explicit trust per project/account;
- warning when a skill contains scripts, hooks, MCP config, dynamic shell injection, or tool auto-approval;
- no silent install into work account profiles from personal sources.

### Updated recommendation

This feature is worth adding, but it should be MVP+ rather than MVP.

The order should be:

1. Ship session/account routing.
2. Show active instruction/skill sources in `/ls` or the small UI.
3. Adopt `AGENTS.md` and `.agents/skills` as canonical surfaces.
4. Add `horus doctor compat` to report what each agent would load.
5. Add projection generation only after real pain appears.
6. Consider embedding or shelling out to `rulesync` instead of rebuilding broad rule conversion.

This keeps Horus lightweight while still giving it a stronger identity: not just "Telegram for agents," but "the local control and compatibility layer for official coding-agent CLIs."

## Short Verdict

The core concept is valid, but it is not a greenfield category. Several adjacent systems already exist:

- Official remote control surfaces now exist for Claude Code.
- GitHub now offers a multi-agent control plane for Claude and Codex inside GitHub, GitHub Mobile, and VS Code.
- Community tools already expose Claude Code, Codex, and other coding CLIs through dashboards, Telegram bots, tmux, Kubernetes pods, and orchestrators.

That does not kill Horus. It means Horus should be positioned as a small personal/local control room, not as "the first remote agent controller." The real wedge is:

- official CLI subprocesses, not reimplemented agent loops;
- no model API keys;
- Telegram forum topics as task/session threads;
- local execution on your own machine;
- multiple projects and accounts;
- explicit, inspectable permission posture;
- easy manual takeover over Tailscale/SSH.

As a personal tool or OSS utility, this is worth building. As a broadly marketed product, the differentiation would need sharpening because GitHub Agent HQ, Claude Remote Control, OpenClaw-style systems, and existing Telegram bots overlap heavily.

## What Already Exists

### 1. Official Claude Code Remote Control

Anthropic now documents Claude Code Remote Control as a way to continue a local Claude Code session from phone, tablet, or browser. It keeps execution local and exposes the session through `claude.ai/code` and Claude mobile apps.

Implication: Horus should not compete on "use Claude Code from your phone" alone. That is now table stakes. Horus is still differentiated if it does multi-agent, multi-account, Telegram topics, and local gateway semantics.

Source: https://code.claude.com/docs/en/remote-control

### 2. GitHub Agent HQ / Copilot Agents

GitHub has public-preview support for Claude and Codex coding agents for Copilot Pro+ and Enterprise users. GitHub says users can start sessions from github.com, GitHub Mobile, VS Code, issues, pull requests, the Agents tab, and the VS Code agent sessions view.

Implication: for GitHub-centered workflows, some of Horus' "control room" value is already moving into GitHub. Horus remains useful where you want local subscription CLIs, private machine state, Telegram-first control, non-GitHub projects, or account isolation outside GitHub's product model.

Source: https://github.blog/changelog/2026-02-04-claude-and-codex-are-now-available-in-public-preview-on-github/

### 3. Claw Orchestrator / OpenClaw Ecosystem

`claw-orchestrator` already describes itself as a unified runtime for Claude Code, Codex, Gemini, Cursor Agent, OpenCode, and custom coding CLIs, with OpenClaw plugin support.

Implication: the "adapter over multiple coding CLIs" idea exists. Horus should avoid spending too much early design energy on a general adapter framework. Build the smallest local adapter layer needed for Claude and Codex, then revisit ACP/claw-orchestrator only if the project actually grows beyond two agents.

Source: https://github.com/Enderfga/claw-orchestrator

### 4. kube-coder

`kube-coder` runs Claude/OpenCode sessions in tmux inside Kubernetes workspace pods, with dashboard/API concepts and persistent build sessions.

Implication: the tmux/session/dashboard side exists too. Horus' useful counter-position is "no Kubernetes, no pods, no Helm; just local subprocesses and a small Telegram gateway."

Source: https://github.com/imran31415/kube-coder/blob/main/README.md

### 5. Telegram Bots for Claude Code

Existing projects such as `claude-code-telegram` already provide Telegram access to Claude Code with session persistence.

Implication: the Telegram surface is not novel by itself. The valuable version of Horus is Telegram topics plus multi-agent/multi-account routing plus official CLI subprocesses plus strong local security defaults.

Source: https://github.com/RichardAtCT/claude-code-telegram

## Feasibility Check

The core subprocess strategy is technically feasible.

For Codex CLI, the official reference documents:

- `codex exec` for non-interactive/scripted runs;
- `--json` for newline-delimited JSON events;
- `codex exec resume [SESSION_ID]`;
- `--sandbox read-only | workspace-write | danger-full-access`;
- `--skip-git-repo-check`;
- `CODEX_HOME`-based config behavior.

Source: https://developers.openai.com/codex/cli/reference

For Claude Code, the official reference documents:

- `claude -p` / `--print` for non-interactive mode;
- `--output-format text | json | stream-json`;
- `--permission-mode`;
- `--remote-control`;
- structured output-related flags.

Source: https://code.claude.com/docs/en/cli-reference

For Telegram, `python-telegram-bot` supports `message_thread_id` and `create_forum_topic`. The bot must be an administrator with `can_manage_topics` to create topics in a forum supergroup.

Source: https://docs.python-telegram-bot.org/en/v22.5/telegram.bot.html

## Important Corrections / Risks

### Claude "workspace-write" parity is not proven

Codex has a first-class `--sandbox workspace-write` mode. Claude Code's documented `--permission-mode` values are not the same thing as an OS-level filesystem sandbox. The plan currently treats "Claude equivalent allowlist/mode" as likely, but this should stay a risk until tested.

Recommendation: for the MVP, do not promise Claude has Codex-equivalent workspace confinement. Either:

- start Claude in a low-risk permission mode and accept prompts/failures;
- run Claude in an externally constrained environment;
- use git worktrees and process-level safeguards;
- or make Codex the first "workspace-write by default" implementation and keep Claude more conservative.

### Telegram bot security is the load-bearing part

The allowlist-first design is correct. A Telegram bot that can run coding agents is effectively a remote shell with extra steps. The implementation should reject unauthorized users before parsing commands, touching the session registry, or passing any text to an agent.

The plan should also include:

- bot token storage outside the repo;
- chat ID plus sender user ID allowlisting;
- explicit logging redaction;
- no "reply to unknown topic" fallback;
- command audit records, even if prompts/outputs are not logged.

### Account isolation by env var is useful but not complete security

Separate `CODEX_HOME` / Claude config dirs are the right starting point for subscription/profile isolation. They do not isolate the filesystem, SSH agents, shell history, global git config, package manager credentials, cloud CLIs, or environment variables.

Recommendation: treat account dirs as identity isolation, not security isolation. If work/personal separation matters strongly, add separate OS users, containers, VMs, or at least environment scrubbing later.

### Session concurrency needs a lock

The plan mentions `/sleep` before manual takeover, which is good. It should also implement a per-session lock so the Telegram bot cannot resume the same session while a manual SSH/tmux user is active, and so two Telegram messages do not race against one session ID.

Minimal version: `sessions.locked_by`, `locked_at`, and a timeout/force-unlock command.

### "Always-on" plus subscription CLIs may have policy drift

Using official CLIs is the right side of the line compared with OAuth spoofing or reimplementing private APIs. Still, CLI automation and subscription-account use can be policy-sensitive and can change. This should be rechecked before public release, not just before shipping.

## Where The Plan Is Over-Engineering

### Defer ACP and claw-orchestrator

The adapter abstraction is fine, but adopting ACP or forking an orchestrator before the first working Telegram loop would add mass too early. Two hand-written adapters are enough for MVP.

Recommended MVP adapter surface:

- `start(prompt, cwd, account, permissions) -> session_ref`
- `resume(session_ref, prompt, permissions) -> event_stream`
- `parse_event(raw) -> normalized_event`

Avoid a full runtime abstraction until a third agent is real.

### Defer dashboard

Telegram plus `/ls` is enough for the first control room. A dashboard becomes valuable only after sessions are numerous enough that Telegram topics feel cramped.

### Defer PACE-style memory

Memory is attractive, but it changes the product from "remote control plane" into "agent context platform." Build it only after basic session control is reliable.

### Defer triggers

Hooks, cron, webhook triggers, and completion pings are useful, but they multiply security and lifecycle cases. For MVP, human-started sessions are enough.

### Do not publish package stubs too early unless naming matters emotionally

Claiming GitHub is harmless. PyPI/npm stubs create policy and maintenance overhead. For a personal tool, a GitHub repo name is enough until the implementation exists.

## What Is Under-Engineered

### Failure states

The plan should explicitly model:

- `starting`
- `running`
- `waiting_for_permission`
- `blocked`
- `done`
- `failed`
- `sleeping`
- `locked_manual`

Without this, the bot will feel flaky once subprocesses fail, time out, hit approvals, or produce partial JSON.

### Backpressure and message chunking

Telegram has message limits and UX constraints. Streaming raw JSON or long stdout directly into a topic will get noisy. The MVP should chunk assistant text, suppress low-value tool chatter, and send concise status updates.

### Process timeout and cancellation

`/kill` should terminate the child process group, not only mark a session dead. Windows, WSL, Linux, and macOS differ here. Decide the primary host environment for MVP.

### Project allowlist

`/new <project>` should resolve from a configured project map, not arbitrary filesystem paths. This is a major safety simplification.

## Suggested Smaller MVP

Build less than the current MVP, but prove the dangerous pieces first:

1. Telegram long-polling bot with sender and chat allowlist.
2. Forum topic echo with `message_thread_id`.
3. Static project map: project name -> absolute cwd.
4. Single agent first, probably Codex because `exec`, `--json`, `resume`, and `--sandbox workspace-write` are cleanly documented.
5. SQLite session registry with per-session lock and state.
6. `/new codex personal <project>` starts one session.
7. In-topic prompt resumes that session.
8. `/sleep`, `/lock`, `/unlock`, `/kill`, `/ls`.

Then add Claude once permission behavior is empirically tested.

## Recommendation

Proceed, but sharpen the concept:

Horus should be "a tiny local Telegram control room for official coding CLIs," not "a general multi-agent platform."

The highest-value first proof is not multi-agent orchestration. It is this:

> From my phone, in a Telegram topic, I can safely start and resume a Codex session in a known project, under a known account, with workspace-write permissions, and later take over manually without racing the bot.

If that loop feels good, the rest of the plan has a real foundation. If that loop feels awkward, ACP, memory, dashboards, triggers, and extra agents will not save it.
