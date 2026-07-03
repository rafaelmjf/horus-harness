---
status: in-progress

current_feature: "v3 continuity structure as the product (PRD backlog item 1, second half): teach templates/init, close --check, consolidate, infer/skills, and the dashboard the PRD+sessions shape; drop the shims; migrate gym-coach + ttrpg via upgrade-project"
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
delegation_basis: "Frontier supervisor (Fable) + claude/work workers via branch+PR (proven v0.0.18 flow) → low delegation bar for narrow, pytest-gated phases. Phase 1 pins the frontmatter contract every other phase builds on — judgment-heavy, direct. Phase 5's migration engine rewrites real repos' continuity — integrity-sensitive, guards are the work, direct. Phases 2–4 are high-volume/low-ambiguity after phase 1 lands — delegate. Phase 6 is supervised runs + probes, not implementation. Workers spawned visibly per Rafa's preference: horus run --watch, badge, explicit review. Cross-vendor recovery proven on phase 4: an orphaned claude worker's uncommitted worktree finished by a codex gpt-5.5 worker."
last_updated: 2026-07-04
---

# Execution Plan

Tooling learns the PRD+sessions structure that just passed its acceptance test
(5 closures, zero failure flags — docs/structure-test-2026-07-03.html). Order is
dependency-driven: phase 1 defines the PRD-frontmatter contract all readers share;
2–4 fan out on it (independent of each other, parallelizable); 5 builds the
migration engine; 6 migrates the two control repos and re-runs the quiz probe as
the acceptance gate. v2 six-lane projects must keep working untouched at every
phase — the fallback path is part of each gate, not a cleanup at the end.

This file is the fluid coordination surface for the batch (recreated per the v3
structure contract; not a revived lane — replaced when the next batch starts).

## Model Policy

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting | maintainer |
| standard | narrow implementation phases with tests | worker (claude/work via branch+PR) |
| frontier | planning, architecture, risky review, final acceptance | supervisor (whichever session holds this plan) |

## Active Phases

