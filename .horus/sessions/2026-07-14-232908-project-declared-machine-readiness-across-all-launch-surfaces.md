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

- `3a71f33` test: assert the precondition that made the usage-snapshot flake invisible (#416)
  Reproduced the flake on demand and identified the mechanism, which the card had
  recorded as unknown with this hypothesis REFUTED. The refutation was wrong.
  claude_usage.credentials_path() resolves CLAUDE_CONFIG_DIR ahead of HOME, so
  faking HOME isolated the usage CACHE but never the CREDENTIALS. The test read
  the real logged-in account, made a live authenticated call to the usage
  endpoint, and got `fresh` back:
      credentials_path(): .../claude-personal/.credentials.json exists: True
      _oauth_token()    : <token>   (0.00s)
      fetch_usage()     : PAYLOAD   (0.86s)
  A/B on the #406 fixture, same machine, minutes apart:
      WITH    tests/conftest.py -> 1 passed
      WITHOUT tests/conftest.py -> FAILED ... assert 'fresh' == 'unavailable'
  So #406 WAS the fix, despite being committed as "hardening, NOT a verified
  fix". The original A/B misled because this test passes when the live call FAILS
  and fails when it SUCCEEDS -- it ran during a window where the call was failing,
  and a green test was misread as refuting the hypothesis.
  This commit adds only the hardening: assert the PRECONDITION (credentials are
  genuinely unreachable) before asserting the outcome, so a regression fails at
  that line naming CLAUDE_CONFIG_DIR and the conftest fixture, instead of
  resurfacing as an unexplained `assert 'fresh' == 'unavailable'`. Verified by
  removing the fixture and watching the new diagnostic fire.
  Green on CI forever because CI has no credentials -- which is precisely how it
  survived to cost a dispatched worker its delivery.
  Suite 2249.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `1e187de` backlog: librarian receipt + hygiene (satisfied deps, stale count)
  Ships the usage-snapshot-test-flake card (PR #416) that was left uncommitted,
  corrects the PRD Shaping count 38->37, and records the v0.0.75-era flake
  resolution in Shipped.
  Adds .horus/audits/2026-07-26-backlog-librarian.md — one advisory receipt over
  70 active / 121 archived cards. Five actionable findings, none applied (the
  librarian is advisory by contract):
    L1 tui-backlog-refine-and-order [high] is Gated on backlog-readiness-
       disposition, which is archived as status: shipped. Its own reason says the
       gate would make it Ready-Attended, so a high-priority card has been blocked
       on delivered work.
    L2 explore-converge-lifecycle carries a satisfied depends-on (roadmap-
       convergence, shipped) but its real gate is different -- remove the field,
       keep deferred.
    L3 codex-isolated-config-leak's Related note still attributes plugin-parity
       companionship to remedy 1, but remedy 3 was chosen 2026-07-26.
    L4 PRD Shaping count (fixed in this commit).
    L5 horus-wiki-readmodel: 563 lines on origin/spike/horus-wiki-readmodel with
       no card at all.
  Clean: no stale cards (>56d), no duplicates (13 pairs compared, cap 25, no
  truncation), no broken links (8 apparent dangles resolve to .horus/research/
  docs), no lingering terminal states, no unclassified cards.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `86a37fc` backlog: apply librarian L1-L3 and retire three dead branches
  L1 tui-backlog-refine-and-order [high]: Gated -> Ready/attended. Its
     depends-on (backlog-readiness-disposition) resolved to an archived card with
     status: shipped, while the card's own reason named that as the ONLY
     precondition ("then this becomes Ready-Attended"). A high-priority card had
     been blocked on already-delivered work.
  L2 explore-converge-lifecycle: removed the satisfied depends-on
     (roadmap-convergence, shipped). Readiness deliberately UNCHANGED -- its real
     gate (a per-card usage signal) is different and still unmet.
  L3 codex-isolated-config-leak: the Related note still described remedy 1's
     consequence for plugin parity, but remedy 3 was chosen 2026-07-26. Rewritten
     for the chosen remedy (a fresh `codex login` dir carries no plugin block
     either, so parity remains a companion -- for a different reason).
  PRD counts corrected: Ready-Attended 1->2, Gated 7->6.
  Deleted three provably dead remote branches:
    fix/codex-usage-stale-cache     -- its fix (494f897) is already in main;
                                       only a stale continuity commit remained
    design/process-tree-orphan-reap -- card archived in main as status: retired,
                                       with MORE content than the branch
    feat/pwa-installable            -- PWA already landed by another route
                                       (dashboard manifest/SW + assets/icon-512)
  Kept: spike/horus-wiki-readmodel (563 lines, no card -- librarian L5).
  Left alone: PR #117 feat/structure-staleness-migration; it is arguably moot (all
  10 registered projects are already v3) but that is an open PR with real code,
  so closing it is the owner's call, not a branch cleanup.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `18c0050` fix(datums): label Codex lanes by declared length, not slot order (#417)
  `_codex_usage_entry` read the rate-limit lanes POSITIONALLY --
  primary->pct_5h, secondary->pct_weekly -- while `usage_snapshot` and
  `usage check` both classify via `report.windows()`, which uses the length Codex
  declared for each lane. Since Codex lifted the 5-hour limit it reports ONE
  window, a weekly one, in the primary slot; the datum path therefore recorded a
  weekly percentage as `pct_5h`.
  Observed live 2026-07-26: for the same account at the same moment `horus usage
  all` rendered `5h - · weekly 82%` while the worker datum recorded `pct_5h=82`.
  Today's dispatch actuals ("start=5h=82% -> end=5h=1%") were weekly readings all
  along. Datums feed `horus capabilities --models` and the delegation rubric, so
  a mislabelled lane silently corrupts calibration data.
  Also fixes staleness, which was judged on `primary_resets_at` -- the same
  positional assumption -- so a weekly reading sitting in the primary slot was
  assessed as if it were the fast lane. Now any lane past its OWN reset is stale.
  Owner input (2026-07-26): weekly-only is likely the NEW NORMAL for Codex rather
  than a temporary state, which is what makes this worth correcting now instead of
  watching.
  The three existing tests used hand-rolled stubs declaring only the positional
  fields, so they could not exercise `windows()` -- exactly how this drifted.
  Replaced with a builder returning a REAL `codex_usage.UsageReport`, plus three
  regressions: weekly-only is never recorded as 5h, a fast lane in the secondary
  slot is still 5h, and staleness follows the lane whose own reset passed.
  Live after the fix: datum reads pct_weekly=6.0 with no pct_5h, agreeing with
  `usage all`. Suite 2252.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `cdcd435` fix(usage): say the percent is USED, and lock that orientation (#418)
  A bare "weekly 6%" reads equally well as "6% used" or "6% left". The owner read
  it the second way on 2026-07-26 and asked to invert the Codex calc so it would
  match Claude.
  Both providers already report USED and Horus was already consistent. Ground
  truth from a live rollout:
      "rate_limits":{"primary":{"used_percent":6.0,"window_minutes":10080,
                                "resets_at":1785668181},"secondary":null}
  Codex's field is literally `used_percent`; Claude's is `utilization`. Inverting
  would have turned 6% used into 94% used, so the run preflight (PREFLIGHT_REFUSE
  = 95) would start refusing launches on a nearly EMPTY account -- and would wave
  through an exhausted one. The apparent conflict was staleness, not orientation:
  the 82% that looked wrong was a 27h-old pre-reset reading, and a fresh one read
  2% used, which agrees with the owner's "~100% available".
  So no calc changed. Instead the orientation is now stated where it is read:
    - `usage all` header: "Usage — all accounts (% USED, 5h · weekly)" -- in the
      header rather than per cell, so phone-width rows stay short;
    - `usage check`: "weekly limit 6% used (resets ...)" for both providers;
    - run preflight: "{who} has USED 96% of its weekly window (resets ...)".
  And two contract tests pin it: the parsers must keep reading `used_percent` /
  `utilization` and must not parse a remaining-oriented field, and the thresholds
  must stay ordered so a HIGHER percent means LESS headroom -- true only under
  used-orientation. The question was asked from memory; now it is checkable.
  Suite 2251.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `ad3d06c` fix(codex): usage readers were blind to isolated account homes (#419)
  `latest_account_usage` and `latest_usage` both fell back to `codex_home()` --
  $CODEX_HOME or ~/.codex -- when no home was passed. Three callers do exactly
  that: closure.py:570, cli.py:3415 (`usage check`) and dashboard.py:237.
  Under Horus account isolation that home never sees a real session. Every
  isolated run writes its rollouts into the ACCOUNT's own CODEX_HOME, so the
  ambient home only accumulates non-isolated runs and goes permanently stale --
  these readers could not report current Codex usage at all, by construction.
  Measured on this machine:
      ~/.codex/sessions                          newest rollout 2026-07-19
      ~/.horus/accounts/codex-personal/sessions  newest rollout 2026-07-26
  which is exactly why `usage check` said "weekly limit snapshot stale (reset
  2026-07-25)" while `usage all` -- which resolves the per-account home -- read
  6% correctly. That is the "two readers disagree" half of
  codex-usage-stale-snapshot-gates-dispatch, and the disagreement was never about
  rollout selection within a home: they were reading DIFFERENT HOMES.
  With no explicit home, both readers now scan every known home (configured
  account homes first, then ambient, de-duplicated) and let the newest observation
  win. An explicit home stays authoritative, so `usage all` is unchanged.
  Applies to the project-context read too, deliberately: it had the same defect
  for the same reason, which is why `usage check` also reported a week-old 20.0%
  context where the true figure is 74.2%.
  Known limitation, documented in the helper: with several configured accounts a
  homeless read can mix them. The per-account view is `horus usage all`, which
  always passes an explicit home.
  All three surfaces now agree: weekly 6% used, resets 2026-08-02 12:56.
  Suite 2256.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `d158bf4` feat(closure): surface unmerged remote branches (#420)
  Fetch-first guidance already exists and is not sufficient on its own. On
  2026-07-26 a session fetched, then still opened a duplicate PR (#402) for a card
  that had already merged as #401, and separately re-diagnosed a defect from
  scratch because its card sat on PR #391, open since 07-23.
  Both share one cause: `gh pr list` shows only OPEN PRs and nothing inspects
  branches, so work living on an unmerged ref is invisible to every check a
  session actually runs. Five such branches existed that day, carrying real cards
  and 563 lines of code.
  Guidance was the cheap rung and it was already in place, so this promotes one
  rung to a deterministic signal: `close --check` / the boundary gate now name
  unmerged remote branches, oldest first, and add an explicit "invisible to `gh pr
  list`" advisory once the oldest passes UNMERGED_BRANCH_STALE_DAYS (3).
  Rendered at `info`, exactly like parallel deliveries: a supervisor legitimately
  closes with branches in flight, so it must be visible without ever flipping a
  fresh verdict to stale.
  Best-effort throughout -- an unusable git, a missing origin/HEAD, or unparseable
  dates all resolve to silence rather than a false alarm. The default branch and
  HEAD are excluded.
  Verified live in both directions: silent at zero unmerged branches, and naming
  the branch once one exists. Suite 2262.
  From the 2026-07-26 process retrospective, recommendation R1.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `eb26b63` docs(backlog-refine): a card's `surface` is a hint, not a boundary (#421)
  Twice on 2026-07-26 an implementer scoped itself faithfully to a card's
  `surface:` list and correctly left everything else alone:
    codex-identity-guard (#404) named horus/launch.py, so pty_host.py's second
    copy of the same guard went untouched -- it shipped as a HALF-FIX, and the
    gap was found only by probing a different surface before a release.
    project-registration-onboarding-gap omitted horus/skills.py and
    horus/templates.py, the two files carrying the guidance text its own control 1
    required.
  Neither was worker error. Both workers did exactly as briefed and CI was green
  on the exact SHA. The defect is that `surface` reads as a boundary while being
  hand-written and unverified.
  backlog-refine v5 now states that it is a HINT, requires the implementer to
  report any file touched beyond it and why, and records WHY this stays guidance:
  a hand-written list cannot be mechanically verified as complete, and a check
  demanding it would only teach people to pad the field.
  The cheap control is already proven -- the project-registration worker was
  briefed with exactly that reporting line and duly surfaced four files the card
  never named, which is how the supervisor knew where to look.
  Projections regenerated for both agents; the existing version pin moved 4 -> 5.
  Suite 2258.
  From the 2026-07-26 process retrospective, recommendation R2.
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `7d1b96e` Bump version to 0.0.76 (#422)
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369
- `d694a4d` fix(deploy): wait for the service to bind before judging the deploy (#423)
  `deploy-hosted.sh` restarted the unit, slept 2 seconds, then probed /health and /
  exactly once. That races systemd. Observed on the 0.0.76 deploy: /health came
  back unreachable, / returned 000, the script printed an "it may be ungated"
  warning and exited 1 -- while the service was in fact healthy moments later
  (active, --exposed, /health version 0.0.76, / -> 403).
  A false failure here is not cosmetic. This script is the mandatory last step of
  every release and is intended to become the last step of an AUTOMATED one
  (CLAUDE.md: the webhook/self-hosted-runner is the eventual hard guarantee); a
  verdict that flaps would fail good deploys and train people to ignore it.
  Now polls /health for up to ~30s and proceeds as soon as it answers. The
  subsequent assertions are unchanged -- / must still be 403, and the running
  version must still match the target -- so a genuinely broken deploy fails
  exactly as before.
  Verified by re-running the real deploy: the same restart that produced the false
  failure now reports "done; running version 0.0.76 matches target".
  Claude-Session: https://claude.ai/code/session_014Z2jLATWKLECzqWk49X369

- `1ff7e0e` docs: card the --resume session id mismatch (#424)
  `horus sessions` and `horus tail` show the horus session id; `horus run
  --resume` needs the agent session id. Passing the visible one exits
  rc=1 in two seconds with no error text.
  Observed while resuming a worker in another project: the run jsonl
  records agent_session_id set to the horus id that was passed in, and the
  result event is a bare failure. The healthy run records the id the agent
  actually issued.
  Worth fixing rather than documenting because the failure is silent and
  the only id the operator has been shown is the wrong one. Inside a
  scheduled supervise/resume loop it would read as a crashed worker rather
  than a bad argument.
  Three candidate remedies on the card; accepting either id subsumes the
  others. Whichever is chosen, the error path should not exit rc=1 with no
  text.
  Claude-Session: https://claude.ai/code/session_016BGnNJHdmf9KPtsvegymXL
- `9297624` feat(backlog): sparse `order:` sequence + a one-key attended refine pass (#425)
  * feat(backlog): sparse `order:` sequence + a one-key attended refine pass
  `tui-backlog-refine-and-order`. The `backlog-refine` skill already owned the
  whole interactive contract *including* the ordering rules, and a 2026-07-21
  pass had already written `order: 20` onto `windows-native-horus-setup` — but
  nothing in Python parsed the field and no surface launched the pass. This
  supplies both halves.
  **The field.** `order:` parses to an int and joins `readiness_sort_key`, the
  single sort chokepoint every renderer already routes through (`backlog list`,
  `--tree`, the TUI), so the approved sequence needed writing once. It nests
  INSIDE the readiness queue: every renderer prints per queue, so a cross-queue
  sequence could not be displayed, and the plan that matters is the sequence of
  schedulable cards. Unordered cards keep today's priority ordering behind the
  stamped ones, so a repo that has never been ordered renders as before — zero
  migration. A non-integer stamp stays unsequenced rather than being coerced into
  a guessed position.
  **The launch surface.** `o` on the TUI's backlog pane runs the existing
  accounts -> launch_form pipeline with a refine prompt; `horus backlog refine`
  prints the same prompt for piping into `horus open`. One builder, two
  consumers. Neither restates the flow — the skill remains the single authority.
  **Live delivery state (owner addition).** A refine pass judges what is open
  work, and the cards alone cannot answer that: other sessions open bug PRs and
  leave branches unmerged, so a card already fixed on an open PR reads as
  untouched. The prompt embeds the deterministic facts — open PRs (via a new
  unfiltered `integration.open_prs`; the `horus/` prefix only ever caught
  continuity PRs), unmerged remote branches via #420's reader, and continuity
  freshness — instead of instructing a session to go look. Every probe degrades
  to a stated "unknown", never a false all-clear. Skill bumped v5 -> v6 with the
  same reconciliation as step 0, so a hand-invoked refine does it too.
  Duplicate/malformed stamps warn via `backlog.order_findings`, wired into
  `hygiene_findings` (consolidate + `close --check`) and printed by `backlog
  list`. This deviates from the card's "`horus doctor` warns" wording — doctor
  does not call hygiene_findings, and wiring it in would have emitted every
  existing card warning; owner-approved, recorded in the card's Reviews.
  Gate: full suite 2288 green (was 2264; ~24 new tests). Probe: a scratch repo
  with three stamped cards lists them in `order:` sequence ahead of the
  unstamped one, and removing a stamp drops that card to the pool; the TUI, run
  under an isolated tmux socket, shows `o refine+order` in its footer, sorts
  identically, and `o` lands on the account picker titled "Refine account".
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  * closure: backlog order/refine delivered; PRD handoff refreshed
  Folds PR #425 into canonical continuity, pre-merge because Horus's own gate
  refuses the merge while lanes are stale — the closure needs THIS session's
  context, which is gone afterward. Working as designed; it fired on me.
  - Shipped: one line for the `order:` field + its consumers, the two launch
    surfaces, and the owner's mid-session addition (the pass starts from live
    delivery state, because bug PRs other sessions open make a picture wrong).
  - Readiness breakdown corrected against `readiness_counts()`: Ready—eligible
    was stale at (1) since #424 added `resume-session-id-mismatch`, and the Gated
    prose still listed `tui-backlog-refine-and-order` as gated when the librarian
    had un-gated it on 07-26. Ready—Attended stays (2) until the card is shipped
    and archived post-merge.
  - `tui-toggle-card-into-scheduler` flagged for a readiness re-check: it was
    Gated on exactly the `order:` field that just shipped.
  - Distribution line corrected — it claimed v0.0.74 was current; v0.0.76 has
    been released and deployed since 07-26.
  - Frontmatter handoff refreshed. PRD is 236 lines: past the 235 advisory, 14
    short of the cap, and deliberately not trimmed — shaving it would mean
    deleting real shipped history.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  ---------
- `ad23575` closure: ship the refine/order card (#425, 9297624)
  Stamps merge provenance and archives the delivered card, then corrects the one
  count that shipping changes: Ready—Attended (2) -> (1). Deliberate two-step —
  the ship stamp needs the merge SHA, which does not exist until after the merge
  the freshness gate guards.
  Continuity-only diff on main, per the closure direct-push exemption.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
- `ff6c65a` fix(run): `--resume` accepts either session id, and says which it used (#426)
  `resume-session-id-mismatch`, remedy option 1 (accept either id) — the card's own
  recommendation, and it subsumes option 3.
  `horus sessions` and `horus tail` identify a run by its HORUS id; `--resume` needs
  the AGENT conversation id. The operator has only ever been shown the horus id, so
  that is the value they reach for, and passing it died in two seconds with rc=1 and
  nothing naming which of the two ids was wanted. Inside a scheduled supervise loop
  that reads as a crashed worker rather than a bad argument — the expensive version
  of this bug, and the one that would have muddied the away-mode drill.
  `Registry.resolve_resume_id` now translates: a known horus id becomes its recorded
  `agent_session_id` (saying so), an agent id passes through silently, and an id
  Horus never tracked passes through WITH a note rather than being refused — an agent
  session Horus never registered is legitimately resumable. Translation happens in
  `cmd_run` before the RunRequest, so the detached tmux runner receives an
  already-correct payload and both paths resume identically.
  **Lookup order is load-bearing.** The horus id is a row key, so it is checked before
  the agent-id scan: a failed resume attempt registers a fresh row whose
  `agent_session_id` is the bad horus id it was handed, so scanning agent ids first
  would match that self-inflicted row and feed the same wrong value back forever.
  Covered by a named regression test.
  Also: a failed run that used `--resume` now names the id it resumed with, so the
  rc=1 path can never again be textless about the cause.
  Files touched beyond the card's `surface` list (which named only the run/`--resume`
  handling, the sessions display, and the run jsonl): `horus/registry.py` holds the
  translation, and `horus/run_executor.py` holds the failure message. The sessions
  display was deliberately NOT changed — that was option 2, and option 1 makes it
  unnecessary.
  Gate: full suite 2297 green. Probe: with the fake adapter under an isolated HOME,
  `--resume <horus id>` translates and resumes, `--resume <agent id>` is silent,
  an untracked id warns and still launches, and re-resuming the original visible id
  after a failed-attempt row exists still resolves correctly.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
- `52ecc0b` fix(usage): a stale reading may warn, but must never refuse a launch (#429)
  * fix(usage): a stale reading may warn, but must never refuse a launch
  The last open acceptance item on `codex-usage-stale-snapshot-gates-dispatch`.
  A best-effort telemetry snapshot was being used as an authoritative gate. On
  2026-07-23 it refused a valid `--worker codex --account personal` dispatch at
  "99% used" on an account that was ~0% used; `--force` got the work through and it
  ran to completion and merged a PR. Reproduced here 2026-07-26 from a rollout ~27h
  old, where the next real Codex turn collapsed 82% to ~1%.
  `UsageSnapshot` now carries `captured_at` — the PROVIDER's capture time, not
  Horus's cache time. That distinction is the whole fix: Codex reports capacity only
  when it takes a turn, so an idle account yields an hours-old rollout served through
  a seconds-old cache entry. `_read_codex` populates it from the rollout event's own
  timestamp, which was being discarded. A reading older than
  `REFUSAL_MAX_READING_AGE` (2h) can still WARN but can no longer REFUSE.
  Horizon rationale, because it is a judgment call: the cost is asymmetric. A false
  refusal blocks legitimate dispatch and teaches `--force`, which disables the gate
  wholesale; a false green-light merely lets a run die in a window it would have died
  in anyway, which the run itself reports. Only the refusal is gated on freshness —
  the advisory bands still fire, because "possibly low" is exactly what an old
  reading can honestly say. Readings with no capture time (Claude's pushed statusline)
  keep refusing unchanged.
  NOTE — the previous session's handoff proposed a different rule, and it is wrong:
  "a reading predating `resets_at - window_minutes*60` describes a previous window."
  That can never fire. A reading is always captured inside the window its own
  `resets_at` closes, so the test is equivalent to the `without_expired_windows`
  check that already exists. Verified against this card's own reproduced case:
  capture 07-25 09:48, resets_at 07-29 20:53, weekly window 10080min → span
  [07-22 20:53, 07-29 20:53]; the capture sits inside it, so the formula scores that
  reading FRESH — the very reading documented as stale and wrongly refusing. The
  card's own acceptance bullet asks for "a reading older than a documented horizon",
  which is what shipped. Recorded in the card's Reviews.
  Gate: full suite 2306 green. Probe: with real rollout fixtures under an isolated
  CODEX_HOME, a 99% reading captured 2d ago (window resets in 2 days, so NOT expired
  — exactly the gap `without_expired_windows` misses) now warns and proceeds, while
  the same 99% captured now still refuses with exit 2.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  * fix(usage): `usage check` says when a Codex reading is stale
  Completes the same acceptance item rather than leaving a one-liner open. The card's
  own diagnosis was that an idle account's percentage is "presented as current with no
  staleness signal" — and `usage check` was still doing exactly that, printing a bare
  `weekly limit 99% used` from a rollout captured two days earlier.
  `UsageReport.timestamp` was already the capture time, so this only renders it. The
  horizon is imported from `usage_snapshot` rather than redefined, so this surface and
  the `horus run` refusal gate cannot drift apart (lazy import, since usage_snapshot
  reads this module).
  Verified while checking the card's OTHER acceptance items rather than trusting the
  PRD's account of them: against one stale rollout fixture, `usage all`, `usage check`,
  and the run preflight now all report the same window (weekly), the same orientation
  (used), the same percentage, and the same reset — which was the card's core "two
  readers disagree" complaint, and it holds.
  Gate: full suite 2308 green. Probe: a 2-day-old 99% reading now renders "reading
  captured 2026-07-25 11:48 — Codex has been idle since, so these limit percentages
  are not current"; the same reading captured now prints no staleness noise.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  * closure: fold #426/#427 into continuity ahead of the merge
  Both dispatch-path fixes recorded in one Shipped line, plus the frontmatter handoff
  for a session that may or may not cut the release.
  Corrections found by checking claims rather than trusting them:
  - `tui-toggle-card-into-scheduler` is STILL correctly gated. I flagged it earlier
    for a readiness re-check because #425 cleared its `order:` dependency; it also
    depends on `autotest-e2e-away-mode-drill`, and arming cards for unattended
    execution before the drill answers its readiness question is exactly what the
    drill exists to prevent. The PRD now says so, so the next session doesn't
    re-litigate it.
  - The Shaping prose still named `usage-snapshot-test-flake-blocks-workers` as the
    highest-value bug; it shipped in #416 and is archived.
  - `codex-usage-stale-snapshot-gates-dispatch` is marked as delivered-pending-ship
    rather than silently left in Shaping.
  Handoff states plainly that v0.0.76 is still the published version and nothing
  since is released, and repeats the invariant that `deploy-hosted.sh` must be the
  last release step or the hosted app stays on the old pin.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  ---------
- `d7ce84b` test: drop 15 hardcoded skill-version assertions (#428)
  * test: drop 15 hardcoded skill-version assertions
  Answering "are all these tests necessary?" with the one category that provably
  isn't. The suite is not the problem — 2308 tests run in 76s (33ms each) and test
  LOC is 0.78x prod LOC across 44k lines. Volume is fine; this is about edit
  friction.
  `assert refine.version == 6` and its fourteen siblings cannot catch a defect.
  They assert only that a human typed the same integer in the test as in the
  registry, and they break on every legitimate bump — I paid that cost four times
  in this session alone while bumping backlog-refine v5 -> v6.
  The two guards that DO catch real drift are untouched:
  - `test_bundled_skills_have_version_markers` asserts, for every skill,
    `installed_version(s.content) == s.version` — the marker-vs-registry
    disagreement that actually breaks version-aware installs;
  - `test_backlog_refine_projections_match_the_bumped_source` asserts the
    checked-in projection carries the bundled version, DERIVED dynamically
    (`next(s.version for s in skills.SKILLS ...)`) rather than hardcoded. That
    test caught a real miss today when I bumped the skill without regenerating
    the projections. It is also the pattern the deleted lines should have used.
  No test lost its last assertion (checked by AST walk); 49 tests in
  tests/test_skills.py still pass, full suite still 2308.
  Known gap this exposes, NOT fixed here: nothing catches a skill's prose being
  edited without a version bump, so installed copies would silently never
  upgrade. The deleted assertions looked like they covered that but did not —
  they pass whether or not the text changed. Worth a card if the risk is real.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  * closure: release bundle folded in; both fixes shipped and archived
  Closes out the four-delivery bundle sitting on main, and records what the session
  learned rather than just what it built.
  - `resume-session-id-mismatch` shipped (#426, ff6c65a) and
    `codex-usage-stale-snapshot-gates-dispatch` shipped (#429, 52ecc0b); both cards
    archived. Readiness breakdown recomputed from `readiness_counts()` rather than
    edited by hand: Ready—eligible 1, Ready—Attended 1, Shaping 36.
  - The test-suite question answered with measurements that outlive the session
    (2308 tests / 76s / 0.78x prod LOC), so it does not get re-litigated, plus the
    prose-assertion judgment call left explicitly to the owner.
  - NEW RULE: never `--delete-branch` a PR that another PR is stacked on. Merging
    #426 that way auto-CLOSED #427, and a closed PR's base cannot be retargeted
    (422), so it had to be reopened as #429. The rule also records that stacked PRs
    get no CI at all while they target a non-main base, because the workflows
    trigger on `pull_request: branches: [main]`. Landing this in the process rather
    than in memory, per the project's own rule.
  - Handoff states plainly that nothing is released (still v0.0.76) and that
    `deploy-hosted.sh` must be the LAST step of any release, and flags that
    `verify-guidance-long-running-services` is now the ONLY Ready—eligible card —
    so an unattended loop with a free hand would pick exactly the reserved drill
    payload it must not touch.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  ---------
- `3c4343b` docs(block): name merge-watch in the gate rule; add wait discipline (block v14→15) (#430)
  * docs(block): name merge-watch in the gate rule; add wait discipline (v14->15)
  The two accepted retrospective controls for today's ~30 minutes of dead
  wall-clock, landed in the process rather than in agent memory — per the block's
  own rule about exactly that.
  R1: the "reproduce the gate" rule prescribed watching a required CI check on the
  exact commit but named no tool, so a session invents a mechanism. `horus
  merge-watch <pr|sha>` has done precisely this all along — bounded
  `--interval`/`--timeout`, prints each check as it resolves — and was mentioned
  ONCE in horus/skills.py and nowhere in CLAUDE.md, AGENTS.md, or PRD.md. Now named
  where the behavior is prescribed, with an explicit "do not hand-roll a polling
  loop for it".
  R2+R3, folded into one bullet because they share a root cause (a wait nobody can
  see failing): never discard stderr from a command whose output drives a loop
  condition or a gate; run a wait's exit condition once in the foreground and watch
  it produce output before backgrounding it; and account for a backgrounded wait
  before the turn ends rather than assuming its timeout bounds it.
  The incident is cited inline, briefly, because the rule is otherwise easy to read
  as generic hygiene: three loops on `gh pr checks --json` (a flag that does not
  exist in this gh) with `2>/dev/null` swallowing `unknown flag`, ~30 minutes; then
  a fourth still polling a DELETED PR an hour later, past its stated timeout,
  surfaced only by the owner noticing a task indicator. Without the silenced
  stderr the whole thing costs one second.
  Also: dropped the hardcoded "block v9" from CLAUDE.md's hand-written preamble
  (it was 6 versions stale, sits outside the managed block so upgrade-project never
  corrects it, and would rot again on the next bump). It points at the block's own
  marker instead — the same derive-don't-hardcode fix as #428.
  Gate: full suite 2308 green; `horus doctor instructions` reports blocks matched
  after regenerating both projections.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  * closure: record the retrospective and its two shipped controls
  Folds PR #430 (block v14->v15) into continuity. The retrospective itself leaves no
  artifact by design — the skill's rule is that accepted outcomes land in an existing
  surface, which here is the managed block plus this Shipped line.
  Two things recorded deliberately because they are easy to lose:
  - the measured exoneration (CI 9s/46s/47s, local suite steady ~71s), so "things are
    slow today" is not re-diagnosed from scratch next time;
  - that the retrospective's own "capped at two recommendations" conclusion was WRONG,
    and the owner found the third by spotting a task indicator while I was writing the
    analysis. A fourth loop was still polling a deleted PR an hour later with 0 bytes
    of output. The lesson that generalizes is about background waits surviving turn
    boundaries, not about gh flags.
  Also notes for the release decision that block v15 makes every other fleet project
  show an instructions advisory until it upgrades.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  ---------
- `9ff3139` closure: reserve the drill leg as Deferred+trigger, not as prose
  Outcome of a wildcard run plus the owner's clarifying question, which killed the
  skill's own proposal and left a better one.
  The finding: `is_autonomous_candidate()` returned exactly one card,
  `verify-guidance-long-running-services`, while `autotest-e2e-away-mode-drill`
  says that card "must NOT be implemented early — it is payload, not free work, and
  this session nearly took it". The deterministic selector was aiming an unattended
  loop at the one card that would destroy the drill, and the only thing preventing
  it was prose in the PRD and next_prompt — the authority the managed block
  explicitly says does not count.
  The wildcard proposed a new `reserved` frontmatter state. The owner asked what
  "reserved" meant, and the answer dissolved the proposal: `deferred` is already
  defined as "deliberately inactive until an explicit trigger or owner review",
  which is exactly this, and deferred cards are already excluded from
  `is_autonomous_candidate()`. No schema change, no code — the defect was one
  misclassified card. I had checked the candidate against other CARDS and never
  against the readiness vocabulary itself.
  So:
  - `verify-guidance-long-running-services` -> `readiness: deferred` with the release
    trigger named (drill armed and leg used/dropped, or drill abandoned), `autonomy`
    dropped since it belongs only on Ready cards; verdict recorded in its Reviews.
  - The drill card now states that reserving a leg IS an operation — set the card
    deferred + name the trigger — because "chosen and reserved now" previously had
    no mechanism, which is what produced the contradiction.
  - PRD: Ready—eligible 1->0, Deferred 24->25, both flagged by
    `prd_readiness_count_findings` before I touched them (#396 earning its keep), and
    next_action now says an empty eligible pool is the honest state and must NOT be
    refilled by promoting something.
  Recurring theme this session, third costume: prose in one artifact has no effect on
  another artifact's machine-readable state.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
- `b6dc99e` docs(block): cut branches from the default branch, not the current one (block v15→16) (#431)
  * docs(block): cut branches from the default branch, not the current one (v15->16)
  The upstream half of the stacked-PR rule added in #430. That rule says how to land
  a stack safely; this one prevents creating one by accident, which is what actually
  happened.
  Observed 2026-07-27: #426 (registry/run_executor) and #429 (usage_snapshot/
  codex_usage) shared exactly ONE file and touched different functions ~100 lines
  apart. They were never dependent — they were stacked purely because the checkout
  was standing on the earlier branch when the second was cut. That accident cost a
  PR: merging the parent with --delete-branch auto-closed the child, whose base
  could then not be retargeted.
  A stack is markedly more expensive than two siblings and the cost is not obvious
  up front: no CI at all while it targets a non-default base, and the parent's merge
  can destroy it. So the cheap habit is upstream of the careful one.
  WHAT THIS COMMIT IS NOT: I went looking for a code fix first and did not find one
  worth making. The candidate was the continuity/merge two-step (a card needs its
  merge SHA, which exists only after the merge the freshness gate guards). It does
  not survive evidence: all 102 archived cards have shipped_sha values that resolve
  to real commits, so hand-typed provenance has no observed failure class to guard;
  and the second write is mechanical and batchable — the block already says
  continuity is "a checkpoint at context boundaries, not a transaction log for every
  card". I was doing per-card transactions against a rule that already exists.
  Batching a bundle into one continuity commit then merging the bundle already
  works; 75df40e did exactly that for #426+#429.
  Gate: full suite 2308 green; `horus doctor instructions` blocks matched after
  regenerating both projections.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  * closure: record #431 and the code fix that failed its evidence test
  Folds the branch-from-default rule (block v16) into continuity, and — more usefully
  — records WHY the continuity/merge two-step did not become code, so it is not
  re-proposed: 102/102 archived cards have resolvable shipped_sha values, and the
  batching rule the friction violated already exists in the block.
  Also notes the session's recurring theme now that it has three instances: prose in
  one artifact has no effect on another artifact's machine-readable state.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  ---------
- `2025e7c` closure: correct the Vision's one genuinely stale card reference
  Found by the second wildcard run: the Vision presented `roadmap-convergence` as a
  current card alongside `explore-converge-lifecycle`, but it shipped and is archived.
  That was the ONLY genuinely misleading card reference in the document. The wildcard
  had flagged a much bigger-looking number — 12 of 27 card-shaped references in PRD
  prose point at archived cards — and rejected it as a candidate after checking WHERE
  each sits: they are overwhelmingly legitimate history in `## Shipped` and citations
  in `## Rules`. A naive lint would have fired ~12 times to catch this one, including
  on prose that explicitly explains a card already shipped. Recorded here so the
  "stale references!" finding is not re-raised as a defect.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
- `e4db28b` Bump version to 0.0.77 (#432)
  * Bump version to 0.0.77
  Cuts the release for six merged deliveries, none of which were reachable from an
  installed CLI. Timing is not arbitrary: `horus schedule` bakes
  `sys.executable -m horus` into the timer, so a scheduled dispatch runs whichever
  horus scheduled it. With `autotest-e2e-away-mode-drill` armed after 2026-07-29,
  staying on 0.0.76 would run the drill against exactly the two defects that were
  fixed to protect it — `--resume` accepting only the agent id (a bad argument reads
  as a crashed worker inside a supervise loop), and a stale usage reading able to
  hard-refuse the launch outright.
  In this release:
  - #425 sparse `order:` in the single sort chokepoint, `o` on the TUI backlog pane,
    `horus backlog refine`, and a refine prompt that embeds live delivery state
  - #426 `--resume` accepts either the horus or the agent session id
  - #429 a usage reading older than 2h may warn but never refuse; `usage check`
    names its capture time
  - #428 15 hardcoded skill-version assertions dropped
  - #430 block v15: `horus merge-watch` named in the reproduce-the-gate rule; wait
    discipline (no silenced stderr on a loop condition; account for backgrounded waits)
  - #431 block v16: cut branches from the default branch, not the current one
  Note for the fleet: block v14->v16 means every other initialized project shows an
  instructions advisory until it runs `horus upgrade-project`.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  * closure: cover the v0.0.77 bump before its merge
  The gate is pre-merge by design, so the release entry lands with the bump rather
  than after it. Records WHY the release was cut now instead of batched further —
  the scheduler bakes its own interpreter into the timer, so an unreleased fix does
  not protect the drill it was written for.
  Deployment verification (PyPI live, /health reporting 0.0.77, / still 403) is
  deliberately NOT claimed here; it goes in the closure once observed.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
  ---------
- `b3e455b` closure: v0.0.77 released, deployed and verified; session distilled
  Release verified independently rather than from the deploy script's own word:
  PyPI reports 0.0.77, hosted /health reports 0.0.77 with / still 403, the
  dashboard (system unit) and notify-listen (user unit) are both active, and the
  tag resolves to the bump commit e4db28b.
  Distilled the day's six Shipped entries into the single v0.0.77 release entry —
  the PRD's own "one line per capability" rule — taking the file 247 -> 237 lines.
  Kept only the findings that would cost real time to rediscover:
  - the resume lookup-order trap (a failed attempt poisons the registry with the
    bad id, so scanning agent ids before row keys feeds it back forever);
  - that the inherited staleness formula can NEVER fire, so it is not re-attempted;
  - the test-suite measurements, so "are all these tests necessary" has an answer;
  - the two code fixes withdrawn after testing, so they are not re-proposed;
  - the session theme, now at four instances: prose in one artifact has no effect
    on another artifact's machine-readable state.
  Handoff points the next session at the drill (genuinely unblocked now — 0.0.77
  carries both fixes written to protect it) and at a backlog-refine pass, which has
  never run despite the 2026-07-20 audit routing 7 prune candidates and 4 facet
  questions to it; its one-keypress launch shipped in this very release.
  Claude-Session: https://claude.ai/code/session_01N4YL3xmgsVvKWuTgHrUnq4
- `28bdf77` closure: refine 69 cards, retarget wildcard v1→v4, ship `horus sync`
  Session had three arcs. (1) An owner-attended `backlog-refine` pass over all 69
  cards — the first since the 2026-07-20 audit routed work to it. 13 decision
  screens, 56 approved no-change keeps. The finding outweighed the card movement:
  only 1 of 13 converted, because conversion tracks the KIND of open decision, not
  whether a card documents one — 83% of Shaping cards already carried an explicit
  open-decisions section. Hence `[refine]`/`[session]` tagging and a `refine_passes`
  counter, both landing via `refine-autonomy-hardening-lens`.
  (2) `wildcard` audited and rewritten v1→v4 across five live runs. Two of the three
  revisions fixed defects a *previous revision introduced* — most sharply v2's
  "promote-or-drop", which silently redefined the skill as subtractive and produced a
  run where 4 of 6 ideas were pruning proposals, i.e. refinement's authority. Lesson
  recorded in the receipt: re-read a revision against the skill's purpose, not only
  against the finding it was written for.
  (3) `horus sync` shipped (PR #433) closing the remedy half of fetch-first.
  Also closed for good, so no future planning run re-raises them: the 7 audit prune
  candidates (KEEP — resolution stamped into the audit receipt) and X5's undated hold
  (deliberate, not neglect). And the Vision gained the **Why this exists** +
  **Surfaces and audiences** sections that #405 shipped fleet-wide on 2026-07-25 but
  never applied to this repo's own PRD, because that card's `surface:` list omitted it.
  Known debt left as an owner decision, not hygiene: PRD.md is over the ~250-line cap
  and a real distillation means promoting Shipped method lessons into Rules.
  Claude-Session: https://claude.ai/code/session_01HibUJ7ufbu7LtXA2ES7WvD
- `4c34684` feat(sync): `horus sync` — explicit ff-only remedy for fetch-first (+ wildcard skill v4) (#433)
  * feat(sync): add `horus sync` — the explicit ff-only remedy for fetch-first
  Fetch-first already fired deterministically at session start (`fetchcheck`), but
  the *remedy* was hand-typed: three surfaces printed `git pull --ff-only` for the
  owner to copy. A session on 2026-07-21 read continuity 5 commits stale and never
  saw cards other sessions had left, because detecting behind-N and acting on it
  were separate manual steps.
  `horus sync` closes that gap without breaking the hook contract. Hooks advise and
  ask, never override, so nothing runs implicitly — the owner invokes it. It
  fast-forwards only when unambiguously safe (clean tree, no local commits, strictly
  behind) and otherwise refuses with the reason, never mutating the tree to force an
  outcome. `git merge --ff-only` is the operation rather than `git pull`: the fetch
  already happened, so it avoids a second round-trip and cannot create a merge
  commit.
  `sync.plan()` is a pure decision over a `git_state` mapping, so the whole refusal
  matrix is testable without a repo; two live probes on a throwaway repo pair prove a
  real fast-forward moves the checkout and that `--ff-only` refuses a real divergence
  without moving HEAD.
  The three surfaces that printed the hand-typed command now name `horus sync`:
  `fetchcheck.warning_line`, the `closure` remote-lanes refusal, and the dashboard
  sync row.
  One existing assertion in test_closure pinned the literal word "pull" and so failed
  on a message improvement rather than a behaviour change; it now asserts the
  contract (refuses · names why · names a runnable remedy).
  Suite 2319 green.
  Claude-Session: https://claude.ai/code/session_01HibUJ7ufbu7LtXA2ES7WvD
  * docs(wildcard): retarget the skill at additive vision moves (v1 → v4)
  Audited after five live runs in one session (receipt lands with the session's
  continuity). Two rounds of findings, both from running it rather than reading it:
  v2 — the skill never stated its purpose and its six example frames were all
  operational-hygiene lenses, so three runs produced zero branch-advancing ideas
  while 19 of 68 cards sat under four vision branches. Also replaced
  one-winner-plus-rejects (mandated in five places, and the reject trace was most of
  each run's output) with rank-all-valid, having established that the autonomy safety
  comes from proposal-not-mutation, not from N=1. Added a Rules check and a premise
  check — between them they would have caught both cards the owner rejected.
  v3 — the ranked table made a decision, an experiment and a code change look like
  the same size of thing, so added a per-idea scope block.
  v4 — two defects the v3 run exposed, one of them introduced by v2's own text:
  "promote-or-drop" in the Purpose and "a reason to drop it outright" in the lens
  list steered the skill into pruning, which is backlog-refine's and convergence's
  authority. The skill is now strictly ADDITIVE. And the scope block was still
  abstract, so it is replaced with an action-first one led by `Do this` (one
  imperative sentence) and `Change performed if accepted` (the concrete before→after,
  naming files/commands/behaviour), gated by an action test: if it would not let a
  fresh agent start work, the idea is not ready to emit. Added paired good/bad worked
  examples, the bad one quoting the skill's own real output.
  Lesson recorded in the receipt: a revision can *introduce* a drift — re-read it
  against the skill's purpose, not only against the finding it was written for.
  Both projections stay byte-identical. `wildcard` has no generator constant in
  horus/skills.py yet, so these files are its source; `bundle-test-phase-skills`
  carries the registration work.
  Claude-Session: https://claude.ai/code/session_01HibUJ7ufbu7LtXA2ES7WvD
  ---------
- `10a04a9` closure: seal PR #433 merge SHA into the Shipped ledger
  The pre-merge continuity gate is by design (closure authoring needs the session
  context the merge discards), so the closure commit necessarily precedes the merge
  and `close --check` then reports the squash commit as delivery not yet covered.
  Stamping the merge SHA closes that loop.
  Claude-Session: https://claude.ai/code/session_01HibUJ7ufbu7LtXA2ES7WvD
- `1af2fbf` fix(tests): de-rot two date-pinned fixtures unblocking CI; card the model-roster staleness tripwire (#435)
  * fix(tests): de-rot two date-pinned fixtures; card the model-roster staleness tripwire
  Main's CI went red on 2026-07-29 for three date-driven reasons, blocking every PR.
  Two are genuine fixture rot; one is a real signal we card rather than fake.
  - test_envelope: the two guard tests run through `cli._envelope_guard`, which compares
    expiry to the REAL clock (no injectable `now`), yet `_make()` pinned
    `expires="2026-07-28"`. They rotted the instant wall-time passed it. New `_make_live()`
    dates the envelope a week ahead of `date.today()`, so it never rots; the frozen-`now`
    tests keep the fixed date they rely on.
  - test_datums: `test_..._default_seed_is_fresh` is not a fixture bug — it is the 14-day
    model-roster staleness tripwire firing correctly (seed researched_at=2026-07-14, 15
    days old today). Faking freshness would lie about when the priors were checked, so the
    test is `xfail(strict=False)` (self-heals on refresh) and the underlying reliance on
    MANUAL refresh is carded.
  - New card `automated-model-roster-grounding` (Delegation calibration, shaping): keep the
    roster fresh from external benchmark platforms + other users' shared experience instead
    of manual date bumps. Supersedes the retired `benchmark-platforms-grounding` with the
    broader shared-experience dimension the owner named.
  Full suite: 2318 passed, 1 xfailed, 0 failed.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  * closure: consolidate the sync/cockpit session — naming split, two cockpit cards, CI de-rot
  Refreshes PRD frontmatter (current_focus / next_action / next_prompt /
  execution_recommendation / last_updated) for the 2026-07-29 session, fixes the
  Shaping count (35→36) for the new `automated-model-roster-grounding` card, and
  records the naming split (Sync = state inward; Horus Assets Refresh = assets outward).
  Continuity notes both PRs of this session: #435 (this branch — CI de-rot) and #434
  (cockpit remote-freshness + inbound Sync, landing next). #434's card-state changes
  (freshness → Ready, cockpit-sync-action minted) arrive with that PR; this branch's
  deterministic breakdown reflects only the card added here.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  ---------
- `c916d70` feat(tui): cockpit remote-freshness indicator + inbound "Sync" (see→act), name the two sync directions apart (#434)
  * refine(backlog): name the two sync directions apart; mint the cockpit see→act pair
  Owner refine pass on the sync/cockpit cluster. Resolves the "sync" collision that
  had the CLI and TUI meaning opposite things: `horus sync` (shipped, PR #433) =
  inbound git fast-forward; the TUI "Projection Sync" screen = outbound Horus-asset
  refresh. Same word, opposite directions.
  Naming split, applied across all four cards:
  - "Sync"                = project state pulled INWARD (matches the horus sync verb)
  - "Horus Assets Refresh" = Horus's skills/managed-block pushed OUTWARD (was
    "Projection Sync"; jargon, and it put the ownership boundary last)
  Cards:
  - tui-fleet-artifact-refresh: renamed the screen label; stays gated.
  - tui-remote-freshness-indicator: minted Ready/attended (order 30), the "see" half
    — render behind-N per project row, cache-first paint. Five open decisions disposed
    (placement=per-row Home; GH-identity panel dropped; verb collision resolved; scope
    git-only; offline=unknown+age).
  - cockpit-sync-action: NEW Ready/attended card (order 40), the "act" half — TUI Sync
    button + fleet Sync-all over the shipped sync.plan/fast_forward, depends-on the see
    card.
  - continuity-sync-friction: kept as the residual explore card; its manual-sync slice
    was promoted out, leaving the contentious auto-ff-at-launch question + format
    frictions, all [session]-class.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  * feat(tui): remote-freshness indicator on the home screen + `g` fleet fetch
  Implements tui-remote-freshness-indicator (the "see" half). The TUI was the one
  launch surface that never fired fetch-first: it painted confident, current-looking
  focus lines that could be silently behind origin.
  - Each project row now shows remote freshness read from on-disk refs (no network in
    the paint path): `current` / `behind N` / `detached`, tagged with the age of the
    last fetch ("46m ago" / "not fetched"). A branch with no upstream falls back to
    divergence from origin/<default> so the row still answers "is my base current?".
    A purely local repo shows no token.
  - `g` on the projects screen is an explicit fleet fetch: read-only `git fetch` across
    all projects concurrently under one global deadline (ThreadPoolExecutor, never
    N × the per-repo timeout), then re-read freshness. It is the only place the TUI
    touches the network for git, and only on that keypress; inert on every other screen.
  - fetchcheck gains public `fetch` / `last_fetch` / `note_fetch` so a concurrent fanout
    can fetch without racing the single-threaded TTL cache.
  - Renames the TUI "Projection Sync" screen to "Horus Assets Refresh" (display labels
    only) — resolving the collision where the CLI's `horus sync` (inbound git) and the
    TUI's "sync" (outbound assets) meant opposite things. Now: "Refresh" = Horus assets
    out; freshness/"Sync" = project state in.
  Tests: per-row behind/current/local-only/no-upstream rendering, the real `g` binding
  driving a fleet fetch (behind→current) and its projects-only scoping, and age/token
  units. Full suite green except 2 pre-existing date-pinned failures on main (expired
  envelope fixture; 15-day-old model priors) unrelated to this change.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  * feat(tui): inbound "Sync" action — fast-forward a project (or the fleet) from the cockpit
  Implements cockpit-sync-action (the "act" half). Once the freshness indicator shows
  a project is behind, the owner can fast-forward it without leaving the TUI.
  - `y` on the projects screen fast-forwards the SELECTED project; `Y` fast-forwards
    every clean-behind project. Both are thin surfaces over the shipped
    `horus.sync.plan` / `fast_forward` (PR #433) — no new git logic. A dirty, ahead,
    diverged, detached, or upstream-less checkout is never mutated, only reported with
    `sync.plan`'s exact reason. Fleet sync is sequential (a fast-forward is a local
    merge; `g` already did the fetch). Both keys are inert off the projects screen.
  - After a sync the project's row re-reads freshness and flips to `current`; the fleet
    action shows a durable tally (N synced · N current · N skipped · [N failed]).
  Naming: this is "Sync" — inbound project state — matching the `horus sync` CLI verb,
  distinct from the outbound "Horus Assets Refresh".
  Tests: `y` fast-forwards the selected project (behind→current), refuses a dirty tree
  without calling fast_forward, explains a non-project row; `Y` syncs only the
  clean-behind project across a mixed fleet; both keys inert off-screen. Live-probed
  unmocked on a throwaway repo pair driven through the real `Y` binding: the clean-behind
  clone fast-forwarded to origin, the dirty clone stayed put with its edit preserved.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  * closure: reflect #434's cockpit cards in the readiness breakdown
  Ready—Attended 3→5 (tui-remote-freshness-indicator order 30, cockpit-sync-action
  order 40 join the queue), Shaping 36→35 (freshness card left shaping for ready).
  next_action updated: #435 is merged (1af2fbf); #434 rebased on it, fully green,
  ready to merge and ship its two cards.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  ---------
- `411db67` closure: ship the cockpit see→act cards; seal #434 into the Shipped ledger
  Both PRs of the 2026-07-29 session landed: #434 (c916d70, cockpit remote-freshness
  indicator + inbound Sync) and #435 (1af2fbf, CI de-rot). Ships tui-remote-freshness-
  indicator and cockpit-sync-action to backlog/archive with the merge SHA, restores the
  readiness breakdown (Ready—Attended 3, Shaping 35), adds the Shipped line, and points
  the handoff at the remaining attended queue.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
- `c740f9b` closure: first Rules distillation pass — 257→210 lines (evidence for the audit shaping)
  Tightened 6 of the heaviest Rules bullets (scheduling, usage, exposure, hooks,
  capability-catalogs, version-floor). Every invariant preserved; dropped inline incident
  narration (git/history hold it) and — the dominant lever — unwrapped hard-wrapped
  bullets to single lines. Rules 165→118, PRD under both the 235 soft and 250 hard caps
  with headroom. Deliberately did NOT touch the Rules↔Structure-contract duplication or
  any possibly-superseded rule — those are judgment moves for owner sign-off.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
- `64792c3` feat(consolidate): PRD cap warning names the driving section + hard-wrap lever (#436)
  * feat(consolidate): PRD cap warning names the driving section + the hard-wrap lever
  The cap check said "the file is big" but its own remedy blamed Shipped ("one-line
  shipped entries") — when the real driver is Rules (60% of the PRD), and the biggest,
  purely-mechanical trim is unwrapping hard-wrapped bullets, not deleting content. This
  cost a hand-measured investigation on 2026-07-29 before that was clear.
  Now, whenever the PRD is over (or approaching) the cap, the warning names the largest
  section with its share and — when that section has hard-wrapped bullets — points at
  unwrapping ("largest section is 'Rules' (118 lines, 60%); 13 of its bullets are
  hard-wrapped — unwrapping to one line each reclaims lines with no loss"). Purely
  deterministic; no judgment, no new command. The judgment half (superseded/duplicate
  rules) stays where it belongs — owner-gated skill territory, not a mechanical check.
  New helpers `_section_breakdown` / `_hard_wrapped_bullets` / `_prd_size_hint`, unit +
  integration tested; existing cap-substring assertions preserved. Suite 2332.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  * closure: record the consolidate cap-warning signal (PR #436)
  Shipped line + next_action for the deterministic PRD-size-driver signal that grew out
  of this session's first Rules distillation. Continuity boundary for the delivery commit.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  ---------
- `1981a1e` closure: mark the session complete — #436 merged, next_action points at the standing queue
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
- `74ef334` closure: judgment distill — de-duplicate Rules against the Structure contract + skills
  Three de-duplication moves, each deferring content to its authoritative home (no
  invariant dropped — verified):
  - Orchestration rule → trimmed to a pointer: its full contract lives in the
    horus-execution skill (v8), it is behavioral text per "PRD is state, not behavior",
    and the Vision disclaims orchestration. Reaping safety stays in Rules.
  - Readiness rule → the field enum/reason/autonomy contract defers to the Structure
    contract's `backlog/` entry (which owns it more completely); the behavioral
    invariants (unclassified-never-schedulable, only-eligible-arms, tooling) stay.
  - Structure-contract Closure → defers the procedure to the Rules closure cluster,
    keeping only its unique "recovery note when needed" invariant.
  Evidence for the audit shaping: unlike the earlier unwrap pass, de-duplication cuts
  ~0 physical lines (these bullets were already single-line) — it removes drift risk,
  not size. The two distill kinds are distinct: unwrap for the cap, de-dup for clarity.
  13 hard-wrapped bullets still remain if a future unwrap pass is wanted.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
- `67638a4` closure: unwrap the remaining 13 Rules bullets — PRD 212→156, Rules 118→62
  Pure formatting: each hard-wrapped bullet joined to a single line, zero content
  changed (13 insertions / 69 deletions, bullet count intact). Completes the distillation
  started this session — Rules is now uniformly one-line-per-bullet and the PRD sits well
  under both caps (156 vs 235 soft / 250 hard), with headroom. The `consolidate` size
  signal now reports 0 hard-wrapped bullets.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
- `a610fd0` feat: launchable pinned/older models — config-editable list (Layer 1) + vendor-docs refresh skill (Layer 2) (#438)
  * feat(launch): config-editable launch-model list; expose pinned older Claude models
  Layer 1 of the model-selection feature. The TUI launch form only offered bare family
  aliases (opus/sonnet/haiku/fable), each = the latest, so pinned older versions the
  `/model` picker hides (e.g. claude-opus-4-8) weren't launchable even though `--model`
  accepts them.
  - config: new managed `[launch_models]` table (per-agent selector lists) with
    `load_launch_models` / `launch_models_for` / `set_launch_models`; threaded through
    `_write_config` so it survives unrelated rewrites; tolerates malformed values.
  - TUI `_agent_models`: a configured `[launch_models]` list wins; else the adapter
    default — so a curated list (hand-edited or written by the coming skill) overrides,
    with zero-config behaviour unchanged.
  - Claude adapter default now includes `claude-opus-5` + `claude-opus-4-8` alongside the
    families, so comparing Opus 5 vs Opus 4.8 works out of the box.
  Layer 2 (the launch-model-refresh skill that keeps this list current from vendor
  model-deprecation docs) follows in the next commit.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  * feat(skills): launch-model-refresh — keep the launch-model list current from vendor docs
  Layer 2: the owner-invoked skill that populates Layer 1's [launch_models] config.
  On the owner's signal (a model shipped/became default, "refresh the launch models"),
  an agent researches the vendor's own model-deprecation docs — one authoritative table
  for Claude (platform.claude.com model-deprecations), two merged pages for Codex
  (OpenAI models ∪ deprecations) — identifies the still-Active --model selectors incl.
  pinned older versions, proposes a curated subset for owner approval, and writes it via
  config.set_launch_models(). Evidence-first, owner-gated, never auto-run/polled, never
  exposes a model past retirement. Sibling of automated-model-roster-grounding (calibration
  tiers/prices) — kept separate by data and source.
  The per-vendor recipe (Claude=one page, Codex=two-page merge) and the retirement-date
  bonus were validated by a live simulation before writing the skill. Registered in the
  SKILLS generator (v1) with both projections; guard test pins its mechanism + sources.
  Updated two adapter/TUI tests for the expanded Claude default. Suite 2339.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  * closure: record the launchable-models feature (PR #438)
  Shipped line + next_action for Layer 1 ([launch_models] config) + Layer 2
  (launch-model-refresh skill). Continuity boundary for the delivery commits.
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
  ---------
- `82cd600` closure: mark the session complete — #438 merged, both model-selection layers landed
  Claude-Session: https://claude.ai/code/session_013Jqwcdrf9LfmEZPhq5Sipy
