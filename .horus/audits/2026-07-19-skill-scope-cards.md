# Skill audit: scope-cards — 2026-07-19

Trigger: owner-requested calibration after the first full interactive backlog-curation
run failed to follow the intended format.

## Evidence

- The original owner specification required a product-and-branch picture before any
  questions, followed by one interactive decision card at a time with a recommended
  option and explicit consequences.
- `scope-cards` v5 mentions those ideas only inside a backlog-grooming subsection. The
  first Codex invocation skipped the picture and did not preserve the strict picker
  contract.
- Revisions v3–v5 also made `scope-cards` both the chosen-branch decomposer and the
  owner of final dispatch readiness. That contradicts the owner's intended pipeline:
  pathfinder produces alternative directions, `scope-cards` turns the chosen direction
  into aligned high-level drafts, and a separate attended refinement pass makes cards
  executable.
- `pathfinder` and `cockpit-autonomous-dispatch-contract` now repeat that accidental
  ownership by pointing to the dispatchable-card contract in `scope-cards`.

## Verdict: revise

Split shaping from readiness instead of adding another exception to `scope-cards`.

### Exact replacement contract

1. `scope-cards` consumes an approved roadmap branch or equivalent owner direction and
   proposes durable, high-level `readiness: shaping` card drafts. Each draft preserves
   why, intended outcome, broad boundaries, source evidence, Vision/branch relationship,
   and unresolved decisions. It does not invent final implementation steps, collision
   stamps, supervisor acceptance, autonomy, or execution order.
2. A new standalone `backlog-refine` skill consumes the existing backlog and owns the
   single execution-ready card contract. It starts with “Here is our current picture,”
   presents product direction plus every active branch and readiness/priority counts,
   judges before linting, skips settled cards, and escalates only real pending decisions.
3. Each escalated card uses the native structured picker when available: card number,
   problem, proposed solution, current state, 2–3 mutually exclusive options with the
   recommendation first and marked, and the exact consequence of each option. Free-text
   Other remains available. A numbered 1–3 plus “4. type anything” rendering is the
   fallback when no picker exists.
4. `backlog-refine` assigns final how/acceptance/non-goals/dependencies/order/tier/
   surface/parallel plus `readiness`; only Ready cards receive `autonomy`.
5. `pathfinder` sequences both skills. Dispatch consumers reference only
   `backlog-refine` for readiness and route Shaping/Unclassified cards there.

## Ceremony check

This removes duplicated flows: branch scoping no longer performs a backlog-wide audit,
and backlog polish no longer runs the market/branch chain. No CLI or receipt is required
to invoke either skill; the TUI remains a future thin launcher.

## Owner verdict

Approved in the implementation plan on 2026-07-19: preserve X6 as a raw branch, then
land the complete skill seam before applying the backlog curation decisions.
