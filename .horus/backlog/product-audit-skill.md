---
status: claimed
priority: medium
tier: sonnet
created: 2026-07-16
type: feature
parallel: safe
surface: new .claude/skills/product-audit (bundled via horus/skills.py), horus/cli.py (staleness signal), PRD frontmatter stamp
---

# Release-stamped product audit (signal + skill)

The owner's periodic self-audit of the product — is a feature used, is a ritual
ceremony, does a native platform now cover it — demonstrably works (six-lane
retirement, capabilities truth-layer reframe 2026-07-16) but fires only on mood.
Codify the *trigger* deterministically and the *questions* as a skill, per the
project's own architecture: CLI emits a staleness signal, the agent supplies
judgment.

## Acceptance

- A `last_product_audit` stamp (PRD frontmatter or equivalent) records the version
  at the last audit; `horus close`/`consolidate` print one advisory line when it is
  ≥5 releases or ≥30 days stale ("last product audit: vX, N releases ago"). No hook,
  no gate, never blocks anything.
- A bundled `product-audit` skill encodes the question set: (1) which Horus surfaces
  did the owner actually use since the last audit (evidence, not recall); (2) what
  have Claude Code / Codex shipped natively since then that overlaps a Horus surface
  (changelog check); (3) which rituals were skipped or felt like ceremony; (4) per
  finding, the verdict set is **demote / defer / retire / no-change only** — the
  audit can never propose new features.
- Running the audit updates the stamp; two consecutive no-change audits recommend
  lengthening the interval (anti-ceremony guard on the anti-ceremony tool).
- Tests cover the staleness computation and the advisory line; the skill content
  follows the bundled-skill sync/version pattern.

## Boundaries

- Advisory only, exactly like the delegation skills: it emits findings the owner
  acts on; nothing auto-archives or auto-demotes cards.
- Do not build command-usage telemetry for question (1) — the interview + integration
  -point grep method is the current rung; promote only if it proves insufficient.
