# Multi-model / multi-harness — landscape scan (X4 candidate)

**Date:** 2026-07-18 · **Type:** market/landscape scan (manual, bounded — no deep-research fan-out)
**Question (owner):** run GPT models inside Claude Code now; longer-term, select *model* and
*harness* separately so Horus can route work to the best harness×model. Do the proxy
projects (CLIProxyAPI, claude-code-proxy) fit as deps, is there a better way, or build our
own? Worth an **X4** vision branch?

## Headline finding (partly overturns the premise)

**The plumbing is commoditized and getting more so — so Horus must NOT differentiate on it.**
"Run any model in any harness" is now a first-class, documented feature of the harnesses and
gateways themselves:

- **Claude Code has OFFICIAL non-Anthropic support** via env vars — no custom code needed:
  `ANTHROPIC_BASE_URL` (point at any Anthropic-Messages-API gateway), `ANTHROPIC_AUTH_TOKEN`,
  `ANTHROPIC_MODEL=gpt-5`, and `ANTHROPIC_CUSTOM_MODEL_OPTION` to add a picker entry. Gateway
  model discovery (`GET /v1/models` → picker, "From gateway") exists but is **opt-in as of
  v2.1.129** (`CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`). There is even a one-click
  productized "claude-code-provider-gateway" app.
- **The newer harnesses are natively multi-model:** **opencode** (~160k★, 75+ providers,
  switch model mid-session, OpenAI-compatible + local) and **pi** (earendil-works, 20+
  providers via a unified `pi-ai` API, BYOK by design) already do "any model in this harness"
  as their core pitch. **Codex** is the OpenAI-native one.
- **LiteLLM** is the de-facto open gateway; it serves `/v1/messages` and translates to any
  provider — the standard way to put GPT/Gemini/Bedrock behind Claude Code.

**What is genuinely unsolved (and IS Horus's lane):** picking *which* (harness, model) for a
given task from **measured** evidence + **owner judgment**, and carrying repo-local
**continuity across harnesses**. Nobody calibrates across harnesses or carries continuity
between them. Research backs the "measured, not auto" stance: *"Agent-as-a-Router"* (arXiv
2606.22902) finds even a zero-shot LLM-as-router falls short of the per-task oracle by a wide
margin — auto-routing underperforms, which is exactly why Horus's rule is **calibration
measures; the agent judges** (never auto-route). One paper's practical policy — "burn remnant
token capacity first, then a tiered routing table for overflow" — literally describes Horus's
warmup/keep-warm + neutral tiers + capacity-triggered dispatch.

## The two named proxies (+ the one they missed: LiteLLM)

| | CLIProxyAPI | claude-code-proxy | **LiteLLM** |
|---|---|---|---|
| Lang / license | Go / MIT | Python / MIT | Python / MIT |
| Stars / maturity | ~43k★, 767 releases, very active | ~2.7k★, single-maintainer-ish | de-facto standard gateway |
| Scope | multi-provider gateway (OpenAI/Gemini/Claude/Grok/Kimi/Codex), OAuth + key pooling | narrow Anthropic↔OpenAI translator | multi-provider `/v1/messages` gateway |
| Shape | long-running daemon | small local server | proxy/daemon |
| Fit | ~= the endgame router, external | stage-1-shaped but narrow/narrow-maintained | strongest general option |

**Supply-chain evidence for "point-at, never vendor":** Anthropic warns LiteLLM PyPI
**1.82.7 / 1.82.8 shipped credential-stealing malware** — pin a known-clean release, rotate
creds if installed. Concrete proof that a proxy must be an *external, user-run, pinned*
service, never a Horus hard dependency.

## LiteLLM vs CLIProxyAPI — the axis that decides it (auth model)

They are different categories. **LiteLLM** = an enterprise **API-key gateway**: you give it
*provider API keys*, clients bill **per-token**; strong governance (virtual keys, budgets,
logging). **CLIProxyAPI** = a **subscription-OAuth bridge + account pooler**: it reuses the
official CLI *subscription* logins ("OpenAI Codex (GPT models) via OAuth login", Claude Code,
Gemini, Grok) with round-robin pooling; a client consumes the **subscription** creds, not
per-token API billing.

For Horus this is decisive: Horus is **subscription-shaped** (accounts, rate-limit windows,
warmup/keep-warm, capacity-triggered tiers, per-account isolation). LiteLLM bolts a per-token
API-key billing axis onto that — foreign, and the open-ended spend the owner is wary of.
**CLIProxyAPI keeps everything in Horus's world** — reuse the subs already paid for, pool the
accounts. So for the owner's stated constraint (**drive GPT via the Codex sub, not an API
key**), CLIProxyAPI is not just preferred, it is *required* — the API-key gateways cannot ride
a subscription at all.

**Fair use, not a gray zone (owner, 2026-07-18):** reusing the Codex subscription through a
bridging proxy is treated as fair use — current maintainer/Codex-employee posts support the
pattern. Revisit only if a provider explicitly forbids it; do not pre-gate on it.

