---
status: open
priority: medium
readiness: ready
autonomy: attended
created: 2026-07-28
created_by: owner
last_refined: 2026-07-28
refine_passes: 1
vision_facet: "Introspection & self-improvement"
tier: low
type: chore
parallel: safe
phase: converge
surface: "horus/skills.py (add a `_WILDCARD_SKILL` text constant + `Skill(\"wildcard\", 2, _WILDCARD_SKILL)` in the SKILLS list, ~line 2876), tests/test_skills.py, .claude/skills/wildcard/SKILL.md + .agents/skills/wildcard/SKILL.md (become GENERATED output — stop hand-editing them). Report any file touched beyond this list and why."
---

# bundle-test-phase-skills — a skill in test phase lives outside the generator, unprotected

## Why — measured 2026-07-28

A skill under test is authored as a hand-maintained projection pair
(`.claude/skills/<name>/SKILL.md` + `.agents/` twin) before it is registered in
`horus/skills.py`. In that state it is outside every guarantee the bundled set has:

- **No version-aware install.** `skills.py` classifies a skill as installed / outdated /
  missing / unversioned against the bundled version. An unbundled skill is invisible to
  that machinery, so `horus skill install` and `horus doctor` cannot see it, and
  `horus skill map` cannot report it stale across the fleet.
- **The version rule does not protect it.** The PRD Rule reads "**Bundled** skill edits
  bump the skill version, always" — an unbundled pair has no such guard, so the two
  copies can silently diverge. Parity today is intact, but only because it was checked by
  hand during this session.
- **No test coverage.** `tests/test_skills.py` iterates `skills.SKILLS`; an unbundled
  skill is in no assertion at all.
- **No fleet projection.** It reaches exactly one machine — the one it was written on.

**Current scope is exactly one skill.** Measured 2026-07-28: 18 of 19 projected skills are
bundled; `wildcard` (v2) is the only one that is not. Its `.agents/` parity was verified
identical the same day. So this card is concrete rather than speculative, and small.

**A live consequence, already hit.** The `skill-audit` skill instructs "never edit the
projected `SKILL.md` copies directly — they are regenerated." That is true for bundled
skills and **false for `wildcard`**, whose projections *are* the source. The 2026-07-28
audit had to improvise past that instruction (recorded there as finding F9). Registering
`wildcard` removes the exception rather than documenting it.

## How

1. Move the v2 text into `horus/skills.py` as a `_WILDCARD_SKILL` constant and add
   `Skill("wildcard", 2, _WILDCARD_SKILL)` to `SKILLS`, keeping the version marker at the
   value the audit set (**2**), so already-installed copies are recognised as current
   rather than re-written.
2. Regenerate both projections from the constant and confirm they are byte-identical to
   what is on disk today — a clean no-op diff is the proof the move preserved the text.
3. Extend `tests/test_skills.py` so the bundled set covers it like any other skill.
4. Verify with `horus skill install --force` and confirm `wildcard` reports `installed`
   at v2, not `unversioned` or `outdated`.

## Acceptance

- `wildcard` appears in `skills.SKILLS` at version 2; `horus skill install` / `doctor` /
  `skill map` all see it.
- Regenerating produces no diff against the current on-disk projections.
- Both agent projections stay byte-identical, and the generator is the single writer.
- Gate: full suite green on the exact SHA. Probe: run `horus skill install --force` in a
  disposable project and confirm `wildcard` installs at v2 and is reported `installed`.

## Non-goals

- **No general test-phase-skill machinery.** N is 1. Do not build a registry of
  "provisional" skills, a promotion workflow, or a new lifecycle state — the path below is
  a documented sequence to reuse, not a mechanism to build.
- Not a rewrite of `wildcard`'s contract — v2 is the audited text
  (`.horus/audits/2026-07-28-skill-wildcard.md`); this card only packages it.
- No change to how skills install, resolve scope, or project to `.agents/`.

## The reusable path (documentation, not machinery)

If another skill is authored in test phase later, the sequence is: draft the projection
pair by hand → calibrate on real runs → audit it → then run steps 1-4 above. The
hand-maintained phase is legitimate and should stay cheap; the point is that it must be
**exited** once the contract settles, not left indefinitely.

## Open decisions

- Whether the `wildcard` backlog card should shed its registration claim once this card
  exists, so design and packaging stop sharing one card. [refine] — recommend yes; that
  card's 2026-07-21 Review currently says registration is "the dedicated-session step this
  card drives," which now duplicates this card.

## Source

Owner request, 2026-07-28, immediately after the `wildcard` skill audit
(`.horus/audits/2026-07-28-skill-wildcard.md`) applied v1 → v2 by hand-editing both
projections — the act that made the unbundled state's cost concrete. Bundling gap measured
the same day: 18 of 19 projected skills bundled, `wildcard` the sole exception.
