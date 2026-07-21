---
status: open
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "Agreed as a skill upgrade; the exact checklist wording and where it sits in the backlog-refine flow need drafting. Explore, then draft the skill-text change."
phase: explore
type: feature
vision_facet: "Introspection & self-improvement"
---

# refine-autonomy-hardening-lens — force "contingent vs intrinsic" on every attended card

## Why — owner, 2026-07-21

During the 2026-07-21 refine pass we noticed cards land `attended` for two very
different reasons, and only one is fixable:

- **Contingent-attended** — attended *only* because a decision, an unknown, or a
  deterministic acceptance is missing. Front-loadable: resolve it in the pass →
  promote to `eligible`.
- **Intrinsic-attended** — attended by nature: high/irreversible blast radius,
  taste/UX judgment, or verification that can't be made deterministic. Not
  front-loadable (though blast-radius can be mitigated by moving safety into
  code + tests).

Today the eligible/attended call is a gut judgment. Making it a checklist would
systematically widen the autonomous-eligible pool *without* lowering the bar.

## Rough shape (open)

Add a lens to `backlog-refine`: for every card that would be `attended`, force the
question **"contingent or intrinsic?"** If contingent, name the ONE thing to
front-load — the decision to make now, the unknown to pin, or the deterministic probe
to write — that would promote it to `eligible`. The biggest lever is a **deterministic
acceptance gate**: "the owner eyeballs it" is the usual hidden reason a card is
attended.

## Guardrails

- Do NOT manufacture determinism — a fake gate (mocked tests blessing nonexistent
  flags) is worse than an honest `attended`. Taste and high-irreversible-risk cards
  stay attended by design.
- Goal is "don't leave a card attended *merely* from a lazy acceptance," not
  "maximise eligible."

## Open questions

- Exact checklist wording + where in the flow (inside the per-card questionnaire, or a
  closing sweep?).
- Does it amend the skill's Ready-contract text, or just add a lens?

## Source

In-session process discussion, 2026-07-21, generalised from the pass's
attended-vs-eligible calls. Related: `delegation-rubric`, `execution-decision`,
`dispatch-decision` (the autonomy/verification calibration they encode), and `wildcard`
(the same lens applied to pathfinder). Skill target: `.claude/skills/backlog-refine`.
