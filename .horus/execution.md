---
status: active
current_feature: "Continuity-model + dashboard refinement: async perf, lane discipline (decisions/roadmap/history), bake into skills, reflow lanes, dashboard render-to-match"
supervisor_tier: frontier
worker_tier: standard
continuity_tier: economy
delegation_basis: "Single frontier agent, gated per phase (user's choice). Phases 2-4 are interconnected continuity-model design — coherence favors one mind, stay direct. Only the mechanical Codex skill-mirror in phase 3 is a delegation candidate. Phases 1 & 5 are UI/perf where the user's eyeball is the real gate."
last_updated: 2026-06-30
---

# Execution Plan

Active phased plan for refining Horus's continuity model and the dashboard. Born
from the dashboard-redesign review (PR #51): opening a project takes ~6.5s (token
overhead ~4s + context-cache ~2.5s of JSONL parsing — NOT markdown rendering, which
is ~3ms), and the `decisions.md`/`roadmap.md`/`history.md` lanes have drifted into
long logs that tax both the dashboard and every native session's context.

Goal: make the dashboard paint fast, and make the lanes short, current, and
readable — with the discipline baked into the skills/templates that generate them
(Claude + Codex), not just hand-fixed once.

## PR split

- **PR #51 (`feat/dashboard-sumi-e-redesign`)**: phases 1 and 5 (dashboard perf + render).
- **New branch (from `main` after #51 lands, or off #51)**: phases 2-4
  (lane discipline spec + skills/templates/instructions + reflow Horus's own lanes).

## Model Policy

Tiers, resolved locally per agent/account/availability.

| tier | Intended use | Examples |
|---|---|---|
| economy | mechanical continuity updates, formatting, small docs from explicit notes | maintainer |
| standard | narrow implementation phases with tests | worker |
| frontier | planning, architecture, risky review, final acceptance | supervisor |

## Active Phases

| phase | status | difficulty | mode | worker_tier | delegation_basis | handoff_note | review |
|---|---|---|---|---|---|---|---|
| 1-dashboard-perf | done | medium | direct | — | UI/perf; frontier judgment + user is gate; small surface. PR #51. | — | DONE: render_project 6426ms→8.1ms (overhead+cache async via /project-overhead, /project-cache); 502 green. User to confirm in-app. |
| 2-lane-discipline-spec | todo | medium | direct | — | Design that drives phases 3-4; must be coherent → one mind. New branch. | — | decisions/roadmap/history target shapes agreed with user |
| 3-bake-skills | todo | high | direct (Codex-mirror delegable) | standard | Interconnected (skill + templates + managed block) stays direct; mechanical `.agents/skills` mirror is the only delegation candidate. | — | horus-consolidate + templates + CLAUDE/AGENTS block consistent and mirrored to .claude/.agents; doctor + suite green |
| 4-reflow-lanes | todo | medium | direct | — | Judgment over Horus's own content; not mechanical. | — | this repo's decisions/roadmap/history match the spec; `horus close --check` + doctor green |
| 5-dashboard-render | todo | medium | direct | — | UI; user's eyeball is the gate. PR #51. | — | roadmap top/open-only inline, history → open-in-editor link, decisions curated + open-full button; suite green; user confirms |

## Notes carried into the plan

- Perf is the two log-parsing panels, confirmed by measurement (overhead ~4s,
  cache ~2.5s, markdown ~3ms). Fix = async-load those panels (the `data-horus-src`
  + `fetch` pattern the accounts strip already uses); deeper log-parse optimization
  is a possible follow-up, not required for the paint win.
- Lane discipline target (phase 2 will firm this up): **decisions.md** = short,
  topic-grouped, current-and-relevant rule bullets (not a dated log); **roadmap.md**
  = top/open items, completed condensed/archived; **history.md** = the narrative
  detail/lessons, and *not* loaded inline on the dashboard.
- "Open lane in editor" (phase 5): the dashboard is local-only, so the server can
  open a lane's raw `.md` via the OS default handler (`os.startfile` on Windows);
  guard it as a local, same-origin action by project/lane, never an arbitrary path.

## Worker Handoff Contract

If any phase is delegated (only the phase-3 Codex mirror is a candidate), the worker
writes `.horus/temp/<phase>.md` via `horus execution handoff <phase>`: changed files,
behavior, tests run + result, risks, suggested durable `.horus/` updates. The
supervisor reproduces the gate and reviews the diff before marking accepted.

**Known pre-existing test baseline:** none currently red — full suite is 502 green as
of 2026-06-30; do not misattribute a new red to an unrelated cause.
