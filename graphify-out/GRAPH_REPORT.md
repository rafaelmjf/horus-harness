# Graph Report - .  (2026-08-07)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 6868 nodes · 18288 edges · 239 communities (226 shown, 13 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 336 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9524e96d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- Community 201
- Community 202
- Community 203
- Community 204
- Community 205
- Community 206
- Community 207
- Community 208
- Community 209
- Community 210
- Community 211
- Community 212
- Community 213
- Community 214
- Community 215
- Community 216
- Community 217
- Community 219
- Community 220
- Community 221
- Community 222
- Community 223
- Community 224
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 231
- Community 232
- Community 233
- Community 234
- Community 235
- Community 236
- Community 237
- Community 238
- Community 239
- Community 240

## God Nodes (most connected - your core abstractions)
1. `main()` - 252 edges
2. `_init()` - 143 edges
3. `_home()` - 129 edges
4. `SessionRecord` - 115 edges
5. `init_project()` - 106 edges
6. `TerminalUI` - 106 edges
7. `build_parser()` - 100 edges
8. `UsageSnapshot` - 84 edges
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
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/base.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/registry.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/base.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 3-file cycle: `horus/hosts/__init__.py -> horus/hosts/tmux.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/capabilities.py -> horus/cli.py -> horus/terminal_app.py -> horus/terminal_tui.py -> horus/capabilities.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/hosts/base.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/hosts/base.py -> horus/run_executor.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/hosts/runnerspec.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/launch.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/current.py -> horus/run_executor.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/base.py -> horus/launch.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/base.py -> horus/run_executor.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/hosts/base.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/hosts/runnerspec.py -> horus/registry.py -> horus/hosts/__init__.py`
- 4-file cycle: `horus/hosts/__init__.py -> horus/hosts/herdr.py -> horus/launch.py -> horus/registry.py -> horus/hosts/__init__.py`

## Communities (239 total, 13 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (136): FormattedTextControl, _account_usage(), _active_cards(), _agent_models(), _ambient_alias(), _Attach, _backlog_metrics(), _BodyControl (+128 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (131): Capabilities, Path, Protocol, What a session host is, and what it can be asked to do. A *session host* is the…, Create an attended session, and attend it when ``attach`` is set., Host a one-shot `horus run` worker and return after the runner handoff., Put this terminal on a live session. Error string, or ``None``., Kill a live session. Error string, or ``None``. (+123 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (122): Add a GitHub user/org to the remote catalog. Returns True if newly added., register_github_owner(), gather_untracked_repos(), process_launch(), Return (visible, hidden) untracked repos from the on-disk cache for all…, Handle a Control-tab launch request; return the query string to redirect…, _refresh_forms(), render_remote_catalog() (+114 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (123): Add ``project_path`` to the user config. Returns True if newly added., register_project(), SessionRecord, launch_tmux(), Create a unique detached tmux session, then optionally attach this TTY., Kill host sessions that are provably abandoned; return the killed refs. Safety…, reap_orphans(), The hard limit, pinned. herdr cannot report attached/idle, so its panes are… (+115 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (113): _fmt_reset(), _account_alias_form(), _account_usage(), _add_local_form(), _add_owner_form(), _best_next_text(), _breakdown_html(), _cache_metric() (+105 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (107): The registered path whose directory basename is ``name``, or ``None``., resolve_project_path(), _baseline_recipe(), build_parser(), cmd_attach(), cmd_brainstorm(), cmd_capabilities(), cmd_config() (+99 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (87): _project_overhead_html(), Aggregate-only token overhead card for one project detail view., _add_usage(), baseline_comparison(), _baseline_group(), BaselineComparison, BaselineGroup, BaselineSession (+79 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (90): main(), _capture_run_posture(), _home(), Record the posture the SpawnSpec carried into the fake adapter., cmd_run fails fast — before any worktree or worker is created — on a codex…, End to end: `--resume <horus id>` now resumes instead of dying in 2s with rc=1.…, _stamp_prd(), test_account_command_show_and_set() (+82 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (70): _attach_cockpit(), _cockpit_is_live(), _create_cockpit(), _find_cockpit(), open_in(), `horus tui <host>` — open the Horus cockpit *inside* a session host. `horus…, Restart the TUI inside an existing but dead cockpit pane., The ref of this host's live cockpit, or ``None``. Asked of the host's own… (+62 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (82): Datum, _overlap_peers(), One measured run. Mechanical fields are written automatically at…, Tracked workers on the same account whose effective interval overlaps…, Classify stored start/end usage evidence without estimating future cost. A…, Render-ready per-attempt worker actuals, grouped by native session id., usage_accounting(), worker_breakdown() (+74 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (81): Non-blocking nudge printed to stderr: never affects exit code or stdout., _warn_if_priors_stale(), build_model_rollup(), _build_model_tier_map(), _capability_cell(), _codex_usage_entry(), datums_path(), delegation_matrix_to_dict() (+73 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (45): _Args, Tests for the bundled agent-skills layer (scaffold, version-aware install,…, v8: full facet coverage belongs to the narrative position read-out (section 1);…, v8: the skill names the receipt that is the shape to reproduce. v7 cited…, EVERY skill's projected copies must equal `Skill.content`, not just a named…, The runbook lived in three places (PRD Rules, CLAUDE.md, AGENTS.md) and in none…, PRD Rules and the agent instruction files keep the INVARIANT and point at the…, `_read_hook_stdin` checks isatty() first — a fake without it is not the object… (+37 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (73): capture_delivery_evidence(), _checked_git(), classify_delivery(), _closest_to(), _continuity_closed(), delivery_receipt(), DeliveryEvidence, DeliveryReceipt (+65 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (72): _prune_worktrees(), Reclaim linked worktrees whose branch is merged — report unless --apply.…, _branch_exists(), branch_slug(), ensure_worktree(), _git(), _looks_merged(), primary_checkout() (+64 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (69): force_refresh_remote(), gather_remote_projects(), _hidden_row(), _untracked_card(), _cache_path(), _default_branch(), discover(), drop_registered() (+61 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (68): _body_text(), BranchGroup, build_tree(), build_tree_from_cards(), _card_sort_key(), _convergence_line(), FacetGroup, filter_cards() (+60 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (80): claim(), claim_check(), find_card(), hygiene_findings(), load_cards(), Finding, Backlog-root cards, sorted by filename; archived cards are never loaded., Look up a card by its filename stem, with or without a trailing `.md`. (+72 more)

### Community 17 - "Community 17"
Cohesion: 0.04
Nodes (66): _prd_backlog_now_items(), _prd_dashboard_data(), Title + compact first-sentence detail for each 'Now / next candidates' item,…, Backlog top items/counts, shipped count+latest, and the line-budget meter for a…, _as_date(), _backlog_item_texts(), campaign_prompt(), _consolidate_signals_v3() (+58 more)

