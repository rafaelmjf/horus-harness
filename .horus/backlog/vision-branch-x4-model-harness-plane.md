---
status: open
priority: medium
created: 2026-07-18
tier: opus
type: feature
parallel: safe
phase: explore
created_by: owner
surface: .horus/backlog/ (divergence umbrella); may inform a future PRD Vision facet; links the model×harness cards
---

# vision-branch-x4 — model × harness plane

> **Vision branch (divergence umbrella, `phase: explore`, no `vision_facet` yet).** A
> coherent *direction* plus the cards that would realise it, so it can be judged as a unit
> and either promoted to a Vision facet or dropped. Refine conventions in future sessions.

## Why (owner, 2026-07-18)

Since the "Horus is a repo-local **product owner**, not a harness" shift, the owner wants
Horus to be **flexible across harnesses and models** — this space is highly competitive, and
being able to adapt to whichever harness/model is best at a given thing is itself the edge.
Today a launch fixes `account + model`, coupled to one vendor's CLI. The direction: **choose
a *harness* and a *model* separately**, and let Horus route work to the best combination.
Concrete first step the owner is already exploring: run **GPT inside the Claude Code CLI**
(currently the best harness), driven by the **Codex subscription already configured** — not a
new per-token API key.

## Landscape finding (scan `research/2026-07-18-multi-model-harness-scan.md`)

**The plumbing is commoditized — so Horus must not differentiate on it, or own it.**

- Claude Code has **official** non-Anthropic support: `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`
  + `ANTHROPIC_MODEL`, plus opt-in gateway model discovery (`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`,
  off by default since v2.1.129). But it is **client-side pointing only** — a server that speaks
  the Anthropic Messages API must sit at that base URL, because Claude Code never emits OpenAI
  format. So GPT-in-Claude-Code **always** needs a translator in the middle.
- The newer harnesses are **natively** multi-model: **opencode** (~160k★, 75+ providers),
  **pi** (20+, BYOK). **Codex** is OpenAI-native. **LiteLLM** is the de-facto gateway.
- Auto-routing **does not work**: research ("Agent-as-a-Router", arXiv 2606.22902) shows an
  LLM-as-router falls short of the per-task oracle by a wide margin. This is exactly Horus's
  existing rule — **calibration measures, the agent judges, never auto-route**.

**The moat (already ours):** choosing which *(harness, model)* for a task from **measured**
evidence + **owner judgment**, and carrying repo-local **continuity across harnesses**. Nobody
does cross-harness calibration or continuity. This branch is *convergence* of the existing
**Delegation calibration** + **Continuity core** facets, not a new invention.

## Design principles (owner, 2026-07-18) — bind every card in this branch

1. **Third-party tools are OPTIONAL, never dependencies.** A proxy/gateway (CLIProxyAPI, etc.)
   is opt-in exactly like the hermes sink: an **explicit Control-pane toggle, off by default**.
   Horus works fully without it; enabling it is a deliberate owner choice.
2. **Guided setup, not loose support.** When the toggle is turned on, Horus **walks the user
   through** enabling the integration — install check, OAuth login, verify-reachable — and
   surfaces status. It must NOT be "supported" merely by documentation telling the user to go
   configure a third-party tool themselves. The UX guides; it does not gesture.
3. **Fair use, not a gray zone.** Reusing an existing subscription (e.g. the Codex sub) through
   a bridging proxy is treated as **fair use** — current maintainer/Codex-employee posts support
   this pattern. Revisit only if a provider **explicitly** forbids it; do not pre-gate on it.
4. **Horus owns no runtime.** It routes and calibrates and points the harness at a gateway via
   that harness's own mechanism. The moment Horus maintains the gateway or the API-translation
   shim, it has become the harness it says it is not → drop or rescope. **This is the branch's
   convergence kill-switch.**

## Stages (ordered children — thin now, `scope-cards` later)

- **Stage 0 — prove it (spike):** [[gpt-models-in-claude-code-harness]] — run GPT inside Claude
  Code via **CLIProxyAPI bridging the Codex subscription** (the OAuth-subscription path; LiteLLM
  / claude-code-proxy are API-key-only and cannot ride a sub). Prove **tool-use / agentic
  parity**, the **subscription-bridge stability**, and the **usage-visibility gap** (Horus usage
  is Anthropic-rate-limit-shaped; GPT-via-gateway usage may be unmeterable in our path). No Horus
  code; dated receipt + go/no-go.
- **Stage 1 — Horus wiring + the optional toggle:** `ClaudeAdapter.build_env` injects the official
  env vars for a "proxied" account; GPT appears as a launch model choice; a **Control-pane toggle**
  enables the CLIProxyAPI integration with a **guided setup flow** (principles 1–2).
- **Stage 2 — harness axis:** register opencode / pi / codex as adapters (already multi-model, so
  Horus just launches + carries continuity); split the **model × harness** axes in the launch UI; a
  neutral tier resolves to a *combo* at dispatch.
- **Stage 3 — calibration across the matrix:** datums capture (model, harness, task) outcomes;
  recommendations span the matrix; still owner-judged, never auto-routed. **The actual moat.**
- **Optional / parallel:** an API-key path (LiteLLM / claude-code-proxy) for users without a
  subscription to reuse — same optional-toggle + guided-setup pattern.

**Out of scope (named):** Omnigent is an execution/orchestration plane (already Vision
out-of-scope), not a harness on this axis.

## Convergence criterion (judge the branch as a unit)

Promote to a Vision facet (e.g. "Model × harness plane") **iff** cross-harness calibration +
continuity prove valuable in real use. **Drop** if it stays a thin wrapper over commoditized
plumbing (no calibration/continuity edge), or if realising it forces Horus to own a gateway /
translation runtime (principle 4 breached).

## Acceptance (for the branch, not the cards)

- The owner can read this one card and grasp the direction, what's commoditized vs. the moat,
  the optional-integration + guided-UX principles, and which staged cards close each gap.
- The convergence decision is explicit: promote (tight boundary) or drop as a unit.