| phase | status | difficulty | mode | worker_agent | worker_tier | delegation_basis | handoff_note | review gate |
|---|---|---|---|---|---|---|---|---|
| 1-prd-frontmatter-contract | done (PR #101, merged 2026-07-03) | medium | direct | native | — | DONE: `frontmatter.resolve_focus` is the shared PRD-first reader (per-field PRD → shim fallback), consumed by close --check/merge gate (freshness_signals), resume, dashboard load_project, execution prompt, doctor check_project (PRD present → six lanes not required), and the GitHub catalog (PRD.md marks Horus-enabled). This repo's shims deleted; frontmatter lives in PRD.md. | — | Reproduced: 678 tests green (17 new v3), scratch v2 project identical live, close --check rc 0, resume PRD-sourced, dashboard NEXT from PRD (v2 control unchanged), doctor rc 0. |
| 2-templates-init-v3 | accepted (PR #102, merged 2026-07-03; supervisor reproduced pytest 682 green + fresh-v3/scratch-v2 init gates) | medium | delegated | claude | standard | High volume, low ambiguity once phase 1 pins the contract: init scaffolds PRD.md + sessions/ (+ .horus/README, sessions .gitignore) instead of six lanes; managed-block closure contract text becomes "PRD backlog/shipped + session note + close"; never-clobber semantics keep existing v2 projects untouched. | .horus/temp/2-templates-init-v3.md | Supervisor reproduces: pytest green; scratch `horus init` → cold `close --check` rc 0 → a cold read of the scaffold answers focus/next-step from PRD alone. |
| 3-consolidate-hygiene-infer-skills | accepted (PR #103, merged 2026-07-03; supervisor reproduced pytest 701 green + v3 hygiene-only consolidate + v2 scratch unchanged; follow-ups noted: v2-worded CONSOLIDATE_PROMPT trailer, distill-history v3 archive target) | medium | delegated | claude | standard | Enumerable checks with a crisp gate. consolidate's v3 path = backlog hygiene (PRD line count vs ~250 cap, lingering done items, stale last_updated, undistilled session-note count, duplicate backlog titles) — no lane-purity warnings; infer fills the PRD skeleton from canonical docs; the four bundled skills (consolidate / infer / distill-history / execution) rewritten for v3 with explicit v2 fallback wording; skill version markers bumped. Supervisor specifies the exact check list in the brief. | .horus/temp/3-consolidate-hygiene-infer-skills.md | Supervisor reproduces: pytest green; `horus consolidate` on this repo emits hygiene signals only (zero lane warnings); on gym-coach (still v2) behavior unchanged. |
| 4-dashboard-prd | implemented (PR #104, 2026-07-04) — awaiting Rafa's detail-page eyeball before accept/merge. First claude/work worker (becca9cf) orphaned at the usage limit with the diff uncommitted in the hh-wt-phase4 worktree; a codex gpt-5.5 worker reviewed/completed it (added the missing /projects-grid regression coverage). Supervisor reproduced: pytest 710 green on host, live dashboard from the worktree — v3 detail PRD 248/250 amber badge + backlog/shipped panels, gym-coach (v2) unchanged, /projects-grid clean. | medium | delegated | claude→codex | standard | Bounded UI slice on the phase-1 reader: project detail renders PRD focus, top backlog items, shipped count + latest line, and a line-budget meter vs the ~250 cap; v2 projects render exactly as today. The user's eyeball is the real gate (visual). | .horus/temp/4-dashboard-prd.md | Supervisor drives the live dashboard (both a v3 and a v2 project) + pytest green; Rafa eyeballs the detail page before accept. |
| 5-migration-engine | implemented (PR #105, 2026-07-04) — awaiting review/merge. Direct supervisor work on `feat/v3-migration-engine`: added `upgrade-project --structure prd` dry-run/apply, deterministic v2 lane collapse into generated PRD, verbatim archive moves, and apply-time dirty/behind-origin refusal after fetch-first safety. Supervisor reproduced focused CLI tests + full suite (711 green) and gym-coach scratch migration with all six archive files byte-identical to originals; rehearsal caught and fixed checked-item continuation leakage in generated backlog. | high | direct | native | — | `upgrade-project --structure prd` (opt-in): deterministic six-lane → PRD+sessions collapse — git mv lanes to .horus/archive/, scaffold PRD with mapped sections (project→Vision, open roadmap→Backlog, features→Shipped one-liners, decisions→Rules), carry roadmap frontmatter into PRD frontmatter, leave an agent-polish TODO marker. Integrity-sensitive rewrite of real repos' continuity: refuses on dirty tree / behind-origin (fetch-first), never deletes content, archives verbatim. Safety in the code — direct. | — | Reproduced: `uv run pytest tests/test_cli.py -q` 79 passed; `uv run pytest -q` 711 passed; scratch clone of gym-coach dry-run/apply succeeded, `.horus/archive/{project,roadmap,features,decisions,history,execution}.md` cmp-identical to originals, generated Backlog contains open roadmap items only. |
| 6-migrate-controls-validate | planned | medium | delegated | codex | standard | Supervised runs, not implementation: run the engine on agentic-gym-coach + agentic-ttrpg, then one bounded worker per repo polishes the generated PRD prose (codex auto-edit — read-only .git, supervisor owns commit/push per rule). Acceptance = the same pre-registered cold-reader quiz (5 questions, .horus/ only) scores 5/5 on BOTH migrated repos + close --check rc 0 + dashboard NEXT correct. Then delete PRD backlog item 1, release v0.0.21. | .horus/temp/6-migrate-controls-validate.md | Supervisor reproduces the quiz probes + close --check on both repos and commits/pushes their continuity; release cut with the 3-file bump ritual, suite rerun AFTER the bump. |

## Phase 1 spec (supervisor draft — the contract to implement)

**Fields.** PRD.md frontmatter gains the shim fields, same names, same semantics:
`current_focus`, `next_action`, `next_prompt`, `execution_recommendation`
(plus the existing `status`, `last_updated`). Shims win only when PRD.md is absent
or lacks the field (v2 projects) — PRD is preferred the moment it exists.

**One reader, many call sites.** Add a single resolution helper (suggested home:
`horus/frontmatter.py` — e.g. `resolve_focus(root) -> dict`, reading
`.horus/PRD.md` frontmatter first, then `roadmap.md`/`project.md`), then swap the
scattered readers onto it:

- `horus/continuity.py` — `COMMITTED_FILES` + the current_focus/placeholder
  findings (~lines 12, 78–90); this drives `close --check` freshness and the
  merge gate. v3 committed-set becomes `PRD.md` (+ `sessions/` structure).
- `horus/dashboard.py` — NEXT box + project detail (~lines 73–115).
- `horus/cli.py` — `horus resume` / catalog rows (~lines 175, 585).
- `doctor project` — must stop requiring the six lanes when PRD.md exists
  (the known cosmetic `[fail]` on missing decisions.md from the prototype note).
- `horus/templates.py` / managed block — only the *text* that tells agents where
  focus lives; actual template swap is phase 2.

**End state for THIS repo:** move the live shim frontmatter values into PRD.md
frontmatter, `git rm` `project.md` + `roadmap.md`, and the gate is:
full suite green + `horus close --check` rc 0 + `horus resume` prints the
PRD-sourced next step + dashboard NEXT populated + `doctor project` clean.
A scratch v2 project must behave exactly as before throughout.

## Notes

- Phases 2–4 are mutually independent once 1 lands; run up to two workers in
  parallel with `--watch` terminals, review one at a time.
- Shim removal (end of phase 1) is repo-local; OTHER v3 repos keep working because
  the reader prefers PRD frontmatter and only falls back to shims when present.
- The quiz probe in phase 6 reuses the acceptance-test wording verbatim (session
  note 2026-07-03-210751 → baseline note 2026-07-03-090957) with Q5 pinned to the
  then-latest release.
