---
status: open
priority: medium
readiness: ready
autonomy: eligible
readiness_reason: "Demonstrated live (2026-07-20), and the owner call it was waiting on is now made (2026-07-26): the hard-block set is the five freshness conditions, and no card-readiness state ever blocks merge. Acceptance is fully deterministic, so it no longer needs owner presence during execution."
created: 2026-07-20
created_by: claude
last_refined: 2026-07-26
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
- **Owner decision, made 2026-07-26:** those five conditions — dashboard stale,
  continuity does not cover all product commits, dirty tree, unpushed commits,
  unaccounted parallel delivery — are the **complete** hard-block set, and **no
  card-readiness state ever blocks merge**. A `blocking` card state was considered
  and declined: it would reintroduce planning state into a delivery gate, which is
  the defect this card exists to remove.

## Acceptance

- With ≥1 Unclassified card but all freshness conditions met, `horus close --check` exits 0
  and `gh pr merge` proceeds; the Unclassified cards still print as advisory warnings.
- A genuinely stale continuity (e.g. a delivery commit not covered) still exits 1 and blocks.
- Gate: full suite green on the exact SHA. Probe: reproduce the 2026-07-20 state (fresh
  continuity + an unclassified card) and confirm the merge is no longer blocked.

## Source

Observed by the claude-work session working in `pbi-ecosystem`, 2026-07-20, while merging
the continuity-consolidation + kickstart-E2E PRs. Filed from that session's direct context.

## Reviews

- 2026-07-26 — Refined with the owner. The embedded gate-semantics decision is now
  made (see "What to change"): the five freshness conditions are the complete
  hard-block set; no card-readiness state blocks merge; a `blocking` card state was
  considered and declined. With the decision closed the acceptance is fully
  deterministic — unclassified + fresh exits 0, an uncovered delivery still exits 1 —
  so autonomy moved **attended → eligible**. Note for sequencing: verify the
  verdict/exit-code surface against `codex-usage-stale-snapshot-gates-dispatch` and
  `project-registration-onboarding-gap` before running any of them in parallel;
  `routines.py` may be shared.
