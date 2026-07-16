---
status: shipped
priority: medium
tier: sonnet
created: 2026-07-16
vision_facet: "PO lifecycle"
type: feature
parallel: safe
surface: new bundled skill (sibling to product-audit); composes deep-research; .horus/research/ receipt dir; horus-consolidate hand-off into PRD Vision + candidate cards
shipped_pr: 283
shipped_sha: 8fff2c625a7541a6a83cee9aa9a4f8e2f8df11c1
---

# market-scan — outward, evidence-first market/competitive research skill

The outward twin of `product-audit` (which audits our OWN surface): a lightweight,
owner-invoked skill for structured market/competitive research when **starting a new idea
or pivoting** an existing product. Fills a real ecosystem gap — the leading open skill
collections (obra/superpowers, mattpocock/skills) are all inward-facing (spec/build) and
none offers a lightweight outward research skill (research receipt:
`.horus/research/2026-07-16-po-capabilities.md`).

**Ethos guard:** thin orchestration + a dated receipt. COMPOSES the existing `deep-research`
harness for fan-out/verify/citations — never rebuilds search. Advisory only: proposes Vision
text + candidate cards; the owner accepts them. Not continuous monitoring (that's the
commercial SaaS category — out of scope).

## Acceptance (scoped minimal subset)

- Bakes in exactly the outward trio + one capped check:
  1. **JTBD hypothesis** — "When [situation] I want [motivation] so I can [outcome]" +
     current alternatives (framed as hypothesis-to-validate; a skill can't run interviews).
  2. **Competitive teardown grid** — 3-6 named rivals × {does well / gap / positioning /
     price}, each row evidence-backed by a fetched URL.
  3. **PR-FAQ vision paragraph** — 1 para "the headline is…" + 3-5 hard FAQ questions.
  4. **Market-size sanity** — ONE sentence (big enough / saturated?), hard-capped.
- Output is a dated repo-local receipt `.horus/research/YYYY-MM-DD-<slug>.md` (mirrors the
  `.horus/audits/` convention) with: trigger (new-idea|pivot), JTBD, alternatives, teardown
  grid, prior-art verdict (green/yellow/red), Vision draft, open questions, market-size line,
  candidate backlog items (each sourced to a specific gap), sources.
- Hand-off is advisory: Vision draft distills into PRD Vision via `horus-consolidate`;
  candidate items become candidate cards each traced to evidence. Never auto-writes Vision or
  auto-creates cards.
- Skill ships in the bundled `SKILL.md` format (+ optional `references/receipt-template.md`);
  bumps the skill version on any text change (per the bundled-skill-version rule).
- Deliberately OMITS: Wardley mapping, full Lean Canvas (optional appendix at most),
  multi-interview JTBD, continuous monitoring/scraping, any superpowers-style
  mandatory-invocation ceremony.

## Notes

- Token-intensive by nature (composes deep-research): the skill must state its research
  envelope and get owner confirmation before spending, per the grounding rule.
- Vision expansion has landed (Vision = repo-local product owner, PO-lifecycle facet), so this
  is no longer gated. Build order: after `roadmap-convergence` (the lower-risk, fully-in-repo
  card is going first); this one is the higher-leverage outward capability that follows.
