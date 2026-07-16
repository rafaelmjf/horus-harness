---
name: product-audit
description: >-
  Periodic evidence-first audit of the Horus product surface itself: which
  surfaces the owner actually used since the last audit, what Claude Code /
  Codex now cover natively, and which rituals became ceremony. Use when
  `horus close` / `horus consolidate` print the product-audit staleness
  advisory, or when the owner asks "audit the product", "what should we
  retire", or "is this feature still earning its keep". Advisory only: every
  verdict is demote / defer / retire / no-change — this audit can never
  propose new features, add telemetry, or auto-archive anything.
---

<!-- horus-skill-version: 1 -->

# Product audit — prune, never grow

You are auditing Horus itself, not a target project. The CLI supplied only the
deterministic trigger (the staleness advisory); you supply the judgment.

## Questions (evidence, not recall)

1. **Usage.** Which Horus surfaces did the owner *demonstrably* use since the
   last audit? Evidence means shell history the owner shows you, `.horus/`
   artifacts, git history, and a short interview — plus grepping the
   integration points (hooks, skills, TUI bindings) for surfaces nothing
   references. Do NOT build or propose command-usage telemetry; the
   interview + integration-point grep is the current rung.
2. **Native overlap.** What have Claude Code and Codex shipped natively since
   the stamped version that overlaps a Horus surface? Check their changelogs /
   release notes. A surface a host app now covers is a demote/retire candidate.
3. **Ceremony.** Which rituals were skipped, rubber-stamped, or felt like
   ceremony? A step everyone bypasses is evidence against the step, not the
   people.

## Verdicts — the only four

Per finding: **demote** (weaker rung: instruction instead of code),
**defer** (revisit next audit, with the reason), **retire** (propose removal —
the owner acts; nothing auto-archives), or **no-change**. New features are out
of scope for this audit by construction.

## Close the audit

- Update the PRD frontmatter stamp: `last_product_audit: <installed horus
  version> <today YYYY-MM-DD>` (run `horus --version` for the version).
- Record verdicts in the existing continuity flow (PRD Rules/Backlog via the
  owner) — never in a new artifact created just for the audit.
- **Anti-ceremony guard:** if this and the previous audit were both all
  no-change, recommend the owner lengthen the audit interval (e.g. 10 releases
  / 60 days) — note it alongside the stamp.

## v2 six-lane projects (fallback)

The staleness advisory reads `PRD.md` frontmatter, so it never fires on a
six-lane project. The audit itself still applies: ask the same three questions,
use the same four verdicts, and record the stamp in `project.md` frontmatter so
it carries over when the project migrates to the PRD structure.
