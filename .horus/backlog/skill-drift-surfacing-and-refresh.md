---
status: open
priority: low
created: 2026-07-17
last_refined: 2026-07-19
tier: medium
type: bug
vision_facet: "Introspection & self-improvement"
parallel: safe
surface: horus/skills.py (skill_findings, missing_or_stale, _skill_nudge in cli.py), launch/resume preflight, fleet/status projections
---

# Skill drift across installed projects — surfacing and refresh

When the CLI ships new or updated bundled skills, already-onboarded projects keep
stale copies (and miss newly added skills) silently. The detection primitives exist —
`skills.skill_findings` reports missing / outdated / unversioned-marker skills, and
`missing_or_stale` feeds the `_skill_nudge` tip trailer — but they do not propagate to
where anyone acts:

- The nudge is a passive one-line `tip:` after routine commands that lists every
  bundled skill name without distinguishing "not installed" from "outdated"; it reads
  as an ad and is easy to ignore.
- The launch/resume path does not check at all: a session can be launched in a mode
  whose posture skill is not installed and the mode silently degrades.
- There is no fleet-wide view: after a CLI upgrade, nothing tells the owner which of
  the N registered projects are behind. Only a per-project `horus doctor` shows it,
  and nothing prompts running doctor after an upgrade.
- Two refresh paths are advertised in different findings (`horus upgrade-project
  --apply --target X` vs `horus skill install --target X`); which is canonical is
  unclear.

**Evidence (2026-07-17, horus-agent):** a session was launched in `inline-batch` mode
(the launch-mode skill shipped in PR #307 / v0.0.60) but `inline-batch-session` was not
installed in the project, so the mode's posture instructions were silently absent. A
manual `horus skill install --target claude` then created 9 missing skills and updated
4 stale ones (horus-execution v13, delegation-rubric v8, execution-decision v3,
dispatch-decision v3) — none of which had surfaced as an actionable warning in the
normal resume/consolidate/close flow.

## Acceptance (draft — to be refined)

- After a CLI upgrade, skill drift in registered projects is visible from one place
  (fleet/status/doctor summary or an upgrade-time report), not only via per-project
  doctor runs nobody is prompted to make.
- Launching a session in a mode that depends on a skill warns (or refuses) when that
  skill is missing or stale in the target project.
- One canonical, sanctioned refresh command; the two current suggestions are
  reconciled.
- Customized or unversioned skill files are never silently overwritten (preserve the
  current `--force` semantics).

## Boundaries

- Owner sized this medium/low as a bug; scope and refine in a dedicated horus-harness
  session before implementation — this card records the gap, not the design.
- Detection logic already exists; prefer routing/surfacing existing findings over new
  scanning machinery.
- No auto-refresh without an explicit owner-visible step; skills live in project repos
  and changes must go through each project's normal commit flow.
