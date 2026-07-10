---
status: open
priority: later
tier: sonnet
created: 2026-07-10
---
# Doctor compat (observe) + workflow-policy ladder

**Doctor compat:** per project, report what each agent would load
(instructions/skills/MCP/hooks). **Workflow-policy:** block v7 carries the branch→PR
default as instruction text (fabric field evidence: direct-to-main went unchallenged);
remaining per the ladder rule: per-project `.horus/` override, then **CI gate
promotion** only if the instruction rung observably fails again — continuity check
advisory → required once proven; decide if `init` installs the merge gate by default.
