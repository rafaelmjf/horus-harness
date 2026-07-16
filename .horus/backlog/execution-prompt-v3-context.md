---
status: claimed
priority: medium
tier: inline
created: 2026-07-16
type: bug
parallel: safe
surface: horus/templates.py, horus/cli.py, tests/test_cli.py
---

# Structure-aware execution supervisor prompt

`horus execution prompt` resolves v3 PRD frontmatter correctly but still labels the
field `Roadmap NEXT` and instructs the supervisor to read the retired six-lane files.
That contradicts lazy-loading guidance and wastes supervisor context for both Claude
and Codex.

## Acceptance

- A v3 project renders `PRD NEXT` and asks for `.horus/PRD.md` plus the active
  `.horus/execution.md`, not retired lane files.
- A v2 project keeps the six-lane read list and `Roadmap NEXT` label.
- Focus and execution metadata remain unchanged; tests pin both structures.

## Boundaries

- Do not redesign the execution workflow or add more generated prose.