### Community 18 - "Community 18"
Cohesion: 0.05
Nodes (66): WatchOutcome, _assert_denied(), _claude_hook_run(), _guard_hook_run(), _merge_hook_run(), _push_hook_run(), parametrize, Integration tests driving commands through the CLI entry point. (+58 more)

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (56): Activity, _armed(), collect(), fired_outcomes(), _ledger_rows(), outcome_glyph(), outcome_summary(), _ran_item() (+48 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (62): cmd_schedule_at(), Register a one-shot `horus run` to fire later on this machine., load_all(), parse_when(), A target time from ``+90m`` / ``+2h`` or an absolute ``2026-07-22 09:00``.…, Every Horus schedule this machine knows about, soonest first. Reconstructed…, _read_directive(), _unquote_exec() (+54 more)

### Community 21 - "Community 21"
Cohesion: 0.07
Nodes (58): CodexAdapter, ``codex_homes`` maps an account alias to its ``CODEX_HOME`` dir for multi-…, _codex_home_with_account_id(), _home(), Path, Tests for the Codex adapter. parse_event fixtures are real JSONL lines captured…, A fake CODEX_HOME containing an auth.json logged in as ``account_id``., Codex and Claude must stay on the same orientation: the percent is USED.… (+50 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (60): consolidate_signals(), Detect what a consolidation pass should route/prune/distill. Read-only., _facet_card(), _mk_horus(), _mk_prd_facets(), _mk_prd_v3(), _mk_session(), _prd_body() (+52 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (57): cmd_proxy(), Manage the optional CLIProxyAPI integration (run GPT models inside Claude…, _await_models(), _claude_config_dirs(), default_state(), disable(), docker_available(), docker_run_command() (+49 more)

### Community 24 - "Community 24"
Cohesion: 0.07
Nodes (58): _all_on_path(), _code_cli_finding(), _console_script_finding(), _dist_requires_python(), _gh_auth_finding(), _hook_command_findings(), _interpreter_floor_finding(), _iter_hook_commands() (+50 more)

### Community 25 - "Community 25"
Cohesion: 0.09
Nodes (55): config_path(), launch_models_for(), load_backlog_fields(), load_launch_defaults(), load_launch_models(), load_launch_profile(), _load_table(), One managed table-of-tables (e.g. ``[launch_profiles.claude]``) as plain dicts,… (+47 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (56): load_project(), process_brainstorm(), Collect everything the dashboard shows for one project (read fresh)., Handle an Ideas/Brainstorm POST; return the query string to redirect with. Same…, render_index(), init_project(), NamedTuple, UpgradeAction (+48 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (43): add_review(), archive_dir(), backlog_dir(), _card_from_path(), _claim_lock(), default_author(), _lines_outside_reviews(), load_shelved_cards() (+35 more)

### Community 28 - "Community 28"
Cohesion: 0.05
Nodes (41): _geom_log(), _Handler, _manifest_json(), _open_terminals(), _page(), process_account_remove(), process_session_dismiss(), _project_prs_html() (+33 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (32): ABC, Enum, AgentAdapter, AgentRun, AgentSession, EventType, PermissionPosture, Popen (+24 more)

### Community 30 - "Community 30"
Cohesion: 0.08
Nodes (45): _claude_home(), config_path(), credentials_path(), current_account(), fetch_usage(), _fmt_reset(), is_over_threshold(), latest_usage() (+37 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (47): integrate(), IntegrationResult, Integrate a change from the working tree according to the workflow policy.…, The /github-onboard handler reports a non-ok integration via ``integ.detail``.…, test_integration_result_exposes_detail_not_error(), _fail(), FakeRunner, _last_git_checkout() (+39 more)

### Community 32 - "Community 32"
Cohesion: 0.09
Nodes (42): ClaudeAdapter, ``config_dirs`` maps an account alias to its ``CLAUDE_CONFIG_DIR`` for multi-…, Argv for an *attended* TUI session (no ``-p``): the user types in it.…, _config_dir_with_email(), _home(), parametrize, Tests for the Claude Code adapter. parse_event fixtures are real lines captured…, The wizard maps alias→dir before the user signs in, so the login is invisible… (+34 more)

### Community 33 - "Community 33"
Cohesion: 0.07
Nodes (45): new_record(), PreparedInteractive, Validated attended-agent command shared by every local terminal surface., access_label(), is_attachable(), Whether Horus has a persistent host it can safely reattach. Asked of the host,…, _created(), _fail() (+37 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (46): launch_interactive(), prepare_interactive(), Path, Open an attended session in its own terminal and register it as running.…, Validate and build an attended launch without choosing its terminal host.…, _descendant_pids(), focus_window_for_pid(), login_argv_env() (+38 more)

### Community 35 - "Community 35"
Cohesion: 0.07
Nodes (45): AccountRef, AccountResolution, _alias_tokens(), known_accounts(), _name_tokens(), One configured isolated account. ``label`` is both how it is displayed and a…, The outcome of naming an account. Exactly one of ``ref`` / ``error`` is set., Every configured isolated account, claude first then codex, alias-sorted. (+37 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (44): Availability, create(), _escape(), _halt_marker(), install_proxy_service(), _keepwarm_service_unit(), _listen_service_unit(), _live_state() (+36 more)

### Community 37 - "Community 37"
Cohesion: 0.10
Nodes (37): BackendError, Handle, LaunchBrief, LaunchFailed, LocalBackend, Exception, The frozen LaunchBackend seam — one interface for launching a session, wherever…, One observed output event from :meth:`LaunchBackend.stream`. Minimal on… (+29 more)

### Community 38 - "Community 38"
Cohesion: 0.10
Nodes (44): await_response(), cleanup(), InputRequest, InputResponse, list_pending(), _load_request(), mark_pushed(), _new_id() (+36 more)

### Community 39 - "Community 39"
Cohesion: 0.08
Nodes (42): BlockResult, check_drift(), DriftReport, normalize_block(), NamedTuple, Managed-block extraction and drift detection for AGENTS.md / CLAUDE.md. The…, Compare the managed blocks in two instruction files., Canonicalize a block for comparison: neutralize the cross-reference line and… (+34 more)

### Community 40 - "Community 40"
Cohesion: 0.10
Nodes (29): _apply_delivery_completion(), _aware_utc_iso(), is_recent(), _jsonl_result(), _legacy_log_result(), _now_iso(), process_alive(), datetime (+21 more)

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (42): escalate(), load_notify_config(), NotifyConfig, Read ``[notify]`` from ``~/.horus/config.toml``. Tolerant like the other owner-…, Best-effort push of one escalation. NEVER raises. ``force=True`` bypasses the…, The ``[notify]`` block, already parsed. ``sink == "none"`` means pull-only., _esc(), _escalate_args() (+34 more)

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (38): _base_root(), bundled_for(), install_skills(), installed_version(), is_horus_repo(), missing_or_stale(), Finding, NamedTuple (+30 more)

### Community 43 - "Community 43"
Cohesion: 0.11
Nodes (39): _append_checkpoints(), boundary_freshness_gate(), _canonical_checkpoint(), _canonical_continuity_paths(), checkpoint_gate(), close_check_healthy(), closure_status(), _enforce_push() (+31 more)

### Community 44 - "Community 44"
Cohesion: 0.09
Nodes (37): EmptyWalkError, format_report(), load_manifest(), load_manifest_file(), Path, RuntimeError, Generic file-tree inventory reconciliation. Three of four Drive-to-Git bulk…, Human-readable report lines for a :class:`ReconcileResult`. (+29 more)

### Community 45 - "Community 45"
Cohesion: 0.13
Nodes (36): cmd_onboard(), DiscoveryResult, Return value of :func:`discover`., onboard_github_project(), OnboardResult, Take an untracked GitHub repo and make it a Horus project in one step. Steps:…, _automerge_responses(), _fail() (+28 more)

### Community 46 - "Community 46"
Cohesion: 0.07
Nodes (37): _check_focus(), check_project(), _check_sessions(), horus_dir(), Path, `.horus/` continuity model and the `horus doctor project` check., current_focus health via the shared PRD-first resolver., Report when repo-local continuity is absent from this machine's fleet. (+29 more)

### Community 47 - "Community 47"
Cohesion: 0.16
Nodes (36): Best-effort usage gate before a run spawns. Returns an exit code to refuse the…, _run_usage_preflight(), The MORE-CONSTRAINING window as ``(percent, reset, label)``. A higher…, UsageSnapshot, _home(), `horus run` usage preflight — warn / refuse / --force / fake-exempt., The gate is not weakened generally — only readings that can't describe now., Claude's pushed statusline readings report no capture time; silently weakening… (+28 more)

### Community 48 - "Community 48"
Cohesion: 0.13
Nodes (36): _commit_env(), _current_branch(), emergency_rescue(), _git(), _in_git_repo(), is_worker_context(), _push_worker_branch(), CompletedProcess (+28 more)

### Community 49 - "Community 49"
Cohesion: 0.11
Nodes (22): AgentEvent, Consume the whole stream and return every event (convenience for tests)., A normalized event. ``raw`` keeps the original parsed payload for callers that…, FakeAdapter, ``script`` overrides the default event stream with raw line payloads (each a…, Tests for the agent-adapter contract, exercised through the FakeAdapter., _run_of(), _spec() (+14 more)

### Community 50 - "Community 50"
Cohesion: 0.09
Nodes (26): _backfill(), capture_usage_snapshot(), _claude_usage_entry(), _now_iso(), Best-effort snapshot of every readable usage surface (claude, codex). One entry…, Seed the store with the fleet's existing known datums (from session-note prose,…, Rows keyed by session id. When the file is absent the backfill is returned as…, Datums whose session id starts with ``prefix`` (git-short-hash style). (+18 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (31): append_event(), follow(), Any, Path, Per-session run logs — the file side of background-worker visibility. ``horus…, Read everything after ``offset`` bytes; return ``(text, new_offset)``. The…, Poll ``path`` from ``offset``, passing new text to ``emit``, until…, Log file for a session. The id is sanitized because it names a file and comes… (+23 more)

### Community 52 - "Community 52"
Cohesion: 0.11
Nodes (34): Two readiness count lines for the cockpit panel, labelled from the single…, readiness_count_summary(), _branch_lines(), _continuity_lines(), delivery_state(), findings(), order_state(), _pr_lines() (+26 more)

### Community 53 - "Community 53"
Cohesion: 0.10
Nodes (35): _apply_unattended_defaults(), Give `--unattended` the safe dispatch posture, then return ``None`` to proceed…, _make(), _posture_args(), Tests for standing dispatch envelopes — the bound an unattended run runs into.…, The worst failure this artifact has: a misnamed account creates an envelope…, `personal`, `claude personal`, `claude-personal` are one account., `personal` is a different rate-limit pool under each agent. (+27 more)

### Community 54 - "Community 54"
Cohesion: 0.10
Nodes (36): _clean_group_by(), load_backlog_group_by(), load_github_owners(), load_remote_control_default(), load_terminal_host(), load_tui_defaults(), load_workspace_root(), _normalize_ignored_repo() (+28 more)

### Community 55 - "Community 55"
Cohesion: 0.13
Nodes (34): build(), _card_record(), _compact(), _curator_manifest(), FleetReview, _gh_content(), _gh_json(), _git() (+26 more)

### Community 56 - "Community 56"
Cohesion: 0.12
Nodes (28): BatchMember, BatchReport, _claim_once(), emit_if_complete(), _escalation(), _leg_line(), _project_name(), Path (+20 more)

### Community 57 - "Community 57"
Cohesion: 0.12
Nodes (32): BrainstormResult, build_prompt(), note_relpath(), _prepare(), Path, Launch a tracked brainstorm session — shared by the CLI and the dashboard. A…, Start the brainstorm as an in-app PTY terminal (headless-safe); return…, Outcome of starting a brainstorm: the launch result plus where the draft lands. (+24 more)

### Community 58 - "Community 58"
Cohesion: 0.13
Nodes (33): block_version(), The block's version marker, or None for blocks written before it existed., Replace the managed block in ``text`` with ``new_block``. If no block is…, replace_block(), _git(), migration_git_safety(), Path, Refresh project-local Horus projections from the installed CLI version. (+25 more)

### Community 59 - "Community 59"
Cohesion: 0.14
Nodes (22): autonomy_block_reason(), Card, is_autonomous_candidate(), order_findings(), The card's raw frontmatter value for ``key``, or "" when it has none., Return the canonical six-queue key for ``card``. A Ready card with…, The single canonical card sort — `horus backlog list`, `--tree`, and the TUI…, All six queues, including empty ones, in canonical execution order. (+14 more)

### Community 60 - "Community 60"
Cohesion: 0.09
Nodes (34): _path_list_param(), process_offboard(), process_upgrade_project(), Apply `upgrade-project` to a registered project only from a clean checkout,…, Return the exact, de-duplicated generated paths recorded by upgrade actions., Offboard a registered project (by index): remove projected artifacts +…, _upgrade_action_paths(), _commit_scaffold() (+26 more)

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (33): A snapshot from the JSON Claude Code passes to a ``statusLine`` command. This…, Persist a pushed reading into the shared cache every consumer already reads.…, Whatever ``horus run`` preflight / the PreToolUse guard last wrote to disk for…, read_cache_only(), record_snapshot(), snapshot_from_claude_statusline(), _isolated_home(), _payload() (+25 more)

### Community 62 - "Community 62"
Cohesion: 0.12
Nodes (22): AccessJWTError, _b64url_decode(), _b64url_decode_int(), _decode_json_segment(), _emsa_pkcs1_v15_encode_sha256(), fetch_jwks(), is_valid_access_jwt_request(), JWKSCache (+14 more)

### Community 63 - "Community 63"
Cohesion: 0.16
Nodes (32): ignore_repo(), load_ignored_repos(), Return the per-machine list of repo full-names (``owner/repo``) to hide., Add a repo full-name to the per-machine ignore list. Returns True if newly…, filter_ignored(), Partition *repos* (``RemoteProject`` or ``UntrackedRepo``, both have…, config.ignore_repo persists the repo to the ignore list., test_config_ignore_repo_persists() (+24 more)

### Community 64 - "Community 64"
Cohesion: 0.14
Nodes (31): extract_block(), Pull the managed block (markers included) out of a file's text., Remove the managed block (markers included) from ``text`` — the inverse of…, remove_block(), _handle_horus_dir(), offboard_project(), OffboardAction, _prune_empty_dirs() (+23 more)

### Community 65 - "Community 65"
Cohesion: 0.11
Nodes (13): PtyHost, PtyTerminal, Path, Spawn an interactive agent under a PTY; return the terminal id. Reuses the…, Force the TUI to repaint its full screen: a double TIOCSWINSZ jiggle (rows-1…, Register viewer `viewer_id`'s fitted size and apply the smallest-wins effective…, Drop a viewer (hidden page or disconnected stream) and re-apply the smallest-…, Kill (if still alive) and *forget* a terminal — no tab renders for it again.… (+5 more)

### Community 66 - "Community 66"
Cohesion: 0.11
Nodes (30): _grep_installed_surface(), CompletedProcess, Exception, Path, ``horus reinstall --verify <marker>`` — the known-good reinstall sequence, plus…, Best-effort: any known Horus systemd service still ACTIVE, which keeps serving…, ``uv cache clean <package>`` then ``uv tool install --force --reinstall…, The reinstall sequence itself (cache clean or tool install) failed. (+22 more)

### Community 67 - "Community 67"
Cohesion: 0.08
Nodes (33): install_keepwarm_service(), keepwarm_active_accounts(), keepwarm_service_active(), keepwarm_service_installed(), keepwarm_unit(), The unit basename for an account's keep-warm service. The alias is sanitised to…, Whether a keep-warm unit for ``account`` exists on disk., Whether ``account``'s keep-warm service is running or coming up. (+25 more)

### Community 68 - "Community 68"
Cohesion: 0.11
Nodes (31): build_state(), _cache_path(), check_update(), fetch_release_info(), installed_disk_version(), is_newer(), Path, _python_floor() (+23 more)

### Community 69 - "Community 69"
Cohesion: 0.11
Nodes (32): cache_dir(), _cache_key(), _cache_path(), Path, A single live usage read for ``agent``+``account``. Never raises., _read_claude(), _read_codex(), _read_live() (+24 more)

### Community 70 - "Community 70"
Cohesion: 0.08
Nodes (33): _bare_origin_and_worker_clone(), _git(), _init_repo(), _patch_gh(), Path, The acting close's user-visible verdict describes the pushed checkpoint., A run under `--worktree` records its `project` as the WORKTREE path; `--card`…, `fleet` and `status` must refresh remotes (fetch) before rendering git state,… (+25 more)

### Community 71 - "Community 71"
Cohesion: 0.15
Nodes (31): cmd_workflow(), Show or update the git-integration workflow policy., load_workflow_policy(), Return the three workflow policy keys, falling back to defaults for any missing…, Update the provided workflow policy keys, persist, and return the new full…, set_workflow_policy(), set_workflow_policy + load_workflow_policy round-trips; render_settings…, POST /settings: config.set_workflow_policy is called with submitted values and… (+23 more)

### Community 72 - "Community 72"
Cohesion: 0.11
Nodes (31): Name remote branches that are not merged into the default branch. Fetch-first…, One-act-acceptance probe (`horus datum close --card`): is the TARGET project's…, target_continuity_staleness(), unmerged_branch_findings(), _branch_lines(), _mk_repo_with_note(), Tests for the git-aware closure routine., The pre-existing line is unchanged for a branch that carries no continuity. (+23 more)

### Community 73 - "Community 73"
Cohesion: 0.11
Nodes (31): DispatchRequest, envelope_path(), envelopes_dir(), ledger_path(), load(), load_all(), datetime, Path (+23 more)

### Community 74 - "Community 74"
Cohesion: 0.12
Nodes (31): apply_filters(), load_fleet_rollup(), load_project_rollup(), Filter each project's cards to `type_filter` (if given) and sort them by…, One project's backlog roll-up, read fresh from disk. Never raises — a project…, Every registered project's roll-up, sorted by name for determinism., _mk_card(), _mk_prd() (+23 more)

### Community 75 - "Community 75"
Cohesion: 0.13
Nodes (29): Path, Wrap an :class:`AgentRun`: register the session once its id is known and record…, track(), _finished_pid(), Tests for the session/process registry., The regression that makes lookup ORDER load-bearing. A failed `--resume…, Never refuse: an agent session Horus never tracked is still resumable., _rec() (+21 more)

### Community 76 - "Community 76"
Cohesion: 0.08
Nodes (32): discover_canonical_docs(), distill_signals(), find_source_log(), infer_signals(), _log_stats(), _name_stopwords(), _placeholder_lanes(), Path (+24 more)

### Community 77 - "Community 77"
Cohesion: 0.09
Nodes (30): _account_launch_form(), _launch_target_options(), _live_count(), _nav(), The Sessions cockpit (revived from the retired Control tab): one drivable sub-…, A compact "N live → Sessions" banner for the project/index pages. The Sessions…, One-click fresh session as this account. Native terminal on a desktop; the in-…, Launch destinations for the "Open in" select. The in-app terminal works… (+22 more)

### Community 78 - "Community 78"
Cohesion: 0.14
Nodes (24): _fake_host(), _FakePty, Tests for the PTY session-host and the cross-platform PTY abstraction., In-memory stand-in for a PtySession: feed output, capture input., Two simultaneously visible viewers must BOTH be able to render the full grid:…, A resize must NOT drop the buffer: it carries the TUI's mode-setting sequences…, The browser reset marker must sit exactly between already-buffered bytes and…, A viewer that vanishes without posting /pty/release (killed tab, dropped… (+16 more)

### Community 79 - "Community 79"
Cohesion: 0.13
Nodes (28): continuity_source(), Document, has_prd(), parse(), parse_file(), prd_path(), NamedTuple, Path (+20 more)

### Community 80 - "Community 80"
Cohesion: 0.16
Nodes (33): _claude_checkpoint_hook_command(), _claude_fetch_check_hook_command(), _claude_guard_hook_command(), _claude_hook_command(), _claude_merge_hook_command(), _claude_skill_usage_hook_command(), _claude_usage_guard_hook_command(), _codex_checkpoint_hook_command() (+25 more)

### Community 81 - "Community 81"
Cohesion: 0.14
Nodes (28): _chat_id_of(), dispatch(), handle_update(), Map one bounded command string onto a deterministic ``horus`` invocation. Pure…, Turn one Telegram update into a :class:`Reply`, or ``None`` if it is ignored…, _bridge_home(), _cfg(), fixture (+20 more)

### Community 82 - "Community 82"
Cohesion: 0.16
Nodes (28): bundled_skill_versions(), _codex_home(), _frontmatter_description(), instance_verdict(), Path, Read-only skill map: every agent skill installed on this machine, across…, Every skill instance visible on this machine (registered projects + ambient…, Per-instance verdict: ``current``/``stale``/``unmarked`` for Horus-bundled… (+20 more)

### Community 83 - "Community 83"
Cohesion: 0.40
Nodes (5): _pair_overlaps(), Heuristic glob-vs-glob overlap: does either pattern match the other read as a…, Pairs of globs (one from `a`, one from `b`) that overlap., surface_overlap(), test_surface_overlap_glob_matching()

### Community 84 - "Community 84"
Cohesion: 0.15
Nodes (30): _closure_sentinel_kind(), cmd_usage_check(), _current_band(), _emit_usage_closure(), Parse the JSON a native app pipes to a hook command (empty when run by hand)., Closure-escalation bands: the configured threshold plus the emergency band., The highest band ``percent`` has crossed, or None while below all bands., Separate sentinels per hook event: the soft UserPromptSubmit advisory must… (+22 more)

### Community 85 - "Community 85"
Cohesion: 0.11
Nodes (29): continuity_off_default(), default_branch(), ``(branch, default)`` when canonical continuity lives on a branch that…, The remote's default branch name, or "" when it cannot be determined. Read from…, _checkpoint_msgs(), _feature_branch_clone(), Fresh committed repo, no remote: tree clean, and the unpushed check is skipped…, `enforce_push: false` in PRD frontmatter skips the unpushed-commits check. (+21 more)

### Community 86 - "Community 86"
Cohesion: 0.12
Nodes (28): accounts_path(), alias_for(), _clean_backlog_fields(), load_account_aliases(), _load_accounts(), User-level Horus config: the list of project paths the dashboard knows about,…, Forget an account from local config: drop its isolated dir mapping(s) and any…, Public alias for a raw account identifier (email/uuid). Returns the configured… (+20 more)

### Community 87 - "Community 87"
Cohesion: 0.11
Nodes (28): Poll ``ref`` (a PR number/URL or a literal commit sha) until its watched checks…, watch(), fake_gh(), _FakeGh, _json_ok(), fixture, Scripted responder keyed by the command's stable prefix (argv[1:3])., Reproduces the reported bug: a squash-merge sha linked to an already merged PR… (+20 more)

### Community 88 - "Community 88"
Cohesion: 0.09
Nodes (28): _api(), Command, emit_pending_requests(), format_request(), _get_updates(), _help_text(), listen(), ListenResult (+20 more)

### Community 89 - "Community 89"
Cohesion: 0.10
Nodes (29): cancel(), halt(), Andon: disarm a pending scheduled dispatch so it cannot fire, but keep its…, Andon inverse: re-arm a halted dispatch once its base is fixed. The exact undo…, Disarm and delete a schedule. ``None`` when no such schedule exists. Only ever…, release(), _create(), A half-written schedule is worse than none: it looks armed and never fires. (+21 more)

### Community 90 - "Community 90"
Cohesion: 0.09
Nodes (32): _absolute_exec(), install_listen_service(), listen_service_active(), listen_service_installed(), Whether the persistent listen unit file exists on disk., Whether the persistent listen service is running or coming up., Resolve the command's executable to an ABSOLUTE path. systemd resolves a bare…, Write and enable the persistent listen service. Refuses a second one.… (+24 more)

### Community 91 - "Community 91"
Cohesion: 0.07
Nodes (54): _account_for_ambient_config_dir(), cmd_statusline(), Render the Claude Code status line from the pushed stdin payload, and record…, The alias whose isolated dir this process is running under, or ``None``. The…, The account label for the status line: the alias when isolated, else the email.…, _statusline_account_label(), _as_pct(), _dget() (+46 more)

### Community 92 - "Community 92"
Cohesion: 0.20
Nodes (27): cmd_account(), config_dir(), default_account_dir(), isolate_account(), load_account_config_dirs(), Map of account alias -> ``CLAUDE_CONFIG_DIR`` for per-account login isolation., The canonical isolated config dir for an account:…, Give ``alias`` its own isolated config dir by default: copy the current login… (+19 more)

### Community 93 - "Community 93"
Cohesion: 0.17
Nodes (21): CacheStatus, _claude_jsonl_files(), _codex_status_from_event(), _event_datetime(), _int(), latest_claude_cache_status(), latest_codex_cache_status(), _mtime_datetime() (+13 more)

### Community 94 - "Community 94"
Cohesion: 0.15
Nodes (27): harvest_checkpoint(), Append new commit messages to an existing optional recovery note and advance…, _msgs(), The closing commit must never be appended into the note it just committed., Hook/skill projections count as continuity: an untracked .claude/settings.json…, A legacy tracked marker must not make the checkpoint hook warn about itself., One universal rule (2026-07-19): the commit is the durable delivery receipt and…, A committed `continuity_granularity` is inert — the axis is gone, so a stale… (+19 more)

### Community 95 - "Community 95"
Cohesion: 0.11
Nodes (27): A violated bound. ``bound`` is the machine-readable name; ``message`` names it…, The wall. ``None`` authorizes the dispatch; a ``Refusal`` names the exact…, Refusal, validate(), An allow-list, so it holds without this module owning a tier ordering., A card with no `tier:` is not implicitly cheap — it is simply not allowed., A card tagged `tier: sonnet` matches an envelope authorizing `medium`., A pre-existing envelope stored with a model-named tier still matches once the… (+19 more)

### Community 96 - "Community 96"
Cohesion: 0.16
Nodes (25): _compact(), gather(), _git_projection(), _pct(), _project_key(), _project_projection(), Any, datetime (+17 more)

### Community 97 - "Community 97"
Cohesion: 0.15
Nodes (25): fast_forward(), plan(), Any, Path, Explicit fast-forward sync — the remedy half of the fetch-first rule. Fetch-…, Decide what to do from a :func:`horus.gitstate.git_state` mapping. Pure…, Run the fast-forward merge. Returns ``(ok, message)``., _git() (+17 more)

### Community 98 - "Community 98"
Cohesion: 0.10
Nodes (24): AccountUsage, all_account_targets(), all_accounts_usage(), _fmt_epoch(), Cached usage snapshot — the shared substrate for the usage-limit survival kit.…, Local ``%Y-%m-%d %H:%M`` for a unix-epoch-seconds reset, which is the shape the…, Public: parse a human-readable reset string into a POSIX timestamp, or ``None``…, Every ``(agent, account_alias)`` to read: each configured alias per agent, or… (+16 more)

### Community 99 - "Community 99"
Cohesion: 0.14
Nodes (24): On Windows, re-exec the current ``horus`` invocation under ``pythonw.exe`` so…, Resolve the platform default for the companion artwork style., One badge line per agent summarizing background worker sessions. ``running``…, relaunch_without_console(), resolve_mascot_style(), worker_status_lines(), Tests for the lightweight Horus companion shell., test_relaunch_without_console_noop_off_windows() (+16 more)

### Community 100 - "Community 100"
Cohesion: 0.11
Nodes (26): _ambient_account_dir(), _as_key(), clear_proxy_env(), load_projects(), prune_projects(), Path, Set the machine-local root where remote projects should be cloned., Remove ``project_path`` from the user config. Returns True if it was present. (+18 more)

### Community 101 - "Community 101"
Cohesion: 0.15
Nodes (22): Finding, findings(), _front_matter(), inspect(), _missing_detail(), _parse_declaration(), NamedTuple, Path (+14 more)

### Community 102 - "Community 102"
Cohesion: 0.12
Nodes (26): freshness_signals(), _key_tokens(), Prompt for resuming a project without front-loading every Horus lane.…, Significant lowercase tokens for fuzzy cross-lane matching., Detect when the dashboard would show *stale* state after a close — read-only.…, resume_prompt(), routines.resume_prompt should not raise for a project with no .horus/ dir — the…, test_resume_prompt_degrades_to_empty_without_horus_dir() (+18 more)

### Community 103 - "Community 103"
Cohesion: 0.15
Nodes (24): _is_horus_file(), NamedTuple, Path, Static VS Code task projection — the one-keypress tier of "launch in VS Code".…, Create `.vscode/tasks.json` when absent; upgrade in place when it's an unedited…, Offboard counterpart: remove tasks.json only if it's an unedited Horus…, remove_tasks(), TaskAction (+16 more)

### Community 104 - "Community 104"
Cohesion: 0.12
Nodes (24): claude_accounts(), Warm up the Claude usage window on demand. Claude's 5-hour usage window only…, Every configured Claude account alias (each an isolated CLAUDE_CONFIG_DIR)., Open one ``claude -p`` turn under ``config_dir`` to start its window., Open one cheap turn per Claude account to start its 5h window. ``accounts``…, _warm_one(), warmup(), WarmupResult (+16 more)

### Community 105 - "Community 105"
Cohesion: 0.16
Nodes (24): migrate_inline_backlog(), Convert `project_root`'s `.horus/PRD.md` inline `## Backlog` items into cards…, `horus backlog migrate` — inline PRD `## Backlog` -> one card per item., The intro sentence before any list item isn't a card — it must not be silently…, A fresh v3 scaffold's PRD (thin pointer from the start, no inline items) is…, Owner decision (2026-07-12): `horus backlog migrate` stays per-project — no…, The original item text (marker stripped) must appear verbatim in its card — no…, test_inline_backlog_item_count_counts_items() (+16 more)

### Community 106 - "Community 106"
Cohesion: 0.15
Nodes (23): cmd_usage_guard(), _emergency_state_save(), _emit_pretooluse_context(), _guard_session_id(), Alias of the account this session runs under (registered alias when known, else…, Inject advisory context on a PreToolUse hook (never a deny)., Perform the worker-aware emergency state-save once per window, then inject…, PreToolUse usage guard: advisory near the limit, emergency state-save at the… (+15 more)

### Community 107 - "Community 107"
Cohesion: 0.15
Nodes (25): _envelope_guard(), _envelope_usage_remaining(), _EnvelopeAuth, An authorized unattended dispatch, carried from the guard to the ledger write., Percent of the account's most-constraining window still available, or ``None``…, Validate an unattended dispatch against its standing envelope. Returns…, _args(), _make_live() (+17 more)

### Community 108 - "Community 108"
Cohesion: 0.21
Nodes (9): b64url_encode(), b64url_int(), jwks_dict(), make_token(), Shared TEST-ONLY RSA fixture for Access gate tests. This keypair was generated…, Independently re-derives the EMSA-PKCS1-v1.5/SHA-256 block and signs with the…, sign_rs256(), valid_payload() (+1 more)

### Community 109 - "Community 109"
Cohesion: 0.13
Nodes (24): _board_ui(), _gt(), _project_with_branch_tree(), A UI parked on the backlog screen of a project with one branch umbrella (one…, A UI parked on the backlog of a project with a priority + readiness spread,…, The one launch axis is WHAT CONTEXT is loaded — resume loads the authored…, test_backlog_group_children_get_tree_connectors_and_priority_dots(), test_backlog_screen_shows_grouped_sections_expanded_by_default() (+16 more)

### Community 110 - "Community 110"
Cohesion: 0.18
Nodes (22): Finding, Report project context and account-global rate limits. Context usage belongs to…, usage_findings(), Tests for read-only Codex rollout usage signals., A token_count event whose lanes declare their own window_minutes., The live 2026-07-17 shape: 5-hour limit removed, weekly lane in `primary`., If Codex restores the 5-hour limit, nothing needs changing here., The card's original complaint: an idle account's percentage was "presented as… (+14 more)

### Community 111 - "Community 111"
Cohesion: 0.09
Nodes (24): gather_projects(), render_control(), render_sessions_card(), Every viewer registers under a vid (smallest-wins geometry) and releases it…, A viewer attaching across a geometry change must reset its screen and request a…, The viewer must handle both gone-session signals: the 'unknown' SSE status…, Compact mode must use a >=16px cell font (iOS zooms the page on focusing an…, One PTY geometry serves all viewers: a viewer must re-claim it when the user… (+16 more)

### Community 112 - "Community 112"
Cohesion: 0.16
Nodes (22): _default_branch(), git_state(), Any, Path, Best-effort git signals for a project directory. Deterministic freshness layer…, One-line text summary (for the CLI peer). Empty string if not a repo.…, Continuity may be stale" hint, or "" when there's nothing to say. Only fires…, Short name of the remote's fetched default branch (e.g. "main"), read from on-… (+14 more)

### Community 113 - "Community 113"
Cohesion: 0.09
Nodes (15): CurrentHost, Path, Run the agent in this terminal; it lives and dies with it., Run an attended agent in this TTY, returning after the agent exits.…, default_target(), The id of the host this process will use. Prefers a persistent host whenever…, _only_available(), Horus running in a tmux pane is NOT a reason to drop to ``current``: the new… (+7 more)

### Community 114 - "Community 114"
Cohesion: 0.10
Nodes (31): cmd_hook_install(), _claude_hooks_dict(), install_claude_checkpoint_hook(), install_claude_fetch_check_hook(), install_claude_guard_hook(), install_claude_merge_hook(), install_claude_skill_usage_hook(), install_claude_usage_guard_hook() (+23 more)

### Community 115 - "Community 115"
Cohesion: 0.18
Nodes (23): Image, autocrop(), clear_dark_edges(), defringe(), floodfill_bg(), _is_checker_bg(), keep_largest_opaque_component(), key_checkerboard_bg() (+15 more)

### Community 116 - "Community 116"
Cohesion: 0.13
Nodes (22): continuity_pr_findings(), _default_branch(), _has_required_checks(), open_horus_prs(), open_prs(), CompletedProcess, Finding, Path (+14 more)

### Community 117 - "Community 117"
Cohesion: 0.40
Nodes (5): skipif, A repo clone on a machine without Horus: the committed hook command must exit 0…, A horus that exists but dies (e.g. dead-on-import) must also be silenced —…, test_guarded_hook_is_silent_noop_when_cli_missing(), test_guarded_hook_is_silent_when_cli_broken()

### Community 118 - "Community 118"
Cohesion: 0.10
Nodes (27): install_claude_usage_hook(), install_codex_guard_hook(), install_codex_merge_hook(), install_codex_usage_hook(), Install/update project-local Codex hooks for usage checks., Install/update local fast feedback; required CI owns the hard merge gate., Install/update the project-local Codex host/worker shell-safety guard., Install/update Claude Code hooks for usage-driven closure. `UserPromptSubmit`… (+19 more)

### Community 119 - "Community 119"
Cohesion: 0.18
Nodes (21): account_limit_homes(), codex_home(), latest_account_usage(), latest_usage(), _matches_project(), Any, Path, Read-only Codex rollout usage signals. Codex desktop/CLI records session events… (+13 more)

### Community 120 - "Community 120"
Cohesion: 0.14
Nodes (21): acquire_singleton_lock(), _app_browser(), _app_window_argv(), dashboard_profile_dir(), _flatpak_app(), mascot_asset_path(), mascot_background_path(), mascot_frame_paths() (+13 more)

### Community 121 - "Community 121"
Cohesion: 0.13
Nodes (20): _dashboard_command(), ensure_dashboard(), log_companion_event(), _log_line(), _open_startup_log(), Command for a fresh dashboard process from this installed CLI., Append handle to ``~/.horus/logs/<name>.log`` (rotated once when oversized), or…, Record a companion lifecycle event/failure (visible even under pythonw). (+12 more)

### Community 122 - "Community 122"
Cohesion: 0.20
Nodes (21): fetch_and_state(), The behind-origin warning for a session start, or "" when there is nothing to…, Fetch (at most once per ``ttl`` seconds per repo), then return the git state.…, warning_line(), _hook_run(), _patch_cache_home(), Session-start fetch-first signal: TTL-cached fetch + behind-origin warning., _state() (+13 more)

### Community 123 - "Community 123"
Cohesion: 0.14
Nodes (20): _cells(), _inline(), _is_table_separator(), plain_text(), A deliberately small, safe Markdown-to-HTML renderer. Covers only what…, Body of a third-level (`### `) markdown section within a section body, until…, Third-level (`### `) heading titles at the top of a markdown section body, in…, Strip markdown emphasis/code markers and collapse whitespace to one line. (+12 more)

### Community 124 - "Community 124"
Cohesion: 0.14
Nodes (21): _context_base(), fetch_check_states(), MergeWatchError, _parse_workflow(), CompletedProcess, Exception, Path, ``horus merge-watch <sha|pr>`` — absorb the wait, not the observation. The… (+13 more)

### Community 125 - "Community 125"
Cohesion: 0.16
Nodes (20): _clone_project(), _clone_repo(), _configure_local_git_identity(), _git_config_value(), GitIdentity, parse_github_target(), Path, Clone/register/start helpers for remote catalog entries. (+12 more)

### Community 126 - "Community 126"
Cohesion: 0.10
Nodes (22): _card_deps(), _close_continuity(), halt_dependents(), _merge_pr(), _pr_state(), Path, Required CI green on the exact head SHA. (True, sha) or (False, why)., The continuity/freshness gate for this PR's diff. (True, "") or (False, why). (+14 more)

### Community 127 - "Community 127"
Cohesion: 0.12
Nodes (20): brainstorm_prompt(), ci_workflow_yaml(), execution_handoff_note(), execution_md(), execution_supervisor_prompt(), features_md(), history_md(), prd_md() (+12 more)

### Community 128 - "Community 128"
Cohesion: 0.19
Nodes (19): Any, Path, Read-only projection-sync check: does each agent surface carry the current…, Per-surface sync summary plus a project-level verdict. Never raises: a broken…, _surface_state(), sync_state(), _verdict(), _fully_synced_project() (+11 more)

### Community 129 - "Community 129"
Cohesion: 0.15
Nodes (19): Counter, counts(), _entries(), log_path(), date, Path, Machine-local record of which bundled skills actually get invoked. `skill-…, (`skill`, count) for every KNOWN skill, most-used first, zeroes included. The… (+11 more)

### Community 130 - "Community 130"
Cohesion: 0.20
Nodes (19): parallel_deliveries(), parallel_delivery_findings(), ParallelSignal, One other writer that a closing/resuming session must not miss., Detect other concurrent writers on this project. Returns (signals, pr_checked);…, Render :func:`parallel_deliveries` as gate findings. Empty (not a false 'all…, _fake_reg(), _gh_stub() (+11 more)

### Community 131 - "Community 131"
Cohesion: 0.29
Nodes (19): _checkpoint_hook(), Stop-hook mode: warn (default) or block (opt-in) when the working tree is dirty…, Finding, NamedTuple, Behaviour of the `horus checkpoint --hook` Stop hook (warn default / block opt-…, Never re-fire when the agent reports the stop was already hook-driven (loop…, Per-turn harvesting went with the granularity knob (2026-07-19): session notes…, _sid() (+11 more)

### Community 132 - "Community 132"
Cohesion: 0.11
Nodes (20): dashboard_identity(), dashboard_is_live(), dashboard_url(), _kill_pid_tree(), _looks_like_horus_dashboard(), _pid_listening_on(), Any, The `/health` identity of a live server, or None (pre-/health build, foreign… (+12 more)

### Community 133 - "Community 133"
Cohesion: 0.18
Nodes (19): await_handoff(), Path, The runner spec: how Horus tells a pane what to become, host-agnostically. Any…, Wait only for the runner's durable PID handoff, never for its agent., ready_path(), runner_dir(), spec_path(), write_payload() (+11 more)

### Community 134 - "Community 134"
Cohesion: 0.16
Nodes (18): _context_from_record(), _escalate(), _escalate_and_halt(), escalate_unresolved(), _find_envelope_for_session(), Unattended verify → merge → close → escalate for a dispatched card. A…, Resolve a session id/prefix (preferred) or a PR ref into a context. A session…, A deferred target that resolved to nothing escalates (andon) and merges… (+10 more)

### Community 135 - "Community 135"
Cohesion: 0.13
Nodes (19): _Cached, cached_usage(), _live_source(), _load_cache(), NamedTuple, A fresh cache entry. ``snapshot`` is ``None`` for a cached negative result…, Best-effort live refresh used when a cached window is known expired. A failed…, Return a cache entry, or ``None`` for a miss/stale/corrupt file. ``ttl=None``… (+11 more)

### Community 136 - "Community 136"
Cohesion: 0.10
Nodes (20): A card without parallel/surface — the pre-existing card shape — still claims., `order:` has a consumer, which is the whole point: the sequence renders with no…, Zero migration: a project that has never been ordered shows no sequence column., The verb is print-only: the one-keypress launch lives in the TUI, and this…, test_backlog_claim_back_compat_no_new_fields(), test_backlog_claim_non_overlapping_proceeds_clean(), test_backlog_claim_warns_and_blocks_on_surface_overlap(), test_backlog_defaults_to_list_and_help_states_default() (+12 more)

### Community 137 - "Community 137"
Cohesion: 0.12
Nodes (17): _horus_own_cli_surface(), ArgumentParser, Recursively walk an argparse parser's subcommand tree. Uses argparse's internal…, _walk_argparse(), _fixture_parser(), ArgumentParser, Tests for the experimental `horus capabilities` fleet capability catalog.…, test_cmd_capabilities_no_project_flag_outside_registered_project_stays_fleet_wide() (+9 more)

### Community 138 - "Community 138"
Cohesion: 0.19
Nodes (19): claude_settings_path(), codex_hooks_path(), file_has_horus_hooks(), HookAction, install_codex_checkpoint_hook(), _load_json(), NamedTuple, Path (+11 more)

### Community 139 - "Community 139"
Cohesion: 0.16
Nodes (18): advisory_line(), parse_stamp(), date, NamedTuple, Path, Release-stamped product-audit staleness (deterministic signal only). The PRD…, Parse ``<version> <YYYY-MM-DD>`` (extra trailing tokens tolerated)., Deterministic release distance for Horus's linear version stream. Sums the… (+10 more)

### Community 140 - "Community 140"
Cohesion: 0.16
Nodes (16): _latest_record_for_branch(), _latest_session_for_card(), The session id of the most-recent envelope-ledger dispatch of ``card``, or…, The most-recent worker session record whose delivery landed on ``branch``., Resolve a DEFERRED target — a card or branch selector — to the worker session…, resolve_deferred(), _Env, A `--card` target resolves at fire time to the newest worker session dispatched… (+8 more)

### Community 141 - "Community 141"
Cohesion: 0.33
Nodes (18): _ask(), _Cancel, _choose_account(), _compact(), _focus(), _home(), _launch(), _line() (+10 more)

### Community 142 - "Community 142"
Cohesion: 0.19
Nodes (17): enforce(), is_at_least(), Path, Structure-version floor: the minimum horus-harness a repo's `.horus/` needs. A…, True when ``installed`` is >= ``floor`` under tuple comparison., The `horus_min_version` recorded in the project's PRD.md, or None when the…, Return an error message when ``installed`` is below the project's recorded…, read_floor() (+9 more)

### Community 143 - "Community 143"
Cohesion: 0.11
Nodes (19): _footer(), _new_ui(), The one action the card asked for: `o` on the backlog pane hands the whole…, `o` must not fire on other screens — the backlog-only bindings are filtered…, A vanished session shaped as `reconcile()` actually leaves it. `target_ref` is…, The session screen must offer Restore for a vanished row. Found by a live probe…, Compact review form: one row per setting showing only its selected value, with…, The `m` (Mission Control) and `t` (Settings) global keys were reachable but… (+11 more)

### Community 144 - "Community 144"
Cohesion: 0.11
Nodes (18): _launch_notice(), _notice(), _path_list_html(), _path_list_value(), _project_action_banner(), Banner shown after a launch POST redirects back to /control., Unified post-redirect banner: project actions (upgrade/offboard) +…, Banner for upgrade/offboard POST redirects (index + project pages). (+10 more)

### Community 145 - "Community 145"
Cohesion: 0.14
Nodes (11): The integrated terminal: a tab + real xterm.js terminal per PTY session. Each…, serve(), _SingleInstanceServer, _terminal_panel(), Handler, main(), _page(), BaseHTTPRequestHandler (+3 more)

### Community 146 - "Community 146"
Cohesion: 0.13
Nodes (11): The local browser session-host: owns PTY viewers for interactive terminals. On…, # NOTE: do NOT clear the scrollback here. It's tempting (bytes written, PtySession, Path, Cross-platform pseudo-terminal (PTY) spawning — the foundation for real TUIs. A…, Spawn ``argv`` attached to a fresh pseudo-terminal of size ``cols``x``rows``., A running process attached to a pseudo-terminal. Byte-oriented + platform-…, Block until output is available; return it. Raise ``EOFError`` at end. (+3 more)

### Community 147 - "Community 147"
Cohesion: 0.24
Nodes (17): Run the unattended acceptance gate for one delivery. See module docstring., supervise(), _ctx(), _no_real_effects(), fixture, Tests for the unattended verify → merge → close → escalate supervisor. The…, All gates green, all actions succeed, no escalation transport, no andon — each…, test_all_green_authorized_and_probe_passes_merges_closes_ships() (+9 more)

### Community 148 - "Community 148"
Cohesion: 0.20
Nodes (18): _drive(), _home_with_project(), A git_state dict with a live upstream, overridable per key., A UI parked on the projects (home) screen for one project whose git_state is…, The real `g` binding must fetch every project (read-only) then re-read…, `g` must never fetch from another screen — the network touch is projects-only., _remote_state(), _select_project_row() (+10 more)

### Community 149 - "Community 149"
Cohesion: 0.24
Nodes (16): _config_dir_conflict_guard(), The CLAUDE_CONFIG_DIR / CODEX_HOME an ``agent`` run under ``account`` will use.…, Advise (never refuse) when a launch shares a live config dir. Claude Code and…, _resolved_config_dir(), Tests for the config-dir concurrency guard in horus.cli. Claude Code and Codex…, Launching on 'personal' while another live session already holds personal's dir., The one live peer on the target dir IS the launching session's own dir., Overseer + another live worker already share the target dir -> still proceeds,… (+8 more)

### Community 150 - "Community 150"
Cohesion: 0.14
Nodes (17): open_dashboard(), Popen, raise_dashboard_window(), Terminate ``process`` and any children it spawned. Windows virtualenv launchers…, Open the dashboard. Owned app-window mode launches a dedicated, trackable…, Best-effort: bring the owned dashboard window to the front. Full on Windows…, Reuse an already-open owned window (raise it) instead of opening a duplicate;…, Close the owned dashboard window when the companion quits, so it doesn't linger… (+9 more)

### Community 151 - "Community 151"
Cohesion: 0.14
Nodes (17): account_login_dir(), load_account_codex_homes(), Standard isolated login directory for ``agent``/``alias`` under ``~/.horus``.…, Map of account alias -> ``CODEX_HOME`` for per-account login isolation., Map an account alias to its ``CODEX_HOME`` (persisted locally)., set_account_codex_home(), process_account_login(), Account-setup wizard: derive an isolated login dir, record the mapping, and… (+9 more)

### Community 152 - "Community 152"
Cohesion: 0.23
Nodes (17): ConfigError, load_dashboard_access(), Load the optional ``[access]`` block that arms dashboard exposed mode. Returns…, Raised when a present-but-malformed config block should fail closed. Tolerant…, _require_str(), _configure_access(), Load the [access] gate — ONLY in exposed mode. Local (loopback) mode never…, _home() (+9 more)

### Community 153 - "Community 153"
Cohesion: 0.22
Nodes (16): Action, _confirm(), _ensure_backlog_dir(), _ensure_ci_workflow(), _ensure_gitignore(), _ensure_instruction_file(), NamedTuple, Path (+8 more)

### Community 154 - "Community 154"
Cohesion: 0.21
Nodes (13): Escalation, _post_json(), Machine-local push channel so an unattended supervisor can reach the owner.…, Human summary for ``horus notify show`` — the token is always redacted., The essentials an owner needs to act, transport-agnostic., _redact(), render_config(), _send_hermes() (+5 more)

### Community 155 - "Community 155"
Cohesion: 0.23
Nodes (14): next_step(), parse_tasks(), Progress, NamedTuple, Parse the roadmap checklist into tasks, progress, and the next actionable step.…, First in-progress task, else first open task, else None (all done/empty)., Task, Tests for roadmap task parsing, progress, and next-step derivation. (+6 more)

### Community 156 - "Community 156"
Cohesion: 0.14
Nodes (16): build_project_catalog(), Capability, cli_surface_for(), CliCommand, _mention_pattern(), Whole-token match for a command phrase: forbids an adjacent word/hyphen char so…, Build one project's catalog entry from its already-read source text. With no…, One Shipped-ledger entry, plus any cheap cross-reference found in it. (+8 more)

### Community 157 - "Community 157"
Cohesion: 0.15
Nodes (16): default_out_path(), generate_project(), load_project_catalog(), project_out_path(), project_path_for_cwd(), Path, The already-read ``.horus/PRD.md`` text for ``root``, or ``None``., Build ONE project's live catalog straight from its ``.horus/`` sources. Unlike… (+8 more)

### Community 158 - "Community 158"
Cohesion: 0.15
Nodes (16): commit_continuity(), continuity_dirty(), continuity_dirty_paths(), Fetch, then count upstream commits not present locally that touch continuity…, Whether any continuity file has uncommitted changes (staged or not)., Changed continuity pathspec entries, including tracked deletions. The porcelain…, Stage and commit the continuity files. Returns (did_commit, detail). With…, remote_lane_divergence() (+8 more)

### Community 159 - "Community 159"
Cohesion: 0.19
Nodes (16): DashboardProcess, ensure_dashboard_for_open(), NamedTuple, Replace a dead child owned by ``horus app``; adopted servers stay untouched., Return a live dashboard before opening the browser. The companion can outlive…, Terminate a dashboard server *this* companion spawned, so it doesn't outlive…, respawn_dashboard_if_needed(), stop_dashboard() (+8 more)

### Community 160 - "Community 160"
Cohesion: 0.14
Nodes (16): _account_add_form(), _account_remove_form(), _accounts_panel(), _accounts_strip(), Small donut showing a usage percent; gray when unknown (offline/no token)., Sticky overview accounts rail: usage rings, alias editing, add/remove, launch., Forget an account mapping; login dir on disk is left intact., _ring() (+8 more)

### Community 161 - "Community 161"
Cohesion: 0.18
Nodes (14): overall_state(), Contexts the base branch's protection requires, or ``None`` when unknowable (no…, ``"pending" | "success" | "failure"`` across the watched set (required contexts…, required_contexts(), `horus merge-watch <sha|pr>` — poll required checks on the exact sha until they…, test_overall_state_failure_wins_over_pending(), test_overall_state_falls_back_to_all_checks_when_required_unknown(), test_overall_state_ignores_non_required_checks() (+6 more)

### Community 162 - "Community 162"
Cohesion: 0.28
Nodes (15): _arm_exposed(), Dashboard exposed mode: [access] config loading + fail-closed handler gate.…, _run(), _same_origin(), test_get_allowed_through_with_valid_auth(), test_get_denied_without_auth_in_exposed_mode(), test_health_public_in_exposed_mode(), test_local_mode_unchanged_when_no_access_block() (+7 more)

### Community 163 - "Community 163"
Cohesion: 0.19
Nodes (16): _plain(), _project_with_cards(), Universal fallback: a project whose default (facet) lens yields no real…, A UI parked on the backlog screen of a project with two cards: one carrying the…, test_backlog_rows_are_unchanged_when_no_fields_are_configured(), test_backlog_rows_render_configured_fields_inline_in_pick_order(), test_backlog_screen_reports_all_six_readiness_queues(), test_backlog_screen_with_no_facets_or_branches_falls_back_to_flat() (+8 more)

### Community 164 - "Community 164"
Cohesion: 0.24
Nodes (14): _catalog_to_dict(), generate(), load_catalog(), ProjectCatalog, EXPERIMENTAL — `horus capabilities`: a read-only fleet capability catalog.…, Read the registry into per-project catalogs. Read-only; skips paths whose…, Deterministic JSON text: stable key/list ordering, no timestamps — two runs…, Build the fleet-wide catalog and write it to ``out_path``. Returns the rendered… (+6 more)

### Community 165 - "Community 165"
Cohesion: 0.26
Nodes (14): _account_isolation_findings(), cmd_doctor(), Finding, Advisory checks that every known account has its own isolated config dir. Two…, _accounts(), Doctor advisory checks: flag non-isolated/shared accounts and outdated managed…, test_account_findings_empty_without_accounts(), test_account_findings_flag_shared_dir() (+6 more)

### Community 166 - "Community 166"
Cohesion: 0.17
Nodes (12): create(), Envelope, EnvelopeError, date, Exception, Create and persist a bounded envelope. Raises ``EnvelopeError`` on bad bounds.…, A malformed envelope request (bad name, bad bounds, already exists)., One owner-created standing authorization. Bounds only — never a selector. (+4 more)

### Community 167 - "Community 167"
Cohesion: 0.23
Nodes (14): _cache_path(), _fetch(), last_fetch(), _load_cache(), note_fetch(), Any, Path, Session-start fetch-first signal. The fetch-first rule lived only in… (+6 more)

### Community 168 - "Community 168"
Cohesion: 0.20
Nodes (13): _default_warm(), keep_warm(), KeepWarmResult, next_delay(), Keep a Claude account's 5-hour usage window continuously warm. ``horus warmup``…, Seconds to sleep before the next warmup of ``account``. Primary: ``warmed_at +…, Warm ``account`` now, then re-warm just after each 5h reset, indefinitely.…, The standing keep-warm loop (`horus warmup --keep`). Cadence logic and the loop… (+5 more)

### Community 169 - "Community 169"
Cohesion: 0.22
Nodes (15): _is_open_state(), Permissive by default (``True``) — only a positively-reported non-"open" PR…, Resolve ``<sha|pr>`` to the exact commit + owning repo (+ PR number/base when…, resolve_target(), Path, test_resolve_target_looks_up_owning_pr_for_a_sha(), test_resolve_target_pr_number_defaults_open_when_state_missing(), test_resolve_target_pr_number_marks_merged_pr_as_not_open() (+7 more)

### Community 170 - "Community 170"
Cohesion: 0.22
Nodes (13): _card_text(), _infer_type(), _Item, _item_title(), MigrateAction, _priority_for_heading(), NamedTuple, `horus backlog migrate` — convert an inline PRD `## Backlog` section (structure… (+5 more)

### Community 171 - "Community 171"
Cohesion: 0.15
Nodes (14): _bold_paragraph_items(), Body of a top-level ``## <heading>`` section, until the next ``## `` heading.…, Text of each *top-level* list item in a section (bullets or numbers). Falls…, Fallback item extractor for ``**Title:** …`` paragraph-style entries. A new…, One-line-per-capability entries from a PRD's ``## Shipped`` section., _section(), shipped_lines(), _top_level_items() (+6 more)

### Community 173 - "Community 173"
Cohesion: 0.20
Nodes (14): direct_push_violations(), Paths in the unpushed commits that may NOT reach the default branch directly.…, _clone_with_origin(), One clone of a bare origin, with origin/HEAD set so default_branch resolves., The failure this closes: a hand-rolled `git add -A && git push` on the default…, Only the default branch is exempt-by-convention, so only it needs the guard; a…, In a repo that GENERATES the projections, they must travel with their source…, A consumer project has no in-repo generator, so its projections are ordinary… (+6 more)

### Community 174 - "Community 174"
Cohesion: 0.20
Nodes (13): classify_exit(), _effective_interval(), _iso_datetime(), datetime, Map an adapter run status to a mechanical exit condition. Usage-death is…, ``(effective_end, exit, returncode)`` from POSITIVE terminal registry/ run-…, Whether the registry independently confirms this session is still live (not…, ``(start, effective_end, bounded)`` for one datum. ``bounded`` is True when… (+5 more)

### Community 175 - "Community 175"
Cohesion: 0.21
Nodes (14): band_sentinel_fired(), closure_already_fired(), mark_band_sentinel(), mark_closure_fired(), True if the ``kind`` sentinel fired for this session within the re-arm window.…, True if closure fired for this session within the re-arm window., True when ``kind`` already fired for this session at ``band`` or higher in the…, sentinel_fired() (+6 more)

### Community 177 - "Community 177"
Cohesion: 0.15
Nodes (12): _machine_ui(), A UI with every machine-state read stubbed, for the Mission Control / Settings…, _StubEnv, test_mission_all_dead_envelopes_reads_as_no_live_envelope(), test_mission_and_settings_back_returns_to_projects(), test_mission_marks_revoked_and_expired_envelopes_not_live(), test_mission_pane_is_read_only_and_shows_readiness_and_activity(), test_settings_notify_test_uses_escalate_force() (+4 more)

### Community 178 - "Community 178"
Cohesion: 0.19
Nodes (13): pr_only_contexts(), Context-base names that ONLY ever trigger on a ``pull_request`` event, read…, _git_workflow_responder(), Handlers for ``git ls-tree``/``git show`` simulating the workflow files as they…, A confidently PR-only workflow (``continuity.yml``) must NOT drop its context…, Same all-or-nothing guarantee when a workflow is readable but its…, test_pr_only_contexts_across_workflows_matches_the_repo_scenario(), test_pr_only_contexts_all_or_nothing_when_one_of_several_workflows_is_unparseable() (+5 more)

### Community 179 - "Community 179"
Cohesion: 0.36
Nodes (5): authorized(), The composed exposed-mode gate: owner header AND a valid Access JWT. Owner…, DashboardAccess, The dashboard's exposed-mode gate config: owner identity + Access params., AuthorizedTests

### Community 180 - "Community 180"
Cohesion: 0.17
Nodes (12): cmd_ask(), cmd_notify_listen(), cmd_warmup(), _cmd_warmup_keep(), _parse_listen_duration(), Parse ``8h`` / ``30m`` / ``90s`` / ``120`` into seconds; None ⇒ run until…, Long-poll the telegram sink for bounded steering commands from the owner. The…, Ask the owner a bounded question and block until answered (or timeout). The… (+4 more)

### Community 181 - "Community 181"
Cohesion: 0.26
Nodes (11): _card_to_dict(), _format_card(), _priority_sort_key(), ProjectRollup, `horus fleet --backlog` — deterministic, read-only fleet-wide backlog roll-up.…, Deterministic JSON text: stable key/list ordering, no timestamps., Human-readable grouped roll-up: one section per project, cards sorted within it…, render_json() (+3 more)

### Community 182 - "Community 182"
Cohesion: 0.20
Nodes (12): Cache-only remote Horus project listing: (visible, ignored, error notes). Reads…, _remote_projects(), _isolated_home(), _project_with_skill_drift(), A UI on the skills screen of a project where claude skills are installed with…, test_agent_models_prefers_config_over_adapter_default(), test_project_screen_offers_skills_entry(), test_remote_projects_drops_already_registered() (+4 more)

### Community 183 - "Community 183"
Cohesion: 0.17
Nodes (12): The 2026-08-03 fabric-build finding: a green close on a pushed-but-unmerged…, A merely-open sibling PR (item 5's parallel-delivery signal) must not flip…, A genuine freshness failure alongside a parallel signal must still flip to…, test_close_check_gates_on_freshness(), test_close_check_keeps_unclassified_cards_advisory(), test_close_check_names_sibling_pr_but_stays_fresh(), test_close_check_stays_stale_with_parallel_signal_and_real_freshness_failure(), test_close_check_still_fails_for_delivery_not_covered_by_continuity() (+4 more)

### Community 184 - "Community 184"
Cohesion: 0.22
Nodes (8): _parse_iso(), datetime, Path, The thread id Codex minted for an interactive session, read back afterwards.…, Confirm the CODEX_HOME for ``account`` is logged in as that account. Codex's…, The ``session_meta`` payload from a rollout file's first line, or ``None``.…, Parse a rollout timestamp into an aware UTC datetime, or ``None``. Rollout…, _rollout_meta()

### Community 185 - "Community 185"
Cohesion: 0.18
Nodes (8): LaunchBackend, Protocol, The frozen seam. A backend serves one or more targets; callers hold only…, The current lifecycle state of the session ``handle`` refers to., Yield the session's output events (where the backend can observe them)., End the session ``handle`` refers to; idempotent for an already-dead session., A backend-neutral lifecycle snapshot returned by :meth:`LaunchBackend.status`., SessionStatus

### Community 186 - "Community 186"
Cohesion: 0.29
Nodes (7): cmd_guard_host(), _guard_host_hook(), _is_host_restart_command(), _is_worker_global_state_delete(), True when a hosted session's Bash command would kill/restart its own host.…, Match a narrow destructive command aimed at user-global agent state., PreToolUse gate for hosted-session and tracked-worker shell footguns. Hosted…

### Community 187 - "Community 187"
Cohesion: 0.35
Nodes (10): Open a watcher terminal running ``horus tail <session_id>`` (--watch). Best-…, _spawn_watcher(), _handoff(), main(), Path, Private child entry point for a Horus-managed tmux pane., Record the durable pane-runner PID before starting any agent process., _run_interactive() (+2 more)

### Community 188 - "Community 188"
Cohesion: 0.18
Nodes (11): canonical_model_name(), normalize_tier(), Normalize a captured model to its canonical versioned name. Prefers…, Map a card/envelope ``tier:`` value to its vendor-neutral tier. A neutral value…, The alias map is derived from the rendered equivalence table — every model…, test_canonical_model_name_falls_back_to_alias_map(), test_canonical_model_name_joins_full_provider_selector_launches_to_the_same_series(), test_canonical_model_name_passes_through_unrecognized() (+3 more)

### Community 189 - "Community 189"
Cohesion: 0.24
Nodes (10): isolate_ambient_agent_env(), isolate_home(), isolate_session_host_sockets(), fixture, Suite-wide isolation from the ambient agent environment. Tests fake ``HOME``…, Point every terminal host's DEFAULT server at a throwaway socket. This is the…, Unset the per-account agent config-dir vars for every test. Hardening, not a…, Give every test a private ``HOME``, so none can reach the real ``~/.horus``.… (+2 more)

### Community 190 - "Community 190"
Cohesion: 0.40
Nodes (10): CompletedProcess, Path, Tests for the hosted deployment's install and runtime version gates., _run_deploy(), test_deploy_accepts_exact_running_target(), test_deploy_refuses_restart_when_pinned_install_never_succeeds(), test_deploy_rejects_running_version_mismatch(), test_deploy_requires_install_success_when_target_is_unresolved() (+2 more)

### Community 191 - "Community 191"
Cohesion: 0.19
Nodes (14): load_active_cards(), load_archived_cards(), Only active backlog-root cards; terminal lifecycle states stay hidden., Every closed card in `backlog/archive/` — delivered or killed — newest first.…, _mk_archived(), Path, Shelving is not closing, and not deleting. `deferred` failed as the set-aside…, The archive is the CLOSED ledger, not the delivery ledger. `ship` moves in work… (+6 more)

### Community 192 - "Community 192"
Cohesion: 0.27
Nodes (10): harvest_target(), _latest_session_note(), Return the newest optional recovery note without creating one., The recovery note the checkpoint harvest may append to, and why not when None.…, _note(), test_harvest_accepts_a_note_with_no_status(), test_harvest_accepts_an_open_note(), test_harvest_refuses_a_note_that_declares_itself_finished() (+2 more)

### Community 193 - "Community 193"
Cohesion: 0.22
Nodes (9): account_dirs(), get_adapter(), The adapter's alias -> isolated-config-dir map, whatever it calls it. Claude…, Return an adapter instance by name. Raises ``KeyError`` if unknown. ``fake`` is…, test_get_adapter_resolves_fake_and_rejects_unknown(), test_get_adapter_resolves_claude(), test_account_dirs_resolves_codex_homes_not_just_claude_config_dirs(), test_get_adapter_resolves_codex() (+1 more)

### Community 194 - "Community 194"
Cohesion: 0.22
Nodes (9): _find_backlog_section(), inline_backlog_item_count(), Path, (section_start_index, section_end_index) of the `## Backlog` section's body…, Best-effort count of inline `## Backlog` list items in `.horus/PRD.md`, for…, backlog_pointer_block(), The PRD's `## Backlog` section body once cards are the fleet standard: a thin…, test_inline_backlog_item_count_none_when_no_prd() (+1 more)

### Community 195 - "Community 195"
Cohesion: 0.22
Nodes (9): _footer_html(), Inner body for the read-only /skills page: every skill installed on this…, Return the inner body HTML for the /settings page (workflow policy editor)., render_settings(), render_skill_map(), render_settings renders three <select> controls with the current policy value…, render_settings(saved=True) includes the success banner; saved=False does not., test_render_settings_saved_banner() (+1 more)

### Community 196 - "Community 196"
Cohesion: 0.31
Nodes (5): CDP, check(), failures, main(), wsConnect()

### Community 197 - "Community 197"
Cohesion: 0.32
Nodes (8): cmd_envelope_create(), cmd_envelope_list(), cmd_envelope_show(), _envelope_state(), date, Create a bounded standing envelope. Bad bounds refuse at create rather than…, The floor is opt-in, so say which regime this envelope is actually in — the…, _usage_floor_label()

### Community 198 - "Community 198"
Cohesion: 0.29
Nodes (6): NamedTuple, RateWindow, One rate-limit lane as Codex reported it, able to name itself., What this window actually is, derived from its own declared length., This report's (fast, slow) lanes, classified by their own declared length…, test_label_names_windows_from_their_length()

### Community 199 - "Community 199"
Cohesion: 0.25
Nodes (8): display_status(), is_deliberate_close(), Whether this row is the owner ending the session, not a failure. Reads the pair…, The status to SHOW, which is not always the status stored. Every surface that…, Historical rows say `failed`; only the reason distinguishes them. Every row…, `is_deliberate_close` shipped in #489 with no production caller. The predicate…, test_display_status_gives_the_predicate_a_consumer(), test_is_deliberate_close_reads_the_pair_so_old_rows_need_no_backfill()

### Community 200 - "Community 200"
Cohesion: 0.25
Nodes (8): Whether a TUI launch should open its own terminal window (True) or take over…, resolve_window_launch(), Observed in a real herdr cockpit: launching popped a native OS window running a…, test_new_window_is_vetoed_inside_a_host_because_the_host_is_the_window_manager(), test_resolve_window_launch_falls_back_over_ssh(), test_resolve_window_launch_falls_back_without_display(), test_resolve_window_launch_new_window_on_desktop(), test_resolve_window_launch_takeover_is_always_false()

### Community 201 - "Community 201"
Cohesion: 0.32
Nodes (8): Clone (if needed) + register + refresh projections for a selected remote…, _RemoteStart, _start_remote(), _remote_project(), test_activate_remote_project_exits_with_remote_start(), test_projects_screen_lists_remote_items_and_renders_distinct_states(), test_start_remote_reports_failure_without_raising(), test_start_remote_reuses_start_github_project_and_reports_clone()

### Community 202 - "Community 202"
Cohesion: 0.43
Nodes (3): is_owner_request(), True iff the Access owner-identity header matches ``owner_email``., OwnerHeaderTests

### Community 203 - "Community 203"
Cohesion: 0.33
Nodes (7): cmd_run(), _codex_delivery_posture_error(), Spawn (or resume) an agent session through an adapter, tracked in the registry.…, Arm-time mirror of the codex delivery-posture guard for `horus schedule run`.…, Error string if a codex dispatch demands a git/PR delivery it structurally…, _resolve_run_posture(), _scheduled_run_delivery_error()

### Community 204 - "Community 204"
Cohesion: 0.43
Nodes (7): cmd_supervise(), Unattended verify → merge → close → escalate for a dispatched card. Resolves…, _supervise_ns(), test_cmd_supervise_deferred_no_match_escalates(), test_cmd_supervise_deferred_resolves_then_supervises(), test_cmd_supervise_refuses_more_than_one_selector(), test_cmd_supervise_refuses_no_selector()

### Community 205 - "Community 205"
Cohesion: 0.29
Nodes (7): _await_active(), _journal_tail(), Best-effort last few journal lines for ``unit``, for the failure message., Poll ``systemctl is-active <unit>`` until it reports ``active``. Raises…, A unit that never leaves 'activating' (rather than failing outright) must still…, test_await_active_returns_once_active(), test_await_active_times_out_when_stuck_activating()

### Community 206 - "Community 206"
Cohesion: 0.29
Nodes (7): _card(), Path, The TUI must not re-derive which statuses are inactive. Three copies of this…, Fresh means fresh: nothing injected, so the owner types into an empty session.…, test_active_card_filter_has_no_status_list_of_its_own(), test_capital_y_syncs_every_clean_behind_project(), test_fresh_launch_prompt_is_genuinely_empty()

### Community 207 - "Community 207"
Cohesion: 0.33
Nodes (6): A short one-line "what IS it" frame from a ``## Vision`` section: its lead…, vision_lead(), first_sentence(), The first sentence of ``text``, or a hard cutoff at ``max_len`` — always ending…, test_vision_lead_extracts_lead_sentence_not_whole_section(), test_vision_lead_none_when_section_absent()

### Community 208 - "Community 208"
Cohesion: 0.33
Nodes (6): _overseer_collision(), The alias -> isolated-dir mapping for ``target`` and its env-var name., True when the requested isolated account is the same underlying account this…, Explicit account-scoped check: resolve the isolated mapping for the alias…, _usage_account_mapping(), _usage_check_account()

### Community 209 - "Community 209"
Cohesion: 0.40
Nodes (6): feature_counts(), feature_items(), Capability row counts per section of features.md., Capability names per section of features.md: shipped / in_progress / planned., test_feature_counts_by_section(), test_feature_items_groups_names_by_section()

### Community 210 - "Community 210"
Cohesion: 0.33
Nodes (6): _mouse_event(), MouseEvent, test_clicking_a_card_in_the_wide_board_opens_that_card(), test_clicking_a_project_in_the_wide_grid_opens_it(), test_left_click_selects_and_activates_the_clicked_row(), test_only_left_button_release_activates_the_launch_row()

### Community 211 - "Community 211"
Cohesion: 0.09
Nodes (27): _close_merge_hook(), cmd_app(), cmd_checkpoint(), cmd_close(), cmd_consolidate(), cmd_distill_history(), cmd_infer(), cmd_offboard() (+19 more)

### Community 212 - "Community 212"
Cohesion: 0.40
Nodes (5): current_account(), Return the ``account_id`` from ``$CODEX_HOME/auth.json``, or ``None`` if…, test_current_account_none_on_malformed_or_no_id(), test_current_account_none_when_file_missing(), test_current_account_reads_account_id()

### Community 213 - "Community 213"
Cohesion: 0.60
Nodes (4): Tests for prompt-cache freshness estimates., test_claude_cache_status_reads_cache_creation_and_read(), test_codex_cache_status_reads_latest_project_turn(), _write_jsonl()

### Community 214 - "Community 214"
Cohesion: 0.40
Nodes (5): Rate limits are account-global; project context remains project-scoped., test_codex_userpromptsubmit_hook_defers_to_user(), test_usage_check_cli_warns_and_codex_stop_hook_blocks_with_json(), test_usage_check_uses_fresh_account_limits_not_stale_project_limits(), _write_codex_rollout()

### Community 215 - "Community 215"
Cohesion: 0.40
Nodes (3): _Proc, Fails safe: sha not present locally (e.g. shallow clone) yields no evidence, so…, test_pr_only_contexts_empty_when_ls_tree_unavailable()

### Community 216 - "Community 216"
Cohesion: 0.40
Nodes (3): Integration: a real PTY echoes output (platform-native ConPTY / stdlib pty)., test_close_kills_and_forgets_terminal(), test_spawn_pty_runs_a_real_command()

### Community 217 - "Community 217"
Cohesion: 0.50
Nodes (3): _provider_selector_for(), Reject a known calibration-only label before it reaches ``claude``. Static and…, Best-effort full-selector spelling for a calibration-only key, for the…

### Community 219 - "Community 219"
Cohesion: 0.50
Nodes (4): _describe_run(), The value passed to ``flag`` in a pass-through `horus run` arg list, or None., A human label for a scheduled dispatch: the card if there is one, else the…, _run_arg_value()

### Community 220 - "Community 220"
Cohesion: 0.50
Nodes (4): How the companion opens the dashboard: ``"owned"`` (dedicated app window we…, resolve_open_mode(), test_resolve_open_mode_defaults_owned_on_windows_tab_elsewhere(), test_resolve_open_mode_flags_win()

### Community 221 - "Community 221"
Cohesion: 0.50
Nodes (4): gather_sessions(), Reconcile the registry against live PIDs, then return records newest-first., test_gather_sessions_reconciles(), test_render_index_has_accounts_strip_and_no_control()

### Community 223 - "Community 223"
Cohesion: 0.50
Nodes (4): _full_capacity(), _isolated_home(), fixture, Envelopes live under ~/.horus; never touch the real one from a test.

### Community 225 - "Community 225"
Cohesion: 0.67
Nodes (3): _age_phrase(), How old a reading is, in words — a usage number without its age invites the…, test_age_phrase_reads_naturally()

### Community 226 - "Community 226"
Cohesion: 0.67
Nodes (3): _parse_frontmatter_date(), date, Coerce a frontmatter `last_updated`/`date` value to a date, tolerantly — a…

### Community 227 - "Community 227"
Cohesion: 0.67
Nodes (3): _offload_control(), Offload a project: two explicit choices — *Keep files* (remove the projected…, test_offload_control_offers_keep_and_remove_completely()

### Community 229 - "Community 229"
Cohesion: 0.67
Nodes (3): _isolate_dashboard_access_globals(), fixture, Snapshot and restore the exposed-mode gate globals around every test.…

### Community 230 - "Community 230"
Cohesion: 0.67
Nodes (3): _isolated_config(), fixture, Point config.toml at a throwaway file so no test reads the real ~/.horus.

### Community 231 - "Community 231"
Cohesion: 0.67
Nodes (3): fixture, Unit files in a temp dir; systemctl stubbed to succeed and record calls., units()

## Knowledge Gaps
- **3 isolated node(s):** `horus-harness`, `deploy-hosted.sh script`, `failures`
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TerminalUI` connect `Community 0` to `Community 1`, `Community 3`, `Community 163`, `Community 109`, `Community 206`, `Community 143`, `Community 148`, `Community 182`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `SessionRecord` connect `Community 3` to `Community 0`, `Community 1`, `Community 130`, `Community 2`, `Community 133`, `Community 134`, `Community 7`, `Community 8`, `Community 9`, `Community 6`, `Community 140`, `Community 143`, `Community 18`, `Community 149`, `Community 26`, `Community 28`, `Community 29`, `Community 33`, `Community 34`, `Community 40`, `Community 177`, `Community 187`, `Community 60`, `Community 70`, `Community 75`, `Community 77`, `Community 93`, `Community 221`, `Community 96`, `Community 99`, `Community 109`, `Community 111`, `Community 113`, `Community 121`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `PtySession` connect `Community 146` to `Community 176`, `Community 65`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `SessionRecord` (e.g. with `AgentSession` and `_DeadProc`) actually correct?**
  _`SessionRecord` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `horus-harness`, `deploy-hosted.sh script`, `failures` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.019655660147295518 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.02332616829870233 - nodes in this community are weakly interconnected._