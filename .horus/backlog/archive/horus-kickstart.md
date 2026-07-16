---
status: shipped
priority: medium
created: 2026-07-17
vision_facet: "PO lifecycle"
phase: explore
tier: sonnet
type: feature
parallel: safe
surface: new thin orchestrator skill composing market-scan + deep-research + horus consolidate; PRD Vision (facet-diff); backlog cards (proposals)
depends-on: market-scan-skill (building block)
relates-to: roadmap-convergence, explore-converge-lifecycle
shipped_pr: 285
shipped_sha: 653f982
---

# horus-kickstart — one guided divergence→convergence re-baseline (also the onboarding path)

**Why (owner, 2026-07-17):** a fresh release ships the convergence machinery but it is
**inert on existing projects** — the read-out is silent without a `## Vision` facet table,
and existing cards carry no `vision_facet`. Onboarding today is hand-work (author facets,
stamp cards). This card is the assisted path that closes that gap AND delivers the owner's
capstone use case: on a project that already has Horus (but not this fresh version), trigger
one flow that re-baselines it.

Marked **`phase: explore`** on purpose — it is a divergent bet on a capstone ritual; it
proves out through real use before promotion (dogfooding the breathing model it implements).

## The flow (each step PROPOSES; the owner decides at every gate)

1. **Introspect** — read the repo + PRD/`.horus/` (current Vision/facets, backlog, shipped).
2. **Market-scan** — run `market-scan` for "where are we now" (outward), respecting the
   shipped ledger so it never re-proposes delivered work.
3. **Propose divergence directions** — a few directions to explore, as a **facet diff**
   against the existing set (add / rename / retire / promote-proven-exploration), NEVER a
   wholesale replacement.
4. **Propose backlog cards** — one per direction, exploratory ones as `phase: explore`.
5. **Propose execution order** — a suggested sequence (dependencies + owner priorities).
6. → **Owner decides** what to explore → fresh backlog to start/continue.
7. **Later: converge** — run the `horus consolidate` read-out, trim the fat, continue
   (re-run kickstart or go ad-hoc until a re-baseline is needed again).

## Acceptance (scoped)

- A **thin orchestrator skill** that SEQUENCES existing skills (`market-scan`,
  `deep-research`, the `horus consolidate` read-out) and pauses for owner approval at every
  gate. Not a monolithic auto-runner; not new roles/multi-file ceremony.
- **Advisory / diff-only:** proposes diffs to Vision + backlog; never auto-applies. Vision
  and backlog are the load-bearing artifacts — reversibility is git; the flow only hands over
  a proposal.
- **Facet diff, not replace:** reconciles proposals against the existing facet set so a
  re-run does not thrash continuity.
- **Onboarding folds in:** on a project with no facet table, step 3 proposes the initial
  facets (from repo + research) and offers to stamp existing cards — this IS the assisted
  onboarding, no separate migration.
- **Token envelope up front** (fans out research): state and confirm the spend before web work.
- Works on v3 (PRD) and v2 (six-lane) projects; onboarding = upgrade CLI + author facets +
  stamp cards (card fields are additive/forward-read, so no min-version bump is needed just
  to read them).

## Notes

- Build after `market-scan` (its core building block, now delivered).
- Open question to resolve during build: how much of the ordering/facet-diff logic is
  deterministic CLI signal vs agent judgment — lean CLI for signals, agent for judgment,
  consistent with the existing architecture.
