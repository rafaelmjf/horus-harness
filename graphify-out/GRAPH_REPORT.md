# Graph Report - bench-graphify  (2026-08-09)

## Corpus Check
- 526 files · ~951,281 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 9408 nodes · 20567 edges · 538 communities (493 shown, 45 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 341 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e6004074`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_dashboard.py
- test_terminal_sessions.py
- dashboard.py
- cli.py
- test_routines.py
- main
- Finding
- test_backlog.py
- RunRequest
- test_datums.py
- terminal_sessions.py
- backlog.py
- test_worktree.py
- test_backlog_tree.py
- test_skills.py
- ._refresh_items
- init_project
- test_registry.py
- herdr.py
- ._body_text
- test_codex_adapter.py
- proxy.py
- test_schedule.py
- test_doctor_machine.py
- Registry
- SessionRecord
- config_dir
- .do_GET
- test_statusline.py
- terminal_tui.py
- datums.py
- schedule.py
- claude_usage.py
- test_config.py
- input_bridge.py
- SpawnSpec
- Codex Plan Review
- ClaudeAdapter
- test_fleet_backlog.py
- test_account_resolution.py
- test_envelope.py
- test_native_hooks.py
- migrate_inline_backlog
- unit_dir
- FakeAdapter
- session-restore — detect sessions that vanished, and offer to restore them
- config.py
- build_model_rollup
- ignore_repo
- test_onboard.py
- test_integration.py
- test_cockpit.py
- RemoteProject
- process_upgrade_project
- fetch_and_state
- test_delivery.py
- test_verify_inventory.py
- envelope.py
- UsageSnapshot
- overhead.py
- skills.py
- versioning.py
- emergency_rescue
- _init_repo
- DatumStore
- test_activity.py
- test_brainstorm.py
- test_capabilities.py
- test_closure.py
- extract_block
- test_notify_listen.py
- templates.py
- capabilities.py
- test_usage_record.py
- fleet_review.py
- test_usage_snapshot.py
- set_workflow_policy
- delivery.py
- upgrade.py
- History — bumps in the road & decision rationale
- refine_prompt
- native_hooks.py
- session_discovery.py
- JWKSCache
- codex_usage.py
- PtyHost
- reinstall
- selfupdate.py
- Path
- usage_snapshot.py
- Horus - project continuity and control for official coding-agent CLIs
- Path
- integration.py
- test_pty_host.py
- git_state
- _setup
- test_codex_usage.py
- parse
- test_skillmap.py
- _new_ui
- _usage_check_claude
- Path
- launch.py
- watch
- install_listen_service
- resume_preflight.py
- test_warmup.py
- install_keepwarm_service
- test_notify.py
- test_terminal_tui.py
- cache_status.py
- test_launch_targets.py
- test_sync.py
- ModelRollup
- test_companion.py
- load_projects
- offboard.py
- machine_requirements.py
- test_vscode.py
- Horus Product Interview
- What You Must Do When Invoked
- What You Must Do When Invoked
- Handoff: Horus Dashboard Redesign
- AccessJwtVerifyTests
- _usage_guard_hook
- _envelope_guard
- render
- regen_mascot.py
- Horus Hub Design
- Handle
- test_backend.py
- Omnigent
- _run
- tui-control-settings-pane — a machine Control pane in the TUI
- session-process-cadence — a more usage-efficient continuity/ceremony cadence, without reviving launch modes
- closure.py
- companion.py
- ensure_dashboard
- github_catalog.py
- launcher.py
- mergewatch.py
- Path
- parallel_deliveries
- notify_listen.py
- test_projection_sync.py
- 4. The branches
- skill_usage.py
- test_batch.py
- cmd_usage_check
- _replace_stale_dashboard
- supervise.py
- _write_backlog_card
- _plain
- Product audit — 2026-07-20 (horus 0.0.73) — inward alignment analysis
- load_notify_config
- remote_start.py
- terminal_app.py
- test_overhead.py
- Bug: `horus app` wedges silently when a stale companion holds the singleton lock
- pty_host.py
- test_supervise.py
- _guard_hook_run
- _home_with_project
- vision-branch-x3 — scheduling & autonomous execution
- test_checkpoint_hook.py
- open_dashboard
- load_dashboard_access
- render_control
- Handler
- initialize.py
- Roadmap branches: deepen-own-use re-baseline — 2026-07-20
- Core technical findings
- parse_tasks
- resolve_deferred
- Diagnosis: hosted terminal sizing & lifecycle (mobile + desktop)
- Mobile/desktop terminal: sizing + lifecycle + controls hardening
- DashboardProcess
- test_mergewatch.py
- notify.py
- Roadmap branches: deepen-own-use re-baseline — 2026-07-31
- Roadmap branches: deepen-own-use re-baseline — 2026-08-01 (v8 run)
- _isolated_home
- test_dashboard_access.py
- `consolidate`
- notify-schedule-batch-complete — a real "the schedule finished" signal, not a timer guess
- review-session-control-calibration — independently review the controls learned in the first Codex session
- tui-backlog-refine-and-order — groom + order the backlog into a schedulable plan
- dispatch-workflow-comparative-study — compare what we have vs other existing workflows
- intent-preserving-goal-campaign — bind the spirit, let a frontier agent choose the form
- Unified Horus artifact refresh — detect, preview, integrate, verify
- cmd_doctor
- test_config_dir_guard.py
- keepwarm.py
- Path
- sentinel_fired
- Roadmap branches: deepen-own-use re-baseline — 2026-07-17 (convergence-test run)
- Product audit — horus-harness, 2026-07-31
- codex-usage-stale-snapshot gates dispatch — wrong, and two readers disagree
- Preserved design proposal (not approved for implementation)
- openwiki-graphify-value-benchmark — test generated context against the repo-native baseline
- validate
- UntrackedRepo
- _UnixPty
- Branches
- Roadmap branches (v5 re-run): host-native cockpit — 2026-07-31
- Omnigent fit as Horus LaunchBackend (2026-07-10)
- Horus
- backend.py
- gpt-models-in-claude-code-harness — run GPT (via the Codex sub) inside Claude Code (spike)
- refine-autonomy-hardening-lens — force "contingent vs intrinsic" on every attended card
- session-host-protocol — one pluggable session host (tmux · current · herdr)
- wildcard — an autonomous divergence skill that emits ONE reviewable card
- CliCommand
- cmd_run
- canonical_model_name
- capture_usage_snapshot
- pr_only_contexts
- _board_ui
- The contract — seven gates, each owner-confirmed
- wildcard — autonomous divergence → ranked, buildable vision-advancing moves
- The contract — seven gates, each owner-confirmed
- wildcard — autonomous divergence → ranked, buildable vision-advancing moves
- DashboardAccess
- account-login-verb — provision + log into an account that has no prior login
- usage-snapshot-test-flake-blocks-workers — a green-on-CI test fails locally and kills dispatched deliveries
- new-machine-setup-guidance — how a fresh machine gets set up correctly
- _apply_unattended_defaults
- Claudex first-session findings — 2026-07-18
- _load_cache
- _claude_hook_run
- _mk_fresh
- Delegation rubric — shared calibration + verification logic
- Horus execution supervision
- Process retrospective — bounded, evidence-first
- Delegation rubric — shared calibration + verification logic
- Horus execution supervision
- Process retrospective — bounded, evidence-first
- Decisions — current rules
- project-registration-onboarding-gap — cloned Horus project stays invisible and mobile hides registration
- vision-omits-intent-and-audiences — the Vision contract captures the destination, never the intent
- codex-isolated-config-leak — an isolated Codex account still points at the ambient home
- fresh-vs-resume-context-split — the resume directive should reach resume sessions only
- vision-branch-x6 — workflow selection compatibility
- tmux_runner.py
- conftest.py
- _clone_with_origin
- _run_deploy
- Publish an OpenWiki visualizer without rebuilding the deployment each time
- Publish an OpenWiki visualizer without rebuilding the deployment each time
- session-remote-control-default — launch Horus sessions with remote control enabled by default
- tui-remote-freshness-indicator — see at TUI launch whether continuity is current
- autonomous-advisory-dispatch-posture — schedule zero-blast skills without a fake delivery card
- Deferred supervision and completion receipt
- vision-branch-x4-model-harness-plane.md
- windows-native-horus-setup — the best way to run horus on Windows, given the TUI's recent growth
- Delegation cost finding — dispatch did not save cost; it raised it
- Market scan: repo-local product-owner re-baseline — 2026-07-17
- Multi-model / multi-harness — landscape scan (X4 candidate)
- X6 boundary inventory — substrate vs continuity contract vs workflow policy
- Market scan: repo-local agent continuity — 2026-07-31
- _Stdin
- backlog-refine — picture first, decisions second, Ready last
- graphify reference: extra exports and benchmark
- Market scan — look outward, propose, never auto-apply
- roadmap-branches — the divergence tree, not a merged roadmap
- Skill audit — one skill's text vs reality
- backlog-refine — picture first, decisions second, Ready last
- graphify reference: extra exports and benchmark
- Market scan — look outward, propose, never auto-apply
- roadmap-branches — the divergence tree, not a merged roadmap
- Skill audit — one skill's text vs reality
- .recover_interactive_thread_id
- get_adapter
- backlog-librarian — autonomous, zero-blast-radius backlog-hygiene digest
- bundle-test-phase-skills — a skill in test phase lives outside the generator, unprotected
- codex-identity-guard — Codex launches skip the account identity check entirely
- Datum supervisor-cost envelope + one-act acceptance [frozen schema — implement as specified]
- herdr-host-probe — answer three questions before designing the host protocol
- process-fixes-live-in-process-not-memory — shared artifacts, not one agent's recall
- remote-control-flag-swallows-launch-prompt — `--remote-control` eats the seeded prompt, so no interactive launch is seeded and Remote Control does not come up
- session-close-ux-and-truthful-end-state — a closed session must not read as a failed one
- tui-nested-tmux-navigation — make `horus tui` usable *inside* tmux (switch-client, not refuse)
- continuity-sync-friction — reduce cross-session/cross-machine friction in git-synced continuity
- horus-phone-chat-poc — one-shot spike: text chat frontend to an agent session with phone-side tool approval
- merge-release-owner-gate — put the wall where the model's speed actually costs
- session-agent-state-awareness — surface working / idle / blocked for running sessions
- vision-branch-x4 — model × harness × credential execution-route plane
- harvest_target
- _launch_notice
- Agent host-freeze incident — 2026-07-18
- Market scan: repo-local product-owner layer for coding agents — 2026-07-20
- repro.mjs
- _merge_hook_run
- Backlog librarian — one advisory hygiene digest
- Execution decision (in-project)
- horus-release — cut a version, and land it where people actually run it
- Backlog librarian — one advisory hygiene digest
- Execution decision (in-project)
- horus-release — cut a version, and land it where people actually run it
- Execution Plan
- Backlog librarian — 2026-07-26
- Skill audit — `wildcard` (v1 → v4) — 2026-07-28
- Rules routing audit — where each of the 84 PRD Rules should live
- audit-advisory-interval — count releases AND days, not releases alone
- autotest-e2e-away-mode-drill — the owner's fully-scheduled away-mode e2e test
- backlog-default-list — `horus backlog` should default to `list`
- close --check hard-blocks merge on Unclassified cards (should be advisory)
- cockpit-sync-action — one-tap "Sync" in the TUI (per-project + fleet), on the shipped engine
- execution-requires-explicit-owner-delegation — authorization and substrate must both be explicit
- prd-rules-section-outgrew-its-budget — 84 rules, 66% of the file, and every close now fights the cap
- tui-backlog-grouped-list — collapsible group-by sections in the TUI backlog list
- tui-backlog-kanban-board — width-adaptive kanban lens over the backlog
- concurrency-safe-continuity — make continuity hold up when multiple agents develop in parallel in one repo
- fleet-sourced-autonomous-batch — feed the loop from the fleet, trip-timed
- herdr-server-shutdown-fragility — herdr's server exits on client-triggered errors, taking every session with it
- vision-branch-x5 — safe execution boundaries and guardrails
- x4 — experiment with PI as a harness via the proxy
- continuity_dirty_paths
- Horus — PRD
- RESCUE — a Claude session went "api unresponsive" after proxy wiring
- Wildcard — branch-first divergence (2026-07-31)
- Dispatch decision (cockpit / multi-project, sessions substrate)
- PRD-structure projects (v3 — `.horus/PRD.md` present)
- pathfinder — the re-baseline workflow (thin by design)
- scope-cards — from a chosen branch to aligned shaping drafts
- Dispatch decision (cockpit / multi-project, sessions substrate)
- PRD-structure projects (v3 — `.horus/PRD.md` present)
- pathfinder — the re-baseline workflow (thin by design)
- scope-cards — from a chosen branch to aligned shaping drafts
- OwnerHeaderTests
- Skill audit: scope-cards — 2026-07-19
- account-settings-sync — one canonical settings block across isolated account dirs
- backlog-readiness-disposition — machine-readable readiness and autonomy
- horus-execution-general-plan-false-trigger — ordinary planning enters the worker-supervision workflow
- schedule-local-dispatcher — a first-class local one-shot/cron dispatcher for `horus run`
- supervise-verify-merge-close — unattended verify → merge → close → escalate for a dispatched card
- tui-vision-backlog-read-out — the cockpit shows direction, not just cards
- unattended-dispatch-attachable-worktree-defaults — make scheduled/detached runs attachable + isolated by default
- unattended-escalation-channel — a push channel so a headless supervisor can reach the owner
- Make card-per-file backlog the fleet standard (unify inline `## Backlog` → cards)
- verify-guidance-long-running-services — "active + emits its signal", not "it installed"
- x3-away-mode-kit-e2e-rehearsal — dogfood the whole away loop once, end-to-end
- automated-model-roster-grounding — keep the model roster fresh from external + shared sources, not manual bumps
- dispatch-collision-guard — stop two concurrent agents from building the same card
- dispatch-receipt-seam — the worker writes facts, the supervisor reproduces the signal
- isolated-account-plugin-parity — an isolated account starts with no plugins
- managed-instruction-drift-lint — deterministically catch managed prose that references a removed CLI surface
- native-app-account-launch-spike — can the TUI launch the desktop app under a chosen account
- Probe smaller open-source workers on a remote Tailscale machine
- optional-host-ci-coverage — CI cannot exercise the herdr host at all
- pathfinder-structured-outcome — refine the pathfinder chain to emit one structured, addressable per-run outcome
- prd-worked-by-account — record which account(s) a project's work actually happened under
- Product naming — track candidates, decide at distribution
- repeated-question-skill-mining — repeatedly-asked questions are undeclared skills
- research-receipts-surfacing — receipts as first-class citizens, not stray .md files
- skill-self-calibration-probe — skills that notice their own drift (wildcard)
- telegram-idea-capture — capture ideas from the phone, triage later (wildcard)
- tui-campaign-native-goal-probe — make Campaign a persistent native goal, not an ordinary prompt
- usage-analytics-read-out — from point-in-time percentages to steering answers
- Ordered stages and children
- window-aware-scheduling — fire when budget exists, not when the clock says (wildcard)
- x6 — declare the continuity contract explicitly
- x6 — fabric as the live contract-sufficiency probe
- x6 — workflow alternatives refresh (shallow, contract-judged)
- cmd_supervise
- Market scan: Horus product-owner capabilities (roadmap-convergence + market-research) — 2026-07-16
- test_capital_y_syncs_every_clean_behind_project
- graphify reference: query, path, explain
- launch-model-refresh — keep the TUI's launchable model list current from vendor docs
- Product audit — the inward evidence step (analysis, never verdicts)
- Claude Code Instructions
- graphify reference: query, path, explain
- launch-model-refresh — keep the TUI's launchable model list current from vendor docs
- Product audit — the inward evidence step (analysis, never verdicts)
- app-usage-cost-opacity — native apps meter usage but surface no cost/context/cache visibility or control
- Ground the ranking in 3rd-party benchmark platforms
- `horus close` can strand a dirty tree: a commit can't reference its own SHA
- cockpit-autonomous-dispatch-contract — a skill wiring discover→pick→scope→dispatch/schedule→supervise
- Display the delegation decision matrix from the CLI (agent-first)
- Fold consolidate's signals into `close --check`; reserve the skill for heavy passes
- horus-statusline-default — ship the status line, don't hand-configure it per machine
- input-bridge-remote-ask — a session asks, the owner answers from the phone
- launch-mode-process-skill — a launch mode attaches a process skill so the working posture holds
- Hosted terminal is not mobile-responsive (glyphs scramble, fixed size)
- Model ranking synthesis — a grounded "current ranking" for the decision matrix
- Dashboard tab: full model-roster research + table + refresh button
- notify-listen-steering-channel — a deterministic two-way steering channel
- notify-listen — trip-mode service + andon-reply (release) completion
- Pricing-aware model-roster research process
- Research: OpenWiki vs. our self-documenting capability catalog
- prd-readiness-count-check — keep the PRD readiness-breakdown counts honest automatically
- resume-session-id-mismatch — the id you can see is not the id `--resume` wants
- standing-dispatch-envelope — bounded pre-authorization for unattended dispatch
- tui-launch-model-effort-selection — pick model + effort at launch, not after
- tui-launch-session-new-window-default — Defaults option: launch sessions in a new window
- codex-usage-blind-across-machines — a Codex usage reading cannot see another machine
- decision-doc-skill — a skill that generates issue/solution decision documentation
- telegram-group-project-topics — a topic per project in one steering group
- tui-toggle-card-into-scheduler — arm/disarm a ready card for autonomous execution
- x5-cross-platform-containment-contract — honest safety guarantees on Linux, Windows, and macOS
- WatchOutcome
- X4 stage-0 spike — GPT in Claude Code via the Codex subscription
- _gt
- Field findings from fabric session — workflow enforcement gaps (2026-07-08)
- Agent Instructions
- Fleet curation
- Fleet curation
- Features — capability ledger
- Attachable detached one-shot worker runs
- codex-delivery-dispatch-needs-full-auto — a delivery dispatch that structurally can't deliver must be refused at arm time
- config-dir-guard-advisory — same-account concurrency is advised, not refused
- Surface under-sampled models — counter the survivorship trap in dispatch
- `horus fleet --backlog` — deterministic fleet-wide backlog roll-up
- global-skill-viewer-tui — see installed vs available skills, per agent
- horus-kickstart — one guided divergence→convergence re-baseline (also the onboarding path)
- horus init optionally scaffolds a minimal project CI gate
- Track model availability / lifecycle — don't invest in soon-to-retire models
- Reconcile canonical model roster rows, prices, and lifecycle provenance
- notify-listen --service: absolute ExecStart + restart-on-upgrade
- parallel-session-continuity-reconciliation — two sessions, one continuity
- parallel-signal-informational-not-verdict — a named sibling PR shouldn't read as "Stale"
- Provider-valid model selector contract
- schedule-run-any-subcommand — the scheduler can't arm a `supervise` (or `warmup`)
- scheduled-dispatch-launch-failure-escalates — don't die silently in the journal
- service-installers-self-verify-active — safety in code, not in the probe
- systemd-unit-absolute-execstart-guard — one test over all unit writers
- telegram-output-minimal-legible — the phone push + button replies are minimal, not log dumps
- tui-branch-tree-glance — the backlog as a tree, at a glance, on the phone
- usage — capacity across all accounts from Telegram
- vendor-neutral-delegation-tiers — tiers name capability, never a vendor
- vscode-terminal-launch-command — open a session in the VS Code terminal + project folder
- warmup — start the 5h usage window on demand
- Explicit worker dispatch consent and cost accounting
- explore-converge-lifecycle — a roadmap that breathes (divergence → convergence)
- Platform- and capability-scoped machine requirements
- x4-codex-usage-in-claude-code — live Codex limits while GPT runs in Claude Code
- x4-provider-credential-routing — separate harness profile from the subscription that serves the model
- x4-tui-execution-route-axis — make the complete model/harness/account route visible and selectable
- x5-container-execution-spike — decide where stronger isolation earns its integration cost
- x5-linux-agent-cgroup-containment — one bounded systemd scope per Horus session
- x5-network-bot-isolation — dedicated boundary for Telegram, Hermes, and future inbound services
- x5-persistent-service-resource-envelopes — bound every Horus daemon and verify the live unit
- x5-resource-policy-calibration — tune limits from machine capacity and real agent workloads
- Mini market scan: X3 scheduled/autonomous dispatch + supervision — 2026-07-17
- _freshness_token
- test_usage_check_uses_fresh_account_limits_not_stale_project_limits
- _Proc
- test_guarded_hook_is_silent_noop_when_cli_missing
- test_spawn_pty_runs_a_real_command
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native AGENTS.md integration
- graphify reference: incremental update and cluster-only
- Distill project history
- Infer Horus continuity from the project's docs
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- Distill project history
- Infer Horus continuity from the project's docs
- .validate_model
- Account-scoped usage check for safe dispatch
- Boundary-based continuity granularity
- Bulk-migration inventory reconciliation (empty-walk-is-an-error)
- Optional campaign-supervision launch from the TUI
- Structure-aware execution supervisor prompt
- Remote-authoritative fleet review + optional TUI curator entry
- market-scan — outward, evidence-first market/competitive research skill
- Merge-watch settles applicable checks on a post-merge SHA
- Proper model names (rename, not alias) + datum migration + table rendering
- Optional recovery notes and honest onboarding
- Evidence-first process retrospective skill
- Release-stamped product audit (signal + skill)
- roadmap-convergence — a healthy backlog that converges toward the Vision, with a DoD
- Stale datum usage-overlap reconciliation
- TUI fleet projection sync
- Start remote-only GitHub projects from the terminal TUI
- Worker guard for destructive global-state cleanup
- Project-local workflow policy overrides
- _describe_run
- _usage_floor_label
- resolve_open_mode
- Execution Plan — two isolated Claude workers
- unit_exit_detail
- .is_authoritative_for_refusal
- openwiki-comparison-2026-07.md
- _isolated_home
- test_a_vanished_session_offers_restore_even_though_its_target_ref_survives
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- .permission_flags
- Accounts strip "refresh (cached)" button is invisible on every viewport
- Project-declared machine requirements (`doctor` + `resume` + dashboard + TUI)
- _age_phrase
- _resolve_tail_session
- _offload_control
- looks_like_usage_death
- test_continuity_workflow.py
- _isolate_dashboard_access_globals
- _isolated_config
- units
- _EmptyReg
- .agents/skills/graphify/references/extraction-spec.md
- .claude/CLAUDE.md
- .claude/skills/graphify/references/extraction-spec.md
- .interactive_command
- 2026-07-16-product.md
- auto-merge-bypasses-freshness-gate.md
- capability-catalog-productionize.md
- close-commit-output-contradicts-success.md
- companion-signals.md
- context-cache-visibility-hook-stamps.md
- datum-outcome-taxonomy-void-and-death.md
- deferred-mvp3-mvp5.md
- deferred-omnigent-seams-misc.md
- doctor-compat-workflow-policy.md
- execution-workflow-tuning.md
- git-aware-overview-mvp25.md
- multi-developer-continuity.md
- resume-preflight-digest.md
- scheduled-usage-aware-continuation.md
- skill-map-followups.md
- tier0-supervision-verbs.md
- tmux-mouse-scroll-and-tui-launch-defaults.md
- tui-capabilities-screen.md
- tui-cockpit-state-gaps.md
- wiki-read-model-productionize.md
- horus/__init__.py
- .horus/README.md
- .refresh_command
- deploy-hosted.sh
- tests/__init__.py
- test_codex_delivery_posture_error_matrix
- test_close_commit_rechecks_post_commit_state
- test_integration_result_exposes_detail_not_error
- horus-harness

## God Nodes (most connected - your core abstractions)
1. `main()` - 252 edges
2. `_init()` - 143 edges
3. `_home()` - 129 edges
4. `SessionRecord` - 115 edges
5. `TerminalUI` - 107 edges
6. `init_project()` - 106 edges
7. `build_parser()` - 100 edges
8. `UsageSnapshot` - 85 edges
9. `Finding` - 77 edges
10. `_home()` - 73 edges

## Surprising Connections (you probably didn't know these)
- `AccessJwtVerifyTests` --uses--> `AccessJWTError`  [INFERRED]
  tests/test_access_gate.py → horus/access_gate.py
- `AuthorizedTests` --uses--> `AccessJWTError`  [INFERRED]
  tests/test_access_gate.py → horus/access_gate.py
- `OwnerHeaderTests` --uses--> `AccessJWTError`  [INFERRED]
  tests/test_access_gate.py → horus/access_gate.py
- `AccessJwtVerifyTests` --uses--> `JWKSCache`  [INFERRED]
  tests/test_access_gate.py → horus/access_gate.py
- `AuthorizedTests` --uses--> `JWKSCache`  [INFERRED]
  tests/test_access_gate.py → horus/access_gate.py

## Import Cycles
- 3-file cycle: `horus/capabilities.py -> horus/cli.py -> horus/fleet_review.py -> horus/capabilities.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/base.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/base.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/capabilities.py -> horus/cli.py -> horus/terminal_app.py -> horus/terminal_tui.py -> horus/capabilities.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/hosts/base.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/hosts/base.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/hosts/runnerspec.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/launch.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/run_executor.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/hosts/base.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/hosts/base.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/hosts/runnerspec.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/launch.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/run_executor.py -> horus/registry.py -> horus/hosts/__init__.py`

## Communities (538 total, 45 thin omitted)

### Community 0 - "test_dashboard.py"
Cohesion: 0.03
Nodes (148): account_login_dir(), Standard isolated login directory for ``agent``/``alias`` under ``~/.horus``.…, Add a GitHub user/org to the remote catalog. Returns True if newly added., register_github_owner(), _hidden_row(), process_account_login(), process_launch(), Account-setup wizard: derive an isolated login dir, record the mapping, and… (+140 more)

### Community 1 - "test_terminal_sessions.py"
Cohesion: 0.04
Nodes (126): Add ``project_path`` to the user config. Returns True if newly added., register_project(), is_restorable(), launch_tmux(), Create a unique detached tmux session, then optionally attach this TTY., Whether this session's conversation can be brought back on a live host. Three…, Kill host sessions that are provably abandoned; return the killed refs. Safety…, reap_orphans() (+118 more)

### Community 2 - "dashboard.py"
Cohesion: 0.04
Nodes (111): _account_add_form(), _account_alias_form(), _account_remove_form(), _accounts_panel(), _accounts_strip(), _add_local_form(), _add_owner_form(), _best_next_text() (+103 more)

### Community 3 - "cli.py"
Cohesion: 0.05
Nodes (108): _baseline_recipe(), build_parser(), cmd_app(), cmd_attach(), cmd_brainstorm(), cmd_checkpoint(), cmd_close(), cmd_config() (+100 more)

### Community 4 - "test_routines.py"
Cohesion: 0.05
Nodes (104): campaign_prompt(), consolidate_signals(), feature_capabilities(), feature_counts(), feature_items(), freshness_signals(), _key_tokens(), Capability row counts per section of features.md. (+96 more)

### Community 5 - "main"
Cohesion: 0.05
Nodes (103): main(), _capture_run_posture(), _home(), Integration tests driving commands through the CLI entry point., Record the posture the SpawnSpec carried into the fake adapter., cmd_run fails fast — before any worktree or worker is created — on a codex…, End to end: `--resume <horus id>` now resumes instead of dying in 2s with rc=1.…, _stamp_prd() (+95 more)

### Community 6 - "Finding"
Cohesion: 0.04
Nodes (101): _check_focus(), check_project(), _check_sessions(), Finding, horus_dir(), NamedTuple, Path, `.horus/` continuity model and the `horus doctor project` check. (+93 more)

### Community 7 - "test_backlog.py"
Cohesion: 0.05
Nodes (96): claim(), claim_check(), find_card(), hygiene_findings(), load_active_cards(), load_cards(), Finding, Backlog-root cards, sorted by filename; archived cards are never loaded. (+88 more)

### Community 8 - "RunRequest"
Cohesion: 0.04
Nodes (67): Capabilities, Protocol, What a session host is, and what it can be asked to do. A *session host* is the…, An argv that renders ``target_ref`` in a PTY or native window. Takes the ref…, Live refs owned by this host → ``(attached, last_activity_epoch)``. Only…, Static facts about a host. Dynamic ones are methods on the host itself., The nine things every caller of a host needs. Implementations live beside this…, Whether this host can be used on this machine at all. (+59 more)

### Community 9 - "test_datums.py"
Cohesion: 0.06
Nodes (81): Datum, One measured run. Mechanical fields are written automatically at…, Classify stored start/end usage evidence without estimating future cost. A…, Render-ready per-attempt worker actuals, grouped by native session id., usage_accounting(), worker_breakdown(), _home(), _mk_target_card() (+73 more)

### Community 10 - "terminal_sessions.py"
Cohesion: 0.04
Nodes (68): await_handoff(), Path, The runner spec: how Horus tells a pane what to become, host-agnostically. Any…, Wait only for the runner's durable PID handoff, never for its agent., ready_path(), runner_dir(), spec_path(), write_payload() (+60 more)

### Community 11 - "backlog.py"
Cohesion: 0.06
Nodes (72): add_review(), archive_dir(), autonomy_block_reason(), backlog_dir(), Card, _card_from_path(), _claim_lock(), default_author() (+64 more)

### Community 12 - "test_worktree.py"
Cohesion: 0.07
Nodes (72): _prune_worktrees(), Reclaim linked worktrees whose branch is merged — report unless --apply.…, _branch_exists(), branch_slug(), ensure_worktree(), _git(), _looks_merged(), primary_checkout() (+64 more)

### Community 13 - "test_backlog_tree.py"
Cohesion: 0.06
Nodes (69): _body_text(), BranchGroup, build_tree(), build_tree_from_cards(), _card_to_dict(), _convergence_line(), FacetGroup, filter_cards() (+61 more)

### Community 14 - "test_skills.py"
Cohesion: 0.03
Nodes (38): Tests for the bundled agent-skills layer (scaffold, version-aware install,…, v8: full facet coverage belongs to the narrative position read-out (section 1);…, v8: the skill names the receipt that is the shape to reproduce. v7 cited…, EVERY skill's projected copies must equal `Skill.content`, not just a named…, The runbook lived in three places (PRD Rules, CLAUDE.md, AGENTS.md) and in none…, PRD Rules and the agent instruction files keep the INVARIANT and point at the…, Verified live 2026-08-02: PreToolUse fires for the `Skill` tool exactly as it…, Final readiness lives once in backlog-refine; consumers reference it. (+30 more)

### Community 15 - "._refresh_items"
Cohesion: 0.03
Nodes (38): FormattedTextControl, _account_usage(), _agent_models(), _BodyControl, _host_choices(), _invert_mobile_scroll(), _launch_accounts(), MouseEvent (+30 more)

### Community 16 - "init_project"
Cohesion: 0.05
Nodes (68): load_project(), process_brainstorm(), Collect everything the dashboard shows for one project (read fresh)., Handle an Ideas/Brainstorm POST; return the query string to redirect with. Same…, render_index(), init_project(), No target (or target=app) runs the brainstorm under the session-host PTY — the…, load_project sets artifacts_stale=True and count when upgrade returns a would-… (+60 more)

### Community 17 - "test_registry.py"
Cohesion: 0.06
Nodes (59): is_recent(), datetime, Whether ``record`` was updated within ``horizon_hours`` of ``now``. Used to de-…, append_event(), follow(), Any, Path, Per-session run logs — the file side of background-worker visibility. ``horus… (+51 more)

### Community 18 - "herdr.py"
Cohesion: 0.06
Nodes (51): _cockpit_is_live(), _create_cockpit(), _find_cockpit(), `horus tui <host>` — open the Horus cockpit *inside* a session host. `horus…, Restart the TUI inside an existing but dead cockpit pane., The ref of this host's live cockpit, or ``None``. Asked of the host's own…, Create the cockpit pane and return ``(ref, error)``., The argv that runs *this* Horus's TUI inside a pane. Always this interpreter's… (+43 more)

### Community 19 - "._body_text"
Cohesion: 0.05
Nodes (32): _capability_freshness(), _fit_cell(), _priority_dot(), _projection_counts(), datetime, Render the home cockpit as responsive columns on wide terminals., A color-coded readiness dot for a board cell: green = ready (dispatch- able),…, The priority board: one column per priority (readiness-dotted, ready- first),… (+24 more)

### Community 20 - "test_codex_adapter.py"
Cohesion: 0.07
Nodes (57): CodexAdapter, ``codex_homes`` maps an account alias to its ``CODEX_HOME`` dir for multi-…, _codex_home_with_account_id(), _home(), Path, Tests for the Codex adapter. parse_event fixtures are real JSONL lines captured…, A fake CODEX_HOME containing an auth.json logged in as ``account_id``., Codex and Claude must stay on the same orientation: the percent is USED.… (+49 more)

### Community 21 - "proxy.py"
Cohesion: 0.07
Nodes (57): cmd_proxy(), Manage the optional CLIProxyAPI integration (run GPT models inside Claude…, _await_models(), _claude_config_dirs(), default_state(), disable(), docker_available(), docker_run_command() (+49 more)

### Community 22 - "test_schedule.py"
Cohesion: 0.06
Nodes (59): cmd_schedule_at(), Register a one-shot `horus run` to fire later on this machine., load_all(), parse_when(), A target time from ``+90m`` / ``+2h`` or an absolute ``2026-07-22 09:00``.…, Every Horus schedule this machine knows about, soonest first. Reconstructed…, _args(), Scheduling a `horus run` to fire later on this machine. Everything that can be… (+51 more)

### Community 23 - "test_doctor_machine.py"
Cohesion: 0.07
Nodes (58): _all_on_path(), _code_cli_finding(), _console_script_finding(), _dist_requires_python(), _gh_auth_finding(), _hook_command_findings(), _interpreter_floor_finding(), _iter_hook_commands() (+50 more)

### Community 24 - "Registry"
Cohesion: 0.06
Nodes (43): Path, Create an attended session, and attend it when ``attach`` is set., Host a one-shot `horus run` worker and return after the runner handoff., Path, Run an attended agent in this TTY, returning after the agent exits.…, _apply_delivery_completion(), _aware_utc_iso(), display_status() (+35 more)

### Community 25 - "SessionRecord"
Cohesion: 0.06
Nodes (53): Put this terminal on a live session. Error string, or ``None``., Kill a live session. Error string, or ``None``., new_record(), PreparedInteractive, Validated attended-agent command shared by every local terminal surface., SessionRecord, access_label(), is_attachable() (+45 more)

### Community 26 - "config_dir"
Cohesion: 0.08
Nodes (57): _account_for_ambient_config_dir(), cmd_account(), The alias -> isolated-dir mapping for ``target`` and its env-var name., The alias whose isolated dir this process is running under, or ``None``. The…, The CLAUDE_CONFIG_DIR / CODEX_HOME an ``agent`` run under ``account`` will use.…, _resolved_config_dir(), _usage_account_mapping(), accounts_path() (+49 more)

### Community 27 - ".do_GET"
Cohesion: 0.05
Nodes (41): gather_sessions(), gather_untracked_repos(), _geom_log(), _Handler, _manifest_json(), _open_terminals(), _page(), process_account_remove() (+33 more)

### Community 28 - "test_statusline.py"
Cohesion: 0.07
Nodes (52): cmd_statusline(), Render the Claude Code status line from the pushed stdin payload, and record…, The account label for the status line: the alias when isolated, else the email.…, _statusline_account_label(), _as_pct(), _dget(), _epoch(), git_branch() (+44 more)

### Community 29 - "terminal_tui.py"
Cohesion: 0.05
Nodes (50): _active_cards(), _Attach, _backlog_metrics(), _Campaign, _card_field_choices(), _card_field_detail(), _card_field_suffix(), _card_prompt() (+42 more)

### Community 30 - "datums.py"
Cohesion: 0.07
Nodes (39): _backfill(), _build_model_tier_map(), classify_exit(), _claude_usage_entry(), _codex_usage_entry(), _effective_interval(), _iso_datetime(), _now_iso() (+31 more)

### Community 31 - "schedule.py"
Cohesion: 0.07
Nodes (52): _absolute_exec(), Availability, _await_active(), create(), _escape(), _halt_marker(), install_proxy_service(), _journal_tail() (+44 more)

### Community 32 - "claude_usage.py"
Cohesion: 0.08
Nodes (46): _claude_home(), config_path(), credentials_path(), current_account(), fetch_usage(), _fmt_reset(), is_over_threshold(), latest_usage() (+38 more)

### Community 33 - "test_config.py"
Cohesion: 0.09
Nodes (51): launch_models_for(), load_backlog_fields(), load_launch_defaults(), load_launch_profile(), Return the persisted TUI launch defaults, falling back to…, The configured launch-model selectors for ``agent``, or [] when unset., Persist the TUI's default launch permission posture (home-level Defaults…, The saved launch profile for one agent, or {} when none was ever saved. Keys… (+43 more)

### Community 34 - "input_bridge.py"
Cohesion: 0.10
Nodes (47): cmd_ask(), Ask the owner a bounded question and block until answered (or timeout). The…, await_response(), cleanup(), InputRequest, InputResponse, list_pending(), _load_request() (+39 more)

### Community 35 - "SpawnSpec"
Cohesion: 0.10
Nodes (31): ABC, Enum, AgentAdapter, AgentRun, EventType, PermissionPosture, Popen, The agent-adapter contract and the shared subprocess plumbing. An adapter has… (+23 more)

### Community 36 - "Codex Plan Review"
Cohesion: 0.04
Nodes (48): 1. Official Claude Code Remote Control, 2. GitHub Agent HQ / Copilot Agents, 3. Claw Orchestrator / OpenClaw Ecosystem, 4. kube-coder, 5. Telegram Bots for Claude Code, Account isolation by env var is useful but not complete security, Alternative Notes, "Always-on" plus subscription CLIs may have policy drift (+40 more)

### Community 37 - "ClaudeAdapter"
Cohesion: 0.09
Nodes (42): ClaudeAdapter, ``config_dirs`` maps an account alias to its ``CLAUDE_CONFIG_DIR`` for multi-…, Argv for an *attended* TUI session (no ``-p``): the user types in it.…, _config_dir_with_email(), _home(), parametrize, Tests for the Claude Code adapter. parse_event fixtures are real lines captured…, The wizard maps alias→dir before the user signs in, so the login is invisible… (+34 more)

### Community 38 - "test_fleet_backlog.py"
Cohesion: 0.09
Nodes (47): _cmd_fleet_backlog(), `horus fleet --backlog`: deterministic, read-only fleet-wide backlog card roll-…, apply_filters(), _card_to_dict(), _format_card(), load_fleet_rollup(), load_project_rollup(), _priority_sort_key() (+39 more)

### Community 39 - "test_account_resolution.py"
Cohesion: 0.07
Nodes (45): AccountRef, AccountResolution, _alias_tokens(), known_accounts(), _name_tokens(), One configured isolated account. ``label`` is both how it is displayed and a…, The outcome of naming an account. Exactly one of ``ref`` / ``error`` is set., Every configured isolated account, claude first then codex, alias-sorted. (+37 more)

### Community 40 - "test_envelope.py"
Cohesion: 0.08
Nodes (47): DispatchRequest, What an unattended launch is asking to do, as the envelope sees it.…, Append one authorized dispatch to the ledger. Call only after ``validate``…, record_dispatch(), _make(), Tests for standing dispatch envelopes — the bound an unattended run runs into.…, The worst failure this artifact has: a misnamed account creates an envelope…, `personal`, `claude personal`, `claude-personal` are one account. (+39 more)

### Community 41 - "test_native_hooks.py"
Cohesion: 0.07
Nodes (46): _claude_hooks_dict(), install_claude_checkpoint_hook(), install_claude_fetch_check_hook(), install_claude_guard_hook(), install_claude_merge_hook(), install_claude_skill_usage_hook(), install_claude_usage_guard_hook(), install_claude_usage_hook() (+38 more)

### Community 42 - "migrate_inline_backlog"
Cohesion: 0.09
Nodes (45): _card_text(), _find_backlog_section(), _infer_type(), inline_backlog_item_count(), _Item, _item_title(), migrate_inline_backlog(), MigrateAction (+37 more)

### Community 43 - "unit_dir"
Cohesion: 0.07
Nodes (46): cmd_schedule_release(), Andon inverse: re-arm a halted dispatch once its base is fixed., cancel(), halt(), Andon: disarm a pending scheduled dispatch so it cannot fire, but keep its…, Andon inverse: re-arm a halted dispatch once its base is fixed. The exact undo…, Disarm and delete a schedule. ``None`` when no such schedule exists. Only ever…, One scheduled dispatch, as reconstructed from its systemd units. (+38 more)

### Community 44 - "FakeAdapter"
Cohesion: 0.09
Nodes (26): AgentEvent, AgentSession, Consume the whole stream and return every event (convenience for tests)., A normalized event. ``raw`` keeps the original parsed payload for callers that…, Mutable handle to a running/finished session. Kept current by AgentRun. This is…, FakeAdapter, ``script`` overrides the default event stream with raw line payloads (each a…, Path (+18 more)

### Community 45 - "session-restore — detect sessions that vanished, and offer to restore them"
Cohesion: 0.04
Nodes (41): 1. The agent's thread id is never recorded, 2026-07-30 — Rafael Figueiredo (manual), 2026-07-30 — Rafael Figueiredo (manual), 2026-07-30 — Rafael Figueiredo (manual), 2026-07-30 — Rafael Figueiredo (manual), 2. The interactive path cannot resume even when given an id, agent-thread-id-and-interactive-restore — Horus cannot reopen a session it launched, Reviews (+33 more)

### Community 46 - "config.py"
Cohesion: 0.11
Nodes (44): _clean_backlog_fields(), _clean_group_by(), config_path(), load_backlog_group_by(), load_github_owners(), load_launch_models(), load_remote_control_default(), _load_table() (+36 more)

### Community 47 - "build_model_rollup"
Cohesion: 0.08
Nodes (42): cmd_capabilities(), EXPERIMENTAL: read-only fleet capability catalog (see horus/capabilities.py).…, build_model_rollup(), datums_path(), _lifecycle_marker(), load_priors(), _oversight_median(), _prior_date_str() (+34 more)

### Community 48 - "ignore_repo"
Cohesion: 0.12
Nodes (42): cmd_ignore(), Manage the per-machine repo ignore list., ignore_repo(), load_ignored_repos(), _normalize_ignored_repo(), Return the per-machine list of repo full-names (``owner/repo``) to hide., Strip whitespace and a leading ``github:`` prefix; return the normalized key., Add a repo full-name to the per-machine ignore list. Returns True if newly… (+34 more)

### Community 49 - "test_onboard.py"
Cohesion: 0.11
Nodes (39): cmd_onboard(), DiscoveryResult, Return value of :func:`discover`., GitIdentity, _automerge_responses(), _fail(), FakeRunner, _known_git_identity() (+31 more)

### Community 50 - "test_integration.py"
Cohesion: 0.16
Nodes (40): integrate(), IntegrationResult, Integrate a change from the working tree according to the workflow policy.…, _fail(), FakeRunner, _last_git_checkout(), _ok(), _policy() (+32 more)

### Community 51 - "test_cockpit.py"
Cohesion: 0.07
Nodes (41): _attach_cockpit(), open_in(), Put this terminal on the cockpit. Error string, or ``None``. Goes through the…, Open the cockpit inside ``host_id``. Returns ``(exit_code, message)``., _home(), `horus tui <host>` — the cockpit front door, and the host-preference default., One cockpit per host. Two would split the owner's state across panes they then…, Being inside herdr is a default, not a veto: the owner's config and the env… (+33 more)

### Community 52 - "RemoteProject"
Cohesion: 0.09
Nodes (38): force_refresh_remote(), gather_remote_projects(), _cache_path(), force_refresh(), _now_iso(), _project_to_cache(), Discover live projects and persist the last successful owner snapshot. Builds…, Refresh one owner and return a user-facing status object. (+30 more)

### Community 53 - "process_upgrade_project"
Cohesion: 0.07
Nodes (41): _path_list_html(), _path_list_param(), _path_list_value(), process_offboard(), process_upgrade_project(), _project_action_banner(), _project_by_index(), Resolve a project POST by its index into the registered list (same safety model… (+33 more)

### Community 54 - "fetch_and_state"
Cohesion: 0.11
Nodes (38): cmd_fetch_check(), _fetch_check_hook(), SessionStart-hook mode: fetch (TTL-cached) and inject a behind-origin warning…, _cache_path(), _fetch(), fetch_and_state(), last_fetch(), _load_cache() (+30 more)

### Community 55 - "test_delivery.py"
Cohesion: 0.13
Nodes (37): The ``<status>-but-delivered · pushed <sha> · PR #N · continuity closed``…, render_receipt(), _bare_origin_and_clone(), _commit_at(), _git(), _head(), _no_pr(), _patch_gh() (+29 more)

### Community 56 - "test_verify_inventory.py"
Cohesion: 0.09
Nodes (37): EmptyWalkError, format_report(), load_manifest(), load_manifest_file(), Path, RuntimeError, Generic file-tree inventory reconciliation. Three of four Drive-to-Git bulk…, Human-readable report lines for a :class:`ReconcileResult`. (+29 more)

### Community 57 - "envelope.py"
Cohesion: 0.09
Nodes (38): cmd_envelope_create(), Create a bounded standing envelope. Bad bounds refuse at create rather than…, create(), envelope_path(), EnvelopeError, envelopes_dir(), ledger_path(), load() (+30 more)

### Community 58 - "UsageSnapshot"
Cohesion: 0.15
Nodes (37): Best-effort usage gate before a run spawns. Returns an exit code to refuse the…, _run_usage_preflight(), The MORE-CONSTRAINING window as ``(percent, reset, label)``. A higher…, UsageSnapshot, test_thresholds_are_used_oriented_so_higher_means_less_headroom(), _home(), `horus run` usage preflight — warn / refuse / --force / fake-exempt., The gate is not weakened generally — only readings that can't describe now. (+29 more)

### Community 59 - "overhead.py"
Cohesion: 0.15
Nodes (38): _project_overhead_html(), Aggregate-only token overhead card for one project detail view., _add_usage(), baseline_comparison(), _baseline_group(), BaselineComparison, BaselineGroup, BaselineSession (+30 more)

### Community 60 - "skills.py"
Cohesion: 0.13
Nodes (37): _base_root(), bundled_for(), install_skills(), installed_version(), is_horus_repo(), missing_or_stale(), Finding, NamedTuple (+29 more)

### Community 61 - "versioning.py"
Cohesion: 0.09
Nodes (35): advisory_line(), parse_stamp(), date, NamedTuple, Path, Release-stamped product-audit staleness (deterministic signal only). The PRD…, Parse ``<version> <YYYY-MM-DD>`` (extra trailing tokens tolerated)., Deterministic release distance for Horus's linear version stream. Sums the… (+27 more)

### Community 62 - "emergency_rescue"
Cohesion: 0.13
Nodes (36): _commit_env(), _current_branch(), emergency_rescue(), _git(), _in_git_repo(), is_worker_context(), _push_worker_branch(), CompletedProcess (+28 more)

### Community 63 - "_init_repo"
Cohesion: 0.07
Nodes (38): _bare_origin_and_worker_clone(), _git(), _init_repo(), _patch_gh(), _push_hook_run(), Path, The acting close's user-visible verdict describes the pushed checkpoint., A run under `--worktree` records its `project` as the WORKTREE path; `--card`… (+30 more)

### Community 64 - "DatumStore"
Cohesion: 0.11
Nodes (32): Activity, _armed(), collect(), fired_outcomes(), _ledger_rows(), _ran_item(), RanItem, Unified read-out of autonomous-dispatch activity: what is ARMED and what RAN.… (+24 more)

### Community 65 - "test_activity.py"
Cohesion: 0.11
Nodes (34): outcome_glyph(), outcome_summary(), Map a run's datum to a ``(glyph, human status)``. Precedence is deliberately…, A one-line delivery outcome for a fired dispatch: the status plus, when the run…, cmd_schedule_status(), One read-out of autonomous-dispatch activity: ARMED dispatches (the future)…, _datum(), _link() (+26 more)

### Community 66 - "test_brainstorm.py"
Cohesion: 0.11
Nodes (34): BrainstormResult, build_prompt(), note_relpath(), _prepare(), Path, Launch a tracked brainstorm session — shared by the CLI and the dashboard. A…, Start the brainstorm as an in-app PTY terminal (headless-safe); return…, Outcome of starting a brainstorm: the launch result plus where the draft lands. (+26 more)

### Community 67 - "test_capabilities.py"
Cohesion: 0.07
Nodes (35): _bold_paragraph_items(), build_project_catalog(), Body of a top-level ``## <heading>`` section, until the next ``## `` heading.…, Text of each *top-level* list item in a section (bullets or numbers). Falls…, Fallback item extractor for ``**Title:** …`` paragraph-style entries. A new…, One-line-per-capability entries from a PRD's ``## Shipped`` section., A short one-line "what IS it" frame from a ``## Vision`` section: its lead…, Build one project's catalog entry from its already-read source text. With no… (+27 more)

### Community 68 - "test_closure.py"
Cohesion: 0.09
Nodes (36): _parse_frontmatter_date(), date, Name remote branches that are not merged into the default branch. Fetch-first…, Coerce a frontmatter `last_updated`/`date` value to a date, tolerantly — a…, One-act-acceptance probe (`horus datum close --card`): is the TARGET project's…, target_continuity_staleness(), unmerged_branch_findings(), _branch_lines() (+28 more)

### Community 69 - "extract_block"
Cohesion: 0.11
Nodes (34): BlockResult, check_drift(), DriftReport, extract_block(), normalize_block(), NamedTuple, Managed-block extraction and drift detection for AGENTS.md / CLAUDE.md. The…, Compare the managed blocks in two instruction files. (+26 more)

### Community 70 - "test_notify_listen.py"
Cohesion: 0.11
Nodes (35): dispatch(), emit_pending_requests(), handle_update(), listen(), The result of handling one update: text to send back, and (for a button tap)…, Map one bounded command string onto a deterministic ``horus`` invocation. Pure…, Turn one Telegram update into a :class:`Reply`, or ``None`` if it is ignored…, Push every not-yet-pushed input request to the owner. Best-effort: a failed… (+27 more)

### Community 71 - "templates.py"
Cohesion: 0.07
Nodes (33): ci_workflow_yaml(), execution_handoff_note(), execution_md(), execution_supervisor_prompt(), features_md(), history_md(), instruction_file(), prd_md() (+25 more)

### Community 72 - "capabilities.py"
Cohesion: 0.10
Nodes (35): Capability, _catalog_to_dict(), default_out_path(), generate(), generate_project(), load_catalog(), load_project_catalog(), project_out_path() (+27 more)

### Community 73 - "test_usage_record.py"
Cohesion: 0.11
Nodes (35): cmd_usage_record(), Record a usage reading pushed by an agent's statusline (stdin JSON). Always…, A snapshot from the JSON Claude Code passes to a ``statusLine`` command. This…, Persist a pushed reading into the shared cache every consumer already reads.…, Whatever ``horus run`` preflight / the PreToolUse guard last wrote to disk for…, read_cache_only(), record_snapshot(), snapshot_from_claude_statusline() (+27 more)

### Community 74 - "fleet_review.py"
Cohesion: 0.13
Nodes (34): build(), _card_record(), _compact(), _curator_manifest(), FleetReview, _gh_content(), _gh_json(), _git() (+26 more)

### Community 75 - "test_usage_snapshot.py"
Cohesion: 0.09
Nodes (35): all_account_targets(), all_accounts_usage(), cached_usage(), Freshest usage snapshot for ``agent``+``account`` (5-hour window). Serves a…, Every ``(agent, account_alias)`` to read: each configured alias per agent, or…, Freshest usage for every configured account (both windows). ``read_only=True``…, _home(), Cached usage snapshot substrate — TTL, negative caching, and failure paths. (+27 more)

### Community 76 - "set_workflow_policy"
Cohesion: 0.13
Nodes (34): cmd_workflow(), Show or update the git-integration workflow policy., load_workflow_policy(), Return the three workflow policy keys, falling back to defaults for any missing…, Update the provided workflow policy keys, persist, and return the new full…, set_workflow_policy(), Return the inner body HTML for the /settings page (workflow policy editor)., render_settings() (+26 more)

### Community 77 - "delivery.py"
Cohesion: 0.11
Nodes (33): capture_delivery_evidence(), _checked_git(), classify_delivery(), _closest_to(), _continuity_closed(), delivery_receipt(), DeliveryEvidence, DeliveryReceipt (+25 more)

### Community 78 - "upgrade.py"
Cohesion: 0.13
Nodes (33): block_version(), The block's version marker, or None for blocks written before it existed., _git(), migration_git_safety(), NamedTuple, Path, Refresh project-local Horus projections from the installed CLI version., Ensure `.horus/PRD.md` records `horus_min_version` >= the current floor. This… (+25 more)

### Community 79 - "History — bumps in the road & decision rationale"
Cohesion: 0.06
Nodes (33): A blocking GUI under console `python.exe` keeps the terminal window alive, A hook file can be installed and still be semantically wrong, A live companion is not proof the dashboard server is live, A machine-local SQLite session registry cut against the ethos, A moving-major action tag that didn't exist silently broke every release, A routine's "verify" step must be reachable by following the routine, A worker handoff file can fake delegation if the supervisor writes it after doing the work, "Allow auto-merge" cannot be enabled on free-plan private repos — the onboard PR class has a plan-level root cause (+25 more)

### Community 80 - "refine_prompt"
Cohesion: 0.12
Nodes (32): Two readiness count lines for the cockpit panel, labelled from the single…, readiness_count_summary(), _branch_lines(), _continuity_lines(), delivery_state(), findings(), _pr_lines(), Finding (+24 more)

### Community 81 - "native_hooks.py"
Cohesion: 0.16
Nodes (33): _claude_checkpoint_hook_command(), _claude_fetch_check_hook_command(), _claude_guard_hook_command(), _claude_hook_command(), _claude_merge_hook_command(), _claude_skill_usage_hook_command(), _claude_usage_guard_hook_command(), _codex_checkpoint_hook_command() (+25 more)

### Community 82 - "session_discovery.py"
Cohesion: 0.14
Nodes (32): _claude_event_timestamp(), _claude_home(), _claude_jsonl_files(), _codex_event_timestamp(), _codex_rollouts(), _codex_session_id(), discover_claude_sessions(), discover_codex_sessions() (+24 more)

### Community 83 - "JWKSCache"
Cohesion: 0.12
Nodes (22): AccessJWTError, _b64url_decode(), _b64url_decode_int(), _decode_json_segment(), _emsa_pkcs1_v15_encode_sha256(), fetch_jwks(), is_valid_access_jwt_request(), JWKSCache (+14 more)

### Community 84 - "codex_usage.py"
Cohesion: 0.11
Nodes (30): latest_codex_cache_status(), account_limit_homes(), codex_home(), _fmt_reset(), latest_account_usage(), latest_usage(), _matches_project(), Any (+22 more)

### Community 85 - "PtyHost"
Cohesion: 0.11
Nodes (13): PtyHost, PtyTerminal, Path, Spawn an interactive agent under a PTY; return the terminal id. Reuses the…, Force the TUI to repaint its full screen: a double TIOCSWINSZ jiggle (rows-1…, Register viewer `viewer_id`'s fitted size and apply the smallest-wins effective…, Drop a viewer (hidden page or disconnected stream) and re-apply the smallest-…, Kill (if still alive) and *forget* a terminal — no tab renders for it again.… (+5 more)

### Community 86 - "reinstall"
Cohesion: 0.11
Nodes (30): _grep_installed_surface(), CompletedProcess, Exception, Path, ``horus reinstall --verify <marker>`` — the known-good reinstall sequence, plus…, Best-effort: any known Horus systemd service still ACTIVE, which keeps serving…, ``uv cache clean <package>`` then ``uv tool install --force --reinstall…, The reinstall sequence itself (cache clean or tool install) failed. (+22 more)

### Community 87 - "selfupdate.py"
Cohesion: 0.11
Nodes (31): build_state(), _cache_path(), check_update(), fetch_release_info(), installed_disk_version(), is_newer(), Path, _python_floor() (+23 more)

### Community 88 - "Path"
Cohesion: 0.08
Nodes (32): _account_usage(), _cached_claude_account_usage(), _dirty_worktree_paths(), _drop_registered(), gather_accounts(), _open_in_editor(), _parse_porcelain_paths(), process_open_lane() (+24 more)

### Community 89 - "usage_snapshot.py"
Cohesion: 0.10
Nodes (29): AccountUsage, cache_dir(), _cache_key(), _cache_path(), _fmt_epoch(), _live_source(), Path, Cached usage snapshot — the shared substrate for the usage-limit survival kit.… (+21 more)

### Community 90 - "Horus - project continuity and control for official coding-agent CLIs"
Cohesion: 0.06
Nodes (31): 0. Current Thesis, 10. Security And Privacy, 11. Short Roadmap, 12. Open Questions, 13. References, 1. Product Principles, 2. Repo-Local Continuity, 3. Native Instruction Files (+23 more)

### Community 91 - "Path"
Cohesion: 0.12
Nodes (31): cmd_hook_install(), claude_settings_path(), codex_hooks_path(), file_has_horus_hooks(), HookAction, install_codex_checkpoint_hook(), install_codex_guard_hook(), install_codex_merge_hook() (+23 more)

### Community 92 - "integration.py"
Cohesion: 0.09
Nodes (30): continuity_pr_findings(), _default_branch(), _has_required_checks(), open_horus_prs(), open_prs(), pr_for_branch(), Any, CompletedProcess (+22 more)

### Community 93 - "test_pty_host.py"
Cohesion: 0.14
Nodes (24): _fake_host(), _FakePty, Tests for the PTY session-host and the cross-platform PTY abstraction., In-memory stand-in for a PtySession: feed output, capture input., Two simultaneously visible viewers must BOTH be able to render the full grid:…, A resize must NOT drop the buffer: it carries the TUI's mode-setting sequences…, The browser reset marker must sit exactly between already-buffered bytes and…, A viewer that vanishes without posting /pty/release (killed tab, dropped… (+16 more)

### Community 94 - "git_state"
Cohesion: 0.12
Nodes (28): cmd_fleet(), cmd_status(), _fleet_fetch(), Refresh remote-tracking refs before reading fleet/status git state: a TTL-…, Headless peer of the dashboard overview: git freshness + latest session., One-line dispatch view for every registered project except the cockpit, or…, _default_branch(), git_state() (+20 more)

### Community 95 - "_setup"
Cohesion: 0.13
Nodes (30): _append_checkpoints(), harvest_checkpoint(), Append new commit messages to an existing optional recovery note and advance…, _msgs(), The closing commit must never be appended into the note it just committed., Hook/skill projections count as continuity: an untracked .claude/settings.json…, A legacy tracked marker must not make the checkpoint hook warn about itself., One universal rule (2026-07-19): the commit is the durable delivery receipt and… (+22 more)

### Community 96 - "test_codex_usage.py"
Cohesion: 0.14
Nodes (28): current_account(), Finding, Return the ``account_id`` from ``$CODEX_HOME/auth.json``, or ``None`` if…, Report project context and account-global rate limits. Context usage belongs to…, usage_findings(), Tests for read-only Codex rollout usage signals., A token_count event whose lanes declare their own window_minutes., The live 2026-07-17 shape: 5-hour limit removed, weekly lane in `primary`. (+20 more)

### Community 97 - "parse"
Cohesion: 0.13
Nodes (28): continuity_source(), Document, has_prd(), parse(), parse_file(), prd_path(), NamedTuple, Path (+20 more)

### Community 98 - "test_skillmap.py"
Cohesion: 0.16
Nodes (28): bundled_skill_versions(), _codex_home(), _frontmatter_description(), instance_verdict(), Path, Read-only skill map: every agent skill installed on this machine, across…, Every skill instance visible on this machine (registered projects + ambient…, Per-instance verdict: ``current``/``stale``/``unmarked`` for Horus-bundled… (+20 more)

### Community 99 - "_new_ui"
Cohesion: 0.08
Nodes (30): _footer(), _new_ui(), The one action the card asked for: `o` on the backlog pane hands the whole…, `o` must not fire on other screens — the backlog-only bindings are filtered…, `U` exists because usage is spent on other machines and the native apps. A…, One unreachable account must not cost the other accounts their refresh.…, A partial refresh must not read as a full one. The whole point of the key is…, `u` stays cache-only; only `U` is allowed to fetch. They are one keystroke… (+22 more)

### Community 100 - "_usage_check_claude"
Cohesion: 0.07
Nodes (29): _close_merge_hook(), _closure_sentinel_kind(), cmd_guard_host(), cmd_hook_skill_invoked(), _current_band(), _emit_usage_closure(), _guard_host_hook(), _is_gh_pr_merge_command() (+21 more)

### Community 101 - "Path"
Cohesion: 0.14
Nodes (29): _canonical_checkpoint(), _canonical_continuity_paths(), checkpoint_gate(), commit_continuity(), continuity_off_default(), default_branch(), direct_push_violations(), _enforce_push() (+21 more)

### Community 102 - "launch.py"
Cohesion: 0.14
Nodes (27): launch_interactive(), prepare_interactive(), Path, Spawn an attended agent session and track it — shared by the CLI and the…, Open an attended session in its own terminal and register it as running.…, Validate and build an attended launch without choosing its terminal host.…, _home(), Tests for the shared attended-launch orchestration (`horus.launch`). (+19 more)

### Community 103 - "watch"
Cohesion: 0.11
Nodes (28): Poll ``ref`` (a PR number/URL or a literal commit sha) until its watched checks…, watch(), fake_gh(), _FakeGh, _json_ok(), fixture, Scripted responder keyed by the command's stable prefix (argv[1:3])., Reproduces the reported bug: a squash-merge sha linked to an already merged PR… (+20 more)

### Community 104 - "install_listen_service"
Cohesion: 0.11
Nodes (28): cmd_notify_listen(), Long-poll the telegram sink for bounded steering commands from the owner. The…, install_listen_service(), listen_service_active(), listen_service_installed(), Whether the persistent listen unit file exists on disk., Whether the persistent listen service is running or coming up., Write and enable the persistent listen service. Refuses a second one.… (+20 more)

### Community 105 - "resume_preflight.py"
Cohesion: 0.16
Nodes (26): cmd_resume(), _compact(), gather(), _git_projection(), _pct(), _project_key(), _project_projection(), Any (+18 more)

### Community 106 - "test_warmup.py"
Cohesion: 0.12
Nodes (26): cmd_warmup(), Open one cheap turn per Claude account to start its 5h usage window. Claude…, claude_accounts(), Warm up the Claude usage window on demand. Claude's 5-hour usage window only…, Every configured Claude account alias (each an isolated CLAUDE_CONFIG_DIR)., Open one ``claude -p`` turn under ``config_dir`` to start its window., Open one cheap turn per Claude account to start its 5h window. ``accounts``…, _warm_one() (+18 more)

### Community 107 - "install_keepwarm_service"
Cohesion: 0.10
Nodes (28): _cmd_warmup_keep(), The ``horus warmup --keep`` family: run/install/stop/restart/status the per-…, install_keepwarm_service(), keepwarm_active_accounts(), keepwarm_service_active(), keepwarm_service_installed(), keepwarm_unit(), linger_enabled() (+20 more)

### Community 108 - "test_notify.py"
Cohesion: 0.19
Nodes (26): escalate(), NotifyConfig, Best-effort push of one escalation. NEVER raises. ``force=True`` bypasses the…, The ``[notify]`` block, already parsed. ``sink == "none"`` means pull-only., _esc(), Tests for the machine-local escalation channel (`horus/notify.py`). The…, A phone message must not print the summary twice. Telegram sends body() (which…, A pre-launch death is actionable, so it escalates without opt-in — like the… (+18 more)

### Community 109 - "test_terminal_tui.py"
Cohesion: 0.12
Nodes (25): _machine_ui(), _project_with_branch_tree(), A UI parked on the backlog screen of a project with one branch umbrella (one…, The one launch axis is WHAT CONTEXT is loaded — resume loads the authored…, A UI with every machine-state read stubbed, for the Mission Control / Settings…, _StubEnv, test_backlog_group_children_get_tree_connectors_and_priority_dots(), test_backlog_screen_shows_grouped_sections_expanded_by_default() (+17 more)

### Community 110 - "cache_status.py"
Cohesion: 0.17
Nodes (20): CacheStatus, _claude_jsonl_files(), _codex_status_from_event(), _event_datetime(), _int(), latest_claude_cache_status(), _mtime_datetime(), _parse_datetime() (+12 more)

### Community 111 - "test_launch_targets.py"
Cohesion: 0.11
Nodes (26): _account_launch_form(), _launch_target_options(), _nav(), The Sessions cockpit (revived from the retired Control tab): one drivable sub-…, A compact "N live → Sessions" banner for the project/index pages. The Sessions…, One-click fresh session as this account. Native terminal on a desktop; the in-…, Launch destinations for the "Open in" select. The in-app terminal works…, render_sessions() (+18 more)

### Community 112 - "test_sync.py"
Cohesion: 0.15
Nodes (25): fast_forward(), plan(), Any, Path, Explicit fast-forward sync — the remedy half of the fetch-first rule. Fetch-…, Decide what to do from a :func:`horus.gitstate.git_state` mapping. Pure…, Run the fast-forward merge. Returns ``(ok, message)``., _git() (+17 more)

### Community 113 - "ModelRollup"
Cohesion: 0.11
Nodes (26): Non-blocking nudge printed to stderr: never affects exit code or stdout., _warn_if_priors_stale(), _capability_cell(), delegation_matrix_to_dict(), _format_price(), ModelRollup, CAPABILITY column text. ``--verbose``/``--full`` shows a fuller (still bounded)…, Truncate at a word boundary (never mid-word) for a short "a few words" glance,… (+18 more)

### Community 114 - "test_companion.py"
Cohesion: 0.14
Nodes (24): On Windows, re-exec the current ``horus`` invocation under ``pythonw.exe`` so…, Resolve the platform default for the companion artwork style., One badge line per agent summarizing background worker sessions. ``running``…, relaunch_without_console(), resolve_mascot_style(), worker_status_lines(), Tests for the lightweight Horus companion shell., test_relaunch_without_console_noop_off_windows() (+16 more)

### Community 115 - "load_projects"
Cohesion: 0.12
Nodes (26): _ambient_account_dir(), _as_key(), clear_proxy_env(), load_projects(), prune_projects(), Path, Set the machine-local root where remote projects should be cloned., Remove ``project_path`` from the user config. Returns True if it was present. (+18 more)

### Community 116 - "offboard.py"
Cohesion: 0.17
Nodes (24): Remove the managed block (markers included) from ``text`` — the inverse of…, remove_block(), _handle_horus_dir(), offboard_project(), OffboardAction, _prune_empty_dirs(), NamedTuple, Path (+16 more)

### Community 117 - "machine_requirements.py"
Cohesion: 0.15
Nodes (22): Finding, findings(), _front_matter(), inspect(), _missing_detail(), _parse_declaration(), NamedTuple, Path (+14 more)

### Community 118 - "test_vscode.py"
Cohesion: 0.15
Nodes (24): _is_horus_file(), NamedTuple, Path, Static VS Code task projection — the one-keypress tier of "launch in VS Code".…, Create `.vscode/tasks.json` when absent; upgrade in place when it's an unedited…, Offboard counterpart: remove tasks.json only if it's an unedited Horus…, remove_tasks(), TaskAction (+16 more)

### Community 119 - "Horus Product Interview"
Cohesion: 0.08
Nodes (25): `AGENTS.md` And `CLAUDE.md`, Budget-Aware / Context Rollover Closure, Build For Current Needs, Closure Ritual, Core Shift, Current Product Definition, Cynic Tests And Answers, Git Policy For `.horus/` (+17 more)

### Community 120 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native AGENTS.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 121 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 122 - "Handoff: Horus Dashboard Redesign"
Cohesion: 0.08
Nodes (24): 1. Header / nav (`header.top`, shared across views), 2. Projects overview / cockpit (`#overview`), 3. Project detail page (`#detail`), 4. Settings (`#settings`), About the Design Files, Assets, Dark theme (`:root`), Design Language (+16 more)

### Community 123 - "AccessJwtVerifyTests"
Cohesion: 0.21
Nodes (9): b64url_encode(), b64url_int(), jwks_dict(), make_token(), Shared TEST-ONLY RSA fixture for Access gate tests. This keypair was generated…, Independently re-derives the EMSA-PKCS1-v1.5/SHA-256 block and signs with the…, sign_rs256(), valid_payload() (+1 more)

### Community 124 - "_usage_guard_hook"
Cohesion: 0.16
Nodes (22): cmd_usage_guard(), _emergency_state_save(), _emit_pretooluse_context(), _guard_session_id(), Alias of the account this session runs under (registered alias when known, else…, Inject advisory context on a PreToolUse hook (never a deny)., Perform the worker-aware emergency state-save once per window, then inject…, PreToolUse usage guard: advisory near the limit, emergency state-save at the… (+14 more)

### Community 125 - "_envelope_guard"
Cohesion: 0.16
Nodes (24): _envelope_guard(), _envelope_usage_remaining(), _EnvelopeAuth, An authorized unattended dispatch, carried from the guard to the ledger write., Percent of the account's most-constraining window still available, or ``None``…, Validate an unattended dispatch against its standing envelope. Returns…, _args(), _make_live() (+16 more)

### Community 126 - "render"
Cohesion: 0.12
Nodes (22): _cells(), first_sentence(), _inline(), _is_table_separator(), plain_text(), A deliberately small, safe Markdown-to-HTML renderer. Covers only what…, Body of a third-level (`### `) markdown section within a section body, until…, Third-level (`### `) heading titles at the top of a markdown section body, in… (+14 more)

### Community 127 - "regen_mascot.py"
Cohesion: 0.18
Nodes (23): Image, autocrop(), clear_dark_edges(), defringe(), floodfill_bg(), _is_checker_bg(), keep_largest_opaque_component(), key_checkerboard_bg() (+15 more)

### Community 128 - "Horus Hub Design"
Cohesion: 0.08
Nodes (23): Assets, Attack Surface, Decisions to Carry Forward, Deployment Shape, Hard Requirement Trace, Horus Hub Design, Interop Seam, Launch Capability (+15 more)

### Community 129 - "Handle"
Cohesion: 0.12
Nodes (15): Handle, LaunchBackend, Protocol, One observed output event from :meth:`LaunchBackend.stream`. Minimal on…, The frozen seam. A backend serves one or more targets; callers hold only…, Start a session for ``brief`` and return its :class:`Handle`., The current lifecycle state of the session ``handle`` refers to., Yield the session's output events (where the backend can observe them). (+7 more)

### Community 130 - "test_backend.py"
Cohesion: 0.21
Nodes (20): LaunchBrief, LocalBackend, Runs the session on *this* machine, wrapping today's attended local launcher.…, A backend-neutral request to launch a session. Mirrors the inputs of today's…, _home(), Tests for the frozen LaunchBackend seam and its only concrete impl,…, test_default_brief_targets_local(), test_handle_ownership_is_guarded() (+12 more)

### Community 131 - "Omnigent"
Cohesion: 0.09
Nodes (19): Claude research — additions to the Codex pass (2026-06-29), Codex research (verbatim, 2026-06-29), Drift triggers — if you're about to build any of these, STOP, Fit against the current use case (2026-06-29), Omnigent, Sources, Suggested interop shape (continuity-MCP first) — NOT scheduled, Two planes (the division if/when adopted) (+11 more)

### Community 132 - "_run"
Cohesion: 0.12
Nodes (23): _checkpoint_msgs(), _feature_branch_clone(), A repo without hooks/skills installed: `git add` must not fail wholesale on…, Fresh committed repo, no remote: tree clean, and the unpushed check is skipped…, `enforce_push: false` in PRD frontmatter skips the unpushed-commits check., A clone with a known remote HEAD, sitting on a pushed feature branch. With…, A close performed directly on the default branch reports exactly as before., A branch that never touched continuity has nothing canonical pending — the… (+15 more)

### Community 133 - "tui-control-settings-pane — a machine Control pane in the TUI"
Cohesion: 0.10
Nodes (18): Acceptance, autonomous-activity-timeline — one read-out of what's armed + what ran, How, Non-goals, Acceptance, Decisions (owner, 2026-07-18), How (stays within the TUI-thin rule), Non-goals (+10 more)

### Community 134 - "session-process-cadence — a more usage-efficient continuity/ceremony cadence, without reviving launch modes"
Cohesion: 0.09
Nodes (20): Acceptance, close-check-claims-canonical-while-unmerged — a green gate that the default branch does not back, Related, Source, The defect is the wording, not the check, Two candidate remedies, pick one, Why — measured in fabric-build, 2026-08-03, Candidate directions (open — sketches, not decisions) (+12 more)

### Community 135 - "closure.py"
Cohesion: 0.14
Nodes (21): boundary_freshness_gate(), closure_status(), freshness_gate(), _latest_session_note(), ParallelSignal, pending_delivery_findings(), pr_diff_freshness(), pr_freshness_gate() (+13 more)

### Community 136 - "companion.py"
Cohesion: 0.14
Nodes (21): acquire_singleton_lock(), _app_browser(), _app_window_argv(), dashboard_profile_dir(), _flatpak_app(), mascot_asset_path(), mascot_background_path(), mascot_frame_paths() (+13 more)

### Community 137 - "ensure_dashboard"
Cohesion: 0.13
Nodes (20): _dashboard_command(), ensure_dashboard(), log_companion_event(), _log_line(), _open_startup_log(), Command for a fresh dashboard process from this installed CLI., Append handle to ``~/.horus/logs/<name>.log`` (rotated once when oversized), or…, Record a companion lifecycle event/failure (visible even under pythonw). (+12 more)

### Community 138 - "github_catalog.py"
Cohesion: 0.19
Nodes (21): CachedCatalog, _default_branch(), discover(), drop_registered(), load_cache(), _local_projects_by_remote(), _match_local(), _normalize_remote() (+13 more)

### Community 139 - "launcher.py"
Cohesion: 0.13
Nodes (20): _descendant_pids(), focus_window_for_pid(), login_argv_env(), open_terminal(), open_vscode(), _posix_terminal_argv(), Path, Open an interactive agent session in its own terminal window. This is the… (+12 more)

### Community 140 - "mergewatch.py"
Cohesion: 0.14
Nodes (21): _context_base(), fetch_check_states(), MergeWatchError, _parse_workflow(), CompletedProcess, Exception, Path, ``horus merge-watch <sha|pr>`` — absorb the wait, not the observation. The… (+13 more)

### Community 141 - "Path"
Cohesion: 0.10
Nodes (22): _card_deps(), _close_continuity(), halt_dependents(), _merge_pr(), _pr_state(), Path, Required CI green on the exact head SHA. (True, sha) or (False, why)., The continuity/freshness gate for this PR's diff. (True, "") or (False, why). (+14 more)

### Community 142 - "parallel_deliveries"
Cohesion: 0.19
Nodes (20): _gh_json(), _is_ancestor(), parallel_deliveries(), parallel_delivery_findings(), Is ``commit`` an ancestor of ``of``? None when it cannot be decided (unknown…, A best-effort `gh ... --json` call. None on any failure (gh absent, offline,…, Detect other concurrent writers on this project. Returns (signals, pr_checked);…, Render :func:`parallel_deliveries` as gate findings. Empty (not a false 'all… (+12 more)

### Community 143 - "notify_listen.py"
Cohesion: 0.11
Nodes (20): _api(), _chat_id_of(), Command, format_request(), _get_updates(), _help_text(), ListenResult, _parse_answer() (+12 more)

### Community 144 - "test_projection_sync.py"
Cohesion: 0.19
Nodes (19): Any, Path, Read-only projection-sync check: does each agent surface carry the current…, Per-surface sync summary plus a project-level verdict. Never raises: a broken…, _surface_state(), sync_state(), _verdict(), _fully_synced_project() (+11 more)

### Community 145 - "4. The branches"
Cohesion: 0.10
Nodes (20): 1. Where we are, 2. Where the market is, 3. The tree, 4. The branches, 5. Speculative branches (no facet yet), 6. Backlog disposition — done AFTER the branches, 7. Recommendation, held loosely, 8. Owner gate (+12 more)

### Community 146 - "skill_usage.py"
Cohesion: 0.15
Nodes (19): Counter, counts(), _entries(), log_path(), date, Path, Machine-local record of which bundled skills actually get invoked. `skill-…, (`skill`, count) for every KNOWN skill, most-used first, zeroes included. The… (+11 more)

### Community 147 - "test_batch.py"
Cohesion: 0.24
Nodes (16): emit_if_complete(), Emit the single ``schedule-batch-complete`` signal, once, when the batch is…, EscalationResult, What happened to one escalation. ``delivered`` is the only success state;…, _capture_escalations(), _datum(), The aggregate `schedule-batch-complete` signal. Membership is reconstructed…, _sched() (+8 more)

### Community 148 - "cmd_usage_check"
Cohesion: 0.28
Nodes (19): cmd_usage_check(), _args(), Account-scoped `usage check --account`: explicit mapping resolution, no ambient…, It used to say "missing/expired credentials, offline, or no telemetry yet" —…, A previous reading is better evidence than claiming to know nothing — but it…, Hermetic stubs: no real config, credentials, or network reads. ``snapshot`` is…, _stub(), test_a_failed_fresh_read_falls_back_to_the_last_reading_with_its_age() (+11 more)

### Community 149 - "_replace_stale_dashboard"
Cohesion: 0.11
Nodes (20): dashboard_identity(), dashboard_is_live(), dashboard_url(), _kill_pid_tree(), _looks_like_horus_dashboard(), _pid_listening_on(), Any, The `/health` identity of a live server, or None (pre-/health build, foreign… (+12 more)

### Community 150 - "supervise.py"
Cohesion: 0.16
Nodes (18): _context_from_record(), _escalate(), _escalate_and_halt(), escalate_unresolved(), _find_envelope_for_session(), Unattended verify → merge → close → escalate for a dispatched card. A…, Resolve a session id/prefix (preferred) or a PR ref into a context. A session…, A deferred target that resolved to nothing escalates (andon) and merges… (+10 more)

### Community 151 - "_write_backlog_card"
Cohesion: 0.10
Nodes (20): A card without parallel/surface — the pre-existing card shape — still claims., `order:` has a consumer, which is the whole point: the sequence renders with no…, Zero migration: a project that has never been ordered shows no sequence column., The verb is print-only: the one-keypress launch lives in the TUI, and this…, test_backlog_claim_back_compat_no_new_fields(), test_backlog_claim_non_overlapping_proceeds_clean(), test_backlog_claim_warns_and_blocks_on_surface_overlap(), test_backlog_defaults_to_list_and_help_states_default() (+12 more)

### Community 152 - "_plain"
Cohesion: 0.15
Nodes (20): _plain(), _project_with_cards(), _project_with_skill_drift(), Universal fallback: a project whose default (facet) lens yields no real…, A UI parked on the backlog screen of a project with two cards: one carrying the…, A UI on the skills screen of a project where claude skills are installed with…, test_backlog_rows_are_unchanged_when_no_fields_are_configured(), test_backlog_rows_render_configured_fields_inline_in_pick_order() (+12 more)

### Community 153 - "Product audit — 2026-07-20 (horus 0.0.73) — inward alignment analysis"
Cohesion: 0.11
Nodes (18): 1. The product, in plain terms, 2. Facets — roster and standing at a glance, 3. Vision branches — roster and standing at a glance, 4. Where each facet stands — detail, 5. Triage, 6. Ceremony observations, 7. Routed suggestions (nothing decided here), Accounts & isolation (+10 more)

### Community 154 - "load_notify_config"
Cohesion: 0.16
Nodes (19): cmd_notify_escalate(), Push one escalation now — the machine-local entrypoint a scheduled dispatch's…, load_notify_config(), Read ``[notify]`` from ``~/.horus/config.toml``. Tolerant like the other owner-…, _escalate_args(), No sink configured ⇒ behaves exactly as today: no escalation, no failure., Best-effort by construction: a dead bot must never turn a pre-launch death into…, test_escalate_appends_an_explicit_detail() (+11 more)

### Community 155 - "remote_start.py"
Cohesion: 0.19
Nodes (18): _clone_project(), _clone_repo(), _configure_local_git_identity(), _git_config_value(), onboard_github_project(), OnboardResult, parse_github_target(), Path (+10 more)

### Community 156 - "terminal_app.py"
Cohesion: 0.33
Nodes (18): _ask(), _Cancel, _choose_account(), _compact(), _focus(), _home(), _launch(), _line() (+10 more)

### Community 157 - "test_overhead.py"
Cohesion: 0.30
Nodes (18): _claude_event(), _codex_call(), _codex_meta(), _codex_tokens(), _codex_turn(), Tests for Horus token overhead estimation., test_baseline_comparison_aggregates_explicit_sessions(), test_claude_overhead_dedupes_request_ids() (+10 more)

### Community 158 - "Bug: `horus app` wedges silently when a stale companion holds the singleton lock"
Cohesion: 0.11
Nodes (17): 1. Surface the condition before detaching (P0), 1. The diagnostic message is swallowed in the default (detached) path, 2. Reap a stale companion on 8764, mirroring the dashboard path (P0/P1), 2. The lock has no staleness/liveness/version check, 3. Add an explicit escape hatch (P1), 3. No window-raise across processes, 4. Investigate the double-spawn (P2), Acceptance criteria (+9 more)

### Community 159 - "pty_host.py"
Cohesion: 0.13
Nodes (11): The local browser session-host: owns PTY viewers for interactive terminals. On…, # NOTE: do NOT clear the scrollback here. It's tempting (bytes written, PtySession, Path, Cross-platform pseudo-terminal (PTY) spawning — the foundation for real TUIs. A…, Spawn ``argv`` attached to a fresh pseudo-terminal of size ``cols``x``rows``., A running process attached to a pseudo-terminal. Byte-oriented + platform-…, Block until output is available; return it. Raise ``EOFError`` at end. (+3 more)

### Community 160 - "test_supervise.py"
Cohesion: 0.24
Nodes (17): Run the unattended acceptance gate for one delivery. See module docstring., supervise(), _ctx(), _no_real_effects(), fixture, Tests for the unattended verify → merge → close → escalate supervisor. The…, All gates green, all actions succeed, no escalation transport, no andon — each…, test_all_green_authorized_and_probe_passes_merges_closes_ships() (+9 more)

### Community 161 - "_guard_hook_run"
Cohesion: 0.16
Nodes (18): _assert_denied(), _guard_hook_run(), parametrize, test_global_state_cleanup_is_not_blocked_in_attended_terminal(), test_guard_allows_benign_command_when_hosted(), test_guard_allows_mere_mentions_of_the_host(), test_guard_blocks_app_relaunch_when_hosted(), test_guard_blocks_dashboard_relaunch_via_module() (+10 more)

### Community 162 - "_home_with_project"
Cohesion: 0.20
Nodes (18): _drive(), _home_with_project(), A git_state dict with a live upstream, overridable per key., A UI parked on the projects (home) screen for one project whose git_state is…, The real `g` binding must fetch every project (read-only) then re-read…, `g` must never fetch from another screen — the network touch is projects-only., _remote_state(), _select_project_row() (+10 more)

### Community 163 - "vision-branch-x3 — scheduling & autonomous execution"
Cohesion: 0.12
Nodes (15): Closure acceptance (for the branch, not the individual cards), Current state (refreshed 2026-07-19), Notes, Original exists-vs-gaps map (findings, 2026-07-17), Promotion + kit order (owner, 2026-07-17), Reviews, Scope tension (the reason this is a *branch*, not accepted scope), The branch's cards (proposed together) (+7 more)

### Community 164 - "test_checkpoint_hook.py"
Cohesion: 0.34
Nodes (16): _checkpoint_hook(), Stop-hook mode: warn (default) or block (opt-in) when the working tree is dirty…, Behaviour of the `horus checkpoint --hook` Stop hook (warn default / block opt-…, Never re-fire when the agent reports the stop was already hook-driven (loop…, Per-turn harvesting went with the granularity knob (2026-07-19): session notes…, _sid(), _stub_findings(), _stub_stdin() (+8 more)

### Community 165 - "open_dashboard"
Cohesion: 0.14
Nodes (17): open_dashboard(), Popen, raise_dashboard_window(), Terminate ``process`` and any children it spawned. Windows virtualenv launchers…, Open the dashboard. Owned app-window mode launches a dedicated, trackable…, Best-effort: bring the owned dashboard window to the front. Full on Windows…, Reuse an already-open owned window (raise it) instead of opening a duplicate;…, Close the owned dashboard window when the companion quits, so it doesn't linger… (+9 more)

### Community 166 - "load_dashboard_access"
Cohesion: 0.23
Nodes (17): ConfigError, load_dashboard_access(), Load the optional ``[access]`` block that arms dashboard exposed mode. Returns…, Raised when a present-but-malformed config block should fail closed. Tolerant…, _require_str(), _configure_access(), Load the [access] gate — ONLY in exposed mode. Local (loopback) mode never…, _home() (+9 more)

### Community 167 - "render_control"
Cohesion: 0.13
Nodes (17): gather_projects(), render_control(), render_sessions_card(), A viewer attaching across a geometry change must reset its screen and request a…, The viewer must handle both gone-session signals: the 'unknown' SSE status…, Every page (projects, control, sessions) includes the Settings nav link., test_accounts_panel_badges_and_codex_launch_form(), test_accounts_panel_renders_weekly_bar_with_reset() (+9 more)

### Community 168 - "Handler"
Cohesion: 0.15
Nodes (10): The integrated terminal: a tab + real xterm.js terminal per PTY session. Each…, serve(), _SingleInstanceServer, _terminal_panel(), Handler, main(), _page(), BaseHTTPRequestHandler (+2 more)

### Community 169 - "initialize.py"
Cohesion: 0.22
Nodes (16): Action, _confirm(), _ensure_backlog_dir(), _ensure_ci_workflow(), _ensure_gitignore(), _ensure_instruction_file(), NamedTuple, Path (+8 more)

### Community 170 - "Roadmap branches: deepen-own-use re-baseline — 2026-07-20"
Cohesion: 0.12
Nodes (16): 1. Where we are, 2. Where the market is, 3. The tree, 4. The branches, 5. Speculative branches, 6. Existing-backlog dispositions (nothing inherited silently), 7. Recommendation, held loosely, A — Declare the engine's API (secondary) (+8 more)

### Community 171 - "Core technical findings"
Cohesion: 0.12
Nodes (16): Approaches considered, Cloud rendezvous via an outbound connection, Codex mobile finding (corrects the initial assumption), Conclusions, Core technical findings, iOS sandbox blocks a Horus-style account-switch helper, Mobile access to agent sessions — terminal persistence, session sharing, and account-switch friction — 2026-07-21, Open questions to verify before anything is load-bearing (+8 more)

### Community 172 - "parse_tasks"
Cohesion: 0.23
Nodes (14): next_step(), parse_tasks(), Progress, NamedTuple, Parse the roadmap checklist into tasks, progress, and the next actionable step.…, First in-progress task, else first open task, else None (all done/empty)., Task, Tests for roadmap task parsing, progress, and next-step derivation. (+6 more)

### Community 173 - "resolve_deferred"
Cohesion: 0.18
Nodes (14): _latest_record_for_branch(), The most-recent worker session record whose delivery landed on ``branch``., Resolve a DEFERRED target — a card or branch selector — to the worker session…, resolve_deferred(), _Env, A `--card` target resolves at fire time to the newest worker session dispatched…, _rec(), _Reg (+6 more)

### Community 174 - "Diagnosis: hosted terminal sizing & lifecycle (mobile + desktop)"
Cohesion: 0.12
Nodes (15): 1. What the terminal is (so the fix stays in scope), 2. Live reproduction (headless Chromium over CDP), 3. Root-cause map (8 symptoms → shared causes), 4. Symptom 2 is out of this redesign's spine (but must be tracked), 5.1 Sizing: make the terminal a self-observing, fill-its-region surface, 5.2 Fullscreen + tabs + touch state: track it, don't decide it once, 5.3 Controls: fewer misclicks, reversible actions, 5.4 Genuine constraints (called out honestly) (+7 more)

### Community 175 - "Mobile/desktop terminal: sizing + lifecycle + controls hardening"
Cohesion: 0.12
Nodes (13): Investigation 2026-07-12 (inline session, no dispatch), Mobile terminal accepts no input on the hosted/mobile app, Execution note, Folds in (history preserved, not deleted), Genuine constraints (doc §5.4), Mobile/desktop terminal: sizing + lifecycle + controls hardening, Proposed work (doc §5; no impl yet), Root causes (confirmed; see doc §3 for the symptom→cause map) (+5 more)

### Community 176 - "DashboardProcess"
Cohesion: 0.19
Nodes (16): DashboardProcess, ensure_dashboard_for_open(), NamedTuple, Replace a dead child owned by ``horus app``; adopted servers stay untouched., Return a live dashboard before opening the browser. The companion can outlive…, Terminate a dashboard server *this* companion spawned, so it doesn't outlive…, respawn_dashboard_if_needed(), stop_dashboard() (+8 more)

### Community 177 - "test_mergewatch.py"
Cohesion: 0.18
Nodes (14): overall_state(), Contexts the base branch's protection requires, or ``None`` when unknowable (no…, ``"pending" | "success" | "failure"`` across the watched set (required contexts…, required_contexts(), `horus merge-watch <sha|pr>` — poll required checks on the exact sha until they…, test_overall_state_failure_wins_over_pending(), test_overall_state_falls_back_to_all_checks_when_required_unknown(), test_overall_state_ignores_non_required_checks() (+6 more)

### Community 178 - "notify.py"
Cohesion: 0.23
Nodes (12): Escalation, _post_json(), Machine-local push channel so an unattended supervisor can reach the owner.…, Human summary for ``horus notify show`` — the token is always redacted., The essentials an owner needs to act, transport-agnostic., _redact(), render_config(), _send_hermes() (+4 more)

### Community 179 - "Roadmap branches: deepen-own-use re-baseline — 2026-07-31"
Cohesion: 0.12
Nodes (15): 1. Where we are, 2. Where the market is, 3. The tree, 4. The branches, 5. Speculative branches, 6. Existing-backlog dispositions — nothing inherited silently, 7. Recommendation, held loosely, 8. Owner verdict — the tree was REJECTED, and why (2026-07-31) (+7 more)

### Community 180 - "Roadmap branches: deepen-own-use re-baseline — 2026-08-01 (v8 run)"
Cohesion: 0.12
Nodes (15): 1. Where we are, 2. Where the market is, 3. The tree, 4. The branches, 5. Speculative branches, 6. Recommendation, held loosely, 7. Owner gate, Branch A — Cockpit tells the truth (primary) (+7 more)

### Community 181 - "_isolated_home"
Cohesion: 0.17
Nodes (16): Cache-only remote Horus project listing: (visible, ignored, error notes). Reads…, Clone (if needed) + register + refresh projections for a selected remote…, _remote_projects(), _RemoteStart, _start_remote(), _isolated_home(), _remote_project(), test_activate_remote_project_exits_with_remote_start() (+8 more)

### Community 182 - "test_dashboard_access.py"
Cohesion: 0.28
Nodes (15): _arm_exposed(), Dashboard exposed mode: [access] config loading + fail-closed handler gate.…, _run(), _same_origin(), test_get_allowed_through_with_valid_auth(), test_get_denied_without_auth_in_exposed_mode(), test_health_public_in_exposed_mode(), test_local_mode_unchanged_when_no_access_block() (+7 more)

### Community 183 - "`consolidate`"
Cohesion: 0.13
Nodes (14): Boundaries, Commands, `consolidate`, Deterministic pre-pass (Horus, Python), Deterministic pre-pass (Horus, Python), `distill-history`, Emitted prompt, Emitted prompt (+6 more)

### Community 184 - "notify-schedule-batch-complete — a real "the schedule finished" signal, not a timer guess"
Cohesion: 0.13
Nodes (12): Acceptance, How, Non-goals, notify-schedule-batch-complete — a real "the schedule finished" signal, not a timer guess, Acceptance, How (thin, read-only projection), Non-goals, schedule-status-outcome-not-just-fired — Mission Control shows the outcome, not just "fired" (+4 more)

### Community 185 - "review-session-control-calibration — independently review the controls learned in the first Codex session"
Cohesion: 0.13
Nodes (14): 1. Resume context was mistaken for authorization, 2. Delegation analysis loaded without an owner request, 3. Inline batch confused backlog cards with incidental findings, 4. A direct mode was missing, Action — fresh-context review only, Exit / acceptance, Follow-up session context — 2026-07-19, Independent fresh-context review — 2026-07-19 (Claude, All Gas session) (+6 more)

### Community 186 - "tui-backlog-refine-and-order — groom + order the backlog into a schedulable plan"
Cohesion: 0.13
Nodes (13): Acceptance, How — the four revisions (scope-cards v3→4, plus one pathfinder touch), Non-goals, scope-cards-v4-grooming-and-contract-refinements — what the first live run taught, Source, 2026-07-27 — Rafael Figueiredo (agent), Acceptance (firmed 2026-07-19 — order design decided above), How (to design in-card) (+5 more)

### Community 187 - "dispatch-workflow-comparative-study — compare what we have vs other existing workflows"
Cohesion: 0.13
Nodes (14): Boundaries, Candidate comparison set (refine when claimed), Deliverable, Design directions to test (hypotheses, not decisions), dispatch-workflow-comparative-study — compare what we have vs other existing workflows, Findings (starting point — lived from the `tabi-triage-1` run, 2026-07-23), Motivation, Non-negotiable (+6 more)

### Community 188 - "intent-preserving-goal-campaign — bind the spirit, let a frontier agent choose the form"
Cohesion: 0.13
Nodes (14): Alternatives deliberately not required up front, Another autonomous-refinement subsystem, Bulk rewrite of existing cards, Evidence and verdict, Form — advisory by default, intent-preserving-goal-campaign — bind the spirit, let a frontier agent choose the form, Non-goals, Open decisions (+6 more)

### Community 189 - "Unified Horus artifact refresh — detect, preview, integrate, verify"
Cohesion: 0.13
Nodes (13): Exit, Field evidence — stale skill produced WRONG WORK, not stale prose (2026-07-30), Field evidence — two hand refreshes at 0.0.73 (2026-07-20), Field evidence — v0.0.73 made the fleet's prose stale (2026-07-19), Narrowed scope (2026-07-28) — two steps, not five, Non-goals while Shaping, Open decisions, Reviews (+5 more)

### Community 190 - "cmd_doctor"
Cohesion: 0.26
Nodes (14): _account_isolation_findings(), cmd_doctor(), Finding, Advisory checks that every known account has its own isolated config dir. Two…, _accounts(), Doctor advisory checks: flag non-isolated/shared accounts and outdated managed…, test_account_findings_empty_without_accounts(), test_account_findings_flag_shared_dir() (+6 more)

### Community 191 - "test_config_dir_guard.py"
Cohesion: 0.29
Nodes (14): _config_dir_conflict_guard(), Advise (never refuse) when a launch shares a live config dir. Claude Code and…, Tests for the config-dir concurrency guard in horus.cli. Claude Code and Codex…, Launching on 'personal' while another live session already holds personal's dir., The one live peer on the target dir IS the launching session's own dir., Overseer + another live worker already share the target dir -> still proceeds,…, _rec(), _setup() (+6 more)

### Community 192 - "keepwarm.py"
Cohesion: 0.20
Nodes (13): _default_warm(), keep_warm(), KeepWarmResult, next_delay(), Keep a Claude account's 5-hour usage window continuously warm. ``horus warmup``…, Seconds to sleep before the next warmup of ``account``. Primary: ``warmed_at +…, Warm ``account`` now, then re-warm just after each 5h reset, indefinitely.…, The standing keep-warm loop (`horus warmup --keep`). Cadence logic and the loop… (+5 more)

### Community 193 - "Path"
Cohesion: 0.22
Nodes (15): _is_open_state(), Permissive by default (``True``) — only a positively-reported non-"open" PR…, Resolve ``<sha|pr>`` to the exact commit + owning repo (+ PR number/base when…, resolve_target(), Path, test_resolve_target_looks_up_owning_pr_for_a_sha(), test_resolve_target_pr_number_defaults_open_when_state_missing(), test_resolve_target_pr_number_marks_merged_pr_as_not_open() (+7 more)

### Community 194 - "sentinel_fired"
Cohesion: 0.20
Nodes (15): band_sentinel_fired(), closure_already_fired(), mark_band_sentinel(), mark_closure_fired(), mark_sentinel_fired(), True if the ``kind`` sentinel fired for this session within the re-arm window.…, True if closure fired for this session within the re-arm window., True when ``kind`` already fired for this session at ``band`` or higher in the… (+7 more)

### Community 195 - "Roadmap branches: deepen-own-use re-baseline — 2026-07-17 (convergence-test run)"
Cohesion: 0.13
Nodes (14): 1. Where we are, 2. Where the market is, 3. The tree, 4. The branches, 5. Speculative branches, 6. Recommendation, held loosely, Branch A — Agent-neutrality deepening (primary), Branch B — PO-loop proof-of-value (secondary) (+6 more)

### Community 196 - "Product audit — horus-harness, 2026-07-31"
Cohesion: 0.14
Nodes (13): 1. What this document is, 2. The product, in plain terms, 3. The Vision's units, 4. Vision branches, 5. Per-unit detail, 6. Triage, 7. Ceremony observations, 8. Routed suggestions (+5 more)

### Community 197 - "codex-usage-stale-snapshot gates dispatch — wrong, and two readers disagree"
Cohesion: 0.14
Nodes (12): 2026-07-27 — Rafael Figueiredo (agent), Acceptance, Boundaries / relation, codex-usage-stale-snapshot gates dispatch — wrong, and two readers disagree, Evidence (same account, same reset window), Reviews, Suspected cause, Why it matters (+4 more)

### Community 198 - "Preserved design proposal (not approved for implementation)"
Cohesion: 0.14
Nodes (13): Data contract: ownership and outcome are separate axes, Deterministic and live gates, Finding: a PID walk after failure is too late, One process-scope primitive, Owner approval gate, Platform boundary, Preserved design proposal (not approved for implementation), Reap eligibility truth table (+5 more)

### Community 199 - "openwiki-graphify-value-benchmark — test generated context against the repo-native baseline"
Cohesion: 0.14
Nodes (13): Convergence / drop criterion, Human-usefulness test (question 2), Intended outcome, Maintenance-cost evidence to record, Open decisions, openwiki-graphify-value-benchmark — test generated context against the repo-native baseline, Resolved — run design (2026-08-08), Resolved — the three pilot tasks (owner, 2026-08-08) (+5 more)

### Community 200 - "validate"
Cohesion: 0.21
Nodes (11): Envelope, date, A violated bound. ``bound`` is the machine-readable name; ``message`` names it…, The wall. ``None`` authorizes the dispatch; a ``Refusal`` names the exact…, One owner-created standing authorization. Bounds only — never a selector., Expiry is inclusive: an envelope is live through the end of its ``expires`` day., Whether ``card`` is inside the whitelist, directly or via its vision branch., Refusal (+3 more)

### Community 201 - "UntrackedRepo"
Cohesion: 0.14
Nodes (13): A GitHub repo with neither `.horus/PRD.md` nor `.horus/project.md`., _untracked_to_cache(), UntrackedRepo, When prior_untracked has a matching pushed_at, no gh api .horus/ call is made., Changed pushedAt on a previously-untracked repo triggers full fetch. If…, save_cache + load_cache persists untracked repos; local_path is recomputed on…, A repo cloned at workspace_root/<name> but never registered still shows as…, A same-named workspace directory whose remote points elsewhere must NOT match. (+5 more)

### Community 203 - "Branches"
Cohesion: 0.14
Nodes (13): A — One state, any agent (primary), B — The loop earns its keep (secondary), Branches, C — Dispatch you can trust (rescoped after owner push-back), D — Cockpit polish (filler, no thesis), Pathfinder branch tree — horus-harness, 2026-07-17 (second dogfood), Recommendation (held loosely), Skill-calibration findings from this run (drove the v2 factoring) (+5 more)

### Community 204 - "Roadmap branches (v5 re-run): host-native cockpit — 2026-07-31"
Cohesion: 0.14
Nodes (13): 1. Where we are, 2. Where the market is, 3. The tree, 4. The branches, 5. Speculative branches, 6. Backlog disposition — done AFTER the branches, per v5, 7. Recommendation, held loosely, H — Adopt herdr as a state source, not just a pane host *(primary)* (+5 more)

### Community 205 - "Omnigent fit as Horus LaunchBackend (2026-07-10)"
Cohesion: 0.14
Nodes (13): Adopt: ContainerBackend only for named Omnigent providers, Adopt: optional Omnigent backend for POSIX remote hosts, Adoption gates and risks, Build vs adopt, Cross-cutting requirement matrix, Decision, Do not adopt for native Windows; do not build a full Horus replacement, Fit to the LaunchBackend seam (+5 more)

### Community 206 - "Horus"
Cohesion: 0.15
Nodes (11): Project machine requirements, Adding Horus to a project, Commands, GitHub remote catalog, Horus, Install, Keeping projected artifacts current, License (+3 more)

### Community 207 - "backend.py"
Cohesion: 0.21
Nodes (10): BackendError, LaunchFailed, Exception, The frozen LaunchBackend seam — one interface for launching a session, wherever…, Base for LaunchBackend failures., The backend cannot serve the brief's ``target`` (raised instead of falling…, The backend has no honest implementation of this operation for this handle., The launch was attempted but did not start a session. (+2 more)

### Community 208 - "gpt-models-in-claude-code-harness — run GPT (via the Codex sub) inside Claude Code (spike)"
Cohesion: 0.15
Nodes (11): Acceptance (spike), gpt-models-in-claude-code-harness — run GPT (via the Codex sub) inside Claude Code (spike), Non-goals, Reviews, Spike questions (answer before building), The mechanism (from the scan — verify live, do not trust the summary), Acceptance, Bugs to fix before shipping (safety in code, per repo rule) (+3 more)

### Community 209 - "refine-autonomy-hardening-lens — force "contingent vs intrinsic" on every attended card"
Cohesion: 0.15
Nodes (12): Acceptance, Axis 1 — the `attended` axis (original scope), Axis 2 — the `shaping` axis (owner, 2026-07-28), Guardrails, Open decisions, refine-autonomy-hardening-lens — force "contingent vs intrinsic" on every attended card, Reviews, Source (+4 more)

### Community 210 - "session-host-protocol — one pluggable session host (tmux · current · herdr)"
Cohesion: 0.15
Nodes (12): Acceptance, Capabilities a host declares, Guardrails, Open decisions, Reviews, Selection, session-host-protocol — one pluggable session host (tmux · current · herdr), Source (+4 more)

### Community 211 - "wildcard — an autonomous divergence skill that emits ONE reviewable card"
Cohesion: 0.15
Nodes (12): Field evidence — recency anchoring beats the frame rules (2026-07-31), Grounding — the pathfinder run (owner-decided, 2026-07-21), Non-goals, Open questions, Prerequisite — structured pathfinder run outcome (`pathfinder-structured-outcome`), Prior art / to explore, Quality bar (open), Reviews (+4 more)

### Community 212 - "CliCommand"
Cohesion: 0.18
Nodes (13): cli_surface_for(), CliCommand, _horus_own_cli_surface(), _mention_pattern(), ArgumentParser, Recursively walk an argparse parser's subcommand tree. Uses argparse's internal…, Whole-token match for a command phrase: forbids an adjacent word/hyphen char so…, One node in an extracted CLI subcommand tree. (+5 more)

### Community 213 - "cmd_run"
Cohesion: 0.18
Nodes (13): cmd_open(), cmd_run(), _codex_delivery_posture_error(), Spawn (or resume) an agent session through an adapter, tracked in the registry.…, Arm-time mirror of the codex delivery-posture guard for `horus schedule run`.…, Open a tracked attended agent in a window, this TTY, or a persistent host., Error string if a codex dispatch demands a git/PR delivery it structurally…, _resolve_run_posture() (+5 more)

### Community 214 - "canonical_model_name"
Cohesion: 0.15
Nodes (13): canonical_model_name(), normalize_tier(), Normalize a captured model to its canonical versioned name. Prefers…, Map a card/envelope ``tier:`` value to its vendor-neutral tier. A neutral value…, Resolve a card's `tier:` to one of `models`, via the SAME tier->model…, _resolve_recommended_model(), The alias map is derived from the rendered equivalence table — every model…, test_canonical_model_name_falls_back_to_alias_map() (+5 more)

### Community 215 - "capture_usage_snapshot"
Cohesion: 0.22
Nodes (13): capture_usage_snapshot(), Best-effort snapshot of every readable usage surface (claude, codex). One entry…, _codex_report(), A REAL ``codex_usage.UsageReport``, not a hand-rolled stub. The previous…, test_capture_usage_snapshot_claude_fresh_at_read_time(), test_capture_usage_snapshot_codex_fresh_when_recent_and_unexpired(), test_capture_usage_snapshot_codex_stale_when_cache_predates_run(), test_capture_usage_snapshot_codex_stale_when_reset_past() (+5 more)

### Community 216 - "pr_only_contexts"
Cohesion: 0.19
Nodes (13): pr_only_contexts(), Context-base names that ONLY ever trigger on a ``pull_request`` event, read…, _git_workflow_responder(), Handlers for ``git ls-tree``/``git show`` simulating the workflow files as they…, A confidently PR-only workflow (``continuity.yml``) must NOT drop its context…, Same all-or-nothing guarantee when a workflow is readable but its…, test_pr_only_contexts_across_workflows_matches_the_repo_scenario(), test_pr_only_contexts_all_or_nothing_when_one_of_several_workflows_is_unparseable() (+5 more)

### Community 217 - "_board_ui"
Cohesion: 0.15
Nodes (13): _board_ui(), _mouse_event(), MouseEvent, A UI parked on the backlog of a project with a priority + readiness spread,…, test_board_2d_navigation_moves_across_and_within_columns(), test_board_falls_back_to_list_when_narrow(), test_board_renders_priority_columns_and_detail_pane_when_wide(), test_clicking_a_card_in_the_wide_board_opens_that_card() (+5 more)

### Community 218 - "The contract — seven gates, each owner-confirmed"
Cohesion: 0.17
Nodes (11): 1. Discover, 2. Pick, 3. Ready-gate (is the card dispatch-ready?), 4. Decide, 5. Authorize the standing envelope (the hard gate), 6. Dispatch or schedule, 7. Pair a supervisor, Boundaries (+3 more)

### Community 219 - "wildcard — autonomous divergence → ranked, buildable vision-advancing moves"
Cohesion: 0.17
Nodes (11): Grounding — where ideas come from (NEVER the backlog), Non-goals, Output, Procedure, Purpose — move the vision FORWARD, Quality bar, References, The self-sufficiency bar — the primary gate (+3 more)

### Community 220 - "The contract — seven gates, each owner-confirmed"
Cohesion: 0.17
Nodes (11): 1. Discover, 2. Pick, 3. Ready-gate (is the card dispatch-ready?), 4. Decide, 5. Authorize the standing envelope (the hard gate), 6. Dispatch or schedule, 7. Pair a supervisor, Boundaries (+3 more)

### Community 221 - "wildcard — autonomous divergence → ranked, buildable vision-advancing moves"
Cohesion: 0.17
Nodes (11): Grounding — where ideas come from (NEVER the backlog), Non-goals, Output, Procedure, Purpose — move the vision FORWARD, Quality bar, References, The self-sufficiency bar — the primary gate (+3 more)

### Community 222 - "DashboardAccess"
Cohesion: 0.36
Nodes (5): authorized(), The composed exposed-mode gate: owner header AND a valid Access JWT. Owner…, DashboardAccess, The dashboard's exposed-mode gate config: owner identity + Access params., AuthorizedTests

### Community 223 - "account-login-verb — provision + log into an account that has no prior login"
Cohesion: 0.17
Nodes (11): 2026-08-02 — Rafael Figueiredo (manual), Acceptance, account-login-verb — provision + log into an account that has no prior login, Adjacent fixes (cheap, same area, prevent the recurrence), Bug to fix in the same change, Notes from the live run (2026-07-20), Related, Reviews (+3 more)

### Community 224 - "usage-snapshot-test-flake-blocks-workers — a green-on-CI test fails locally and kills dispatched deliveries"
Cohesion: 0.17
Nodes (11): Acceptance, Deliberately not doing, Hardening shipped with this card, How — get a repro first, Mechanism — IDENTIFIED and reproduced, 2026-07-26 (this section preserved as filed; see Reviews for the correction), Related, Reviews, Source (+3 more)

### Community 225 - "new-machine-setup-guidance — how a fresh machine gets set up correctly"
Cohesion: 0.17
Nodes (11): Broad boundaries, Intended outcome, new-machine-setup-guidance — how a fresh machine gets set up correctly, Open decisions for backlog-refine, Open question that decides whether the skill is reachable at all — UNTESTED, Ordering requirements found by running it (2026-07-20), Raw material — migration findings (2026-07-20, retiring the Desktop checkouts), Raw material — the verified Windows sequence (2026-07-20) (+3 more)

### Community 226 - "_apply_unattended_defaults"
Cohesion: 0.24
Nodes (12): _apply_unattended_defaults(), Give `--unattended` the safe dispatch posture, then return ``None`` to proceed…, _posture_args(), Namespace, The whole point: a scheduled worker must be reachable and must not touch the…, Unattended dispatch IS worker dispatch: headless, detached, unsupervised., test_attended_run_keeps_an_explicit_target(), test_attended_run_posture_is_untouched() (+4 more)

### Community 227 - "Claudex first-session findings — 2026-07-18"
Cohesion: 0.17
Nodes (11): 1. The minimal same-model recipe is genuinely small, 2. Harness profile is not provider credential, 3. Named routing is available upstream, 4. Codex usage has a reliable native status surface, 5. GPT context telemetry is not trustworthy yet, Claudex first-session findings — 2026-07-18, Durable follow-ups, Findings (+3 more)

### Community 228 - "_load_cache"
Cohesion: 0.18
Nodes (11): _Cached, _load_cache(), NamedTuple, A fresh cache entry. ``snapshot`` is ``None`` for a cached negative result…, Return a cache entry, or ``None`` for a miss/stale/corrupt file. ``ttl=None``…, Whatever is cached for ``agent``+``account`` — at any age — with the source and…, read_cache_entry(), Forward/backward-readable, like the session registry. (+3 more)

### Community 229 - "_claude_hook_run"
Cohesion: 0.17
Nodes (12): _claude_hook_run(), Drive `usage check --target claude --hook` with a mocked usage snapshot + stdin., Regression: the soft UserPromptSubmit advisory must not consume the Stop hook's…, Within one usage window the Stop prompt escalates by band, not by timer: quiet…, test_claude_advisory_does_not_suppress_stop_block(), test_claude_bands_rearm_on_window_reset(), test_claude_hook_fires_once_per_session(), test_claude_hook_injects_closure_over_threshold() (+4 more)

### Community 230 - "_mk_fresh"
Cohesion: 0.17
Nodes (12): The 2026-08-03 fabric-build finding: a green close on a pushed-but-unmerged…, A merely-open sibling PR (item 5's parallel-delivery signal) must not flip…, A genuine freshness failure alongside a parallel signal must still flip to…, test_close_check_gates_on_freshness(), test_close_check_keeps_unclassified_cards_advisory(), test_close_check_names_sibling_pr_but_stays_fresh(), test_close_check_stays_stale_with_parallel_signal_and_real_freshness_failure(), test_close_check_still_fails_for_delivery_not_covered_by_continuity() (+4 more)

### Community 231 - "Delegation rubric — shared calibration + verification logic"
Cohesion: 0.18
Nodes (10): Delegation rubric — shared calibration + verification logic, Hard boundary (do not cross), Precondition — prove delegation has a dividend, Step 1 — Read the calibration data, Step 2 — Read the task shape (four axes), Step 3 — Tier-trust ladder (data, not hardcode), Step 4 — Shape → mode + tier, Step 5 — Verification depth, dialed by the SAME tier-trust (+2 more)

### Community 232 - "Horus execution supervision"
Cohesion: 0.18
Nodes (10): Boundaries, Confirm delegation already earned its cost, Horus execution supervision, Invocation boundary, Native mapping, Obtain exact-envelope approval before every worker launch, Orchestrating parallel supervisors (orchestrator > supervisor > worker), Steps (+2 more)

### Community 233 - "Process retrospective — bounded, evidence-first"
Cohesion: 0.18
Nodes (10): Attribute cost honestly — six buckets, Check existing coverage before proposing anything, Land the outcome — no new artifacts, Lazy-load only the relevant evidence, Process retrospective — bounded, evidence-first, Recommend the cheapest rung, capped at three, Review this skill itself, Scope the incident before reading anything (+2 more)

### Community 234 - "Delegation rubric — shared calibration + verification logic"
Cohesion: 0.18
Nodes (10): Delegation rubric — shared calibration + verification logic, Hard boundary (do not cross), Precondition — prove delegation has a dividend, Step 1 — Read the calibration data, Step 2 — Read the task shape (four axes), Step 3 — Tier-trust ladder (data, not hardcode), Step 4 — Shape → mode + tier, Step 5 — Verification depth, dialed by the SAME tier-trust (+2 more)

### Community 235 - "Horus execution supervision"
Cohesion: 0.18
Nodes (10): Boundaries, Confirm delegation already earned its cost, Horus execution supervision, Invocation boundary, Native mapping, Obtain exact-envelope approval before every worker launch, Orchestrating parallel supervisors (orchestrator > supervisor > worker), Steps (+2 more)

### Community 236 - "Process retrospective — bounded, evidence-first"
Cohesion: 0.18
Nodes (10): Attribute cost honestly — six buckets, Check existing coverage before proposing anything, Land the outcome — no new artifacts, Lazy-load only the relevant evidence, Process retrospective — bounded, evidence-first, Recommend the cheapest rung, capped at three, Review this skill itself, Scope the incident before reading anything (+2 more)

### Community 237 - "Decisions — current rules"
Cohesion: 0.18
Nodes (10): Accounts & auth, Continuity model (.horus/ lanes), Dashboard & companion, Decisions — current rules, Distribution & licensing, Execution & delegation, Platform support, Product boundary & scope (+2 more)

### Community 238 - "project-registration-onboarding-gap — cloned Horus project stays invisible and mobile hides registration"
Cohesion: 0.18
Nodes (10): Acceptance, Cost attribution, Exact defects, Non-goals, project-registration-onboarding-gap — cloned Horus project stays invisible and mobile hides registration, Proposed controls — cheapest first, Reviews, Source (+2 more)

### Community 239 - "vision-omits-intent-and-audiences — the Vision contract captures the destination, never the intent"
Cohesion: 0.18
Nodes (10): Acceptance, Deliberately not doing, Related, Scope — two elements added to the Vision contract, in all four places, Source, The defect in Horus, vision-omits-intent-and-audiences — the Vision contract captures the destination, never the intent, Why — live field failure, 2026-07-25, `fabric-build` (+2 more)

### Community 240 - "codex-isolated-config-leak — an isolated Codex account still points at the ambient home"
Cohesion: 0.18
Nodes (10): 2026-08-02 — Rafael Figueiredo (manual), 2026-08-02 — Rafael Figueiredo (manual), Acceptance (draft), codex-isolated-config-leak — an isolated Codex account still points at the ambient home, Open item on this machine, Related, Remedy — **3 chosen by the owner, 2026-07-26**, Reviews (+2 more)

### Community 241 - "fresh-vs-resume-context-split — the resume directive should reach resume sessions only"
Cohesion: 0.18
Nodes (10): 2026-08-02 — Rafael Figueiredo (manual), Acceptance (draft — refine before actioning), Adjacent: the directive is a proposal, not an instruction, Deliberately not actioned yet — observe first (owner, 2026-07-19), Design question (open — decide in-card), fresh-vs-resume-context-split — the resume directive should reach resume sessions only, Non-goals, Notes (+2 more)

### Community 242 - "vision-branch-x6 — workflow selection compatibility"
Cohesion: 0.18
Nodes (10): 1. Cross-harness utility platform, 2. Opinionated product-development workflow, Compatibility hypothesis, Convergence criterion, Exists vs gaps (shaped 2026-07-20), Non-goals for this raw branch, Proposed children, in order, Reviews (+2 more)

### Community 243 - "tmux_runner.py"
Cohesion: 0.35
Nodes (10): Open a watcher terminal running ``horus tail <session_id>`` (--watch). Best-…, _spawn_watcher(), _handoff(), main(), Path, Private child entry point for a Horus-managed tmux pane., Record the durable pane-runner PID before starting any agent process., _run_interactive() (+2 more)

### Community 244 - "conftest.py"
Cohesion: 0.24
Nodes (10): isolate_ambient_agent_env(), isolate_home(), isolate_session_host_sockets(), fixture, Suite-wide isolation from the ambient agent environment. Tests fake ``HOME``…, Point every terminal host's DEFAULT server at a throwaway socket. This is the…, Unset the per-account agent config-dir vars for every test. Hardening, not a…, Give every test a private ``HOME``, so none can reach the real ``~/.horus``.… (+2 more)

### Community 245 - "_clone_with_origin"
Cohesion: 0.18
Nodes (11): _clone_with_origin(), One clone of a bare origin, with origin/HEAD set so default_branch resolves., The failure this closes: a hand-rolled `git add -A && git push` on the default…, Only the default branch is exempt-by-convention, so only it needs the guard; a…, In a repo that GENERATES the projections, they must travel with their source…, A consumer project has no in-repo generator, so its projections are ordinary…, test_a_feature_branch_is_never_guarded(), test_continuity_only_push_to_default_branch_is_allowed() (+3 more)

### Community 246 - "_run_deploy"
Cohesion: 0.40
Nodes (10): CompletedProcess, Path, Tests for the hosted deployment's install and runtime version gates., _run_deploy(), test_deploy_accepts_exact_running_target(), test_deploy_refuses_restart_when_pinned_install_never_succeeds(), test_deploy_rejects_running_version_mismatch(), test_deploy_requires_install_success_when_target_is_unresolved() (+2 more)

### Community 247 - "Publish an OpenWiki visualizer without rebuilding the deployment each time"
Cohesion: 0.20
Nodes (9): 1. Pin the publication record, 2. Preflight the content and host, 3. Install the durable origin, 4. Add the private public route, 5. Reproduce the publication gate, Contract, Publish an OpenWiki visualizer without rebuilding the deployment each time, Rollback and removal (+1 more)

### Community 248 - "Publish an OpenWiki visualizer without rebuilding the deployment each time"
Cohesion: 0.20
Nodes (9): 1. Pin the publication record, 2. Preflight the content and host, 3. Install the durable origin, 4. Add the private public route, 5. Reproduce the publication gate, Contract, Publish an OpenWiki visualizer without rebuilding the deployment each time, Rollback and removal (+1 more)

### Community 249 - "session-remote-control-default — launch Horus sessions with remote control enabled by default"
Cohesion: 0.20
Nodes (9): Acceptance, Broad boundaries, First step / open decision (verify before building), Intended outcome, Non-goals, Reviews, session-remote-control-default — launch Horus sessions with remote control enabled by default, Source (+1 more)

### Community 250 - "tui-remote-freshness-indicator — see at TUI launch whether continuity is current"
Cohesion: 0.20
Nodes (9): Acceptance (EARS-lite), Broad boundaries, Decisions — RESOLVED in refine (2026-07-29), Intended outcome, Reviews, Source, tui-remote-freshness-indicator — see at TUI launch whether continuity is current, What already exists — do NOT rebuild this (+1 more)

### Community 251 - "autonomous-advisory-dispatch-posture — schedule zero-blast skills without a fake delivery card"
Cohesion: 0.20
Nodes (9): 2026-08-02 — Rafael Figueiredo (manual), Acceptance direction, autonomous-advisory-dispatch-posture — schedule zero-blast skills without a fake delivery card, Non-goals, Open questions, Reviews, Rough shape, Source (+1 more)

### Community 252 - "Deferred supervision and completion receipt"
Cohesion: 0.20
Nodes (8): Acceptance, Boundaries, Deferred supervision and completion receipt, Reviews, Acceptance, Boundaries, Reviews, Worker progress heartbeat / stall detection

### Community 253 - "vision-branch-x4-model-harness-plane.md"
Cohesion: 0.29
Nodes (5): Acceptance, Design, Non-goals, Why, x4-claudex-subagent-context-policy — same-model or tiered GPT subagents, honest context

### Community 254 - "windows-native-horus-setup — the best way to run horus on Windows, given the TUI's recent growth"
Cohesion: 0.20
Nodes (9): 2026-08-01 — owner + agent (manual), Broad boundaries, Findings — Windows machine setup run, 2026-07-20 (owner-attended), Intended outcome, Open decisions for backlog-refine, Reviews, Source, Why (+1 more)

### Community 255 - "Delegation cost finding — dispatch did not save cost; it raised it"
Cohesion: 0.20
Nodes (9): Caveats on the measurement (honest limits), Delegation cost finding — dispatch did not save cost; it raised it, Forward ideas this raised (see backlog), One-line conclusion, The personal-account 5h window across the four dispatches, This batch was the worst case for delegation, What we measured, When delegation IS worth the markup (narrow) (+1 more)

### Community 256 - "Market scan: repo-local product-owner re-baseline — 2026-07-17"
Cohesion: 0.20
Nodes (9): Candidate backlog items, Competitive teardown, Market scan: repo-local product-owner re-baseline — 2026-07-17, Market-size sanity, Open questions / hard FAQ, Prior-art verdict: **YELLOW**, Problem / JTBD (hypothesis), Sources (+1 more)

### Community 257 - "Multi-model / multi-harness — landscape scan (X4 candidate)"
Cohesion: 0.20
Nodes (9): Build vs. buy verdict, Design principles (owner, 2026-07-18) — bind every card, Headline finding (partly overturns the premise), LiteLLM vs CLIProxyAPI — the axis that decides it (auth model), Multi-model / multi-harness — landscape scan (X4 candidate), Proposed X4 thesis (worth a branch — as `explore`), Sources, Staged plan (candidate children) (+1 more)

### Community 258 - "X6 boundary inventory — substrate vs continuity contract vs workflow policy"
Cohesion: 0.20
Nodes (9): 1. Session/account/scheduler substrate — workflow-agnostic today, 2. Continuity contract — the small machine-read surface (the hinge), 3. Workflow policy — model-read prose + the ritual skills, Feeds, Field datum: fabric-metadata-driven-medallion, Finding: three layers, not two, Implications adopted by the owner, The two-loops framing (+1 more)

### Community 259 - "Market scan: repo-local agent continuity — 2026-07-31"
Cohesion: 0.20
Nodes (9): Candidate backlog items, Competitive teardown, Market scan: repo-local agent continuity — 2026-07-31, Market-size sanity, Open questions / hard FAQ, Problem / JTBD (hypothesis — not validated by interviews), Sources, Verdict — build vs adopt, per capability (+1 more)

### Community 260 - "_Stdin"
Cohesion: 0.22
Nodes (7): _Args, `_read_hook_stdin` checks isatty() first — a fake without it is not the object…, The no-transcripts rule: a name, a project and a day — never arguments., `|| exit 0` guards the shell side; this guards the Python side. Doubled on…, _Stdin, test_skill_usage_hook_exits_zero_on_garbage(), test_skill_usage_hook_records_name_only()

### Community 261 - "backlog-refine — picture first, decisions second, Ready last"
Cohesion: 0.22
Nodes (8): 0. Reconcile against live delivery state before the picture, 1. Present the backlog picture before any questions, 2. The pass — a per-card questionnaire, one card per screen, 3. Readiness and autonomy contract, 4. Apply approved state, backlog-refine — picture first, decisions second, Ready last, Hard boundary, The execution-ready card contract (single authority)

### Community 262 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 263 - "Market scan — look outward, propose, never auto-apply"
Cohesion: 0.22
Nodes (8): Bake in exactly the outward trio (+ one capped check), Composable (standalone or as a pathfinder step), Deliberately omit, Depth: shallow by default, deeper only when the owner asks, Frame it to the intent — build-vs-adopt OR market-gap (ask, don't assume), Hand off — propose, the owner disposes, Market scan — look outward, propose, never auto-apply, Write the receipt (dated, committed, mirrors `.horus/audits/`)

### Community 264 - "roadmap-branches — the divergence tree, not a merged roadmap"
Cohesion: 0.22
Nodes (8): Deliberately omit, Hand off, Inputs (gather, do not re-derive), Onboarding fork, roadmap-branches — the divergence tree, not a merged roadmap, The deliverable — one dated receipt, fixed template, Three disciplines that make the tree trustworthy, Where BRANCHES come from — never the backlog

### Community 265 - "Skill audit — one skill's text vs reality"
Cohesion: 0.22
Nodes (8): Boundaries, Close the audit, Questions (evidence, not recall), Scope: one skill per audit, Skill audit — one skill's text vs reality, Two invariants an audit must check first, Verdicts — five, because amendment is the point, When this fires

### Community 266 - "backlog-refine — picture first, decisions second, Ready last"
Cohesion: 0.22
Nodes (8): 0. Reconcile against live delivery state before the picture, 1. Present the backlog picture before any questions, 2. The pass — a per-card questionnaire, one card per screen, 3. Readiness and autonomy contract, 4. Apply approved state, backlog-refine — picture first, decisions second, Ready last, Hard boundary, The execution-ready card contract (single authority)

### Community 267 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 268 - "Market scan — look outward, propose, never auto-apply"
Cohesion: 0.22
Nodes (8): Bake in exactly the outward trio (+ one capped check), Composable (standalone or as a pathfinder step), Deliberately omit, Depth: shallow by default, deeper only when the owner asks, Frame it to the intent — build-vs-adopt OR market-gap (ask, don't assume), Hand off — propose, the owner disposes, Market scan — look outward, propose, never auto-apply, Write the receipt (dated, committed, mirrors `.horus/audits/`)

### Community 269 - "roadmap-branches — the divergence tree, not a merged roadmap"
Cohesion: 0.22
Nodes (8): Deliberately omit, Hand off, Inputs (gather, do not re-derive), Onboarding fork, roadmap-branches — the divergence tree, not a merged roadmap, The deliverable — one dated receipt, fixed template, Three disciplines that make the tree trustworthy, Where BRANCHES come from — never the backlog

### Community 270 - "Skill audit — one skill's text vs reality"
Cohesion: 0.22
Nodes (8): Boundaries, Close the audit, Questions (evidence, not recall), Scope: one skill per audit, Skill audit — one skill's text vs reality, Two invariants an audit must check first, Verdicts — five, because amendment is the point, When this fires

### Community 271 - ".recover_interactive_thread_id"
Cohesion: 0.28
Nodes (7): _parse_iso(), datetime, Path, The thread id Codex minted for an interactive session, read back afterwards.…, The ``session_meta`` payload from a rollout file's first line, or ``None``.…, Parse a rollout timestamp into an aware UTC datetime, or ``None``. Rollout…, _rollout_meta()

### Community 272 - "get_adapter"
Cohesion: 0.22
Nodes (9): account_dirs(), get_adapter(), The adapter's alias -> isolated-config-dir map, whatever it calls it. Claude…, Return an adapter instance by name. Raises ``KeyError`` if unknown. ``fake`` is…, test_get_adapter_resolves_fake_and_rejects_unknown(), test_get_adapter_resolves_claude(), test_account_dirs_resolves_codex_homes_not_just_claude_config_dirs(), test_get_adapter_resolves_codex() (+1 more)

### Community 273 - "backlog-librarian — autonomous, zero-blast-radius backlog-hygiene digest"
Cohesion: 0.22
Nodes (8): backlog-librarian — autonomous, zero-blast-radius backlog-hygiene digest, Distinct from (not a duplicate), Non-goals, Open questions, Source, What, Why it's safe to autonomize, Why — wildcard-proposed, owner-approved 2026-07-21

### Community 274 - "bundle-test-phase-skills — a skill in test phase lives outside the generator, unprotected"
Cohesion: 0.22
Nodes (8): Acceptance, bundle-test-phase-skills — a skill in test phase lives outside the generator, unprotected, How, Non-goals, Open decisions, Source, The reusable path (documentation, not machinery), Why — measured 2026-07-28

### Community 275 - "codex-identity-guard — Codex launches skip the account identity check entirely"
Cohesion: 0.22
Nodes (8): Acceptance, codex-identity-guard — Codex launches skip the account identity check entirely, Notes, Reviews, Source, Two independent defects, What to build, Why — demonstrated, 2026-07-20

### Community 276 - "Datum supervisor-cost envelope + one-act acceptance [frozen schema — implement as specified]"
Cohesion: 0.22
Nodes (8): 1. Mechanical usage snapshots (launch + close), 2026-07-14 — cockpit-overseer (agent), 2. Agent-supplied cost half — new optional `horus datum close` flags, 3. One-act acceptance (collapse the post-merge tail), 4. Projection + rubric, Acceptance, Datum supervisor-cost envelope + one-act acceptance [frozen schema — implement as specified], Reviews

### Community 277 - "herdr-host-probe — answer three questions before designing the host protocol"
Cohesion: 0.22
Nodes (8): Acceptance, herdr-host-probe — answer three questions before designing the host protocol, Open decisions, Reviews, Source, The three questions, What herdr appears to offer (docs, 2026-07-29 — unverified), Why — owner, 2026-07-29

### Community 278 - "process-fixes-live-in-process-not-memory — shared artifacts, not one agent's recall"
Cohesion: 0.22
Nodes (8): Acceptance, Intended outcome, Non-goals, process-fixes-live-in-process-not-memory — shared artifacts, not one agent's recall, Reviews, Source, Sweep result — 2026-07-26 (verified, not assumed), Why

### Community 279 - "remote-control-flag-swallows-launch-prompt — `--remote-control` eats the seeded prompt, so no interactive launch is seeded and Remote Control does not come up"
Cohesion: 0.22
Nodes (8): Acceptance, Blast radius, Fix — both candidates verified live, Proof — one-line probe against the live binary, Related, remote-control-flag-swallows-launch-prompt — `--remote-control` eats the seeded prompt, so no interactive launch is seeded and Remote Control does not come up, Source, Why — root-caused live, 2026-07-25

### Community 280 - "session-close-ux-and-truthful-end-state — a closed session must not read as a failed one"
Cohesion: 0.22
Nodes (8): 2026-08-03 — Rafael Figueiredo (agent), Broad boundaries, Intended outcome, Open decisions, Reviews, session-close-ux-and-truthful-end-state — a closed session must not read as a failed one, The real scope: four close paths, four fidelities, Why — audit evidence, 2026-07-31

### Community 281 - "tui-nested-tmux-navigation — make `horus tui` usable *inside* tmux (switch-client, not refuse)"
Cohesion: 0.22
Nodes (8): Acceptance, Guardrails, Known rework cost, Source, The key insight — no nesting is actually required, tui-nested-tmux-navigation — make `horus tui` usable *inside* tmux (switch-client, not refuse), What to build, Why — observed live, 2026-07-29

### Community 282 - "continuity-sync-friction — reduce cross-session/cross-machine friction in git-synced continuity"
Cohesion: 0.22
Nodes (8): Candidate directions (sketches, NOT decisions), continuity-sync-friction — reduce cross-session/cross-machine friction in git-synced continuity, Intended outcome (open — explore before committing), Open decisions, Open questions / to explore, Reviews, Source, Why — observed live, 2026-07-21

### Community 283 - "horus-phone-chat-poc — one-shot spike: text chat frontend to an agent session with phone-side tool approval"
Cohesion: 0.22
Nodes (8): Broad boundaries (scope to the RISK, not to "a chat UI"), horus-phone-chat-poc — one-shot spike: text chat frontend to an agent session with phone-side tool approval, Intended outcome (owner intent: a rough thing to actually TRY), North star — the ideal this is a first step toward (NOT the PoC's scope), Open decisions for backlog-refine, Pass / fail, Source, Why

### Community 284 - "merge-release-owner-gate — put the wall where the model's speed actually costs"
Cohesion: 0.22
Nodes (8): Acceptance, Candidate answers recorded 2026-07-28 (NOT adopted — for the design session), merge-release-owner-gate — put the wall where the model's speed actually costs, Open design questions (why this is Shaping, not Ready), Reviews, Source, What this is not, Why

### Community 285 - "session-agent-state-awareness — surface working / idle / blocked for running sessions"
Cohesion: 0.22
Nodes (8): Acceptance (draft — sharpen when the mechanism is chosen), Open decisions, Reviews, session-agent-state-awareness — surface working / idle / blocked for running sessions, Source, What the probe changed (2026-07-29 — evidence in `herdr-host-probe`), What to build (shape, not yet settled), Why — owner, 2026-07-29

### Community 286 - "vision-branch-x4 — model × harness × credential execution-route plane"
Cohesion: 0.22
Nodes (9): Branch acceptance, Convergence criterion, Evidence, First sustained live use — owner verdict (2026-07-18), Principles, Reviews, vision-branch-x4 — model × harness × credential execution-route plane, What is commoditized vs. the edge (+1 more)

### Community 287 - "harvest_target"
Cohesion: 0.31
Nodes (9): harvest_target(), _note_status(), The recovery note the checkpoint harvest may append to, and why not when None.…, _note(), test_harvest_accepts_a_note_with_no_status(), test_harvest_accepts_an_open_note(), test_harvest_refuses_a_note_that_declares_itself_finished(), test_harvest_refuses_every_terminal_status_spelling() (+1 more)

### Community 288 - "_launch_notice"
Cohesion: 0.22
Nodes (9): _launch_notice(), _notice(), Banner shown after a launch POST redirects back to /control., Unified post-redirect banner: project actions (upgrade/offboard) +…, test_account_remove_notice(), test_brainstorm_notice_banner(), test_launch_notice_banner(), test_login_notice_messages() (+1 more)

### Community 289 - "Agent host-freeze incident — 2026-07-18"
Cohesion: 0.22
Nodes (8): Agent host-freeze incident — 2026-07-18, Durable follow-up, Horus/proxy non-causality evidence, Pressure and recovery evidence, Summary, Timeline (local time), Trigger mechanics, What the incident proved

### Community 290 - "Market scan: repo-local product-owner layer for coding agents — 2026-07-20"
Cohesion: 0.22
Nodes (8): Calibration feedback to encode in the market-scan skill text, Candidate backlog items (owner disposes; none created here), Competitive teardown (three lanes), Market scan: repo-local product-owner layer for coding agents — 2026-07-20, Sources (every page opened), Verdict — build / adopt / compose per capability (deepen-own-use frame), Verdict — market-gap per lane (broaden-adoption frame), Vision draft (PR-FAQ, one paragraph)

### Community 291 - "repro.mjs"
Cohesion: 0.31
Nodes (5): CDP, check(), failures, main(), wsConnect()

### Community 292 - "_merge_hook_run"
Cohesion: 0.22
Nodes (9): _merge_hook_run(), test_merge_hook_allows_merge_when_fresh(), test_merge_hook_blocks_merge_when_lanes_stale(), test_merge_hook_gates_actual_merge_after_shell_operator(), test_merge_hook_gates_merge_from_powershell_tool(), test_merge_hook_ignores_non_merge_bash(), test_merge_hook_ignores_non_shell_tool(), test_merge_hook_ignores_quoted_prompt_that_mentions_merge() (+1 more)

### Community 293 - "Backlog librarian — one advisory hygiene digest"
Cohesion: 0.25
Nodes (7): Backlog librarian — one advisory hygiene digest, Evidence pass, Findings — evidence, never guesses, Fixed defaults, Hard boundary, Receipt, Scheduling posture

### Community 294 - "Execution decision (in-project)"
Cohesion: 0.25
Nodes (7): Emit (advisory — you apply it, nothing here auto-runs), Execution decision (in-project), In-project verification note (the substrate specialization of rubric Step 5), Invocation boundary, Load the shared rubric first, Mode vocabulary (this skill's output for the rubric's Step 4 axis), Two substrates — decide this BEFORE reading any usage data

### Community 295 - "horus-release — cut a version, and land it where people actually run it"
Cohesion: 0.25
Nodes (7): Before you start, Boundaries, horus-release — cut a version, and land it where people actually run it, The chain, The invariant this skill exists for, Three OS targets, Traps that have actually bitten

### Community 296 - "Backlog librarian — one advisory hygiene digest"
Cohesion: 0.25
Nodes (7): Backlog librarian — one advisory hygiene digest, Evidence pass, Findings — evidence, never guesses, Fixed defaults, Hard boundary, Receipt, Scheduling posture

### Community 297 - "Execution decision (in-project)"
Cohesion: 0.25
Nodes (7): Emit (advisory — you apply it, nothing here auto-runs), Execution decision (in-project), In-project verification note (the substrate specialization of rubric Step 5), Invocation boundary, Load the shared rubric first, Mode vocabulary (this skill's output for the rubric's Step 4 axis), Two substrates — decide this BEFORE reading any usage data

### Community 298 - "horus-release — cut a version, and land it where people actually run it"
Cohesion: 0.25
Nodes (7): Before you start, Boundaries, horus-release — cut a version, and land it where people actually run it, The chain, The invariant this skill exists for, Three OS targets, Traps that have actually bitten

### Community 299 - "Execution Plan"
Cohesion: 0.25
Nodes (7): Active Phases, Execution Plan, Model Policy, Out of batch (stay on roadmap), Phase 1 design sketch (supervisor), Phase 3 design proposal (supervisor draft — needs user sign-off), Worker handoff contract

### Community 300 - "Backlog librarian — 2026-07-26"
Cohesion: 0.25
Nodes (7): Backlog librarian — 2026-07-26, Boundary, Clean checks, Needs owner interpretation, Proposed actions, Run facts, Summary

### Community 301 - "Skill audit — `wildcard` (v1 → v4) — 2026-07-28"
Cohesion: 0.25
Nodes (7): Applied state (2026-07-28), Defers, Not audited, Proposed replacement text (owner approves before anything is edited), Skill audit — `wildcard` (v1 → v4) — 2026-07-28, The root cause, stated once, Verdict table

### Community 302 - "Rules routing audit — where each of the 84 PRD Rules should live"
Cohesion: 0.25
Nodes (7): Destinations, Judgment calls the owner should make, Rules routing audit — where each of the 84 PRD Rules should live, Tally, The 84, What this audit does not claim, Why this exists

### Community 303 - "audit-advisory-interval — count releases AND days, not releases alone"
Cohesion: 0.25
Nodes (7): audit-advisory-interval — count releases AND days, not releases alone, Broad boundaries, Decisions settled (2026-07-28 refine pass, owner-approved), Intended outcome, Reviews, Source, Why

### Community 304 - "autotest-e2e-away-mode-drill — the owner's fully-scheduled away-mode e2e test"
Cohesion: 0.25
Nodes (7): 2026-08-01 — owner (manual), Acceptance, autotest-e2e-away-mode-drill — the owner's fully-scheduled away-mode e2e test, How (once the gaps land), Non-goals, Reviews, The exact flow the owner described (the target)

### Community 305 - "backlog-default-list — `horus backlog` should default to `list`"
Cohesion: 0.25
Nodes (7): Acceptance, backlog-default-list — `horus backlog` should default to `list`, Broad boundaries, Intended outcome, Reviews, Source, Why

### Community 306 - "close --check hard-blocks merge on Unclassified cards (should be advisory)"
Cohesion: 0.25
Nodes (7): Acceptance, close --check hard-blocks merge on Unclassified cards (should be advisory), Reviews, Source, What to change, Why — demonstrated, 2026-07-20 (pbi-ecosystem), Why this is wrong, not just strict

### Community 307 - "cockpit-sync-action — one-tap "Sync" in the TUI (per-project + fleet), on the shipped engine"
Cohesion: 0.25
Nodes (7): Acceptance, cockpit-sync-action — one-tap "Sync" in the TUI (per-project + fleet), on the shipped engine, How, Non-goals, Reviews, Source, Why

### Community 308 - "execution-requires-explicit-owner-delegation — authorization and substrate must both be explicit"
Cohesion: 0.25
Nodes (7): Acceptance, Contract to enforce, execution-requires-explicit-owner-delegation — authorization and substrate must both be explicit, Related, Second variant — native Codex subagents were routed into Horus workers, Why — live recurrence, 2026-07-29, Why the previous fix did not hold

### Community 309 - "prd-rules-section-outgrew-its-budget — 84 rules, 66% of the file, and every close now fights the cap"
Cohesion: 0.25
Nodes (7): 2026-08-02 — Rafael Figueiredo (manual), Broad boundaries, Intended outcome, Open decisions, prd-rules-section-outgrew-its-budget — 84 rules, 66% of the file, and every close now fights the cap, Reviews, Why — measured 2026-08-01, at the v0.0.81 close

### Community 310 - "tui-backlog-grouped-list — collapsible group-by sections in the TUI backlog list"
Cohesion: 0.25
Nodes (7): Non-goals, Open questions, Source, tui-backlog-grouped-list — collapsible group-by sections in the TUI backlog list, What (the cheap, low-risk win — stage 1), Why — owner, 2026-07-21, Why this first (staging)

### Community 311 - "tui-backlog-kanban-board — width-adaptive kanban lens over the backlog"
Cohesion: 0.25
Nodes (7): Depends on, Non-goals, Open questions, Source, The make-or-break constraint: geometry, tui-backlog-kanban-board — width-adaptive kanban lens over the backlog, Why — owner, 2026-07-21

### Community 312 - "concurrency-safe-continuity — make continuity hold up when multiple agents develop in parallel in one repo"
Cohesion: 0.25
Nodes (7): Candidate directions (sketches, NOT decisions), concurrency-safe-continuity — make continuity hold up when multiple agents develop in parallel in one repo, Grounding — the principle already exists, Intended outcome (open — explore when parallelism arrives), Open questions / to explore, Source, Why — anticipated, flagged 2026-07-21

### Community 313 - "fleet-sourced-autonomous-batch — feed the loop from the fleet, trip-timed"
Cohesion: 0.25
Nodes (7): Broad boundaries, fleet-sourced-autonomous-batch — feed the loop from the fleet, trip-timed, Intended outcome, Open decisions, Reviews, Source, Why

### Community 314 - "herdr-server-shutdown-fragility — herdr's server exits on client-triggered errors, taking every session with it"
Cohesion: 0.25
Nodes (7): 2026-08-02 — Rafael Figueiredo (manual), herdr-server-shutdown-fragility — herdr's server exits on client-triggered errors, taking every session with it, Options, Reviews, The durability number, Why — measured 2026-07-30, from `~/.config/herdr/herdr-server.log`, Why this matters for the host

### Community 315 - "vision-branch-x5 — safe execution boundaries and guardrails"
Cohesion: 0.25
Nodes (8): Branch acceptance, Convergence criterion, Distinctions the branch must preserve, Ordered children, Principles, Reviews, vision-branch-x5 — safe execution boundaries and guardrails, Why

### Community 316 - "x4 — experiment with PI as a harness via the proxy"
Cohesion: 0.25
Nodes (7): Acceptance (draft), Notes, Open decisions, Reviews, Scope (to be refined in a fresh session before actioning), Why, x4 — experiment with PI as a harness via the proxy

### Community 317 - "continuity_dirty_paths"
Cohesion: 0.29
Nodes (8): continuity_dirty(), continuity_dirty_paths(), Whether any continuity file has uncommitted changes (staged or not)., Changed continuity pathspec entries, including tracked deletions. The porcelain…, Mimic a post-commit hook edit: the close reports the exact stranded path., test_commit_continuity_surfaces_residual_dirty_path_and_skips_push(), test_continuity_dirty_false_outside_git(), test_continuity_dirty_tracks_horus_changes_only()

### Community 318 - "Horus — PRD"
Cohesion: 0.25
Nodes (7): Backlog, Horus — PRD, Open by readiness — see `.horus/backlog/`, Rules (load-bearing), Shipped, Structure contract (prototype), Vision

### Community 319 - "RESCUE — a Claude session went "api unresponsive" after proxy wiring"
Cohesion: 0.25
Nodes (7): Assets reference (all machine-local), FIX A — revive a still-running poisoned session (fastest; keeps its context), FIX B — stop the bleed for NEW sessions (native Claude again), If a session is unrecoverable, RESCUE — a Claude session went "api unresponsive" after proxy wiring, Tear down the proxy container, What happened (the mechanism)

### Community 320 - "Wildcard — branch-first divergence (2026-07-31)"
Cohesion: 0.25
Nodes (7): 1 — Arm and run the away-mode drill, 2 — Settle the three decisions blocking the continuity-contract declaration, 3 — Define the fabric probe's evidence bar while it still runs, 4 — Measure whether the proxy statusline leak persists, 5 — Redraft `x4-pi-harness-via-proxy` into something launchable, Deliberately excluded — X5, in full, Wildcard — branch-first divergence (2026-07-31)

### Community 321 - "Dispatch decision (cockpit / multi-project, sessions substrate)"
Cohesion: 0.29
Nodes (6): Account routing (cockpit-specific, on top of the rubric), Dispatch decision (cockpit / multi-project, sessions substrate), Emit (advisory — you apply it, nothing here auto-runs), Load the shared rubric first, Mode vocabulary (this skill's output for the rubric's Step 4 axis), Overseer verification note (the substrate specialization of rubric Step 5)

### Community 322 - "PRD-structure projects (v3 — `.horus/PRD.md` present)"
Cohesion: 0.29
Nodes (6): Boundaries, Consolidate Horus continuity, PRD-structure projects (v3 — `.horus/PRD.md` present), Steps, The dashboard contract — keep these current at EVERY close, Two jobs — do not conflate them

### Community 323 - "pathfinder — the re-baseline workflow (thin by design)"
Cohesion: 0.29
Nodes (6): Before you spend — confirm the token envelope, Deliberately omit, Hard boundary — advisory, gated, never auto-applied, pathfinder — the re-baseline workflow (thin by design), Step 0 — pin the intent BEFORE anything (never assume it), The flow

### Community 324 - "scope-cards — from a chosen branch to aligned shaping drafts"
Cohesion: 0.29
Nodes (6): Alongside the shaping drafts, propose the branch's edits, Deliberately omit, Gate, then write, Input, Output — the shaping-draft contract, scope-cards — from a chosen branch to aligned shaping drafts

### Community 325 - "Dispatch decision (cockpit / multi-project, sessions substrate)"
Cohesion: 0.29
Nodes (6): Account routing (cockpit-specific, on top of the rubric), Dispatch decision (cockpit / multi-project, sessions substrate), Emit (advisory — you apply it, nothing here auto-runs), Load the shared rubric first, Mode vocabulary (this skill's output for the rubric's Step 4 axis), Overseer verification note (the substrate specialization of rubric Step 5)

### Community 326 - "PRD-structure projects (v3 — `.horus/PRD.md` present)"
Cohesion: 0.29
Nodes (6): Boundaries, Consolidate Horus continuity, PRD-structure projects (v3 — `.horus/PRD.md` present), Steps, The dashboard contract — keep these current at EVERY close, Two jobs — do not conflate them

### Community 327 - "pathfinder — the re-baseline workflow (thin by design)"
Cohesion: 0.29
Nodes (6): Before you spend — confirm the token envelope, Deliberately omit, Hard boundary — advisory, gated, never auto-applied, pathfinder — the re-baseline workflow (thin by design), Step 0 — pin the intent BEFORE anything (never assume it), The flow

### Community 328 - "scope-cards — from a chosen branch to aligned shaping drafts"
Cohesion: 0.29
Nodes (6): Alongside the shaping drafts, propose the branch's edits, Deliberately omit, Gate, then write, Input, Output — the shaping-draft contract, scope-cards — from a chosen branch to aligned shaping drafts

### Community 329 - "OwnerHeaderTests"
Cohesion: 0.43
Nodes (3): is_owner_request(), True iff the Access owner-identity header matches ``owner_email``., OwnerHeaderTests

### Community 330 - "Skill audit: scope-cards — 2026-07-19"
Cohesion: 0.29
Nodes (6): Ceremony check, Evidence, Exact replacement contract, Owner verdict, Skill audit: scope-cards — 2026-07-19, Verdict: revise

### Community 331 - "account-settings-sync — one canonical settings block across isolated account dirs"
Cohesion: 0.29
Nodes (6): Acceptance (drafted 2026-07-19 refine pass — owner spot-check), account-settings-sync — one canonical settings block across isolated account dirs, Idea (thin, advisory — not a new config plane), Notes, Open questions, Reviews

### Community 332 - "backlog-readiness-disposition — machine-readable readiness and autonomy"
Cohesion: 0.29
Nodes (6): Acceptance, backlog-readiness-disposition — machine-readable readiness and autonomy, Contract (owner-approved), How, Non-goals, Source

### Community 333 - "horus-execution-general-plan-false-trigger — ordinary planning enters the worker-supervision workflow"
Cohesion: 0.29
Nodes (6): Acceptance, Contract defect, horus-execution-general-plan-false-trigger — ordinary planning enters the worker-supervision workflow, Source, What to change, Why — live incident, 2026-07-24

### Community 334 - "schedule-local-dispatcher — a first-class local one-shot/cron dispatcher for `horus run`"
Cohesion: 0.29
Nodes (6): Acceptance, Idea, Notes, Open questions, Reviews, schedule-local-dispatcher — a first-class local one-shot/cron dispatcher for `horus run`

### Community 335 - "supervise-verify-merge-close — unattended verify → merge → close → escalate for a dispatched card"
Cohesion: 0.29
Nodes (6): Acceptance, Idea, Notes, Open questions, Preconditions (not open questions), supervise-verify-merge-close — unattended verify → merge → close → escalate for a dispatched card

### Community 336 - "tui-vision-backlog-read-out — the cockpit shows direction, not just cards"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, Source, tui-vision-backlog-read-out — the cockpit shows direction, not just cards, Why

### Community 337 - "unattended-dispatch-attachable-worktree-defaults — make scheduled/detached runs attachable + isolated by default"
Cohesion: 0.29
Nodes (6): Acceptance, Idea, Notes, Open questions, Reviews, unattended-dispatch-attachable-worktree-defaults — make scheduled/detached runs attachable + isolated by default

### Community 338 - "unattended-escalation-channel — a push channel so a headless supervisor can reach the owner"
Cohesion: 0.29
Nodes (6): Acceptance, Idea, Notes, Open questions, Reviews, unattended-escalation-channel — a push channel so a headless supervisor can reach the owner

### Community 339 - "Make card-per-file backlog the fleet standard (unify inline `## Backlog` → cards)"
Cohesion: 0.29
Nodes (6): Application mode (how harmonization actually happens — owner Q, 2026-07-12), Bug typing (fold in the `bugs/`-folder decision), Enables, Make card-per-file backlog the fleet standard (unify inline `## Backlog` → cards), Scope, Verification

### Community 340 - "verify-guidance-long-running-services — "active + emits its signal", not "it installed""
Cohesion: 0.29
Nodes (6): 2026-07-27 — Rafael Figueiredo (agent), Acceptance, How, Non-goals, Reviews, verify-guidance-long-running-services — "active + emits its signal", not "it installed"

### Community 341 - "x3-away-mode-kit-e2e-rehearsal — dogfood the whole away loop once, end-to-end"
Cohesion: 0.29
Nodes (6): 2026-07-18 — Rafael Figueiredo (agent), Acceptance, Notes, Reviews, What to exercise (one real small card, isolated account), x3-away-mode-kit-e2e-rehearsal — dogfood the whole away loop once, end-to-end

### Community 342 - "automated-model-roster-grounding — keep the model roster fresh from external + shared sources, not manual bumps"
Cohesion: 0.29
Nodes (6): automated-model-roster-grounding — keep the model roster fresh from external + shared sources, not manual bumps, Intended outcome (broad — scope before committing), Non-goals, Open questions / to explore, Source, Why

### Community 343 - "dispatch-collision-guard — stop two concurrent agents from building the same card"
Cohesion: 0.29
Nodes (6): dispatch-collision-guard — stop two concurrent agents from building the same card, Non-goals, Open questions, Rough shape, Source, Why — the selection-moment blind spot the continuity cards assume away

### Community 344 - "dispatch-receipt-seam — the worker writes facts, the supervisor reproduces the signal"
Cohesion: 0.29
Nodes (6): Acceptance, dispatch-receipt-seam — the worker writes facts, the supervisor reproduces the signal, Open design questions (why this is Shaping, not Ready), Scope boundary, Source, Why

### Community 345 - "isolated-account-plugin-parity — an isolated account starts with no plugins"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, isolated-account-plugin-parity — an isolated account starts with no plugins, Open decisions for backlog-refine, Source, Why

### Community 346 - "managed-instruction-drift-lint — deterministically catch managed prose that references a removed CLI surface"
Cohesion: 0.29
Nodes (6): managed-instruction-drift-lint — deterministically catch managed prose that references a removed CLI surface, Non-goals, Open questions, Rough shape, Source, Why — grounded in a recorded incident, not speculation

### Community 347 - "native-app-account-launch-spike — can the TUI launch the desktop app under a chosen account"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, native-app-account-launch-spike — can the TUI launch the desktop app under a chosen account, Open decisions for backlog-refine, Source, Why

### Community 348 - "Probe smaller open-source workers on a remote Tailscale machine"
Cohesion: 0.29
Nodes (5): Exit line (explore), openrouter-provider-support — many more models behind one key, Acceptance, Boundaries, Probe smaller open-source workers on a remote Tailscale machine

### Community 349 - "optional-host-ci-coverage — CI cannot exercise the herdr host at all"
Cohesion: 0.29
Nodes (6): Acceptance (draft — sharpen once the option is chosen), Open decisions, optional-host-ci-coverage — CI cannot exercise the herdr host at all, Source, The trade-off, which is why this is a decision and not a task, Why — measured on 2026-07-29, the day the herdr host shipped

### Community 350 - "pathfinder-structured-outcome — refine the pathfinder chain to emit one structured, addressable per-run outcome"
Cohesion: 0.29
Nodes (6): Non-goals, Open decisions, pathfinder-structured-outcome — refine the pathfinder chain to emit one structured, addressable per-run outcome, Rough shape (open — this is the design question), Source, Why — owner, 2026-07-21

### Community 351 - "prd-worked-by-account — record which account(s) a project's work actually happened under"
Cohesion: 0.29
Nodes (6): Acceptance (draft), Design constraints, prd-worked-by-account — record which account(s) a project's work actually happened under, Secondary case — cross-machine alias discovery (weaker than it first looked), Source, Why — the primary case is launch defaulting, not discovery

### Community 352 - "Product naming — track candidates, decide at distribution"
Cohesion: 0.29
Nodes (6): 2026-07-16 — Rafael Figueiredo (manual), 2026-07-21 — Rafael Figueiredo (manual), Acceptance, Candidates (append via `horus backlog review`), Product naming — track candidates, decide at distribution, Reviews

### Community 353 - "repeated-question-skill-mining — repeatedly-asked questions are undeclared skills"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, repeated-question-skill-mining — repeatedly-asked questions are undeclared skills, Source, Why

### Community 354 - "research-receipts-surfacing — receipts as first-class citizens, not stray .md files"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, research-receipts-surfacing — receipts as first-class citizens, not stray .md files, Source, Why

### Community 355 - "skill-self-calibration-probe — skills that notice their own drift (wildcard)"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, skill-self-calibration-probe — skills that notice their own drift (wildcard), Source, Why

### Community 356 - "telegram-idea-capture — capture ideas from the phone, triage later (wildcard)"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, Source, telegram-idea-capture — capture ideas from the phone, triage later (wildcard), Why

### Community 357 - "tui-campaign-native-goal-probe — make Campaign a persistent native goal, not an ordinary prompt"
Cohesion: 0.29
Nodes (6): Live findings — 2026-07-24, Non-goals, Source, tui-campaign-native-goal-probe — make Campaign a persistent native goal, not an ordinary prompt, Verdict, Why

### Community 358 - "usage-analytics-read-out — from point-in-time percentages to steering answers"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, Source, usage-analytics-read-out — from point-in-time percentages to steering answers, Why

### Community 359 - "Ordered stages and children"
Cohesion: 0.29
Nodes (7): Optional, Ordered stages and children, Stage 0 — prove GPT inside Claude Code (evidence complete), Stage 1.1 — make the live route truthful, Stage 1 — optional proxy wiring (shipped in v0.0.65), Stage 2 — harness axis, Stage 3 — calibration across the route matrix

### Community 360 - "window-aware-scheduling — fire when budget exists, not when the clock says (wildcard)"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, Source, Why, window-aware-scheduling — fire when budget exists, not when the clock says (wildcard)

### Community 361 - "x6 — declare the continuity contract explicitly"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, Source, Why, x6 — declare the continuity contract explicitly

### Community 362 - "x6 — fabric as the live contract-sufficiency probe"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, Source, Why, x6 — fabric as the live contract-sufficiency probe

### Community 363 - "x6 — workflow alternatives refresh (shallow, contract-judged)"
Cohesion: 0.29
Nodes (6): Broad boundaries, Intended outcome, Open decisions for backlog-refine, Source, Why, x6 — workflow alternatives refresh (shallow, contract-judged)

### Community 364 - "cmd_supervise"
Cohesion: 0.43
Nodes (7): cmd_supervise(), Unattended verify → merge → close → escalate for a dispatched card. Resolves…, _supervise_ns(), test_cmd_supervise_deferred_no_match_escalates(), test_cmd_supervise_deferred_resolves_then_supervises(), test_cmd_supervise_refuses_more_than_one_selector(), test_cmd_supervise_refuses_no_selector()

### Community 365 - "Market scan: Horus product-owner capabilities (roadmap-convergence + market-research) — 2026-07-16"
Cohesion: 0.29
Nodes (6): Headline findings, Market scan: Horus product-owner capabilities (roadmap-convergence + market-research) — 2026-07-16, Net recommendation, Q1 — Roadmap-convergence: what to steal, what to leave, Q2 — Market-research: what to bake in, Sources

### Community 366 - "test_capital_y_syncs_every_clean_behind_project"
Cohesion: 0.29
Nodes (7): _card(), Path, The TUI must not re-derive which statuses are inactive. Three copies of this…, Fresh means fresh: nothing injected, so the owner types into an empty session.…, test_active_card_filter_has_no_status_list_of_its_own(), test_capital_y_syncs_every_clean_behind_project(), test_fresh_launch_prompt_is_genuinely_empty()

### Community 367 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 368 - "launch-model-refresh — keep the TUI's launchable model list current from vendor docs"
Cohesion: 0.33
Nodes (5): 1. Research the vendor's model status (cite sources + an as-of date), 2. Propose the config change (owner-gated — do NOT write yet), 3. Write only what the owner approved, Boundaries, launch-model-refresh — keep the TUI's launchable model list current from vendor docs

### Community 369 - "Product audit — the inward evidence step (analysis, never verdicts)"
Cohesion: 0.33
Nodes (5): Close the audit, Evidence (gather, not recall), Pin the subject before gathering evidence, Product audit — the inward evidence step (analysis, never verdicts), The receipt — fixed spine, written for a no-context reader

### Community 370 - "Claude Code Instructions"
Cohesion: 0.33
Nodes (5): Claude Code Instructions, Claude Notes, graphify, Horus Project Continuity, Releasing horus-harness

### Community 371 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 372 - "launch-model-refresh — keep the TUI's launchable model list current from vendor docs"
Cohesion: 0.33
Nodes (5): 1. Research the vendor's model status (cite sources + an as-of date), 2. Propose the config change (owner-gated — do NOT write yet), 3. Write only what the owner approved, Boundaries, launch-model-refresh — keep the TUI's launchable model list current from vendor docs

### Community 373 - "Product audit — the inward evidence step (analysis, never verdicts)"
Cohesion: 0.33
Nodes (5): Close the audit, Evidence (gather, not recall), Pin the subject before gathering evidence, Product audit — the inward evidence step (analysis, never verdicts), The receipt — fixed spine, written for a no-context reader

### Community 374 - "app-usage-cost-opacity — native apps meter usage but surface no cost/context/cache visibility or control"
Cohesion: 0.33
Nodes (5): app-usage-cost-opacity — native apps meter usage but surface no cost/context/cache visibility or control, Open questions, Source, Why — owner, 2026-07-21, Why this can only be OUR layer

### Community 375 - "Ground the ranking in 3rd-party benchmark platforms"
Cohesion: 0.33
Nodes (5): Feeds, Ground the ranking in 3rd-party benchmark platforms, Notes / caution, Scope, Verification

### Community 376 - "`horus close` can strand a dirty tree: a commit can't reference its own SHA"
Cohesion: 0.33
Nodes (5): `horus close` can strand a dirty tree: a commit can't reference its own SHA, Observed (2026-07-14, tier0-supervision-verbs acceptance cleanup), Proposed fix (not just a description — pick one or combine), Two gaps, Verification

### Community 377 - "cockpit-autonomous-dispatch-contract — a skill wiring discover→pick→scope→dispatch/schedule→supervise"
Cohesion: 0.33
Nodes (5): Acceptance, cockpit-autonomous-dispatch-contract — a skill wiring discover→pick→scope→dispatch/schedule→supervise, Idea, Notes, Open questions

### Community 378 - "Display the delegation decision matrix from the CLI (agent-first)"
Cohesion: 0.33
Nodes (5): Display the delegation decision matrix from the CLI (agent-first), Fold in: older-but-capable models stay in the roster, Shape decision (recommendation — owner input 2026-07-12), Verification, What it renders

### Community 379 - "Fold consolidate's signals into `close --check`; reserve the skill for heavy passes"
Cohesion: 0.33
Nodes (5): Change, Fold consolidate's signals into `close --check`; reserve the skill for heavy passes, Problem (observed 2026-07-12), v2 (six-lane) note, Verification

### Community 380 - "horus-statusline-default — ship the status line, don't hand-configure it per machine"
Cohesion: 0.33
Nodes (5): Acceptance, horus-statusline-default — ship the status line, don't hand-configure it per machine, Idea, Non-goals, Notes

### Community 381 - "input-bridge-remote-ask — a session asks, the owner answers from the phone"
Cohesion: 0.33
Nodes (5): Acceptance, How (the deterministic primitive — Station 1, no LLM), input-bridge-remote-ask — a session asks, the owner answers from the phone, Non-goals, Reviews

### Community 382 - "launch-mode-process-skill — a launch mode attaches a process skill so the working posture holds"
Cohesion: 0.33
Nodes (5): Acceptance, How (thin — reuse the launch picker + the bundled-skill mechanism), launch-mode-process-skill — a launch mode attaches a process skill so the working posture holds, Non-goals / boundaries, Notes

### Community 383 - "Hosted terminal is not mobile-responsive (glyphs scramble, fixed size)"
Cohesion: 0.33
Nodes (5): Hosted terminal is not mobile-responsive (glyphs scramble, fixed size), Likely causes (overseer read of `horus/dashboard.py`), Overlap (READ BEFORE CLAIMING), Provenance, Verification

### Community 384 - "Model ranking synthesis — a grounded "current ranking" for the decision matrix"
Cohesion: 0.33
Nodes (5): Depends on / feeds, Model ranking synthesis — a grounded "current ranking" for the decision matrix, Refinement (later — the richer signals to ground the ranking), v1 (decided now — the easy approach first), Verification

### Community 385 - "Dashboard tab: full model-roster research + table + refresh button"
Cohesion: 0.33
Nodes (5): Boundaries / overlap, Dashboard tab: full model-roster research + table + refresh button, Depends on / feeds, Scope, Verification

### Community 386 - "notify-listen-steering-channel — a deterministic two-way steering channel"
Cohesion: 0.33
Nodes (5): Acceptance, Design, Non-goals, notify-listen-steering-channel — a deterministic two-way steering channel, Security invariants (non-negotiable)

### Community 387 - "notify-listen — trip-mode service + andon-reply (release) completion"
Cohesion: 0.33
Nodes (5): 1. Andon-reply loop — `release` a halted dependent from the phone, 2. Trip-mode persistent listener, Acceptance, Non-goals, notify-listen — trip-mode service + andon-reply (release) completion

### Community 388 - "Pricing-aware model-roster research process"
Cohesion: 0.33
Nodes (5): Architecture (owner-confirmed), Pricing-aware model-roster research process, Relationship, The price-for-capability filter (methodology, for the refresh run), Verification

### Community 389 - "Research: OpenWiki vs. our self-documenting capability catalog"
Cohesion: 0.33
Nodes (5): Decision (2026-07-12, PR #177), Deliverable, Research: OpenWiki vs. our self-documenting capability catalog, Scope (research + a written recommendation — web-grounded, do NOT fabricate), Verification

### Community 390 - "prd-readiness-count-check — keep the PRD readiness-breakdown counts honest automatically"
Cohesion: 0.33
Nodes (5): Non-goals, prd-readiness-count-check — keep the PRD readiness-breakdown counts honest automatically, Rough shape (autonomous, deterministic), Source, Why — a self-detection gap found by living it (2026-07-24)

### Community 391 - "resume-session-id-mismatch — the id you can see is not the id `--resume` wants"
Cohesion: 0.33
Nodes (5): Acceptance, resume-session-id-mismatch — the id you can see is not the id `--resume` wants, Scope — one of these, not all three, Why it is worth fixing rather than documenting, Why — observed 2026-07-27, resuming a fabric-build drill worker

### Community 392 - "standing-dispatch-envelope — bounded pre-authorization for unattended dispatch"
Cohesion: 0.33
Nodes (5): Acceptance, Idea, Non-goals, Reviews, standing-dispatch-envelope — bounded pre-authorization for unattended dispatch

### Community 393 - "tui-launch-model-effort-selection — pick model + effort at launch, not after"
Cohesion: 0.33
Nodes (5): Acceptance, How (thin — reuse existing machinery, add no second launch path), Non-goals, Notes, tui-launch-model-effort-selection — pick model + effort at launch, not after

### Community 394 - "tui-launch-session-new-window-default — Defaults option: launch sessions in a new window"
Cohesion: 0.33
Nodes (5): Acceptance, How (stays TUI-thin — existing rule), Non-goals, The desktop / mobile tension (owner, 2026-07-18), tui-launch-session-new-window-default — Defaults option: launch sessions in a new window

### Community 395 - "codex-usage-blind-across-machines — a Codex usage reading cannot see another machine"
Cohesion: 0.33
Nodes (5): codex-usage-blind-across-machines — a Codex usage reading cannot see another machine, Open questions, Source, Why it matters beyond display, Why — measured 2026-08-08, while adding the TUI's all-accounts usage refresh

### Community 396 - "decision-doc-skill — a skill that generates issue/solution decision documentation"
Cohesion: 0.33
Nodes (5): decision-doc-skill — a skill that generates issue/solution decision documentation, Open questions, Rough shape (open — just tracked for now), Source, Why — owner, 2026-07-21

### Community 397 - "telegram-group-project-topics — a topic per project in one steering group"
Cohesion: 0.33
Nodes (5): Acceptance, How, Non-goals, Reviews, telegram-group-project-topics — a topic per project in one steering group

### Community 398 - "tui-toggle-card-into-scheduler — arm/disarm a ready card for autonomous execution"
Cohesion: 0.33
Nodes (5): Acceptance (firmed 2026-07-19 — consumes the decided `order:` field), How (to design in-card), Non-goals, Notes, tui-toggle-card-into-scheduler — arm/disarm a ready card for autonomous execution

### Community 400 - "x5-cross-platform-containment-contract — honest safety guarantees on Linux, Windows, and macOS"
Cohesion: 0.33
Nodes (5): Acceptance, Non-goals, Research/design, Why, x5-cross-platform-containment-contract — honest safety guarantees on Linux, Windows, and macOS

### Community 401 - "WatchOutcome"
Cohesion: 0.27
Nodes (6): WatchOutcome, The phone `sessions` tap: only sessions live right now, one line each — not the…, test_merge_watch_cli_exits_0_on_green(), test_merge_watch_cli_exits_1_on_red(), test_merge_watch_cli_exits_1_on_timeout(), test_sessions_running_lists_only_live()

### Community 402 - "X4 stage-0 spike — GPT in Claude Code via the Codex subscription"
Cohesion: 0.33
Nodes (5): Artifacts (machine-local, not committed — contain/point at the sub token), Setup that worked (exact), Spike questions — answered, Verdict → stage 1, X4 stage-0 spike — GPT in Claude Code via the Codex subscription

### Community 403 - "_gt"
Cohesion: 0.33
Nodes (6): _grid_nav_target(), Next selection index for arrow navigation over the projects home. Layout…, _gt(), test_grid_nav_falls_into_and_back_out_of_the_single_column_tail(), test_grid_nav_single_column_is_linear_with_left_as_back(), test_grid_nav_two_columns_down_moves_a_row_not_sideways()

### Community 404 - "Field findings from fabric session — workflow enforcement gaps (2026-07-08)"
Cohesion: 0.33
Nodes (5): Field findings from fabric session — workflow enforcement gaps (2026-07-08), Findings, Improvement suggestions beyond the findings (fresh-session checks), Next, The user's target workflow (canonical statement, verbatim intent)

### Community 405 - "Agent Instructions"
Cohesion: 0.40
Nodes (4): Agent Instructions, Codex Notes, Horus Project Continuity, Releasing horus-harness

### Community 406 - "Fleet curation"
Cohesion: 0.40
Nodes (4): Apply an approved cleanup, Close, Fleet curation, Review

### Community 407 - "Fleet curation"
Cohesion: 0.40
Nodes (4): Apply an approved cleanup, Close, Fleet curation, Review

### Community 408 - "Features — capability ledger"
Cohesion: 0.40
Nodes (4): Features — capability ledger, In progress, Planned, Shipped

### Community 409 - "Attachable detached one-shot worker runs"
Cohesion: 0.40
Nodes (4): Acceptance, Attachable detached one-shot worker runs, Boundaries, Reviews

### Community 410 - "codex-delivery-dispatch-needs-full-auto — a delivery dispatch that structurally can't deliver must be refused at arm time"
Cohesion: 0.40
Nodes (4): Acceptance, codex-delivery-dispatch-needs-full-auto — a delivery dispatch that structurally can't deliver must be refused at arm time, How, Non-goals

### Community 411 - "config-dir-guard-advisory — same-account concurrency is advised, not refused"
Cohesion: 0.40
Nodes (4): Acceptance, config-dir-guard-advisory — same-account concurrency is advised, not refused, Non-goals / follow-up, What changed

### Community 412 - "Surface under-sampled models — counter the survivorship trap in dispatch"
Cohesion: 0.40
Nodes (4): Gated by, Scope, Surface under-sampled models — counter the survivorship trap in dispatch, Verification

### Community 413 - "`horus fleet --backlog` — deterministic fleet-wide backlog roll-up"
Cohesion: 0.40
Nodes (4): Depends on, `horus fleet --backlog` — deterministic fleet-wide backlog roll-up, Scope, Verification

### Community 414 - "global-skill-viewer-tui — see installed vs available skills, per agent"
Cohesion: 0.40
Nodes (4): Acceptance, global-skill-viewer-tui — see installed vs available skills, per agent, How, Non-goals

### Community 415 - "horus-kickstart — one guided divergence→convergence re-baseline (also the onboarding path)"
Cohesion: 0.40
Nodes (4): Acceptance (scoped), horus-kickstart — one guided divergence→convergence re-baseline (also the onboarding path), Notes, The flow (each step PROPOSES; the owner decides at every gate)

### Community 416 - "horus init optionally scaffolds a minimal project CI gate"
Cohesion: 0.40
Nodes (4): Acceptance, Boundaries, horus init optionally scaffolds a minimal project CI gate, Reviews

### Community 417 - "Track model availability / lifecycle — don't invest in soon-to-retire models"
Cohesion: 0.40
Nodes (4): Feeds, Scope, Track model availability / lifecycle — don't invest in soon-to-retire models, Verification

### Community 418 - "Reconcile canonical model roster rows, prices, and lifecycle provenance"
Cohesion: 0.40
Nodes (4): Current facts, Reconcile canonical model roster rows, prices, and lifecycle provenance, Required slice, Verification

### Community 419 - "notify-listen --service: absolute ExecStart + restart-on-upgrade"
Cohesion: 0.40
Nodes (4): Acceptance, Fix, notify-listen --service: absolute ExecStart + restart-on-upgrade, Reviews

### Community 420 - "parallel-session-continuity-reconciliation — two sessions, one continuity"
Cohesion: 0.40
Nodes (4): Idea (cheapest rung first — deterministic signal, no locking), Non-goals, parallel-session-continuity-reconciliation — two sessions, one continuity, Reviews

### Community 421 - "parallel-signal-informational-not-verdict — a named sibling PR shouldn't read as "Stale""
Cohesion: 0.40
Nodes (4): Acceptance, Fix (make the parallel signal informational), Non-goals, parallel-signal-informational-not-verdict — a named sibling PR shouldn't read as "Stale"

### Community 422 - "Provider-valid model selector contract"
Cohesion: 0.40
Nodes (4): Acceptance, Boundaries, Evidence, Provider-valid model selector contract

### Community 423 - "schedule-run-any-subcommand — the scheduler can't arm a `supervise` (or `warmup`)"
Cohesion: 0.40
Nodes (4): Acceptance, How, Non-goals, schedule-run-any-subcommand — the scheduler can't arm a `supervise` (or `warmup`)

### Community 424 - "scheduled-dispatch-launch-failure-escalates — don't die silently in the journal"
Cohesion: 0.40
Nodes (4): Acceptance, Concrete design, Non-goals, scheduled-dispatch-launch-failure-escalates — don't die silently in the journal

### Community 425 - "service-installers-self-verify-active — safety in code, not in the probe"
Cohesion: 0.40
Nodes (4): Acceptance, How, Non-goals, service-installers-self-verify-active — safety in code, not in the probe

### Community 426 - "systemd-unit-absolute-execstart-guard — one test over all unit writers"
Cohesion: 0.40
Nodes (4): Acceptance, How, Non-goals, systemd-unit-absolute-execstart-guard — one test over all unit writers

### Community 427 - "telegram-output-minimal-legible — the phone push + button replies are minimal, not log dumps"
Cohesion: 0.40
Nodes (4): Acceptance, How, Non-goals, telegram-output-minimal-legible — the phone push + button replies are minimal, not log dumps

### Community 428 - "tui-branch-tree-glance — the backlog as a tree, at a glance, on the phone"
Cohesion: 0.40
Nodes (4): Acceptance, How (thin, per the TUI rule: render canonical primitives, never a second parser), Non-goals, tui-branch-tree-glance — the backlog as a tree, at a glance, on the phone

### Community 429 - "usage — capacity across all accounts from Telegram"
Cohesion: 0.40
Nodes (4): Acceptance, How, Non-goals, usage — capacity across all accounts from Telegram

### Community 430 - "vendor-neutral-delegation-tiers — tiers name capability, never a vendor"
Cohesion: 0.40
Nodes (4): Acceptance, Non-goals, Owner's initial equivalence mapping (prior, to validate), vendor-neutral-delegation-tiers — tiers name capability, never a vendor

### Community 431 - "vscode-terminal-launch-command — open a session in the VS Code terminal + project folder"
Cohesion: 0.40
Nodes (4): Acceptance, How (to design in-card), Non-goals, vscode-terminal-launch-command — open a session in the VS Code terminal + project folder

### Community 432 - "warmup — start the 5h usage window on demand"
Cohesion: 0.40
Nodes (4): Acceptance, How, Non-goals, warmup — start the 5h usage window on demand

### Community 433 - "Explicit worker dispatch consent and cost accounting"
Cohesion: 0.40
Nodes (4): Acceptance, Boundaries, Explicit worker dispatch consent and cost accounting, Reviews

### Community 434 - "explore-converge-lifecycle — a roadmap that breathes (divergence → convergence)"
Cohesion: 0.40
Nodes (4): Acceptance (scoped), explore-converge-lifecycle — a roadmap that breathes (divergence → convergence), Notes, Reviews

### Community 435 - "Platform- and capability-scoped machine requirements"
Cohesion: 0.40
Nodes (4): Acceptance, Execution, Platform- and capability-scoped machine requirements, Reviews

### Community 436 - "x4-codex-usage-in-claude-code — live Codex limits while GPT runs in Claude Code"
Cohesion: 0.40
Nodes (5): Acceptance, Design, Non-goals, Why, x4-codex-usage-in-claude-code — live Codex limits while GPT runs in Claude Code

### Community 437 - "x4-provider-credential-routing — separate harness profile from the subscription that serves the model"
Cohesion: 0.40
Nodes (5): Acceptance, Design, Non-goals, Why, x4-provider-credential-routing — separate harness profile from the subscription that serves the model

### Community 438 - "x4-tui-execution-route-axis — make the complete model/harness/account route visible and selectable"
Cohesion: 0.40
Nodes (5): Acceptance, Design, Non-goals, Why, x4-tui-execution-route-axis — make the complete model/harness/account route visible and selectable

### Community 439 - "x5-container-execution-spike — decide where stronger isolation earns its integration cost"
Cohesion: 0.40
Nodes (5): Acceptance, Non-goals, Questions, Why, x5-container-execution-spike — decide where stronger isolation earns its integration cost

### Community 440 - "x5-linux-agent-cgroup-containment — one bounded systemd scope per Horus session"
Cohesion: 0.40
Nodes (5): Acceptance, Design questions to resolve, Non-goals, Why, x5-linux-agent-cgroup-containment — one bounded systemd scope per Horus session

### Community 441 - "x5-network-bot-isolation — dedicated boundary for Telegram, Hermes, and future inbound services"
Cohesion: 0.40
Nodes (5): Acceptance, Design questions, Non-goals, Why, x5-network-bot-isolation — dedicated boundary for Telegram, Hermes, and future inbound services

### Community 442 - "x5-persistent-service-resource-envelopes — bound every Horus daemon and verify the live unit"
Cohesion: 0.40
Nodes (5): Acceptance, Design, Non-goals, Why, x5-persistent-service-resource-envelopes — bound every Horus daemon and verify the live unit

### Community 443 - "x5-resource-policy-calibration — tune limits from machine capacity and real agent workloads"
Cohesion: 0.40
Nodes (5): Acceptance, Non-goals, Questions, Why, x5-resource-policy-calibration — tune limits from machine capacity and real agent workloads

### Community 444 - "Mini market scan: X3 scheduled/autonomous dispatch + supervision — 2026-07-17"
Cohesion: 0.40
Nodes (4): Candidates, Mini market scan: X3 scheduled/autonomous dispatch + supervision — 2026-07-17, Sources, Verdict: YELLOW (same shape as the memory finding)

### Community 445 - "_freshness_token"
Cohesion: 0.50
Nodes (5): _fmt_age(), _freshness_token(), Human age for a fetch reading: "just now" / "5m ago" / "not fetched"., (style, text) remote-freshness token for a project row, or None to omit it.…, test_fmt_age_and_freshness_token_units()

### Community 446 - "test_usage_check_uses_fresh_account_limits_not_stale_project_limits"
Cohesion: 0.40
Nodes (5): Rate limits are account-global; project context remains project-scoped., test_codex_userpromptsubmit_hook_defers_to_user(), test_usage_check_cli_warns_and_codex_stop_hook_blocks_with_json(), test_usage_check_uses_fresh_account_limits_not_stale_project_limits(), _write_codex_rollout()

### Community 447 - "_Proc"
Cohesion: 0.40
Nodes (3): _Proc, Fails safe: sha not present locally (e.g. shallow clone) yields no evidence, so…, test_pr_only_contexts_empty_when_ls_tree_unavailable()

### Community 448 - "test_guarded_hook_is_silent_noop_when_cli_missing"
Cohesion: 0.40
Nodes (5): skipif, A repo clone on a machine without Horus: the committed hook command must exit 0…, A horus that exists but dies (e.g. dead-on-import) must also be silenced —…, test_guarded_hook_is_silent_noop_when_cli_missing(), test_guarded_hook_is_silent_when_cli_broken()

### Community 449 - "test_spawn_pty_runs_a_real_command"
Cohesion: 0.40
Nodes (3): Integration: a real PTY echoes output (platform-native ConPTY / stdlib pty)., test_close_kills_and_forgets_terminal(), test_spawn_pty_runs_a_real_command()

### Community 450 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 451 - "graphify reference: commit hook and native AGENTS.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native AGENTS.md integration, graphify reference: commit hook and native AGENTS.md integration

### Community 452 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 453 - "Distill project history"
Cohesion: 0.50
Nodes (3): Boundaries, Distill project history, PRD-structure projects (v3 — `.horus/PRD.md` present)

### Community 454 - "Infer Horus continuity from the project's docs"
Cohesion: 0.50
Nodes (3): Boundaries, Infer Horus continuity from the project's docs, PRD-structure projects (v3 — `.horus/PRD.md` present)

### Community 455 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 456 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 457 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 458 - "Distill project history"
Cohesion: 0.50
Nodes (3): Boundaries, Distill project history, PRD-structure projects (v3 — `.horus/PRD.md` present)

### Community 459 - "Infer Horus continuity from the project's docs"
Cohesion: 0.50
Nodes (3): Boundaries, Infer Horus continuity from the project's docs, PRD-structure projects (v3 — `.horus/PRD.md` present)

### Community 460 - ".validate_model"
Cohesion: 0.50
Nodes (3): _provider_selector_for(), Reject a known calibration-only label before it reaches ``claude``. Static and…, Best-effort full-selector spelling for a calibration-only key, for the…

### Community 461 - "Account-scoped usage check for safe dispatch"
Cohesion: 0.50
Nodes (3): Acceptance, Account-scoped usage check for safe dispatch, Execution

### Community 462 - "Boundary-based continuity granularity"
Cohesion: 0.50
Nodes (3): Acceptance, Boundary-based continuity granularity, Execution

### Community 463 - "Bulk-migration inventory reconciliation (empty-walk-is-an-error)"
Cohesion: 0.50
Nodes (3): Acceptance, Boundaries, Bulk-migration inventory reconciliation (empty-walk-is-an-error)

### Community 464 - "Optional campaign-supervision launch from the TUI"
Cohesion: 0.50
Nodes (3): Acceptance, Execution, Optional campaign-supervision launch from the TUI

### Community 465 - "Structure-aware execution supervisor prompt"
Cohesion: 0.50
Nodes (3): Acceptance, Boundaries, Structure-aware execution supervisor prompt

### Community 466 - "Remote-authoritative fleet review + optional TUI curator entry"
Cohesion: 0.50
Nodes (3): Acceptance, Execution, Remote-authoritative fleet review + optional TUI curator entry

### Community 467 - "market-scan — outward, evidence-first market/competitive research skill"
Cohesion: 0.50
Nodes (3): Acceptance (scoped minimal subset), market-scan — outward, evidence-first market/competitive research skill, Notes

### Community 468 - "Merge-watch settles applicable checks on a post-merge SHA"
Cohesion: 0.50
Nodes (3): Acceptance, Boundaries, Merge-watch settles applicable checks on a post-merge SHA

### Community 469 - "Proper model names (rename, not alias) + datum migration + table rendering"
Cohesion: 0.50
Nodes (3): Proper model names (rename, not alias) + datum migration + table rendering, Scope, Verification

### Community 470 - "Optional recovery notes and honest onboarding"
Cohesion: 0.50
Nodes (3): Acceptance, Execution, Optional recovery notes and honest onboarding

### Community 471 - "Evidence-first process retrospective skill"
Cohesion: 0.50
Nodes (3): Acceptance, Boundaries, Evidence-first process retrospective skill

### Community 472 - "Release-stamped product audit (signal + skill)"
Cohesion: 0.50
Nodes (3): Acceptance, Boundaries, Release-stamped product audit (signal + skill)

### Community 473 - "roadmap-convergence — a healthy backlog that converges toward the Vision, with a DoD"
Cohesion: 0.50
Nodes (3): Acceptance (scoped minimal subset — steal 3, leave the rest), Notes, roadmap-convergence — a healthy backlog that converges toward the Vision, with a DoD

### Community 474 - "Stale datum usage-overlap reconciliation"
Cohesion: 0.50
Nodes (3): Acceptance, Evidence, Stale datum usage-overlap reconciliation

### Community 475 - "TUI fleet projection sync"
Cohesion: 0.50
Nodes (3): Acceptance, Execution, TUI fleet projection sync

### Community 476 - "Start remote-only GitHub projects from the terminal TUI"
Cohesion: 0.50
Nodes (3): Acceptance, Execution, Start remote-only GitHub projects from the terminal TUI

### Community 477 - "Worker guard for destructive global-state cleanup"
Cohesion: 0.50
Nodes (3): Acceptance, Boundaries, Worker guard for destructive global-state cleanup

### Community 478 - "Project-local workflow policy overrides"
Cohesion: 0.50
Nodes (3): Acceptance, Execution, Project-local workflow policy overrides

### Community 479 - "_describe_run"
Cohesion: 0.50
Nodes (4): _describe_run(), The value passed to ``flag`` in a pass-through `horus run` arg list, or None., A human label for a scheduled dispatch: the card if there is one, else the…, _run_arg_value()

### Community 480 - "_usage_floor_label"
Cohesion: 0.50
Nodes (4): The floor is opt-in, so say which regime this envelope is actually in — the…, _usage_floor_label(), The owner reads this while setting up a trip they cannot correct from, so it…, test_usage_floor_label_tells_the_truth_about_which_regime_applies()

### Community 481 - "resolve_open_mode"
Cohesion: 0.50
Nodes (4): How the companion opens the dashboard: ``"owned"`` (dedicated app window we…, resolve_open_mode(), test_resolve_open_mode_defaults_owned_on_windows_tab_elsewhere(), test_resolve_open_mode_flags_win()

### Community 482 - "Execution Plan — two isolated Claude workers"
Cohesion: 0.50
Nodes (3): Execution Plan — two isolated Claude workers, Phase 1 — Post-merge check settling, Phase 2 — Evidence-first process retrospective skill

### Community 483 - "unit_exit_detail"
Cohesion: 0.50
Nodes (4): A short human reason ``unit`` failed: its exit status and systemd result. Read…, unit_exit_detail(), test_unit_exit_detail_is_best_effort_when_systemd_is_unreadable(), test_unit_exit_detail_reads_the_failed_units_exit_code()

### Community 485 - "openwiki-comparison-2026-07.md"
Cohesion: 0.50
Nodes (3): COMPARE vs OURS, RECOMMENDATION, WHAT OPENWIKI IS

### Community 486 - "_isolated_home"
Cohesion: 0.50
Nodes (4): _full_capacity(), _isolated_home(), fixture, Envelopes live under ~/.horus; never touch the real one from a test.

### Community 487 - "test_a_vanished_session_offers_restore_even_though_its_target_ref_survives"
Cohesion: 0.50
Nodes (4): A vanished session shaped as `reconcile()` actually leaves it. `target_ref` is…, The session screen must offer Restore for a vanished row. Found by a live probe…, test_a_vanished_session_offers_restore_even_though_its_target_ref_survives(), _vanished_tmux_record()

### Community 495 - "_age_phrase"
Cohesion: 0.67
Nodes (3): _age_phrase(), How old a reading is, in words — a usage number without its age invites the…, test_age_phrase_reads_naturally()

### Community 496 - "_resolve_tail_session"
Cohesion: 0.67
Nodes (3): The session `horus tail` should follow: prefix match when an id is given (like…, _resolve_tail_session(), test_tail_no_args_resolves_most_recent_running()

### Community 497 - "_offload_control"
Cohesion: 0.67
Nodes (3): _offload_control(), Offload a project: two explicit choices — *Keep files* (remove the projected…, test_offload_control_offers_keep_and_remove_completely()

### Community 498 - "looks_like_usage_death"
Cohesion: 0.67
Nodes (3): looks_like_usage_death(), Whether an ERROR event's text looks like a usage/quota wall., test_looks_like_usage_death_matches_walls_not_prose()

### Community 500 - "_isolate_dashboard_access_globals"
Cohesion: 0.67
Nodes (3): _isolate_dashboard_access_globals(), fixture, Snapshot and restore the exposed-mode gate globals around every test.…

### Community 501 - "_isolated_config"
Cohesion: 0.67
Nodes (3): _isolated_config(), fixture, Point config.toml at a throwaway file so no test reads the real ~/.horus.

### Community 502 - "units"
Cohesion: 0.67
Nodes (3): fixture, Unit files in a temp dir; systemctl stubbed to succeed and record calls., units()

## Knowledge Gaps
- **1796 isolated node(s):** `horus-harness`, `deploy-hosted.sh script`, `failures`, `Hard boundary`, `Fixed defaults` (+1791 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **45 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `main` to `test_terminal_sessions.py`, `cli.py`, `test_backlog.py`, `test_datums.py`, `test_backlog_tree.py`, `init_project`, `WatchOutcome`, `test_registry.py`, `test_close_commit_rechecks_post_commit_state`, `test_doctor_machine.py`, `_write_backlog_card`, `_plain`, `test_overhead.py`, `test_fleet_backlog.py`, `test_integration.py`, `test_verify_inventory.py`, `UsageSnapshot`, `test_usage_check_uses_fresh_account_limits_not_stale_project_limits`, `_init_repo`, `test_capabilities.py`, `fleet_review.py`, `set_workflow_policy`, `reinstall`, `test_skillmap.py`, `_claude_hook_run`, `_mk_fresh`, `resume_preflight.py`, `test_terminal_tui.py`, `load_projects`, `test_vscode.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `SessionRecord` connect `SessionRecord` to `test_dashboard.py`, `test_terminal_sessions.py`, `dashboard.py`, `main`, `RunRequest`, `ensure_dashboard`, `terminal_sessions.py`, `test_datums.py`, `parallel_deliveries`, `init_project`, `test_registry.py`, `herdr.py`, `._body_text`, `WatchOutcome`, `supervise.py`, `Registry`, `.do_GET`, `test_overhead.py`, `render_control`, `FakeAdapter`, `resolve_deferred`, `process_upgrade_project`, `overhead.py`, `_init_repo`, `test_config_dir_guard.py`, `launch.py`, `test_a_vanished_session_offers_restore_even_though_its_target_ref_survives`, `resume_preflight.py`, `test_terminal_tui.py`, `test_launch_targets.py`, `_resolve_tail_session`, `test_companion.py`, `tmux_runner.py`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `Finding` connect `Finding` to `cli.py`, `test_routines.py`, `main`, `test_backlog.py`, `closure.py`, `backlog.py`, `parallel_deliveries`, `test_doctor_machine.py`, `test_close_commit_rechecks_post_commit_state`, `claude_usage.py`, `test_checkpoint_hook.py`, `_merge_hook_run`, `test_integration.py`, `skills.py`, `cmd_doctor`, `_init_repo`, `test_closure.py`, `refine_prompt`, `codex_usage.py`, `integration.py`, `test_codex_usage.py`, `Path`, `resume_preflight.py`, `_envelope_guard`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `SessionRecord` (e.g. with `AgentSession` and `_DeadProc`) actually correct?**
  _`SessionRecord` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `horus-harness`, `deploy-hosted.sh script`, `failures` to the rest of the system?**
  _1796 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_dashboard.py` be split into smaller, more focused modules?**
  _Cohesion score 0.029050772626931568 - nodes in this community are weakly interconnected._
- **Should `test_terminal_sessions.py` be split into smaller, more focused modules?**
  _Cohesion score 0.042814549791293975 - nodes in this community are weakly interconnected._