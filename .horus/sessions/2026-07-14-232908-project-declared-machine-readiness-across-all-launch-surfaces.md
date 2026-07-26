---
date: 2026-07-14T23:29:08
agent: codex
account: personal
environment: host
project: horus-harness
status: complete
summary: "Shipped one safe project-machine readiness result across doctor, resume, dashboard, and TUI, verified against fabric's existing declaration."
---

# project-declared machine readiness across all launch surfaces

## Summary

Implemented the owner-expanded `project-machine-requirements` card with the TUI
as a fourth consumer, without introducing a second parser or probe path.

## Key Points

- Added a dependency-free `.horus/requirements.md` parser for a narrow
  YAML-like frontmatter schema (`tools`/`configs`, with `name`, `probe`,
  `install`, and `needed_for`).
- Put safety in the probe model: a committed tool probe is only a
  `shutil.which` executable-name lookup; a config probe is only a path-existence
  check. Shell command text is rejected and never executed.
- `doctor project` emits canonical readiness findings; `horus resume` prepends
  the canonical missing-machine warning.
- Dashboard project cards/details show a readiness badge and warning panel; the
  TUI project frame shows the same warning above Resume/Fresh launch choices.
- Added user-facing schema/safety documentation.
- The fetched remote-authoritative fabric repo already carried the promised
  declaration. Compatibility was adjusted to its existing contract: tool probes
  may include descriptive argv such as `fab --version` (only `fab` is looked up;
  nothing runs), and configs use `path:` with an optional display name.
- Verification: 475 impacted tests and the full 1,455-test suite passed. A live
  isolated declaration produced the expected warning in doctor, resume,
  dashboard, and the actual TUI frame renderer.
- Live first-consumer proof: fabric's unchanged declaration parsed with no
  issues and all four surfaces warned that this machine lacks `fab`, `pbir`,
  and `~/.config/pbir/config.json` before its deploy-oriented next action.
- Consolidation found 14 active notes after this note was created; the two
  oldest already-distilled notes were moved to the local archive, leaving 12.

## Next

- Finish PR #237, then ask before `datum-outcome-taxonomy-void-and-death`.

## Checkpoints (auto-harvested)

- `105c41a` feat: add project machine readiness across surfaces
- `2f2c7b3` fix: honor existing machine requirement declarations

