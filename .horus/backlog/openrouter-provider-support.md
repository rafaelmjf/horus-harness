---
status: open
priority: low
readiness: deferred
readiness_reason: "Park until the X3 kit ships and a real provider-roster need appears."
created: 2026-07-17
last_refined: 2026-07-19
vision_facet: "Delegation calibration"
phase: explore
tier: medium
type: feature
parallel: safe
created_by: owner
surface: horus/adapters (new provider adapter), horus/datums.py roster, account/usage surfaces
---

# openrouter-provider-support — many more models behind one key

**Why (owner, 2026-07-17):** OpenRouter would expose a wide model roster for
delegation experiments beyond Claude/Codex. Deliberately parked: decide scope after
[[vendor-neutral-delegation-tiers]] lands (neutral tiers are the precondition for a
bigger roster meaning anything) and after the X3 kit ships.

## Exit line (explore)

A bounded probe — one OpenRouter-routed worker on a disposable fixture with a
deterministic gate — ends in adopt (adapter card), or drop. Complements, does not
replace, [[remote-open-model-worker-probe]] (local Tailscale models).
