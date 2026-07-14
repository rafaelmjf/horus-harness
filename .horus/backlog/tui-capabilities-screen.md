---
status: claimed
priority: high
tier: sonnet
created: 2026-07-14
type: feature
parallel: safe
surface: horus/terminal_tui.py, horus/capabilities.py
---

# TUI capabilities screen + vision line on project open

Surface the self-documenting capability record inside `horus tui`, shaped exactly
like the Backlog flow (2026-07-14 owner brainstorm):

- A **Capabilities** item on the project screen (next to Backlog) opening a
  scrollable list of shipped-capability lines with their `related_commands`,
  fed by `capabilities.generate_project` (read-only, idempotent,
  regenerate-on-read — no cache invalidation problem).
- The one-line `vision` field rendered as a muted line when opening a project —
  "what IS this project" orientation for near-zero cost.
- A staleness hint: `generated_at` age + commits since, so the reader knows when
  the record predates recent work.

Boundary: the TUI screen is the *human* surface. Agents keep reading
`capabilities.json` / `horus capabilities` directly — do not route agents
through the TUI, and do not add a second data path (reuse the existing module).
