---
name: backlog-librarian
description: >-
  Produce one autonomous, zero-blast-radius hygiene digest for a card-backed
  Horus backlog. Use when the owner asks to inspect, clean up, or maintain a
  growing backlog; asks for duplicates, stale cards, broken cross-links,
  satisfied dependencies, or contradictory readiness/status; says "run the
  backlog librarian"; or schedules an unattended backlog-hygiene review. Reads
  every active card, proposes exact owner-reviewable actions in a dated receipt,
  and never edits, archives, claims, reprioritizes, or ships cards.
---

<!-- horus-skill-version: 1 -->

# Backlog librarian — one advisory hygiene digest

Maintain the existing set; do not create product direction. This is the curate
half of autonomous PO hygiene: a bounded review artifact, never autonomous
backlog mutation.

## Hard boundary

- Write exactly one receipt under
  `.horus/audits/<YYYY-MM-DD>-backlog-librarian.md`. If that path exists, use
  `-2`, `-3`, and so on; never overwrite a prior run.
- Print the complete receipt in the response too. A scheduled run therefore
  leaves both a tracked artifact and the normal run log.
- Never edit `PRD.md` or a card; never archive, claim, reprioritize, schedule,
  notify, commit, push, open/merge a PR, or implement a proposal. The caller or
  existing dispatch substrate owns delivery of the receipt.
- No web research, embeddings service, subagents, or extra model call. One
  bounded analysis pass over repository evidence only.

## Fixed defaults

- **Stale:** no evidenced touch for 8 weeks (56 days).
- **Suggested cadence:** one owner-authorized run every 4 weeks. This skill
  never arms its own schedule or recurring timer.
- **Touch date:** newest valid date among the card's `last_refined`, its latest
  git commit, and `created` (fallback). Do not treat a PRD mention or this
  librarian's own receipt as a card touch.
- **Semantic budget:** read every active card once, but semantically compare at
  most 25 candidate pairs after the cheap prefilter below. Report truncation and
  the selection rule if more than 25 pairs qualify.

An owner may explicitly override threshold or pair cap for one run; record the
override in Run facts. Do not invent persistent configuration.

## Evidence pass

1. Honor the repository instructions: fetch and verify the working branch
   against its remote before trusting local state. Read `PRD.md`, then run the
   read-only `horus consolidate` and `horus backlog --tree --json` signals.
2. Inventory every active `.horus/backlog/*.md` card. Read its complete
   frontmatter and body exactly once. Inventory archived card names plus
   lifecycle/provenance fields only; read an archived body only when an active
   card explicitly links to it and the relationship needs disambiguation.
3. Resolve each `depends-on` and `branch` value against both active and archived
   names. Split comma-separated dependency values; preserve the spelling shown
   in the source.
4. Determine last touch with targeted `git log -1 --format=%cs --
   <card-path>` calls plus the two card dates. A shallow clone or missing git
   history is unknown, not stale.
5. Build overlap candidates cheaply. Include exact normalized titles, and
   near-title pairs that share a `vision_facet` or `branch` plus at least two
   meaningful title terms. Add pairs where one card explicitly names the other.
   Rank exact titles, explicit mentions, same branch, then same facet; keep the
   first 25. Only now compare their full intent, outcome, boundaries, and source.

## Findings — evidence, never guesses

Classify only findings supported by a quoted field or a short body paraphrase:

- **Duplicate / overlap:** exact duplicate, one card subsumes the other, or two
  cards collide materially. Similar vocabulary alone is not a finding.
- **Stale:** the 56-day rule passed. Suggest review/defer/retire, never infer
  obsolescence from age.
- **Links:** dangling `depends-on`/`branch`; an explicit blocker or umbrella
  relationship described in prose but absent from structured fields; or a
  cross-link that names no existing active/archive card. Do not demand
  reciprocal links.
- **Satisfied dependency:** `depends-on` resolves to an archived shipped card
  (or other unambiguous shipped provenance), while the active card still
  presents it as a gate. Propose removing the dependency and re-evaluating
  readiness; do not claim the dependent card is ready.
- **State contradiction:** include deterministic readiness findings, terminal
  lifecycle states lingering in the active directory, Ready cards that still
  describe an unresolved gate, non-Ready cards without an actionable reason,
  and gated/deferred reasons contradicted by resolved repository evidence.

Use confidence `high|medium|low`. Omit low-confidence semantic suspicions from
the action list; place them in `Needs owner interpretation`. If two cards are
distinct, say why and do not report them as hygiene debt.

## Receipt

Write these sections in order:

1. `# Backlog librarian — <YYYY-MM-DD>`
2. `## Summary` — active/archive counts, finding counts by category, and one
   sentence naming the highest-value review.
3. `## Proposed actions` — table: ID | category | card(s) | evidence | exact
   proposed card diff/action | confidence. Concrete diffs are proposals only.
4. `## Needs owner interpretation` — bounded ambiguous cases, or `None`.
5. `## Clean checks` — explicitly name categories with no findings so silence is
   distinguishable from a skipped check.
6. `## Run facts` — threshold, effective date, branch/SHA, card counts, pair
   count/cap/truncation, commands/signals used, and evidence limitations.
7. `## Boundary` — “Advisory only; no cards or continuity were changed.”

Keep one row per underlying issue; cross-reference a row instead of duplicating
it across categories. Sort actionable rows: state contradiction, satisfied
dependency, broken link, duplicate/overlap, stale. If there are no actions,
still emit the receipt with a clean summary.

## Scheduling posture

A scheduled invocation is an ordinary unattended `horus run` whose prompt says
to use `backlog-librarian`; it remains subject to the existing exact account /
model / effort / envelope approval and usage gates. The receipt is the only
authorized work product. Do not add a daemon, recurrence engine, or librarian-
specific scheduler. Four weeks is guidance for the owner when arming a one-shot
run, not authority for this skill to arm the next one.

## v2 six-lane projects (fallback)

This workflow requires the v3 card-backed `.horus/backlog/` structure. If the
project has only `roadmap.md` and the retired six-lane files, stop with an
unsupported-structure explanation and write no receipt. Do not migrate the
project or reinterpret roadmap bullets as cards.