- `2160ea6` feat: add project machine readiness across surfaces (#237)
  * feat: add project machine readiness across surfaces
  * fix: honor existing machine requirement declarations
  * Update Horus continuity (closure)

- `2bac6ad` Update Horus continuity (closure)

- `c73099e` Update Horus continuity (closure)

- `2a45e16` Update Horus continuity (closure)
- `c73099e` Update Horus continuity (closure)
- `6e0aa2b` Update Horus continuity (closure)
- `0320161` @ Update Horus continuity (closure)
  Account-setup run, 2026-07-20: logged in claude-work, verified all three
  accounts, and carded what the hand-run flow surfaced.
  - account-login-verb: provision + log into an account with no prior login
  - codex-identity-guard [bug]: Codex launches skip the identity check entirely
  - codex-isolated-config-leak [bug]: isolated Codex dirs point at ambient home
  - prd-worked-by-account: worked_by frontmatter for launch-account defaulting
  - new-machine-setup-guidance: refined into a two-branch skill shape
  @
- `c476bb9` backlog: close --check should not hard-block merge on unclassified cards
  Filed from a pbi-ecosystem session where a merge with fully-fresh continuity was
  blocked solely by Unclassified-card warns (all freshness checks [ok], EXIT=1).
  Unclassified is an owner-gated/deferrable scheduling state; it shouldn't gate delivery.
- `af906fe` Capture mobile-agent-session research + two backlog cards
  Research receipt on mobile access to agent sessions: terminal persistence
  (tmux vs bare SSH), app-layer session sharing (remote control / cloud
  rendezvous vs pty bytes), the iOS-sandbox + magic-link limits that make phone
  account-switching unfixable client-side, and a corrected read of the Codex
  mobile app (drives the CLI, but Mac-only worker today).
  Two cards distilled from it:
  - session-remote-control-default [feature, high] — next build; launch Horus
    Claude sessions with remote control on by default (toggle + per-launch
    override). Claude-only for now; verify enable mechanism first.
  - horus-phone-chat-poc [spike, low] — one-shot rough-but-usable phone chat
    tryout, scoped to the tool-permission round-trip.
  PRD next_action points at the remote-control card (implement in a fresh
  session); prior account-setup open items preserved in next_prompt.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `642d6b8` Merge pull request #376 from rafaelmjf/capture/mobile-session-research
  Capture mobile-agent-session research + two backlog cards
- `1c4cbad` backlog: two open-ended continuity-process cards
  From a process review (2026-07-21) of the friction hit during this session's own
  landing:
  - continuity-sync-friction [chore, medium] — the CURRENT git-synced-continuity
    friction: session-start staleness (fetch-first is advisory, not enacted) and the
    PRD-frontmatter hand-merge (next_prompt accretes must-not-lose items; volatile
    pointer shares a file with the cold PRD body). Fix space left open.
  - concurrency-safe-continuity [spike, low] — the COMING parallel-multi-agent
    regime: single-valued frontmatter + a per-merge freshness gate would conflict on
    every concurrent PR. Grounded in CLAUDE.md's existing "workers record delivery
    facts, supervisor owns canonical continuity" principle; the gap is enforcing it in
    the format. Left open-ended to explore when parallelism arrives.
  Both deliberately shaping/open-ended. PRD current_focus notes the review.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `faf33ab` Merge pull request #377 from rafaelmjf/capture/continuity-process-cards
  backlog: two open-ended continuity-process cards
- `5431e71` backlog refine (2026-07-21): 5-card pass + 2 captures + chat north-star
  Owner-attended refinement pass (scope: newest cards + e2e-drill food; 13-decision
  2026-07-20 queue left for its own session).
  Decisions applied:
  - session-remote-control-default: shaping → Ready (attended), order 10 (#1);
    enable-mechanism folded into acceptance step 0; facet Distribution → Dashboard/cockpit.
  - windows-native-horus-setup: kept shaping, order 20 (#2); first step corrected to
    "validate TUI under already-installed WSL2+tmux" (2026-07-20 Findings disproved the
    stale-install premise; WSL2 already present).
  - codex-identity-guard: kept Ready (eligible); explicitly NOT e2e-drill food.
  - verify-guidance-long-running-services: kept Ready (eligible); tagged prime drill food (leg 1).
  - autotest-e2e-away-mode-drill: gated → deferred to after 2026-07-29; leg roster started
    (verify-guidance = leg 1; audit-advisory-interval + backlog-default-list = candidates);
    satisfied depends-on removed.
  Also:
  - horus-phone-chat-poc: added north-star ("any session chattable/attachable from
    anywhere" — the tmux identity-free property extended to the phone).
  - New captures: app-usage-cost-opacity (native apps meter but hide cost — chat-app
    feature-value) and decision-doc-skill (issue→options→solution doc skill). Both shaping/low.
  - PRD frontmatter: ordering + refine outcome.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `94fa947` Merge pull request #378 from rafaelmjf/refine/backlog-2026-07-21
  backlog refine (2026-07-21): 5-card pass + 2 captures + chat north-star
- `759b155` backlog: two self-improvement cards on autonomy (lens + wildcard)
  From a process discussion on why cards land attended vs eligible:
  - refine-autonomy-hardening-lens [feature, low] — add a "contingent vs intrinsic"
    lens to backlog-refine: for every attended card, force naming the ONE thing to
    front-load (decision / unknown / deterministic probe) that would promote it to
    eligible. Guardrail: never manufacture determinism.
  - wildcard [spike, low] — an autonomous pathfinder-divergence skill that emits ONE
    reviewable card (bounded, reversible output = safe to autonomize; convergence and
    implementation stay owner-gated). Signal-grounded with a wild streak; near-ideal
    zero-blast-radius food for the away-mode loop. "Fun to try."
  Both shaping/low. The two ideas are the same principle (autonomize only the
  bounded-output step) aimed at refine and at pathfinder.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `37bddeb` Merge pull request #379 from rafaelmjf/capture/autonomy-lens-and-wildcard
  backlog: autonomy self-improvement cards (lens + wildcard)
- `ac9d574` wildcard: ground it on the pathfinder run (owner decision)
  Resolves the pure-wild-vs-signal-grounded question: wildcard runs on a pathfinder
  run's saved artifacts (position brief, product-audit, market-scan, roadmap-branches
  divergence tree) — fresh run or the previous one — and synthesises ONE evidence-cited
  card. Adds the fresh-vs-previous cost/staleness tradeoff, and flags a likely
  prerequisite: a per-run artifact bundle/manifest so the previous run's evidence loads
  coherently (today artifacts are dated receipts, not grouped by run).
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `992a847` Merge pull request #380 from rafaelmjf/refine/wildcard-grounding
  wildcard: ground it on the pathfinder run
- `debf8a2` backlog: pathfinder-structured-outcome card; wildcard depends on it
  Elevates the run-bundle/manifest from a wildcard footnote to a proper design card:
  refine the pathfinder chain (pathfinder → product-audit → market-scan →
  roadmap-branches → scope-cards → backlog-refine) to emit ONE structured, addressable
  per-run outcome (bundle + manifest) instead of ad hoc dated receipts. Enables wildcard
  (load "the previous run"), re-runs/resumption, review, and traceability.
  Core open decision recorded: directory-per-run vs manifest-referencing-existing-
  receipts (back-compat). Scope guard: changes how outputs are structured, not what each
  step does. wildcard now depends-on this card.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `e3961d6` Merge pull request #381 from rafaelmjf/capture/pathfinder-structured-outcome
  backlog: pathfinder-structured-outcome (chain emits a structured per-run outcome)
- `3556576` product-naming: horus-builder as front-runner (execute at distribution)
  Owner proposed horus-builder (2026-07-21). Logged as the leading candidate: fits the
  lived "general toolbox used to build itself + other products + data work" reality and
  beats harness/po/continuity. Recorded pros + honest cons (generic/functional not
  creative; names the construction layer vs the continuity differentiator) and the key
  flag: adopting it is a small identity rebroadening (PO → general build toolbox) to
  confirm and reflect in the Vision at ship time. Rename stays deferred until first
  external distribution; name effectively pre-decided pending a PyPI check.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `f743f56` Merge pull request #382 from rafaelmjf/refine/product-naming-builder
  product-naming: horus-builder as front-runner
- `c2c055f` research: record live mobile-driven-session evidence
  The 2026-07-21 session (discussion + receipt + ~12 cards across 7 PRs) was authored
  end-to-end from mobile — direct evidence for the remote-access priority.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `37874cf` Merge pull request #383 from rafaelmjf/capture/mobile-evidence-line
  research: record live mobile-driven-session evidence
- `0143485` backlog: session-process-cadence card + adhd prior-art pointer on wildcard
  session-process-cadence [chore, medium] — revisit the per-session continuity/ceremony
  cadence for usage efficiency (today: 8 PRs to grow the backlog). Captures the
  mode-experiment failure to avoid (inline-batch #307/#326 → All Gas No Breaks #360 →
  deleted axis #368) and candidate directions that stay behavioural, not frontloaded:
  capture-batching, un-blocking topic-jumps at the gate, cadence-as-behaviour. Cross-links
  close-check-unclassified-cards-advisory + continuity-sync-friction.
  wildcard — added prior-art pointer: github.com/uditakhourii/adhd (isolated N-frame
  divergence + separate critic convergence), directly relevant to wildcard's
  divergence→one-card and pathfinder roadmap-branches.
  Batched into one PR (applying the granularity lesson).
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `bef17c0` Merge pull request #384 from rafaelmjf/capture/cadence-and-adhd-pointer
  backlog: session-process-cadence + adhd prior-art pointer
- `f4ca134` session-process-cadence: add mid-session recurrence evidence + one-branch fix
  Records the sharpest datum: the premature-merge pattern repeated mid-session even after
  the card was written (a batched PR still merged while work was ongoing) — evidence a
  written instruction didn't hold, arguing for a stronger control rung. Upgrades the
  leading candidate direction to "one session branch, merge once at the boundary"
  (separates don't-strand = commit+push incrementally, from don't-over-ceremony = merge
  once).
  Committed to a session branch and intentionally NOT merged — held for the real boundary
  after the session's last task, demonstrating the fix.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `a9290ee` backlog: two TUI backlog-visualisation cards (grouped-list #3 + kanban board)
  - tui-backlog-grouped-list [feature, medium, order 30] — the cheap, width-safe win:
    collapsible group-by sections (status/facet/autonomy/readiness/priority) in the
    existing list. Position #3.
  - tui-backlog-kanban-board [feature, low] — the bold stretch: width-adaptive kanban
    lens, depends-on the grouped-list; geometry (mobile viewport) is make-or-break.
  Both Dashboard/cockpit, shaping. Same group-by engine, two renderings (list = narrow,
  board = wide). Committed to the session-close branch; held for merge at the boundary.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `3ed83a1` wildcard v0 skill + backlog-librarian card + session closure
  - wildcard v0 SKILL.md (.claude + .agents) — the calibrated divergence→one-grounded-card
    procedure (isolated N-frame diverge → critic converge → one evidence-cited candidate
    card). Draft, auto-discovered; NOT yet bundled in horus/skills.py (dedicated-session
    step, per the wildcard card).
  - backlog-librarian card — the wildcard dry-run's output, owner-approved: autonomous
    zero-blast-radius backlog-hygiene digest (the curate half; wildcard is the create half).
  - wildcard card: Reviews note on the v0 draft + calibration.
  - PRD closure: current_focus session summary; tui-backlog-grouped-list added as next #3.
  Claude-Session: https://claude.ai/code/session_01ViEE961YCDziigBwWtydiM
- `2a082de` Merge pull request #385 from rafaelmjf/consolidation/session-close-2026-07-21
  Session close 2026-07-21: cadence fix + viz cards + wildcard v0 skill + backlog-librarian
- `8129306` session-remote-control-default: enable Claude Remote Control on launch by default (#386)
  Horus-launched *interactive* Claude sessions now request Claude Code Remote
  Control at spawn, so they are reachable from the native/mobile app without
  remembering to enable it in-session. Verified against the live CLI (claude
  v2.1.216): `claude --remote-control [name]` is a real spawn-time flag,
  independent of settings files, composing with CLAUDE_CONFIG_DIR isolation.
  - SpawnSpec gains `remote_control` (a launcher request); adapters honor it only
    when they declare `supports_remote_control` — Claude does, Codex/fake ignore it
    (Claude-only for now, per the card).
  - `prepare_interactive` (the single choke point for CLI `open`, dashboard, and the
    managed-tmux phone-attach path) resolves the request: an explicit per-launch
    override wins, else the global `[tui] remote_control_default` (on by default) —
    so the sessions you *forgot* about are covered.
  - Global toggle: TUI Settings pane `[ ] Remote Control on launch (Claude)` +
    `config.load/set_remote_control_default`.
  - Per-launch override: `horus open --remote-control / --no-remote-control`,
    threaded through launch_window/launch_tmux/run_attached/launch_interactive and
    backend.LaunchBrief so all three targets honor it.
  - Workers (headless `-p`) untouched — Remote Control is an interactive feature.
  Scope guard (from the card): this makes sessions REACHABLE; it does not remove the
  phone account-switch step (server-side, unfixable). Best-effort — the flag never
  fails a spawn; if the account/plan can't use it, Claude just notifies.
  Full suite green (2199). Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
- `e99df65` backlog: ship session-remote-control-default (PR #386, 8129306)
- `543079d` tui-backlog-grouped-list: configurable collapsible group-by lens (#387)
  The flat backlog list is great for "start on a card now" but poor for "see
  the shape" — and the backlog is growing fast. This generalizes the existing
  branch+facet grouping into a configurable group-by lens over the same cards.
  - backlog_tree.sections_for(cards, lens, tree) projects cards into ordered,
    counted GroupSections for lenses: none · readiness · facet · status ·
    priority. `none` = flat; it is also the universal fallback when a lens has
    no real structure (<=1 section) — a new project, or one not using
    facets/branches. build_tree refactored to expose build_tree_from_cards.
  - Global default lens persisted in [tui] backlog_group_by (default `facet`,
    keeping today's behavior), set from the TUI Settings pane; config accessors
    validate against the live lens roster.
  - TUI: `g` cycles the lens live per-session; sections render EXPANDED by
    default with `(count)` headers and are collapsible (Enter on a header),
    tracked per (project, lens, group). Card-open flow and in-group readiness
    sort unchanged. Replaces the branch-only expand state with a generic one.
  Width-safe / phone-safe (no horizontal layout) per the card. Browse/visualise
  only — no card editing from the view. Full suite green (2207).
- `18a7c11` tui-backlog-priority-board: priority board + readiness filter + detail pane (#388)
  The desktop half of the backlog-visualisation idea, plus the filter that pays
  off on mobile too. Builds on the grouped-list engine (sections_for).
  - Readiness filter (`r` cycles All→Active→Ready→Parked), applied to BOTH the
    list and the board. This is the mobile win: "what can I work next" (Active/
    Ready hides parked) and "what to unblock" (Parked). backlog_tree.filter_cards
    + ready_count.
  - Priority board (`b` toggles; renders only at width >= 100, else the list —
    the narrow/mobile fallback). One column per priority, cards column-major and
    sorted ready-first, each with a color-coded readiness dot (green ready / amber
    shaping / dim parked) and a `· N ready` header so a big "high" column of
    mostly-deferred cards can't mislead. Borderless _fit_cell columns (no
    alignment fragility) matching the existing wide-home layout.
  - Bottom detail pane under a rule: selected card's title + meta, facet/surface,
    a blank spacer, then a wrapped "why" snippet from the body.
  - 2D column-major navigation (↑↓ within a column, ←→ across).
  - New bindings filtered to the backlog screen so `r`/`b`/`g` never shadow the
    card-screen review `r` or the defaults-form back `b`.
  Full suite green (2217).
- `f632bf4` tui-vision-backlog-read-out: TUI direction read-out (facets, branches, readiness) (#389)
  Opening a project's Direction view answers "where does this stand, what
  direction is active" at a glance — the same semi-deterministic read-out that
  until now lived only in `horus consolidate` text and dated audit receipts.
  - routines: extract the phase-aware convergence analysis into a structured
    `facet_standings()` (FacetStandings: with_work / no_work / explore / drift);
    `convergence_findings` becomes a thin prose rendering of it, so consolidate
    and the TUI share ONE analysis (its output is byte-for-byte unchanged).
  - TUI: new read-only "Direction" view (project screen → Direction), rendering
    ONLY canonical primitives per the TUI-stays-thin rule — `facet_standings`,
    `backlog.readiness_counts`, and the `backlog_tree` branch projection. No new
    parser, no analysis computed only in the TUI, no editing. Facet standings
    (open counts + no-work + exploratory bucket + convergence drift), readiness
    queues, and vision-branch states with their convergence lines. Scroll-only,
    phone-width friendly.
  Full suite green (2222).
- `55e4a0f` continuity: close 2026-07-21 session — TUI visualisation arc + Remote Control shipped (v0.0.74)
- `c623374` Bump version to 0.0.74 (#390)
  TUI backlog-visualisation arc (grouped-list group-by lens, priority board,
  readiness filter, Direction read-out) + Claude Remote Control on launch.
  PRs #386-#389.
- `2d7c4be` feat: add autonomous backlog librarian skill (#392)

- `7120b92` backlog: capture intent-preserving goal campaign (#393)
- `3895591` backlog: record native goal campaign probe (#394)
- `5ec6197` backlog: mint three wildcard candidate cards (2026-07-24) (#395)
  Three grounded candidate cards from three wildcard runs, each under a
  tighter owner-set frame; all Shaping, no code shipped.
  - managed-instruction-drift-lint: advisory lint of the Horus-managed
    instruction block against the live CLI surface (07-20 audit's
    self-detection gap).
  - dispatch-collision-guard: guards the selection moment — two concurrent
    agents both building the same card — upstream of the merge-moment
    problem concurrency-safe-continuity covers.
  - prd-readiness-count-check: auto-reconcile the PRD readiness-breakdown
    counts against the existing backlog.readiness_counts(); shaped for
    autonomous execution.
  PRD: Shaping 36 -> 39; frontmatter handoff refreshed.
  Claude-Session: https://claude.ai/code/session_01QAZHkJZsVbULEDmSaoJLid
- `2c28d3b` feat: three autonomous continuity checks (readiness counts, TUI labels, unclassified reason) (#396)
  Implements the three owner-approved autonomous cards in one pass; all
  deterministic, code-only, verified by unit tests + the full suite.
  - prd_readiness_count_findings: reconcile PRD.md "Readiness breakdown"
    counts against backlog.readiness_counts(); wired into hygiene_findings
    so a stale hand-edited count surfaces at consolidate/close instead of
    relying on the owner noticing. (card: prd-readiness-count-check)
  - readiness_count_summary: single-source the cockpit readiness labels
    from READINESS_QUEUE_LABELS; removes the hardcoded literals in
    terminal_tui.py that could drift on a canonical rename.
    (card: tui-queue-label-single-source)
  - backlog list: surface autonomy_block_reason for Unclassified cards so a
    card that declared `readiness: ready` but silently degraded says why.
    The core logic (readiness_findings) already existed and is surfaced by
    consolidate/close; only the list surfacing was net-new.
    (card: declared-vs-effective-readiness-advisory)
  Full suite 2229 + 2 new tests; close --check green (the new count check
  confirms Shaping 39). Ship/closure follows this PR's merge.
  Claude-Session: https://claude.ai/code/session_01QAZHkJZsVbULEDmSaoJLid
- `c11f0db` chore: ship three autonomous continuity checks (closure) (#397)
  * chore: ship three autonomous continuity checks; close out
  Continuity closure for PR #396 (merge 2c28d3b):
  - archive prd-readiness-count-check as shipped (pr #396)
  - Shipped line for the three-check trio
  - Readiness breakdown Shaping 39 -> 38; frontmatter handoff refreshed
  The new prd_readiness_count_findings check validates this very closure
  (Shaping 38 reconciles with the archived-card count).
  Claude-Session: https://claude.ai/code/session_01QAZHkJZsVbULEDmSaoJLid
  * ci: retrigger checks
  Claude-Session: https://claude.ai/code/session_01QAZHkJZsVbULEDmSaoJLid
  ---------
- `52eb4c5` backlog: capture execution skill planning false trigger (#398)
- `e3152e6` docs: file project registration onboarding bug
- `d1fa399` Merge pull request #399 from rafaelmjf/docs/project-registration-onboarding-gap
  File cloned-project registration and mobile TUI onboarding gap
- `172a0c9` docs: card the --remote-control seeded-prompt regression (#386) (#400)
  `--remote-control [name]` takes an optional value, so Commander eats the
  next non-`-` token as the RC session name. `interactive_command` appends
  the bare flag and then the positional prompt, so every seeded interactive
  Claude launch since #386 has had its prompt swallowed: no handoff
  delivered, and RC not active at spawn (the multi-line name is rejected).
  Root-caused live from this machine's session argv, reproduced with a
  one-line `-p` probe, and both candidate fixes verified against the live
  binary. Filed ready/autonomy-eligible with the `--` separator remedy and
  the combined-case regression test the suite is missing.
  Claude-Session: https://claude.ai/code/session_01Wydt7hUHBsZZt35NSsn8gj
- `c41225d` docs: card the Vision contract's missing intent and audiences (#401)
  Every place Horus specifies a Vision asks for the same triplet — what the
  project is, its shape, its boundaries (templates.py:35/:264,
  skills.py:516/:1127). All three describe the destination. None asks why the
  project exists, what it deliberately inherited, or who each surface serves.
  Field failure 2026-07-25 in fabric-build: an Opus 5 session with a fine
  resume prompt and a fresh PRD recommended retiring ~193 inherited files that
  are a deliberate offering and the preset path's fixture, identified an
  interactive human command as the agent contract, and proposed fab
  passthrough verbs. Owner corrections were the only thing that caught it.
  The owner located the defect: sessions in the parent metadata repo never get
  this wrong, because there the product is the framework and deploy/ is
  tooling, so surface audience never needs stating. In the fork the product IS
  the command surface, so it does — and the files travelled while the audience
  model did not. horus-infer makes it systematic: it distils inherited docs,
  which describe the parent's product.
  Filed ready/eligible with the exact replacement text. Evidence that these
  are the right two elements: the failed session's own deliverable converged
  on all of them.
  Claude-Session: https://claude.ai/code/session_01Wydt7hUHBsZZt35NSsn8gj
- `90e3fb1` fix(claude): end option parsing before the seeded prompt (#403)
  `claude --remote-control [name]` takes an optional value, so Commander
  consumed the positional initial prompt as the Remote Control session name.
  Every seeded interactive launch since #386 (v0.0.74) — resume handoffs, card
  scopes, dispatch briefs — started unseeded, and Remote Control did not come
  up, both silently.
  Emit `--` before the prompt so it is unambiguously positional. This guards
  any future optional-value flag, keeps Claude's own derived session name, and
  additionally protects prompts beginning with `-`.
  The existing tests asserted `--remote-control` in argv and, separately, that
  the prompt was present; neither exercised the combination. Add the combined
  case asserting adjacency.
  Codex is unaffected — no optional-value flag precedes its prompt.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `828b936` fix(codex): guard isolated account identity (#404)
- `e90eee0` fix(vision): ask for intent and audiences, not just the destination (#405)
  Every place Horus specified a Vision asked for the same triplet -- what the
  project is, its shape, its boundaries. Three present-tense descriptions of the
  destination. None asked why the project exists, what it deliberately inherited,
  or who each surface serves.
  Field failure 2026-07-25 in fabric-build: a session with a fresh PRD and a fine
  resume prompt recommended retiring ~193 inherited files that are a deliberate
  offering, mistook an interactive human command for the agent contract, and
  proposed passthrough verbs. Sessions in the parent metadata repo never get this
  wrong -- there the product is the framework, so surface audience never needs
  stating, and the audience model did not travel at the split.
  Adds "Why this exists" and "Surfaces and audiences" to the Vision contract in
  all four places (managed block, PRD template, and both horus-infer routines),
  and makes horus-infer ask the owner for intent on a fork/split/pivot rather
  than distilling the parent's docs. BLOCK_VERSION 12->13 and horus-infer 4->5 so
  upgrade-project refreshes downstream projects.
  Per the card: no gate or lint, no review-provenance field, no new frontmatter
  field.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `da0ddc2` test: isolate the ambient agent config dirs suite-wide (#406)
  ~20 test helpers fake HOME to point Horus's config/cache tree at a tmp dir, but
  CLAUDE_CONFIG_DIR and CODEX_HOME are resolved ahead of HOME when locating an
  agent's config/credentials (config.py:787), and account isolation always sets
  both. A faked HOME therefore left a real logged-in account dir reachable.
  An autouse fixture in a new tests/conftest.py clears both for every test, so
  "isolated fake HOME" means it. Suite-green: 2233 passed.
  Hardening, NOT a verified fix. It was prompted by
  test_capture_usage_snapshot_unavailable_on_failed_read returning 'fresh'
  instead of 'unavailable' twice on unmodified main, which blocked a dispatched
  worker's delivery -- but that symptom did not reproduce afterwards with or
  without this fixture, and the mechanism is still unidentified. Filed as
  usage-snapshot-test-flake-blocks-workers with the refuted hypotheses recorded;
  do not close that card on this commit.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `c9f02af` bug(backlog): codex usage stale-snapshot gates dispatch (2 readers disagree) (#391)
  * bug(backlog): file codex-usage-stale-snapshot-gates-dispatch
  Owner-reported from an agentic-travel-guide dispatch: horus run preflight
  refused a codex leg on a stale/wrong weekly-usage read (99% used) while
  `horus usage check` said 21% and ground truth was ~0% used. Two readers
  disagree over the same window; a best-effort snapshot is used as an
  authoritative dispatch gate. Distinct from codex-usage-window-semantics
  (labeling/display, deferred).
  Claude-Session: https://claude.ai/code/session_01CJqw3FXA3F89VbsNYAE9XY
  * backlog: add today's live evidence to codex-usage bug + follow-up research card
  - codex-usage-stale-snapshot-gates-dispatch: ## Reviews entry with the 2026-07-23
    tabi-triage-1 evidence — forced codex leg ran to completion + merged (PR #37,
    4a6efa5) on an account the gate declared 99%-exhausted; usage check said 21%;
    ChatGPT ~0% used. False refusal, two readers disagree.
  - dispatch-workflow-comparative-study (type: research): follow-up comparing our
    dispatch/continuity/backlog workflow to other existing agent-workflow systems.
  Claude-Session: https://claude.ai/code/session_01CJqw3FXA3F89VbsNYAE9XY
  * research: sharpen dispatch-workflow-comparative-study to the continuity-cost crux
  Focus narrowed (owner): capability + use case are settled; the live question is
  proportional continuity. Added a starting-point ## Findings from the tabi-triage-1
  run — the ceremony-vs-leverage placement, and the diagnosis that continuity cost
  scaled with concurrency (3 workers each rewrote shared PRD.md → 3-way conflicts)
  while per-card files merged cleanly. Recorded 4 design directions to test
  (append-only per-unit receipts; batch-boundary synthesis; supervisor-only
  frontmatter; delivery-granularity workers) and pointed the continuity research
  question at concrete prior-art patterns.
  Claude-Session: https://claude.ai/code/session_01CJqw3FXA3F89VbsNYAE9XY
  * backlog: land the stranded usage card + refine two bugs to Ready
  The codex-usage-stale-snapshot-gates-dispatch card has sat on this unmerged
  branch since 2026-07-23, so it was invisible to the local backlog. A session
  today hit exactly that defect in horus-harness, re-diagnosed it from scratch,
  and nearly filed a duplicate. Landing it, with today's evidence appended.
  New evidence closes the staleness leg end-to-end: `usage all` reported weekly
  82% from a rollout ~27h old while the owner had reset to ~100% available, both
  `horus run` launches warned "closing window" on it, and the dispatched worker's
  own readings went start=5h=82% -> end=5h=1% -- one real Codex turn collapsed the
  stale figure. The two readers also disagreed again, differently: `usage all` gave
  a confident 82% while `usage check` called the same account's window stale with a
  DIFFERENT reset timestamp, so the paths select different rollouts.
  Refinement pass (owner-attended), two bugs to Ready/eligible:
  - backlog-default-list: confirmed `list` (not --tree) as the bare default,
    matching how `sessions`/`status` answer bare. Added surface + acceptance.
  - close-check-unclassified-cards-advisory: the embedded gate-semantics decision
    is made -- five freshness conditions are the complete hard-block set, no
    card-readiness state ever blocks merge, a `blocking` state declined. Acceptance
    is now deterministic, so attended -> eligible.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
  ---------
- `5a0a67f` fix(skills): make horus execution delegation-only (#407)
- `ed0dcd5` fix: default backlog command to list (#408)

- `1fa00b3` fix: make close-check readiness warnings advisory (#409)

- `7b6334d` fix(instructions): put process corrections in the process, not agent memory (#410)
  Owner rule (2026-07-20): a mistake that is an error in the PROCESS must be
  fixed in the process -- skills, managed blocks, PRD rules, cards -- never only
  in an agent's private memory, because memories are not shared across agents,
  accounts, or machines.
  The observed instance was itself that failure: after auto-merging a format
  contract change without a rendered confirmation, the corrective
  "render-confirm before merging" discipline was written into the Claude agent's
  memory, invisible to Codex and to every other account and machine.
  Adds one bullet to the managed block's working discipline, so it reaches every
  project, both agents, and all machines on upgrade. Capped at one bullet on
  purpose -- this text loads in every session -- and a test asserts that cap
  alongside the wording. BLOCK_VERSION 13->14 so upgrade-project refreshes
  downstream projects; this repo's own CLAUDE.md/AGENTS.md regenerated through
  `horus upgrade-project --apply`.
  Also records the card's memory sweep: the questionnaire format and the receipt
  spines were verified to already live in horus/skills.py, so the render-confirm
  discipline was the only 2026-07-20 correction that was memory-only.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `130eb11` rules: card what you won't do now; fix what you will (#411)
  Owner-raised: carding small tasks that could just be solved adds bureaucracy
  with no durability benefit. A card's only job is to carry work across a context
  boundary, so if it gets fixed in this session the card is pure overhead -- the
  commit and PR are already the record.
  The test is not size, it is whether the work must survive the boundary. Found
  something small and fixing it now would not derail the work in hand -> fix it,
  in its own commit, and say so. Card it only when genuinely not doing it now:
  needs an owner decision, blocked, would derail the task, or too large for the
  session. The "own commit" clause is load-bearing -- without it "just fix it"
  becomes a licence to smuggle unrelated changes into whatever PR is open.
  Evidence from today: backlog-default-list was a ~10-line argparse fix that was
  carded, waited six days, then consumed a refinement exchange, a dispatch, a
  supervisor review cycle, a PR, a merge and a ship stamp.
  Placed in PRD Rules rather than the managed block -- cheapest rung on the
  instruction ladder, no BLOCK_VERSION bump, and no growth in text every session
  loads (the block already gained a bullet today in #410, and
  managed-instruction-drift-lint is open against it). Promote on evidence.
  Also corrects the v0.0.73 Shipped entry in the same commit, because it is the
  finding that motivated the rule rather than an unrelated change: it claimed the
  mode-axis deletion preserved "delegation-trigger and inline-batch
  card-vs-finding rules". Only the delegation-trigger rule survived; the
  card-vs-finding rule is in neither PRD Rules, horus/skills.py, nor the
  projected skills -- it lived in the deleted mode-skill text. The new rule now
  covers that ground.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `dee776d` fix: surface unregistered Horus projects (#412)
- `8ef48b3` fix(codex): the identity guard was still skipped on the PTY-hosted path (#413)
  #404 fixed `codex-identity-guard` in launch.prepare_interactive, because the
  card's `surface:` named only horus/launch.py:92. pty_host.py carries its own
  copy of the same guard and was left reading `config_dirs` directly:
      if account and getattr(adapter, "config_dirs", {}).get(account) and ...
  The Codex adapter has no `config_dirs` (it exposes `codex_homes`), so that
  getattr returns {}, the lookup is None, and the guard SILENTLY DOES NOT RUN --
  the exact defect the card exists to fix, still live on the dashboard-hosted
  launch path. Measured: adapters.account_dirs(codex) is non-empty where
  getattr(adapter,"config_dirs",{}) was empty, so "guard runs" goes False -> True.
  Rather than copy launch.py's three-line resolution into a second place -- which
  is the drift that caused this -- adds one shared accessor,
  `adapters.account_dirs(adapter)`, and routes both paths through it. An adapter
  that names its dir map something new now fails in one place instead of silently
  skipping a guard in another. Also aligns pty_host's mismatch message with the
  alias suffix #404 gave launch.py.
  Tests lock both halves: the accessor across claude/codex/fake, and a source
  assertion that pty_host no longer reaches for `config_dirs` directly.
  Found while probing #404 pre-release: the four dispatched Codex workers this
  session all used the headless path, so nothing had exercised the attended or
  hosted guards. Direct probe confirmed launch.py's guard is correct
  (verify_account('personal') -> ok=True, alias 'personal', no false refusal);
  pty_host's was not reached at all.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `9a24a15` Bump version to 0.0.75 (#414)
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `708d952` fix(adapters): name the identity an account check actually found (#415)
  `IdentityCheck.detected_email` held an email for Claude and an opaque
  account_id for Codex, and the two SHARED mismatch messages in launch.py and
  pty_host.py printed it bare:
      account 'personal' login mismatch (found 6d67cc97-1f90-4dd5-af80-3558e3628b0e,
      alias 'personal').
  A UUID with no indication of what it is. The adapters' own messages already
  labelled it correctly ("account_id is ..."), so only the shared paths were
  opaque -- and the field name was the root cause, since it described one agent's
  identifier shape as if it were universal.
  Three changes:
  - rename `detected_email` -> `detected_identity`, with a docstring stating it is
    deliberately not named for one agent's shape and that the value stays RAW
    because config.alias_for() resolves it (prefixing it would break alias
    resolution -- the reason the obvious one-line fix was wrong);
  - add `AgentAdapter.identity_label`, defaulting to "identity", overridden to
    "login email" (Claude) and "account id" (Codex);
  - interpolate that label in all four messages, so they read consistently:
      account 'personal' login mismatch (found account id 6d67cc97-..., alias
      'personal').
  Tests lock the labels per adapter (including the base default via `fake`), the
  absence of the old field name, and -- as a guard against reverting -- that
  neither shared path prints `found {check.detected_identity` without a label.
  Deferred from pre-release on purpose: it touches a guard's error path, and the
  release was better off without it. Suite 2249.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
