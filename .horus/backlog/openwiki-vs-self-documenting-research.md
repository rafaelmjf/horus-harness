---
status: open
priority: medium
tier: sonnet
type: task
created: 2026-07-12
created_by: overseer
parallel: true
surface: research/, capability-catalog (capabilities.py)
shipped:
---

# Research: OpenWiki vs. our self-documenting capability catalog

**Owner ask (2026-07-12):** OpenWiki just released; from the owner's understanding it
also aims to run *in a codebase and self-document it* — overlapping our self-documenting
capability-catalog direction (`capabilities.py` per-project vision/shipped extraction,
the `capability-catalog-*` cards). Do a scoped research comparison and recommend
adopt-now vs. skip-but-watch.

## Scope (research + a written recommendation — web-grounded, do NOT fabricate)

1. **What OpenWiki actually is** — its goal, how it runs in a codebase, what it produces
   (docs? a wiki? a queryable model?), how it stays current, its license/hosting model,
   and its maturity (just-released → weigh accordingly). Cite sources.
2. **Compare against ours** — the Horus capability catalog + PRD-continuity self-documenting
   approach: what each does better, where they overlap, what OpenWiki would ADD that we
   lack today (and vice-versa), and integration cost/fit if adopted.
3. **Recommendation** — one of: (a) adopt/integrate now (name the concrete value + the
   card it would spawn), (b) **skip but watch** (name the trigger/signal that would make
   it worth revisiting), (c) not a fit (why). Respect the fleet boundary: we adopt
   optional external capabilities at a fit gate, we don't grow a competing doc engine
   speculatively.

## Deliverable

A `research/openwiki-comparison-2026-07.md` note with the findings + recommendation, and
(if adopt/watch) a follow-up card or a named revisit trigger. No code change in this card.

## Verification

Research note exists with sourced findings + an explicit adopt/skip/watch recommendation;
overseer reads it and records the decision. (Research card — no CI-testable surface.)
