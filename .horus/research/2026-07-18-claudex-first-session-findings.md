# Claudex first-session findings — 2026-07-18

## Scope

First sustained Horus session running GPT 5.6 through Claude Code via the shipped
CLIProxyAPI integration (X4 stage 1, mode B). This receipt records what the live
session proved and which product gaps it exposed. It contains no credentials or
provider tokens.

## Verdict

**The basic path works.** Claude Code can run GPT models through the local proxy,
use tools, survive a graphical-session restart through Horus-managed tmux, and
continue after reattachment. The remaining work is not “make Claudex possible”; it
is making the execution route truthful and controllable across model, harness
profile, provider credential, subagent policy, usage, and context.

## Findings

### 1. The minimal same-model recipe is genuinely small

Claude Code resolves a subagent model in this order:

1. `CLAUDE_CODE_SUBAGENT_MODEL`
2. per-invocation Agent `model`
3. agent-definition `model`
4. parent model

Therefore a launch with `CLAUDE_CODE_SUBAGENT_MODEL=gpt-5.6-sol` keeps every
subagent on Sol, even when the invocation asks for Sonnet or Haiku. This is the
five-minute “Claudex” path shared publicly by an OpenAI employee. It is useful as
an explicit **same-as-parent** policy, but it sends cheap searches to the flagship
model too.

The owner's preferred policy is **tiered**: leave the global override unset and map
Claude Code's explicit family requests onto GPT peers through the official
`ANTHROPIC_DEFAULT_*_MODEL` variables:

- Haiku → `gpt-5.6-luna`
- Sonnet → `gpt-5.6-terra`
- Opus → `gpt-5.6-terra`
- Fable → `gpt-5.6-sol`

Claude Code 2.1.214 contains `ANTHROPIC_DEFAULT_FABLE_MODEL` alongside the existing
Haiku/Sonnet/Opus overrides.

### 2. Harness profile is not provider credential

The session ran with the isolated `claude-work` `CLAUDE_CONFIG_DIR`, but proxied
model traffic authenticated with the proxy's own OAuth inventory. At observation
time the proxy held one Claude credential (personal) and one Codex credential
(personal/default); the Codex account id matched the ambient native Codex login.

Two read-only Explore attempts explicitly requested Sonnet and Haiku. The current
alias map resolved those requests to Claude models, so CLIProxyAPI tried its only
Claude credential and returned `429 model_cooldown`. The GPT parent continued
normally through the separate Codex credential. Horus did not choose personal over
work from usage data; work was not present in the proxy's Claude credential pool.

A proxied launch therefore has at least two account identities today:

- **harness profile** — settings/history/config isolation (`CLAUDE_CONFIG_DIR`)
- **provider credential** — the subscription that actually serves and meters the model

The TUI currently presents only the first.

### 3. Named routing is available upstream

CLIProxyAPI OAuth auth files support a per-auth `prefix`, hot-reloaded by the
running service. A prefixed model route can deterministically select a named
credential (for example `codex-personal/gpt-5.6-sol`). One credential has one
prefix, so silently combining deterministic named routes with a second automatic
failover-pool identity would require token duplication, extra proxy instances, or
runtime metadata rewrites. The chosen contract is named credentials plus explicit
owner-selected fallback, never invisible account switching.

### 4. Codex usage has a reliable native status surface

Horus's Codex usage currently comes from the newest native rollout JSONL and was
stale during this session. Codex CLI 0.144.4 exposes the official app-server RPC
`account/rateLimits/read`; it performs an authenticated usage read without creating
a thread or model turn and returns rate-limit windows, reset times, credits, and
limit identities. Horus should call that native surface under the `CODEX_HOME`
whose account id matches the selected proxy credential. Direct token handling or a
Horus-owned `/wham/usage` client is unnecessary.

### 5. GPT context telemetry is not trustworthy yet

The Claude Code context meter visibly oscillated between 0% and 100% while GPT was
active. CLIProxyAPI translates Codex response usage into Claude-compatible events,
but gateway model discovery returns only basic model identity, not a context limit.
The native Codex catalog is the better denominator: `codex debug models` reported
all three GPT 5.6 variants at `context_window=272000` with 95% effective use
(258,400 tokens) during this session.

Horus should inject the validated native effective context ceiling into proxied GPT
launches and treat contradictory translated samples as unknown. A translated GPT
context value must never trigger a Horus closure/guard command.

## Durable follow-ups

- [[x4-claudex-subagent-context-policy]]
- [[x4-codex-usage-in-claude-code]]
- [[x4-provider-credential-routing]]
- [[x4-tui-execution-route-axis]]
- [[vision-branch-x4-model-harness-plane]]

## Sources consulted

- Claude Code model configuration and subagent documentation:
  <https://code.claude.com/docs/en/model-config>
  <https://code.claude.com/docs/en/sub-agents>
- Codex app-server protocol/source: <https://github.com/openai/codex>
- CLIProxyAPI source/configuration: <https://github.com/router-for-me/CLIProxyAPI>
