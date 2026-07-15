---
title: "Optional recovery notes and honest onboarding"
status: shipped
priority: now
type: feature
surface: horus/templates.py, horus/skills.py, horus/continuity.py, horus/closure.py, horus/routines.py, horus/cli.py, horus/initialize.py, horus/remote_start.py, tests/
created: 2026-07-15
created_by: owner
parallel: unsafe
shipped_pr: 247
shipped_sha: 405ddbd261a55c5b553ad7da578f5df61774d5e7
---

# Optional recovery notes and honest onboarding

Apply the first campaign retrospective: keep local session notes as an explicit
Claude↔Codex/incomplete-work recovery buffer, not mandatory closure prose; leave
new project scaffolds blank until real cases exist; and remove the concrete friction
observed while onboarding the Fabric project family.

## Acceptance

- Fresh init creates a blank PRD and tracked empty backlog directory, with no fake card or immediate-infer obligation.
- Managed instructions, local README templates, closure prompts, and consolidate/infer skills use the PRD+git recovery test before suggesting a local note.
- Doctor treats an empty sessions directory as healthy; close never creates or requires a session note.
- `session new` records an explicit/current agent and uses matching Claude/Codex account lookup; an unresolvable agent is `unknown`, never falsely Claude.
- `horus infer` prints v3 PRD/card guidance on a v3 project and six-lane guidance only on v2.
- GitHub onboarding resolves author identity before mutation, inherits a complete invoking-repository identity into the clone as local config when needed, and fails before clone/init when none exists.
- Focused tests, skill validation, full pytest, release publication, install smoke, hosted deployment, and selected projection refresh all pass.

## Execution

Inline in the owner session: the policy strings and runtime behavior are tightly
coupled, so a handoff would pay the full brief/review/gate tax without isolating a
useful work unit.
