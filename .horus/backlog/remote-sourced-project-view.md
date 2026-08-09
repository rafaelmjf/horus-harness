---
status: open
priority: medium
readiness: shaping
readiness_reason: "The value and the data paths are clear, but three scoping decisions are open: how branches are fetched per repo without burning `gh` rate limit, whether remote backlog cards are read per-file or via a single tree call, and what the view shows when a project's remote `.horus/` predates the card layout. Shape before building."
created: 2026-08-09
created_by: owner
last_refined: 2026-08-09
refine_passes: 0
vision_facet: "Dashboard / cockpit"
tier: medium
type: feature
parallel: safe
phase: converge
surface: "horus/github_catalog.py (RemoteProject + discover), horus/dashboard.py (gather_remote_projects, ~line 343)"
---

# remote-sourced-project-view — see every project's branches and cards from remote, without cloning

## Why (owner, 2026-08-09)

The TUI reads **local clones**, so it can only show projects cloned on the machine you are
sitting at. Cloning every project to get the overview is dead weight when you are not
working on them there. That is not a gap the TUI can close — it is what the TUI *is*.

Meanwhile Horus already enforces the habit that makes a remote-sourced view accurate:
every session ends by pushing to remote. So remote is the one place that reliably knows
about all projects at once.

This is the **publication** half of the Dashboard / cockpit facet, as distinct from the
actuation half. Actuation is what went unused: the hosted dashboard can open terminals on
its host, and the owner stopped using that in favour of tmux, herdr and ssh.

## What exists already

Most of the machinery is built — this is largely a rendering and fetch-extension job, not
new plumbing:

- `github_catalog.discover()` reads a project's **`current_focus` / `next_action` /
  `next_prompt` straight out of remote `.horus/`, without cloning**, caching per repo and
  skipping the fetch when `pushedAt` is unchanged.
- `dashboard.gather_remote_projects()` (`dashboard.py:343`) already consumes that cache and
  kicks off a background refresh.
- `horus backlog --tree --json` already emits a board-shaped projection (schema v2:
  readiness groups with counts, grouped by `branch:` umbrella then `vision_facet`) — for
  the *local* project.

## The actual gap

`RemoteProject` carries `owner, name, full_name, url, clone_url, default_branch,
pushed_at, current_focus, next_action, next_prompt, local_path`.

So it has the **default** branch only. The two things this card is for are missing:

1. **Feature branches** per project — nothing fetches them. Local branch signals
   (`closure.unmerged_branch_findings`) read local git, which is unavailable for a project
   that is not cloned.
2. **Backlog cards** — `github_catalog` never reads remote `.horus/backlog/`. It reads
   PRD frontmatter and stops.

Both are reachable the same way the continuity fields already are: remote file reads
against the GitHub API. The mechanism exists; it simply is not pointed at them.

## Inversion this implies

Today the dashboard treats **local as primary and remote as a supplement** — there is even
a guard about a local project "listing again in the remote catalog" reading as a duplicate.
This card inverts that: remote becomes the primary view, and local presence becomes an
attribute of a project rather than the reason it appears.

## Two boundaries to respect, not drift past

- **The Vision explicitly declined boards** — *"Declined: sprints, story-point estimation,
  boards, standups, extra card workflow states."* What is proposed here is a **read-only
  projection** of card state that adds no workflow states and no management affordances.
  That is compatible in spirit, but it is close enough to the declined line that it needs
  an explicit owner re-decision rather than a quiet slide. The risk the boundary guarded
  against is real: a board invites managing the board.
- **The facet's definition of done still says the wrong thing** — *"launches/resumes any
  project from web or phone, no terminal command."* The owner no longer wants that.
  Rewording the DoD to something like *"sees remote fleet state, branches, backlog and
  capabilities for every project, without cloning"* is the cheap precondition that makes
  this card and its successors gradeable. Do that first; it is one edit.

## Acceptance (draft — shape before committing to it)

- When a registered GitHub owner has projects that are not cloned locally, the dashboard
  should list each one with its open feature branches and its backlog cards grouped by
  readiness, read from remote and attributed to the commit they came from.
- A project's row should state how fresh its data is; a reader must never mistake cached
  state for live state.
- Rate limit and cache behaviour must be stated, not incidental: the existing
  `pushedAt`-unchanged fast path is the model to follow.
- Nothing in this card opens a terminal, launches a session, or writes to any project.

## Non-goals

- **No PM tool, and no scan for one.** Structurally settled: every PM tool is a database
  with an API, the backlog is files in git, and the Vision makes those files *"the only
  contract — vendor-neutral; Horus is a helper, never a required runtime."* Adopting means
  either a two-source-of-truth sync engine (a drift generator) or agents needing API
  credentials on every machine forever. GitHub Issues/Projects is the only candidate worth
  revisiting if that ever changes, since `gh` is already a dependency.
- Not removing the dashboard's terminal-opening feature yet — unused, but shifting focus
  does not require deleting it.
- Not the capability catalogue. That is blocked on the authoring rule in `## Rules`, and
  its prior-art question is `backstage-catalog-prior-art-scan`.

## Related

- `backstage-catalog-prior-art-scan` — the catalogue half. Independent of this card; its
  findings may inform which fields a project row shows, but this does not wait on it.
- `openwiki-graphify-value-benchmark` — source of the derived-over-generated principle this
  view must follow: project state is a projection over committed files, never generated prose.

## Source

Owner brainstorm, 2026-08-09, after the benchmark verdict closed the OpenWiki/Graphify
question and the local-vs-remote distinction emerged as the dashboard's real differentiator.
