---
status: shelved
shelved_on: 2026-08-01
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-28
refine_passes: 2
readiness: ready
autonomy: attended
order: 10
phase: converge
type: feature
tier: medium
parallel: safe
vision_facet: "Introspection & self-improvement"
surface: ".claude/skills/backlog-refine/SKILL.md + .agents/ parity (the lens), .claude/skills/scope-cards/SKILL.md + parity (authors the tags at creation), horus/skills.py (bundled text + version bumps), horus/backlog.py (tolerate + expose refine_passes), the backlog-librarian skill (stalled-card check)"
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

## What to build — ONE lens, TWO axes (widened 2026-07-28)

The lens is the same shape on two different axes. Both ask "contingent or intrinsic?" — is
this state forced by the card's nature, or only by a missing decision?

### Axis 1 — the `attended` axis (original scope)

For every card that would be `attended`, force **"contingent or intrinsic?"**

- **Contingent-attended** — attended only because a decision, an unknown, or a deterministic
  acceptance is missing. Front-loadable: resolve it in the pass → promote to `eligible`.
- **Intrinsic-attended** — irreversible blast radius, taste/UX judgment, or verification that
  cannot be made deterministic. Not front-loadable.

The biggest lever is a **deterministic acceptance gate**: "the owner eyeballs it" is the usual
hidden reason a card is attended.

### Axis 2 — the `shaping` axis (owner, 2026-07-28)

For every card that stays `shaping`, force the same question about its **listed open
decisions**, tagging each one:

- **`[refine]`** — answerable in a screening exchange. Editorial (wording, placement) or
  parametric (a default value, a threshold).
- **`[session]`** — needs a working session. Strategic or architectural (where does the token
  live; invest-in-parity or steer-to-WSL; which mechanism).

**A card whose open decisions are ALL `[session]` leaves the screening pool.** Its
`readiness_reason` names the session it needs, and refinement stops re-deriving that
conclusion at the cost of one exchange every pass. That is the actual saving.

The owner's phrasing of the discriminator, which should survive into the skill text:
*"what decisions would move this card to Ready, if any? If there aren't any, it probably needs
its own session and shouldn't be part of the pool anyway."*

### Why NOT a new section (evidence, 2026-07-28)

The obvious fix — "give cards a decisions-pending section" — was measured and rejected:
**30 of 36 Shaping cards (83%) already have one**, 17 under the literal heading
`## Open decisions for backlog-refine`, authored at creation and addressed to the refine pass.
Conversion was still 1 in 13. So the structure is not missing; the **classification** of what
is in it is. This card types the existing section rather than adding another one.

Per the repo's own rule — grep the existing vocabulary before proposing a new field or state —
no new readiness state is introduced either. `shaping` is already defined as "active owner/LLM
work remains: brainstorm, research, scoping… the reason names that next action"; that covers
needs-a-session. What was missing is that the reason was not *required* to say which kind.

### The counter — `refine_passes`

An integer in card frontmatter, incremented each refinement pass, that makes
"screened N times, never moved" **deterministic** instead of a felt impression.

Justification for a new field, against this repo's own bar (*one field with a consumer beats
four fields with none*): nothing existing records it. `last_refined` **overwrites**, so three
passes look like one, and a pass that changes nothing leaves no trace at all — which was true
of 56 cards in the 2026-07-28 pass. Git history cannot fill the gap for the same reason.

Two named consumers, required on day one:

1. **This skill** — reads it, and after N passes without movement asks the axis-2 question
   directly rather than re-screening.
2. **`backlog-librarian`** — a stalled-card check: *screened N times, never moved.*

Additive and optional, like `last_refined`; the backlog parser must tolerate its absence
(verified 2026-07-28: it already does).

## Acceptance

- `backlog-refine`'s per-card screen forces the contingent-vs-intrinsic question on BOTH axes,
  and the readiness contract requires a `[refine]`/`[session]` tag on each listed open
  decision.
- A card whose open decisions are all `[session]` is recorded as out of the screening pool,
  with `readiness_reason` naming the session it needs.
- `scope-cards` authors the tags when it first drafts a card, so the classification exists
  before the first refinement pass rather than being retrofitted.
- `refine_passes` is read by this skill and by the backlog-librarian stalled-card check; a
  card missing the field behaves exactly as today.
- Both agent projections match (Claude + `.agents/`), and each edited skill's version is
  bumped — an unbumped text change leaves committed projections silently stale.
- Gate: full suite green on the exact SHA. Probe: run one live `backlog-refine` pass and
  confirm a `[session]`-only card is parked rather than re-screened, and that `refine_passes`
  increments on the cards it touched.

## Guardrails

- Do NOT manufacture determinism — a fake gate (mocked tests blessing nonexistent
  flags) is worse than an honest `attended`. Taste and high-irreversible-risk cards
  stay attended by design.
- Goal is "don't leave a card attended *merely* from a lazy acceptance," not
  "maximise eligible."

## Open decisions

- Exact checklist wording, and where in the flow it sits (inside the per-card questionnaire,
  or a closing sweep). [refine] — editorial; settle while editing the skill.
- Whether it amends the skill's Ready-contract text or adds a separate lens section.
  [refine] — editorial.
- Seeding `refine_passes` on existing cards. [refine] — **settled 2026-07-28**: seeded as a
  floor, not a history — 2 where the card already had a `last_refined`, else 1. Exact prior
  counts are not recoverable and are not worth reconstructing.

No `[session]`-class items remain, which is why this card converted to Ready in the same pass
that produced the axis-2 idea.

## Source

In-session process discussion, 2026-07-21, generalised from the pass's
attended-vs-eligible calls. Axis 2 + the counter: owner, 2026-07-28 refine pass. Related:
`delegation-rubric`, `execution-decision`, `dispatch-decision` (the autonomy/verification
calibration they encode), and `wildcard` (the same lens applied to pathfinder). Skill targets:
`.claude/skills/backlog-refine` and `.claude/skills/scope-cards`.

## Reviews

- 2026-07-28 — **Shaping → Ready (attended); widened to two axes plus a pass counter**
  (owner, refine pass). Three things happened.

  **The lens earned its evidence.** It was applied informally to three cards in this live pass
  (`account-login-verb`, `windows-native-horus-setup`, `merge-release-owner-gate` — all
  intrinsic, for stated reasons) and it sharpened how each was argued rather than merely
  labelled. That was the missing evidence; its remaining open items are editorial only.

  **The owner widened it.** Observing that repeated passes leave cards in Shaping, they
  proposed a pass counter and a "what decisions would move this to Ready, if any?" question.
  Tested against this pass's 13 decisions before adopting: conversion correlates with the
  **kind** of open item (editorial/parametric convert; strategic/architectural do not, and
  should not), not with whether a decisions section exists — 83% already have one.
  `merge-release-owner-gate` is the proof: the best-structured card in the repo, with an
  explicit "Open design questions (why this is Shaping, not Ready)" section, and it correctly
  went to a dedicated session anyway. So the fix types the existing section instead of adding
  a new one.

  **Attended is intrinsic here**, not conservatism: this is a bundled-skill text change whose
  quality is judged by reading it, and the repo's standing rule is render-and-confirm a
  contract change before merging rather than remembering to.

  Ordered `10` in the Ready—Attended queue, ahead of `telegram-group-project-topics` (20):
  it is small, its open items are editorial, and it improves the very next refinement pass —
  a force multiplier ahead of a feature.
