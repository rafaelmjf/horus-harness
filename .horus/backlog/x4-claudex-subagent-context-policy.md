---
status: open
priority: high
created: 2026-07-18
tier: high
type: feature
parallel: unsafe
phase: explore
created_by: owner
branch: vision-branch-x4-model-harness-plane
surface: horus/proxy.py, horus/adapters/claude.py, horus/adapters/base.py, horus/statusline.py, tests/test_proxy.py, tests/test_statusline.py
---

# x4-claudex-subagent-context-policy — same-model or tiered GPT subagents, honest context

## Why

The first GPT-in-Claude-Code session proved the minimal Claudex recipe and exposed
its tradeoff. `CLAUDE_CODE_SUBAGENT_MODEL=gpt-5.6-sol` has highest precedence and
keeps every subagent on Sol, including cheap searches. Without it, explicit
Sonnet/Haiku subagents follow the current Claude alias map and can consume a Claude
credential instead of staying on GPT. The same session showed the context meter
flipping 0%/100%, which is not useful and may provoke native compaction behavior.
Evidence: [[2026-07-18-claudex-first-session-findings]].

## Design

- Add an explicit proxied-GPT subagent policy:
  - `same-as-parent` injects `CLAUDE_CODE_SUBAGENT_MODEL=<selected GPT id>`.
  - `tiered` (owner default) leaves that global override unset and maps Claude Code
    aliases through `ANTHROPIC_DEFAULT_*_MODEL` to Horus's existing Codex peers:
    Haiku→Luna, Sonnet→Terra, Opus→Terra, Fable→Sol.
- Derive peers from `datums.TIER_EQUIVALENCE`; do not create another model table.
- Add the supported `ANTHROPIC_DEFAULT_FABLE_MODEL` mapping.
- Read the selected model's context window and effective percentage from the
  no-turn native `codex debug models` catalog, validate it, and inject
  `CLAUDE_CODE_MAX_CONTEXT_TOKENS` for proxied GPT launches.
- Context samples that are missing, contradictory, or outside that catalog window
  are unknown. The Horus statusline omits/labels them rather than flashing 0/100.
- Claude-parent and unproxied launches stay provider-native and byte-compatible.

## Acceptance

- A `same-as-parent` GPT Sol launch keeps a subagent on Sol even when its invocation
  requests a lower Claude family.
- A `tiered` launch resolves bounded family probes to Luna/Terra/Terra/Sol and never
  touches a Claude credential for those probes.
- Fable resolves through a concrete served model, not a bare-alias 502.
- The effective context ceiling matches the current native Codex model catalog;
  invalid catalog data fails safe to unknown.
- A live GPT session no longer displays alternating 0%/100% context, and no Horus
  closure/guard command is driven by translated GPT context telemetry.
- Existing native Claude and unproxied tests remain unchanged.

## Non-goals

- No automatic task router: the agent still chooses the explicit tier.
- No provider-account selection (owned by [[x4-provider-credential-routing]]).
- No Codex subscription-window readout (owned by [[x4-codex-usage-in-claude-code]]).
