---
status: open
priority: low
created: 2026-07-18
tier: frontier
type: feature
parallel: safe
phase: explore
created_by: owner
surface: .horus/backlog/ divergence umbrella; model + harness + profile + provider-credential route plane
---

> **ON HOLD / deprioritized (2026-07-18).** The first sustained live use went poorly
> (see "First sustained live use" below): host freeze, painfully slow interaction, ~20%
> Codex capacity burned for little delivery, and statusline breakage that leaked into a
> clean non-proxied session. The GPT-in-Claude-Code harness-switch saga is postponed
> until it can be re-tested in a **less risky context** and shown to be worth it at all.
> The one carved-out active thread is [[x4-pi-harness-via-proxy]] (a different harness,
> also via the proxy). Everything else here waits.

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

## First sustained live use — owner verdict (2026-07-18)

The first real GPT-through-Claude-Code session (GPT 5.6 "sol") was, on the owner's
lived experience, a net-negative trial. This is the evidence that puts the branch on
hold — separate from the mechanism working:

- **Host safety.** Sol emitted a command that crashed the workstation; the owner had to
  drop to tty3 and restart the GUI to recover. This is what spawned the whole X5
  safe-execution-boundaries branch. Evidence: [[2026-07-18-agent-host-freeze-incident]].
- **Painfully slow.** Everything dragged — plans took forever to generate, and ordinary
  commands ran minutes longer than they should. The opposite of the owner's experience
  running GPT inside Codex, where the models feel like "an F1 car speeding" that has to
  be *reined in*; proxied-into-Claude-Code was molasses. Cause unknown: either something
  is fundamentally wrong with the config for running through the proxy inside Claude
  Code, or the whole approach is simply not as beneficial as its online promoters claim.
- **Wasted capacity — weekly, not 5h.** ~20% of Codex **weekly** capacity was consumed
  for almost no delivery beyond the planning cards on this branch. This was not a dent
  in a 5h window that refills in hours — it was a fifth of the whole week's budget, which
  is huge and a first-order reason to keep this off until it proves worth it. Those cards
  will themselves be revised in a fresh session before any are actioned.
- **Statusline leaked into a clean session.** After the trial, even a clean
  Opus/Claude-Code session showed a broken statusline (only the context window, reading
  ~43% at session start — implausible). This suggests the proxy toggle has side effects
  that persist beyond the proxied session. Expectation: untoggling the proxy in the TUI
  reverts it; if it does not, the owner will restore the statusline next session, and
  this is grounds to revert the proxy implementation (v0.0.65) entirely.

**Decision.** Postpone and deprioritize the GPT-in-Claude-Code harness switch. It needs
much more testing in a low-risk context before there is any decision on whether it is
worth it. The owner will disable the proxy toggle and watch; a persistent slowdown or
statusline breakage is grounds to revert v0.0.65. The only work that proceeds now is
[[x4-pi-harness-via-proxy]].

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