## Build vs. buy verdict

- **A · Point at an external gateway (recommended), as an OPTIONAL, TOGGLED integration.**
  Horus configures + points at a gateway the user runs — the way hermes is optional. **Primary
  = CLIProxyAPI** (subscription path). It is opt-in via an **explicit Control-pane toggle, off
  by default**, and enabling it runs a **guided setup** (install check → Codex OAuth login →
  verify reachable → status), never "documentation says go configure it yourself." Stage-1 code
  is a handful of lines in `ClaudeAdapter.build_env` (where `CLAUDE_CONFIG_DIR` is set) to inject
  the official env vars for a "proxied" account. No vendored dependency.
- **B · Vendor claude-code-proxy / hard-depend on LiteLLM.** Rejected: runtime dependency +
  API-key-only (can't ride the sub) + supply-chain exposure (LiteLLM PyPI 1.82.7/8 malware).
  LiteLLM stays a documented *optional* alternative for users who prefer API keys.
- **C · Build our own translator.** Rejected: Anthropic↔OpenAI translation (tool-use,
  streaming, multimodal) is drifting surface area and is exactly the "superpowers/framework
  depth" and "owns no runtime" the Vision forbids. Reinventing a 43k-star wheel.

## Proposed X4 thesis (worth a branch — as `explore`)

> **Horus is the cross-harness planning + calibration + continuity plane.** It picks the
> (harness, model) combo from measured data + owner judgment, points the chosen harness at the
> chosen model via *that harness's own* gateway/env mechanism, and carries `.horus/` continuity
> across them — owning **no** model runtime and **no** translation layer.

- **Convergence criterion / boundary:** Horus routes and calibrates; it never owns the
  gateway/translation runtime. The moment we maintain the API shim or a required proxy, we've
  become the harness we said we aren't → drop/rescope.
- **Vision fit:** advances **Delegation calibration** (neutral tier → (harness, model) at
  dispatch) + **Continuity core** (spans harnesses). Both already facets; this is convergence,
  not a new invention. The plumbing sits *outside* Horus by design.

## Design principles (owner, 2026-07-18) — bind every card

1. **Optional, never a dependency** — a proxy is opt-in like the hermes sink: an **explicit
   Control-pane toggle, off by default**. Horus works fully without it.
2. **Guided setup, not loose support** — turning the toggle on **walks the user through**
   install → OAuth login → verify-reachable → status; never just docs pointing at a 3rd-party.
3. **Fair use** — subscription reuse is fair use unless a provider explicitly forbids it.
4. **Horus owns no runtime** — routes + calibrates + points; never owns the gateway/translation.
   Breaching this is the branch's convergence kill-switch.

## Staged plan (candidate children)

- **Stage 0 — spike (existing `gpt-models-in-claude-code-harness`, refit as X4 child).** Run a
  real Claude Code session against **CLIProxyAPI bridging the Codex subscription** (the owner's
  constraint: use the sub, not an API key — API-key gateways can't ride a sub); confirm
  **tool-use / agentic parity**, **subscription-bridge stability**, and the **usage-visibility
  gap** (GPT-via-gateway usage may be unmeterable in our Anthropic-shaped path; the gateway's
  own metering may be the only signal).
- **Stage 1 — GPT in Claude Code + the optional toggle.** `ClaudeAdapter.build_env` injects
  `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL` (+ discovery flag) for a
  proxied account; GPT appears as a launch model choice; a **Control-pane toggle** enables the
  CLIProxyAPI integration with a **guided setup flow**.
- **Stage 2 — harness axis.** Register opencode / pi / codex as adapters (they're already
  multi-model, so Horus just launches + carries continuity); split model×harness in the launch
  UI; a neutral tier resolves to a *combo* at dispatch.
- **Stage 3 — calibration across the matrix.** Datums capture (model, harness, task) outcomes;
  recommendations span the matrix; still owner-judged, **never** auto-routed (per the router
  research). This is the actual moat.

**Out of scope (named):** Omnigent is an execution/orchestration plane (already Vision
out-of-scope) — not a harness on this axis.

## Sources
- Claude Code model config (env vars, gateway discovery): https://code.claude.com/docs/en/model-config ; discovery opt-in issue: https://github.com/anthropics/claude-code/issues/56492
- LiteLLM + Claude Code (non-Anthropic models; malware advisory): https://docs.litellm.ai/docs/tutorials/claude_non_anthropic_models
- CLIProxyAPI: https://github.com/router-for-me/CLIProxyAPI · claude-code-proxy: https://github.com/fuergaosi233/claude-code-proxy · provider-gateway app: https://github.com/danielalves96/claude-code-provider-gateway
- opencode: https://opencode.ai/docs/providers/ · pi: https://github.com/earendil-works/pi
- Routing research: "Agent-as-a-Router" https://arxiv.org/pdf/2606.22902
