---
status: open
priority: medium
readiness: ready
autonomy: attended
readiness_reason: "Demonstrated live (2026-07-20): a merge with fully-fresh continuity was blocked by `horus close --check` EXIT=1 whose only non-ok lines were Unclassified-card warnings. Fix is a scoped change to the check's exit-code logic, but the exact set of conditions that stay hard-blocking is an owner call (it changes gate semantics)."
created: 2026-07-20
created_by: claude
last_refined: 2026-07-20
vision_facet: "Continuity core"
tier: small
type: bug
parallel: safe
phase: converge
surface: "`horus close --check` verdict/exit-code logic (the pre-merge freshness gate that the `gh pr merge` interceptor keys on) — the Unclassified-card finding should be advisory, not exit-failing."
---

# close --check hard-blocks merge on Unclassified cards (should be advisory)

## Why — demonstrated, 2026-07-20 (pbi-ecosystem)

A merge with **fully fresh continuity** was blocked by the pre-merge gate. The complete
`horus close --check` output:

```
[ ok ] dashboard lanes are fresh (NEXT + focus authored, lanes updated this session)
[warn] backlog card '…' is Unclassified — run backlog-refine before scheduling   ×5
[ ok ] canonical continuity covers all product commits
[ ok ] no parallel deliveries detected
[ ok ] working tree clean
[ ok ] local commits pushed to upstream
Stale — … EXIT=1
```

Every **freshness/continuity** condition — the gate's actual job — is `[ok]`. The *only*
thing forcing `EXIT=1` (and thus the `gh pr merge` block) is five `[warn]` lines about
cards being *Unclassified*. The merge only completed via an owner-authorized bypass
(local merge to `main` + push; the interceptor only catches `gh pr merge`).

## Why this is wrong, not just strict

- The gate's documented purpose is continuity/dashboard **freshness** — the hook's own
  rationale is *"the dashboard would not reflect this work once it lands on main."* That is
  fully satisfied above.
- "Unclassified" is a **scheduling-readiness** state produced by `backlog-refine`, which is
  **explicitly owner-gated and never runs autonomously**. So the gate makes a *deferrable,
  owner-gated planning step* a **hard precondition for delivery**.
- Cards are routinely **created during delivery to defer triage** (this very session created
  several). Coupling "no untriaged cards" to "can merge" means you cannot land *any* work
  while *any* card is unrefined — backwards, and self-contradictory with refine being deferrable.

## What to change

- Treat Unclassified-card findings as **advisory**: keep the `[warn]` line (it's useful), but
  it must **not** set a non-zero exit / block merge.
- Reserve `close --check` non-zero (and the `gh pr merge` block) for genuine freshness
  failures: dashboard stale, continuity does not cover all product commits, dirty tree,
  unpushed commits, or an unaccounted parallel delivery.
- Owner decision embedded here: confirm that list is the complete set of hard-block
  conditions, and whether any card-state (e.g. a card marked `blocking`) should ever
  hard-fail — default proposal is "no card-readiness state blocks merge".

## Acceptance

- With ≥1 Unclassified card but all freshness conditions met, `horus close --check` exits 0
  and `gh pr merge` proceeds; the Unclassified cards still print as advisory warnings.
- A genuinely stale continuity (e.g. a delivery commit not covered) still exits 1 and blocks.
- Gate: full suite green on the exact SHA. Probe: reproduce the 2026-07-20 state (fresh
  continuity + an unclassified card) and confirm the merge is no longer blocked.

## Source

Observed by the claude-work session working in `pbi-ecosystem`, 2026-07-20, while merging
the continuity-consolidation + kickstart-E2E PRs. Filed from that session's direct context.
