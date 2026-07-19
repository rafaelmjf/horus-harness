---
status: open
priority: medium
created: 2026-07-18
vision_facet: "Delegation calibration"
phase: explore
tier: high
type: feature
parallel: safe
created_by: owner
branch: vision-branch-x4-model-harness-plane
surface: (spike — no code) CLIProxyAPI + Codex-subscription OAuth + Claude Code; go/no-go feeds horus/adapters/claude.py build_env wiring at stage 1
---

# gpt-models-in-claude-code-harness — run GPT (via the Codex sub) inside Claude Code (spike)

**Stage 0 of [[vision-branch-x4-model-harness-plane]].** `phase: explore` — a **spike first**,
not a committed feature. Validate the mechanism before any launcher/adapter wiring.

**Why (owner, 2026-07-18):** Claude Code is currently the best harness; GPT models reportedly
run well inside it. If a Claude Code worker can run GPT, Horus's single launch/adapter path can
dispatch either vendor's model on the best harness — directly enabling
`vendor-neutral-delegation-tiers`. The owner wants this driven by the **Codex subscription
already configured**, not a new per-token API key.

## The mechanism (from the scan — verify live, do not trust the summary)

Claude Code's official support (`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL`,
opt-in `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`) is **client-side pointing only** — a server
that speaks the Anthropic Messages API must sit at that base URL. So GPT-in-Claude-Code always
needs a translator. To use the **subscription** (not an API key), that translator must also hold
the **Codex OAuth** — which is exactly **CLIProxyAPI** ("OpenAI Codex (GPT models) via OAuth
login"); LiteLLM and claude-code-proxy are API-key-only and cannot ride a subscription. So the
simplest path that meets the owner's constraint is: **CLIProxyAPI ← Codex OAuth, Claude Code →
`ANTHROPIC_BASE_URL` = CLIProxyAPI.**

## Spike questions (answer before building)

- **Parity:** does a GPT model driven through CLIProxyAPI inside Claude Code hold **tool-use /
  agentic-loop parity** (edits, bash, multi-step) — not just single-turn chat? Run a real
  session; capture evidence.
- **Subscription bridge:** does the Codex-OAuth path work and stay **stable** across a session
  (token refresh, no mid-run drop)? Treated as **fair use**, not a ToS gray zone (owner,
  2026-07-18: Codex-employee posts support this pattern) — do not pre-gate; just record how it
  behaves.
- **Usage visibility:** Horus usage is Anthropic-rate-limit-shaped. Is GPT-via-gateway usage
  visible anywhere (CLIProxyAPI's own metering? the Codex window?), or unmeterable in our path?
- **Fit:** does GPT-in-Claude-Code actually beat just launching a Codex worker for the same GPT
  capability? (The value is *GPT model + Claude Code harness quality*.)

## Acceptance (spike)

- A dated receipt in `.horus/research/` with: the verified launch mechanism, an actually-run
  GPT-in-Claude-Code session transcript/evidence, the subscription-bridge + usage story, and a
  **go/no-go** on wiring stage 1.
- If go → stage 1 card (adapter `build_env` env injection + the **optional Control-pane toggle**
  with **guided setup**, per the branch's design principles); if no-go → record why + drop.

## Non-goals

- No launcher/adapter/tier changes until the spike says go.
- Not a general multi-provider gateway owned by Horus; scoped to "GPT via the Codex sub, inside
  Claude Code." Horus points at CLIProxyAPI — it never owns/vendors it (branch principle 4).
