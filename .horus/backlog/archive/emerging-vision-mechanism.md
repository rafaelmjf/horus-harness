---
status: shipped
priority: high
readiness: shaping
autonomy: attended
created: 2026-08-12
created_by: owner
type: feature
topic: backlog-model
parallel: safe
tier: medium
surface: "horus/routines.py (consolidate read-out + Vision block), .horus/PRD.md (## Vision), horus/templates.py (PRD template)"
depends-on: retire-facets-for-topics
shipped_pr: 506
shipped_sha: 9ee4e53957dc36ef64e7dbf5fd7ecfa7881f8594
---

# emerging-vision-mechanism — make the Vision an emergent section, the way topics are

## Why

Retiring facets (`retire-facets-for-topics`) removes the frozen middle layer: cards no longer
name a `vision_facet` from a closed set with an authored definition-of-done. But the Vision
itself should not become a hand-frozen paragraph either — it should **emerge from what has
actually shipped**, the same pattern topics use one level down. Topics emerge from cards;
the Vision's proven directions emerge from topics.

The old model had one graduation step (topic → facet). The new model keeps a graduation, but
moves it up and makes it *descriptive, not contractual*: a topic that accumulates real shipped
delivery surfaces in the Vision as a **proven direction** — reported from delivery evidence,
never gated by a definition-of-done authored up front.

## The mechanism (to define with the owner, then build)

The `## Vision` section becomes two parts:

1. **Seed (hand-authored, stable).** The north star that does not move with delivery: what
   Horus *is*, why it exists, the non-goals (solo owner-operator; memory+planning plane, never
   orchestration). This is the current opening Vision prose, kept verbatim.
2. **Emergent directions (regenerated at `consolidate` from `topic_standings`).** Each topic
   that has crossed a delivery threshold (e.g. ≥N shipped cards — threshold is an owner knob)
   is rendered as a one-line direction: the topic name + a plain "where it stands" derived from
   its open/shipped counts. No DoD column. Topics below the threshold stay plain topics in the
   backlog read-out and do not appear in the Vision yet — they are exploration, not yet a
   direction.

Key differences from facets, to preserve on purpose:
- **No authored definition-of-done.** A direction reports delivery ("shipped X, N open"); it
  does not assert a finish line a card is measured against. This is what removes the
  authoring-cost-at-max-uncertainty problem the discussion card identified.
- **Descriptive graduation.** A topic becomes a direction because delivery happened, detected
  at consolidate — not by an owner promotion ceremony. Demotion is symmetric: a direction whose
  work all shelves recedes to a plain topic.
- **The seed is the only frozen prose.** Everything below it is regenerated, so it can never
  drift into the "facet reads converged because its cards were shelved" trap (PRD Rule,
  2026-08-03) — a direction with zero shipped simply is not rendered.

Open questions for the owner (shape before building):
- The delivery threshold: shipped-count, or "≥1 shipped AND owner-tagged"? Start simple.
- Regenerated block: fully machine-written, or seed + machine-suggested that the owner edits at
  consolidate? (Mirror whatever `topic_standings` does.)
- Does a discussion-card-only topic (a recorded decision, no work) ever become a direction? Likely
  no — a direction needs shipped delivery.

## For now — simulated Vision (what today's state would render as)

Illustrative only: the 8 current facets re-expressed as emergent directions, "where it stands"
in place of a definition-of-done. This is the shape to build toward, not a committed rewrite.

> **Horus** is a lightweight, repo-local **product owner** for official coding-agent CLIs. A
> PO's memory *and* rituals, repo-local so any native agent session can pick up the role. Built
> for one solo owner-operator; a memory + planning plane, never orchestration. *(seed — stable)*
>
> **Directions so far** *(emergent from topics with shipped delivery)*
> - **Continuity core** — proven and load-bearing: resume-from-durable-state ships and is the spine.
> - **Accounts & isolation** — mostly delivered; the last open thread is login-as-provisioning (shelved).
> - **Delegation calibration** — delivered and measured; first end-to-end dispatched release datum landed (v0.0.81).
> - **Autonomous dispatch** — the worker+supervisor loop ships; refinement cards remain.
> - **Introspection & self-improvement** — the audit skills ship; ongoing.
> - **Distribution** — `uv tool install` + hosted app track releases; ships.
> - **PO lifecycle** — partially shipped; discovery + convergence is the live frontier (this migration).
> - **Dashboard / cockpit** — *not rendered*: the hosted dashboard is unused; the live cockpit is the TUI.
>   (Exactly the case where a facet read "converged" on zero open cards — an emergent Vision omits it.)

Note the last line: the emergent model **automatically drops** the direction the frozen facet
table kept advertising. That is the whole point.

## Acceptance
- `## Vision` renders seed + emergent-directions block; the block is derived from
  `topic_standings`, not hand-maintained.
- A topic with zero shipped delivery does not appear as a direction.
- The threshold and machine-vs-assisted choice are owner-set, documented in `## Rules`.

## Source
Owner request 2026-08-12, extending `d-backlog-model-topics-over-facets` from "topics replace
facets" to "topics also drive an emergent Vision".
