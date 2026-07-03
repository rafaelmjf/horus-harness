---
status: active
current_focus: "v3-tooling execution plan drafted and specced (.horus/execution.md, 6 phases); v0.0.20 on PyPI (0.0.19 broken — skip). Next session (work acc) supervises Phase 1: PRD-frontmatter contract."
next_action: "Phase 1 of .horus/execution.md — PRD-frontmatter contract: PRD.md frontmatter absorbs the shim fields; one shared reader (PRD → shim fallback) behind close --check, merge gate, resume, dashboard NEXT, doctor; delete this repo's shims at phase end. Spec + entry points are in execution.md 'Phase 1 spec'. Then delegate phases 2–4 in parallel."
next_prompt: "Resume Horus as execution supervisor. FIRST git fetch --all --prune (main clean, v0.0.20 on PyPI). THEN read .horus/PRD.md, then .horus/execution.md — the active 6-phase plan for teaching the tooling the PRD+sessions structure. Start with Phase 1 (direct supervisor work): implement the 'Phase 1 spec' section exactly — resolve_focus helper in horus/frontmatter.py with PRD→shim resolution, swap the named call sites (continuity.py, dashboard.py, cli.py, doctor), keep v2 projects byte-identical in behavior, and finish by moving this repo's shim frontmatter into PRD.md and git rm project.md roadmap.md. Gate: suite green + close --check rc 0 + resume + dashboard NEXT + doctor clean. Branch → PR → wait for green checks → merge (no auto-merge on this repo). After Phase 1: delegate phases 2–4 as parallel claude/work workers with --watch per the plan; review one at a time. Release ritual if cutting: bump = pyproject + horus/__init__.py + uv.lock, suite rerun AFTER the bump."
execution_recommendation: "plan-execution — ACTIVE: .horus/execution.md drafted 2026-07-03 (6 phases: frontmatter contract → templates/init → consolidate+skills → dashboard → migration engine → migrate controls + quiz gate). Phase 1 is direct supervisor work; 2–4 delegable in parallel after it."
last_updated: 2026-07-03
---

# Roadmap

**Content moved to `PRD.md` — the backlog lives there** (structure prototype,
2026-07-03). This file remains as a frontmatter shim for the dashboard NEXT box,
`horus resume`, and the merge freshness gate until the tooling reads PRD.md directly.
