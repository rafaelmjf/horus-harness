---
status: open
priority: medium
created: 2026-07-18
vision_facet: "Delegation calibration"
phase: explore
tier: opus
type: feature
parallel: safe
created_by: owner
surface: horus/adapters.py + horus/launcher.py (claude adapter model/env wiring), horus/datums.py (tier→provider mapping), horus/config.py (per-account provider creds)
---

# gpt-models-in-claude-code-harness — run GPT models inside the Claude Code CLI (spike)

**Why (owner, 2026-07-18):** the owner saw that GPT/OpenAI models can be driven *inside
the Claude Code CLI harness* and reportedly work well there. If a Claude Code worker can
run a GPT model, a single launch/adapter path could dispatch either vendor's model —
directly enabling `vendor-neutral-delegation-tiers` (a neutral tier could resolve to a
GPT model on the Claude Code substrate, not only via a separate Codex worker).

`phase: explore` — this is a **spike first**, not a committed feature. Validate the
mechanism before wiring it into the launcher/tiers.

## Spike questions (answer before building)

- **How** does Claude Code invoke a GPT model? (Env vars / base-url override / a gateway
  / `--model` alias? Capture the exact, current, documented mechanism — verify live, do
  not trust a blog post.) Which GPT models, and does tool-use/agentic-loop parity hold
  inside the Claude Code harness?
- **Auth:** where do OpenAI credentials live, and does per-account isolation
  (`CLAUDE_CONFIG_DIR`) cleanly carry them without cross-account bleed?
- **Cost/usage:** how is usage metered/visible (the `[notify]`/`usage record` path is
  Anthropic-rate-limit-shaped) — is there any signal, or is it unmeterable here?
- **Fit:** does this actually beat launching a Codex worker for the same GPT capability?

## Acceptance (spike)

- A dated spike receipt in `.horus/research/` with the verified launch mechanism, an
  actually-run GPT-in-Claude-Code session transcript/evidence, the auth + usage story,
  and a go/no-go on wiring it into the adapter + tiers.
- If go: a follow-up implementation card (adapter model wiring + tier mapping); if no-go:
  record why and close.

## Non-goals

- No launcher/tier changes until the spike says go.
- Not a general multi-provider gateway; scoped to "GPT model via the Claude Code CLI."
