---
status: open
priority: medium
created: 2026-07-18
tier: frontier
type: feature
parallel: safe
phase: explore
created_by: owner
surface: .horus/backlog/ divergence umbrella; model + harness + profile + provider-credential route plane
---

# vision-branch-x4 — model × harness × credential execution-route plane

> **Vision branch (`phase: explore`, no forced Vision facet yet).** A coherent
> direction plus the cards that realise it, judged as a unit and either promoted or
> dropped. The first live GPT-in-Claude-Code session widened the route from two axes
> to the identities the product actually has to preserve.

## Why

Horus is a repo-local product owner, not a harness, so it must remain flexible across
competitive models and harnesses while carrying continuity and measured evidence.
The real execution route is now:

```text
harness + harness profile + model + provider credential + effort + subagent policy
```

A Claude Code profile can run GPT through a Codex subscription; those account names
are not interchangeable. The owner wants the freedom to use the best combination,
with the route explicit and owner-judged rather than silently optimized.

## What is commoditized vs. the edge

Third-party tools already provide model translation and multi-provider plumbing.
Horus does not differentiate by owning a gateway. Its edge is measured
cross-model/cross-harness evidence, truthful account/capacity identity, and repo-local
continuity that survives changing any axis.

**Kill-switch:** if realising this branch requires Horus to maintain an API translation
runtime or become the execution orchestrator, drop/rescope it.

## Principles

1. Third-party integrations stay optional and off by default.
2. Setup is guided and live-verified, not documentation-only.
3. Every launch names the actual harness profile and provider credential; never guess.
4. Calibration measures and the agent/owner judges; no automatic router.
5. Subscription reuse remains fair-use unless a provider explicitly forbids it.
6. Unknown usage/account/context is labelled unknown, never borrowed from another axis.

## Evidence

- Landscape scan: `research/2026-07-18-multi-model-harness-scan.md`
- Stage-0 spike: `research/2026-07-18-x4-stage0-gpt-in-claude-code-spike.md`
- First live session: [[2026-07-18-claudex-first-session-findings]]

## Ordered stages and children

### Stage 0 — prove GPT inside Claude Code (evidence complete)

[[gpt-models-in-claude-code-harness]] proved tool-use parity and subscription OAuth
through CLIProxyAPI, with usage visibility named as an open gap.

### Stage 1 — optional proxy wiring (shipped in v0.0.65)

[[x4-stage1-cliproxy-wiring]] delivered mode B: per-launch env injection, gateway
model discovery, alias→concrete-id mapping, guided toggle/login, and reliable teardown.
No shared `settings.json` rewrite can poison a running session.

### Stage 1.1 — make the live route truthful

1. [[x4-claudex-subagent-context-policy]] — same-model vs tiered GPT subagents and
   trustworthy context handling.
2. [[x4-codex-usage-in-claude-code]] — live native Codex capacity in Claude Code.
3. [[x4-provider-credential-routing]] — deterministic named provider credentials,
   separate from harness profiles.
4. [[x4-tui-execution-route-axis]] — expose and record the complete route.

### Stage 2 — harness axis

Register opencode/pi/codex adapters where they earn scope; split model × harness in
launch UX while preserving continuity. A neutral tier resolves to an owner-approved
combination, never an automatic choice.

### Stage 3 — calibration across the route matrix

Datums capture model + harness + task (+ route identity where relevant); evidence and
recommendations span the matrix. This is the moat, not the gateway.

### Optional

API-key gateway path for users without subscriptions, using the same optional and
guided setup contract.

## Convergence criterion

Converged when: repeated real use proves route truth + cross-harness calibration + continuity are a product edge without Horus owning gateway/orchestration runtime.

**Promote** to a Vision facet only if cross-harness/model route truth plus calibration
and continuity prove valuable in repeated real use. **Drop** if the work remains a
thin wrapper over commoditized plumbing, hidden account/usage ambiguity cannot be
made honest, or Horus must own gateway/orchestration runtime.

## Branch acceptance

- The owner can choose and later audit the actual harness/profile/model/credential
  route without hidden subscription switching.
- Continuity survives moving between route combinations.
- Measured evidence can compare combinations without conflating their accounts.
- Optional integrations remain removable; native agent use still works without them.
