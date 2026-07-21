---
status: open
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "Just captured as an idea; the skill's shape, triggers, output home/format, and whether it is Horus-specific or cross-project are all unscoped. Explore before drafting."
phase: explore
type: feature
vision_facet: "Introspection & self-improvement"
---

# decision-doc-skill — a skill that generates issue/solution decision documentation

## Why — owner, 2026-07-21

The structured decision doc this session produced (the mobile-access research receipt:
problem → considered approaches → trade-offs → comparison table → conclusion) is a pattern
the owner increasingly uses in their BI projects and wants available as a **repeatable
skill** — here, and possibly cross-project. It turns a messy exploration into a durable,
skimmable artifact: **identify the problem → analyse the options with consequences → land a
recommended solution + explanation.**

## Rough shape (open — just tracked for now)

Given a problem/decision under discussion, produce a consistent doc: Problem → Options
(with trade-offs) → Recommendation + rationale, optionally a comparison table. Likely lands
as a dated receipt (like the `research/` receipts) or a standalone doc.

## Open questions

- Position against existing surfaces so it is not a duplicate: `deep-research` (heavier,
  web-sourced), `market-scan`, and the research-receipt convention. This is *lighter* — a
  reasoning-capture / decision-doc aid, no web fan-out required.
- Horus-specific, or a general cross-project skill (owner uses the pattern in BI projects)?
- Trigger: owner-invoked only, or also offered when a discussion resolves into a decision?
- Output home + format; `vision_facet` provisional (skill/process capability — confirm).

## Source

In-session, 2026-07-21. The receipt `.horus/research/2026-07-21-mobile-agent-session-access.md`
is the worked example of the pattern this skill would generalise.
