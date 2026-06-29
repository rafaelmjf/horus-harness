# rulesync

- **What it is:** An npm/Node tool that projects rules / skills / commands / MCP config
  across 20+ agent tools (Claude Code, Cursor, Copilot, Gemini CLI, `.cursor/rules`,
  `.github/instructions/…`, `GEMINI.md`, etc.).
- **Where it overlaps Horus:** the **cross-tool interface sync** track — Layer-1 artifact
  projection (instructions, `SKILL.md`, commands, MCP). It does NOT touch Horus's
  behavioral/semantic layer (per-tool usage-signal source, hook control protocol,
  per-account config-dir env var).
- **Verdict:** **Stay direct at two tools, adopt rulesync at the third.** Horus already
  dual-writes `SKILL.md` to `.claude/skills/` + `.agents/skills/` and reconciles the
  AGENTS↔CLAUDE managed block zero-dep — that's cheap and worth owning at N=2. Layer-1
  projection is a commodity rulesync already solves; don't reinvent a generic converter.
  Own only the behavioral layer (inherently Horus's, never portable). See
  `.horus/decisions.md` "rulesync: stay direct at two tools; own the behavioral layer".

## Drift triggers — if you're about to build any of these, STOP

- A **generic rule/skill/command/MCP converter** for a 3rd/4th agent tool (Gemini CLI,
  Copilot, Cursor) → wrap/document rulesync instead (with provenance + diff-before-install
  + trust UX); never embed it (it's npm/Node).
- A many-target "write `GEMINI.md` / `.cursor/rules` / `.github/instructions`" projector.

→ Keep building **only** the behavioral/semantic adapters (usage→closure hooks per tool,
config-dir env var per tool) — those are Horus's and not portable.

## Sources

- Prior evaluation distilled in `.horus/decisions.md` (2026-06-25) and the cross-tool
  interface sync track in `.horus/roadmap.md`. (No external fetch re-run; refresh if
  rulesync's scope changes materially.)
