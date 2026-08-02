---
name: product-audit
description: >-
  Periodic evidence-first INWARD alignment analysis of THIS project: read its
  delivered code and features against its own Vision — facets where the project
  defines them, the Vision's own claims where it does not — and report where the
  product actually stands: what drifted, what is on track, what is done. Use
  when `horus close` / `horus consolidate` print the product-audit staleness
  advisory, or when the owner asks "audit the product" or "where do we stand".
  Analysis and
  suggestions ONLY — it decides nothing: facet/branch verdicts belong to the
  convergence step (paired with a market-scan receipt), card proposals to
  scope-cards, and every archive/improve/ready decision to backlog-refine.
  The receipt lands dated under `.horus/audits/`.
---

<!-- horus-skill-version: 5 -->

# Product audit — the inward evidence step (analysis, never verdicts)

You are auditing **the project you are invoked in**, against **its own** Vision —
never the tooling that shipped this skill. `.horus/PRD.md` in this repository is
the subject; if you find yourself reading the surfaces of the harness that
installed this file instead of this project's, you have the wrong subject. The
CLI supplied only the deterministic trigger (the staleness advisory); you supply
the judgment. This audit is the INWARD half of the evidence base: its receipt
pairs with a market-scan receipt to feed the owner's convergence decisions. It
suggests; it never prunes, cards, or edits the Vision — and it does not issue
demote/defer/retire verdicts of its own (that "prune, never grow" verdict machine
decided too early and was retired; do not revive it).

**Initial stamp:** if no receipt exists under `.horus/audits/` for the stamped
audit, treat this run as the first real audit: widen every "since the last
audit" question to the whole live surface instead of the stamp window.

## Pin the subject before gathering evidence

1. **The Vision's units.** Use the facet table in `PRD.md` if the project has
   one; else the distinct `vision_facet` values carried by its backlog cards;
   else the Vision's own structural claims (its differentiators, product
   boundary, and out-of-scope lines). Say in the receipt which of the three you
   used — a project without facets is audited against what its Vision actually
   claims, never against a roster you invented for it.
2. **The reference surfaces** — where a delivered surface WOULD be mentioned in
   *this* project if anything used it: its entry points (CLI verbs, API routes,
   exported modules), user- and agent-facing docs, CI config, tests, examples.
   Derive them from the repository; name them in the receipt so the next audit
   reuses the list.
3. **The overlap sources** (for evidence 2 below) — 3-6 named upstreams whose
   releases could subsume something this project delivers: the platform it
   builds on, the ecosystem's dominant tools, a direct competitor. Read them
   from the Vision, the Rules, or the previous receipt; if undeclared, ask the
   owner to name them, and record them in the receipt so they are declared from
   then on. Do NOT open-endedly sweep the web for candidates — a bounded, named,
   reusable list is the contract. Special case: when the project under audit is
   itself an agent harness or agent-facing tooling, those sources are the agent
   CLIs' own changelogs.

## Evidence (gather, not recall)

1. **Usage.** Which surfaces did the owner *demonstrably* use since the last
   audit? Evidence: `.horus/` artifacts, git history, machine-local state, a
   short owner interview — plus grepping the reference surfaces pinned above
   for surfaces nothing references. A command referenced only by its own
   implementation counts as unreferenced — but programmatically-wired plumbing
   greps false-negative; treat the grep as a signal, never a verdict. No usage
   telemetry, ever.
2. **Native overlap.** What have the pinned overlap sources shipped since the
   stamp that overlaps a surface this project delivers? Check their changelogs
   and release notes; cite version and date for every claim.
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
3. **The Vision's units — ONE consolidated table**: unit | in plain terms |
   standing (with evidence) | distance to done | drift? | open/shipped card
   counts. One row per unit, using whichever ladder rung you pinned above; do
   not split roster and detail into separate structures.
4. **Vision branches — same consolidated form** (branch | in plain terms |
   standing | open question), when the backlog carries vision-branch
   umbrellas. Omit the section entirely when it does not.
5. **Per-unit detail** — definition of done restated where the project states
   one, what concretely stands, distance, drift called out separately; depth
   matches the previous accepted receipt for this project, not a bullet skim.
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
  only after the owner accepts the receipt. The stamp belongs to the project
  being audited — write it into *this* repository's `PRD.md`, whatever project
  that is. It records that this project was audited, so a real audit here must
  never be left unstamped.
- Suggestions land through their routed step — never act on them here.
- **Anti-ceremony guard:** read the previous receipt; if it and this audit
  are both all-aligned with no suggestions, recommend lengthening the audit
  interval — and note that the interval should weigh releases AND elapsed
  days (releases alone nag during rapid iteration).

