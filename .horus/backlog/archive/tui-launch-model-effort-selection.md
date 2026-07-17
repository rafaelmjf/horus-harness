---
status: shipped
priority: medium
created: 2026-07-17
tier: sonnet
type: feature
parallel: safe
phase: converge
vision_facet: "Dashboard / cockpit"
created_by: owner
depends-on: tui-branch-tree-glance
surface: horus/terminal_tui.py (new model+effort step after account select; `_Launch` carries model/effort), the launch-execution path (terminal_sessions/run_executor), horus/adapters/ (per-agent valid model list), horus/capabilities.py (tier→recommended-model)
shipped_pr: 305
shipped_sha: bb4cfdf
---

# tui-launch-model-effort-selection — pick model + effort at launch, not after

**Why (owner, 2026-07-17):** launching a session from the TUI — resume, fresh, or by
selecting a backlog card — lets you choose an **account** (claude-personal, claude-work,
codex-personal) but NOT the **model** or **effort**. So the owner routinely launches a
fresh session, changes the model by hand, then tells it to resume from `next_action` —
pure ceremony. The launch flow should offer model + effort selection right after the
account. Most machinery already exists: `horus run`/`RunRequest` take `--model`/`--effort`,
the Defaults-posture screen is the UI pattern, adapters know each agent's valid models,
and `card.tier` + capabilities hold the recommendation — this is mainly TUI wiring.

## How (thin — reuse existing machinery, add no second launch path)

1. In the **TUI** (`terminal_tui.py`) only, after the account is chosen (for fresh /
   resume / card-launch), present a **model** choice scoped to the selected account's
   agent (claude models for a claude account; GPT/Codex models for a codex account —
   read the valid set from the agent's adapter, never a hardcoded list), then an
   **effort** choice from the existing `{low, medium, high, xhigh, max}`. Per-launch
   selection only — no persisted default this pass (a Defaults-style persisted model, like
   the posture setting, can be a later addition if the per-launch pick proves not enough).
2. Thread the chosen model + effort into the launch: `_Launch` carries them and the
   execution path passes them through to the same `RunRequest`/`horus run` fields that
   already exist. Choosing nothing keeps today's behavior (the agent's default model).
3. **Recommended tag:** for a **resume** or **backlog-card** launch, if the card (or the
   project's next-action card) declares a `tier:`, mark the model that tier resolves to
   for the selected agent with a `(recommended)` tag — resolved through the SAME
   tier→model mapping `horus capabilities` uses, so it stays correct before and after
   `vendor-neutral-delegation-tiers` lands (which makes the mapping per-provider, i.e. a
   different recommended model for claude vs codex). A **fresh** launch shows no
   recommendation.

## Acceptance

- After selecting an account in the TUI launch flow, the user selects a model and an
  effort level, and the launched session runs with exactly those (the run request/command
  carries the chosen `model` + `effort`; verifiable without a live agent).
- The offered models are scoped to the selected account's agent; a codex account never
  offers claude models and vice-versa.
- For a resume or card-launch where a `tier:` is declared, the model that tier resolves
  to for that agent is labeled `(recommended)`; a fresh launch shows no `(recommended)`.
- Back-compat: accepting the default launches with the agent's default model exactly as
  today. The browser/xterm launcher (`terminal_app.py`) is out of scope this pass and
  stays unchanged (TUI-only).
- Tests cover: model+effort threaded into the launch, per-agent model scoping, and the
  recommended tag present for a tiered resume/card-launch but absent for fresh.

## Non-goals

- No auto-selection or auto-routing — the recommendation is a label; the owner still
  picks (existing delegation rule). No new model list hardcoded in the TUI. No change to
  the `horus run` CLI surface (it already takes `--model`/`--effort`).

## Notes

- `parallel: safe` but shares `horus/terminal_tui.py` with `tui-branch-tree-glance`, so
  serialize after that card merges (hence `depends-on`). The `(recommended)` mapping is a
  soft coupling to `vendor-neutral-delegation-tiers`: this card works standalone against
  today's model-named tiers and gets richer (per-provider) once neutral tiers land.
