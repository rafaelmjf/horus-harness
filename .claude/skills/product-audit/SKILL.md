---
name: product-audit
description: >-
  Periodic evidence-first INWARD alignment analysis of the Horus product
  itself: read the delivered code and features against the Vision facets and
  active vision branches, and report where the product actually stands —
  what drifted, what is on track, what is done. Use when `horus close` /
  `horus consolidate` print the product-audit staleness advisory, or when the
  owner asks "audit the product" or "where do we stand". Analysis and
  suggestions ONLY — it decides nothing: facet/branch verdicts belong to the
  convergence step (paired with a market-scan receipt), card proposals to
  scope-cards, and every archive/improve/ready decision to backlog-refine.
  The receipt lands dated under `.horus/audits/`.
---

<!-- horus-skill-version: 3 -->

# Product audit — the inward evidence step (analysis, never verdicts)

You are auditing Horus itself, not a target project. The CLI supplied only the
deterministic trigger (the staleness advisory); you supply the judgment. This
audit is the INWARD half of the evidence base: its receipt pairs with a
market-scan receipt to feed the owner's convergence decisions. It suggests; it
never prunes, cards, or edits the Vision (contract corrected by the owner
2026-07-20 — the v2 "prune, never grow" verdict machine decided too early).

**Initial stamp:** if no receipt exists under `.horus/audits/` for the stamped
audit, treat this run as the first real audit: widen every "since the last
audit" question to the whole live surface instead of the stamp window.

## Evidence (gather, not recall)

1. **Usage.** Which surfaces did the owner *demonstrably* use since the last
   audit? Evidence: `.horus/` artifacts, git history, machine-local state
   (schedule ledger, envelopes, datums, notify config), a short owner
   interview — plus grepping the integration points (managed blocks, hook
   templates, TUI, dashboard, bundled skills, `scripts/`) for surfaces nothing
   references. A command referenced only by its own implementation counts as
   unreferenced — but programmatically-wired plumbing greps false-negative;
   treat the grep as a signal, never a verdict. No usage telemetry, ever.
2. **Native overlap.** What have Claude Code and Codex shipped natively since
   the stamp that overlaps a Horus surface? Check changelogs/release notes.
3. **Ceremony.** Which rituals were skipped, rubber-stamped, or nagged? A step
   everyone bypasses is evidence against the step, not the people.

## The receipt — fixed spine, written for a no-context reader

`.horus/audits/<YYYY-MM-DD>-product.md`. The structure is deliberately
semi-deterministic: multiple non-deterministic runs must converge to the same
core reading, so that a summary that "feels off" to the owner is itself a
drift signal pointing at the inputs. Write every section for a reader with
NO prior context — plain-language explanations first; insider terms and PR
numbers only as supporting references. Sections, in order:

1. **What this document is** — the decides-nothing contract, two lines.
2. **The product, in plain terms** — the delivered thesis as it stands NOW
   (not the Vision text restated), including structural findings the window
   produced.
3. **Facets — ONE consolidated table** (owner calibration 2026-07-20): facet |
   in plain terms | standing (with evidence) | distance to done | drift? |
   open/shipped card counts. One row per facet; do not split roster and
   detail into separate structures.
4. **Vision branches — same consolidated form** (branch | in plain terms |
   standing | open question).
5. **Per-facet detail** — DoD restated, what concretely stands, distance,
   drift called out separately; depth matches the accepted 2026-07-20
   receipt, not a bullet skim.
6. **Triage** — three explicit buckets: done or almost done / on track /
   drifted.
7. **Ceremony observations.**
8. **Routed suggestions table** — every suggestion names the step that
   decides it (backlog-refine | convergence step | scope-cards | existing
   card). Nothing is decided in this receipt.

In an interactive session, paste the receipt's formatted content into the
terminal — the owner reviews it in the reply, not by opening the file. End by
offering: dive deeper into ONE named topic from the receipt, or proceed.

## Close the audit

- Update the PRD stamp `last_product_audit: <horus version> <YYYY-MM-DD>`
  only after the owner accepts the receipt.
- Suggestions land through their routed step — never act on them here.
- **Anti-ceremony guard:** read the previous receipt; if it and this audit
  are both all-aligned with no suggestions, recommend lengthening the audit
  interval — and note that the interval should weigh releases AND elapsed
  days (releases alone nag during rapid iteration).

## v2 six-lane projects (fallback)

The staleness advisory reads `PRD.md` frontmatter, so it never fires on a
six-lane project. The analysis still applies: same evidence, same spine with
`project.md` prose standing in for the facet table; record the stamp in
`project.md` frontmatter so it carries over on migration.
