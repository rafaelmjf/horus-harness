"""Tests for the bundled agent-skills layer (scaffold, version-aware install, doctor)."""

from pathlib import Path

from horus import initialize, skills


def test_bundled_skills_have_version_markers():
    assert skills.SKILLS  # at least one shipped skill
    for s in skills.SKILLS:
        assert s.content.startswith("---")  # YAML frontmatter
        assert "name:" in s.content and "description:" in s.content
        assert skills.installed_version(s.content) == s.version


def test_write_skill_create_then_exists(tmp_path):
    s = skills.SKILLS[0]
    assert skills.write_skill(s, tmp_path).status == "created"
    assert skills.skill_path(s, tmp_path).is_file()
    assert skills.write_skill(s, tmp_path).status == "exists"


def test_write_codex_skill_uses_agents_directory(tmp_path):
    s = skills.SKILLS[0]
    assert skills.write_skill(s, tmp_path, target="codex").status == "created"
    assert (tmp_path / ".agents" / "skills" / s.name / "SKILL.md").is_file()
    assert not (tmp_path / ".claude").exists()


def test_write_skill_upgrades_older_version(tmp_path):
    s = skills.SKILLS[0]
    path = skills.skill_path(s, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("<!-- horus-skill-version: 0 -->\nstale body\n", encoding="utf-8")
    assert skills.write_skill(s, tmp_path).status == "updated"
    assert skills.installed_version(path.read_text(encoding="utf-8")) == s.version


def test_write_skill_skips_unversioned_without_force(tmp_path):
    s = skills.SKILLS[0]
    path = skills.skill_path(s, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("hand-written, no marker\n", encoding="utf-8")
    assert skills.write_skill(s, tmp_path).status == "skipped"
    assert skills.write_skill(s, tmp_path, force=True).status == "updated"


def test_expected_skills_registered():
    names = {s.name for s in skills.SKILLS}
    assert {"horus-consolidate", "horus-distill-history", "horus-infer", "horus-execution"} <= names


def test_delegation_decision_skills_registered():
    # Slice 2: the shared rubric + the two thin consumer skills.
    names = {s.name for s in skills.SKILLS}
    assert {"delegation-rubric", "execution-decision", "dispatch-decision"} <= names


def test_market_scan_skill_registered_and_outward():
    market = next(s for s in skills.SKILLS if s.name == "market-scan")
    assert market.version == 5
    # outward twin of product-audit: composes deep-research, advisory, dated receipt.
    assert "deep-research" in market.content
    assert ".horus/research/" in market.content
    assert "JTBD" in market.content and "PR-FAQ" in market.content
    assert "never auto-write" in market.content and "never auto-create" in market.content
    # token-envelope gate before any web spend.
    assert "confirm the envelope" in market.content
    # v2: intent-framed verdict — build-vs-adopt for personal tooling, not only saturation.
    assert "build-vs-adopt" in market.content.lower()
    assert "deepen-own-use" in market.content and "broaden-adoption" in market.content
    assert "WRONG yardstick" in market.content  # saturation is the wrong lens for own-use
    # v4: a pre-declared intent is a proposal — ask with options + free text.
    assert "free-text alternative" in market.content
    # v5: scoped branch-check variant (teardown+verdict+sources; no JTBD/PR-FAQ).
    assert "Branch-check variant" in market.content


def test_cockpit_dispatch_contract_skill_registered_and_sequences():
    ct = next(s for s in skills.SKILLS if s.name == "cockpit-autonomous-dispatch-contract")
    assert ct.version == 2
    # A thin sequencer: composes the decision skills, never re-implements them.
    assert "dispatch-decision" in ct.content
    assert "scope-cards" in ct.content and "pathfinder" in ct.content
    # Wires the away-mode kit commands built this campaign.
    for cmd in ("horus envelope", "horus schedule", "horus supervise", "horus notify"):
        assert cmd in ct.content
    assert "horus run --unattended" in ct.content
    # Merge stays opt-in + probe-gated; default posture is verify+escalate-only.
    assert "--allow-merge" in ct.content
    assert "verify + escalate only" in ct.content or "verify+escalate-only" in ct.content
    # Advisory + owner-gated: proposes, never launches or selects a model itself.
    assert "Never selects a model" in ct.content or "never selects a model" in ct.content
    assert "Proposes, never performs" in ct.content
    # Account routed away from the overseer, gated on usage.
    assert "horus usage check" in ct.content


def test_pathfinder_skill_registered_and_orchestrates():
    pf = next(s for s in skills.SKILLS if s.name == "pathfinder")
    assert pf.version == 6
    # v6: the triage route-out names scope-cards' grooming mode explicitly.
    assert "Grooming an existing backlog" in pf.content
    # v5 (calibration 2026-07-19): the owner's mental model includes the inward
    # audit — product-audit where the project has one, shipped-vs-used elsewhere
    # (product-audit is Horus-specific; pathfinder must run on any project).
    assert "Inward audit" in pf.content
    assert "product-audit" in pf.content
    assert "shipped-vs-used" in pf.content
    # Step 0 triages backlog-POLISH out to the grooming pass instead of running
    # the five-step chain for a grooming need.
    assert "is it a re-baseline at all?" in pf.content
    assert "tui-backlog-refine-and-order" in pf.content
    # Cards land against the single contract authority in scope-cards.
    assert "dispatchable-card contract" in pf.content
    # Renamed from horus-kickstart: age-agnostic name, no old slug lingering.
    assert not any(s.name == "horus-kickstart" for s in skills.SKILLS)
    # v2: genuinely thin — sequences the factored step skills, no analysis inline.
    assert "market-scan" in pf.content and "deep-research" in pf.content
    assert "roadmap-branches" in pf.content and "scope-cards" in pf.content
    assert "horus consolidate" in pf.content
    assert "No new CLI subcommand" in pf.content
    assert "No analysis inside pathfinder" in pf.content
    # Receipts are the step interfaces so the chain pauses/resumes across sessions.
    assert "Receipts are the interfaces" in pf.content
    # Advisory, gated; straight-through pre-auth still never writes unapproved.
    assert "advisory" in pf.content.lower()
    assert "Never auto-apply" in pf.content
    assert "straight-through" in pf.content
    assert "WRITTEN without explicit approval" in pf.content
    # Facet changes stay a diff, never wholesale.
    assert "wholesale" in pf.content
    assert "add / rename / retire / promote" in pf.content
    # Onboarding folds in (delegated to roadmap-branches): initial facets + stamp cards.
    assert "Onboarding fork" in pf.content and "stamp existing cards" in pf.content
    # Token envelope before any web spend; a fresh receipt may be reused.
    assert "confirm the token envelope" in pf.content.lower()
    assert "may be reused" in pf.content
    # Reads for BOTH new and existing projects (the rename's whole point).
    assert "age-agnostic" in pf.content
    # Step 0: pin the intent, never assume it (build-vs-adopt vs adoption frame).
    assert "pin the intent" in pf.content
    assert "deepen-own-use" in pf.content and "broaden-adoption" in pf.content
    # Step 1 emits a pinned shipped+vision+audience brief passed into every step.
    assert "pinned brief" in pf.content.lower() or "pin a ground-truth brief" in pf.content
    assert "HARD CONSTRAINT" in pf.content
    # v2 fallback present (asserted for all skills elsewhere, checked explicitly here too).
    assert "## v2 six-lane projects (fallback)" in pf.content
    # v3: Step 0 confirms the intent interactively even when pre-declared in args.
    assert "Confirm interactively, even when the intent arrives pre-declared" in pf.content
    # v4: a reused receipt's envelope nod replaces the Step 2 gate; prior trees feed step 3.
    # Market-scan is Step 3 since v5 inserted the inward audit as Step 2.
    assert "REPLACES Step 3" in pf.content
    assert "prior branch-tree" in pf.content


def test_roadmap_branches_skill_registered_divergence_tree():
    rb = next(s for s in skills.SKILLS if s.name == "roadmap-branches")
    assert rb.version == 3
    # The deliverable is a TREE of alternative roadmaps, never one merged roadmap.
    assert "never collapse the tree into one merged roadmap" in rb.content
    # Speculative branches (directions with no facet yet) are part of the contract.
    assert "Speculative branches" in rb.content
    # v2: speculative branches must re-test the Vision's out-of-scope list.
    assert "RE-TEST" in rb.content and "out-of-scope list" in rb.content
    # v3: prior trees are inputs; every candidate exits with a disposition;
    # owner verdicts bind via card Reviews, not receipts alone.
    assert "Prior branch-tree receipts" in rb.content
    assert "exits with a disposition" in rb.content
    assert "## Reviews" in rb.content
    # Market evidence appears INSIDE every branch, not only in the market section.
    assert "Market position" in rb.content
    assert "therefore these items" in rb.content
    # Consumes the existing signals; never re-researches or improvises evidence.
    assert "horus consolidate" in rb.content and "market-scan" in rb.content
    assert ".horus/research/" in rb.content
    assert "No new web research" in rb.content
    # Re-justifies the existing backlog with explicit push-back; inherits nothing.
    assert "inherit nothing" in rb.content.lower() or "inherits" in rb.content
    assert "Re-justify the existing backlog" in rb.content
    assert "push-back" in rb.content
    # Claims discipline + no-repetition template rules.
    assert "comparison baseline" in rb.content
    assert "State each fact exactly once" in rb.content
    # Facet changes are a diff; onboarding fork proposes the initial facet set.
    assert "add / rename / retire / promote" in rb.content
    assert "Onboarding fork" in rb.content and "stamp existing cards" in rb.content
    # Advisory: owner picks; the skill never edits Vision or creates cards.
    assert "never edits the Vision" in rb.content
    assert "## v2 six-lane projects (fallback)" in rb.content


def test_scope_cards_skill_registered_self_sufficient():
    sc = next(s for s in skills.SKILLS if s.name == "scope-cards")
    assert sc.version == 4
    # v4 (first live grooming run, 2026-07-19): standalone grooming mode is a
    # specified input shape, not an improvised one.
    assert "Grooming an existing backlog" in sc.content
    assert "never batch judgment calls" in sc.content
    # Contract exceptions the live backlog proved: explore cards may substitute
    # a branch: stamp for vision_facet; umbrellas carry a convergence criterion.
    assert "may\nsubstitute a `branch:" in sc.content or "may substitute a `branch:" in sc.content
    assert "Convergence criterion" in sc.content
    # Probe retrofits are scoped to new/armed/edited cards, never blanket.
    assert "Probe-retrofit policy" in sc.content
    # The one bar: a fresh agent + PRD + card can start correctly.
    assert "self-sufficiency test" in sc.content
    assert "fresh agent" in sc.content
    # Card template carries the full understanding.
    assert "vision_facet" in sc.content and "phase" in sc.content
    assert "Acceptance" in sc.content and "Non-goals" in sc.content
    # Thin input is flagged, never silently padded; findings are never pre-invented.
    assert "do not silently invent" in sc.content
    assert "do not fabricate the findings" in sc.content
    # Also drafts the branch's Vision diff + existing-card push-back edits.
    assert "Vision facet diff" in sc.content
    assert "demote / defer / retire" in sc.content
    # Per-item owner gate before anything is written.
    assert "approve, amend, or drop each item individually" in sc.content
    assert "## v2 six-lane projects (fallback)" in sc.content


def test_dispatchable_card_contract_single_authority():
    """The card contract lives ONCE, in scope-cards; consumers reference it.

    Calibration 2026-07-19: the cockpit ready-gate demanded `surface`/`parallel`
    stamps while scope-cards' template never emitted them — the remediation path
    could not produce what the gate required. Guard the contract's home and the
    producer/consumer alignment so partial copies cannot silently drift again.
    """
    sc = next(s for s in skills.SKILLS if s.name == "scope-cards")
    ct = next(s for s in skills.SKILLS if s.name == "cockpit-autonomous-dispatch-contract")
    # The authority section lives in scope-cards and emits the collision stamps
    # the dispatch machinery reasons with (backlog.py warns without `surface`).
    assert "dispatchable-card contract" in sc.content
    assert "surface:" in sc.content and "parallel: safe | exclusive" in sc.content
    # Acceptance is supervisor-grade: deterministic gate + a named live probe.
    assert "live probe" in sc.content
    # Tier vocabulary is the closed vendor-neutral set (v0.0.62), not model names.
    assert "low | medium | high | frontier" in sc.content
    # The consumer references the authority instead of keeping a rival checklist.
    assert "dispatchable-card contract in `scope-cards`" in ct.content
    assert "single authority" in ct.content


def test_pathfinder_step_skills_projected_to_both_agents():
    for name in ("pathfinder", "roadmap-branches", "scope-cards"):
        bundled = next(s for s in skills.SKILLS if s.name == name)
        for root in (".claude/skills", ".agents/skills"):
            assert Path(f"{root}/{name}/SKILL.md").read_text(encoding="utf-8") == bundled.content
    for root in (".claude/skills", ".agents/skills"):
        # Old slug's projection is gone, not left orphaned.
        assert not Path(f"{root}/horus-kickstart/SKILL.md").exists()


def test_dispatch_consent_skills_match_claude_and_codex_projections():
    by_name = {skill.name: skill for skill in skills.SKILLS}
    for name in ("delegation-rubric", "execution-decision", "dispatch-decision", "horus-execution"):
        expected = by_name[name].content
        assert Path(f".agents/skills/{name}/SKILL.md").read_text(encoding="utf-8") == expected
        assert Path(f".claude/skills/{name}/SKILL.md").read_text(encoding="utf-8") == expected


def test_delegation_rubric_is_the_shared_single_source_of_truth():
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    # Reads the Slice 1 data-only surface, never a pick/router.
    assert "horus capabilities --models" in rubric.content
    assert "--for" in rubric.content  # explicitly forbids adding a pick mode
    assert "data-only" in rubric.content.lower()
    # Tier-trust ladder is data-driven, not hardcoded to a model.
    assert "tier-trust" in rubric.content.lower()
    assert "Proven" in rubric.content and "Unproven" in rubric.content
    assert "clean_count" in rubric.content and "last_outcomes" in rubric.content
    assert "quality_datums" in rubric.content
    assert "died_count" in rubric.content and "void_count" in rubric.content
    # The one lever sets BOTH the pick and the verification depth.
    assert "same tier-trust sets BOTH" in rubric.content or "SAME tier-trust" in rubric.content
    # Verification = observe a gate you didn't author; reproduction != re-run.
    assert "did NOT author" in rubric.content
    assert "Reproduction ≠ re-running" in rubric.content
    assert "CI check green on the" in rubric.content
    # Runtime/visual surface defaults to the owner.
    assert "asking the OWNER" in rubric.content
    # Owner caution/guard flags gate the pick without pinning a current model.
    assert "caution" in rubric.content and "guard" in rubric.content
    assert "token-headroom guard" in rubric.content and "ceiling is near" in rubric.content
    # Hard boundary held.
    assert "advisory" in rubric.content.lower()
    assert "research/omnigent.md" in rubric.content


def test_delegation_rubric_keeps_older_capable_models_in_roster():
    # Fold-in ask (delegation-matrix-display card): don't drop a model from the
    # ladder on recency alone — pick by capability-for-the-task and keep
    # gathering datums on it.
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    assert "older-but-capable" in rubric.content.lower()
    assert "not by release date" in rubric.content.lower() or "not recency" in rubric.content.lower()


def test_delegation_rubric_proves_dividend_before_model_selection():
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    assert rubric.version == 9
    assert rubric.content.index("prove delegation has a dividend") < rubric.content.index(
        "Read the calibration data"
    )
    assert "Cross-project scope, multiple phases" in rubric.content
    assert "Never manufacture work or a worker solely to earn a datum" in rubric.content
    assert "temporarily lifted" in rubric.content and "owner-provided" in rubric.content
    assert "expiring isolated-account" in rubric.content
    assert "Bind dispatch to explicit owner consent" in rubric.content
    for field in ("concrete model", "effort", "account alias", "maximum attempts"):
        assert field in rubric.content
    assert "never permits silent fallback" in rubric.content
    assert "Do not predict a per-task usage percentage" in rubric.content
    assert "today:" not in rubric.content
    for pinned_model in ("sonnet-5", "opus-4.8", "haiku-4.5", "gpt-5.6"):
        assert pinned_model not in rubric.content


def test_delegation_skills_frame_tiers_as_vendor_neutral():
    """`vendor-neutral-delegation-tiers`: the tier names a capability point, and
    the provider is chosen within it at the consent envelope — never defaulted
    from the label."""
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    # The rubric points at the new neutral-tier map and forbids letting the
    # label pick the vendor.
    assert "vendor-neutral tier" in rubric.content
    assert "low | medium | high | frontier" in rubric.content or "low|medium|high|frontier" in rubric.content
    assert "capacity + owner choice" in rubric.content
    # Both consumers emit a vendor-neutral tier resolved to a provider only in
    # the consent envelope.
    for name in ("execution-decision", "dispatch-decision"):
        skill = next(s for s in skills.SKILLS if s.name == name)
        assert "vendor-neutral capability point" in skill.content, name
        assert "low|medium|high|frontier" in skill.content, name
        assert "never defaulted from the label" in skill.content, name


def test_delegation_rubric_distinguishes_calibration_key_from_provider_selector():
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    assert "calibration key" in rubric.content
    assert "not always the same string as" in rubric.content
    assert "horus run` rejects a known" in rubric.content


def test_delegation_rubric_discloses_same_account_parallel_usage_tradeoff():
    rubric = next(s for s in skills.SKILLS if s.name == "delegation-rubric")
    assert "trade attribution for throughput" in rubric.content
    assert "concurrent/confounded" in rubric.content
    assert "isolated account aliases" in rubric.content


def test_execution_skill_requires_provider_valid_selector_in_consent_envelope():
    execution = next(s for s in skills.SKILLS if s.name == "horus-execution")
    assert "not the calibration key" in execution.content
    assert "claude-sonnet-5" in execution.content
    assert "renewed approval" in execution.content
    assert "before creating a worktree or session" in execution.content


def test_delegation_shape_tiers_and_verification_dial_are_structured_and_single_sourced():
    # `horus capabilities --matrix` reads these tables directly (see cli.py /
    # datums.py) instead of forking a duplicate copy of the rubric's mapping.
    shapes = {row["shape"] for row in skills.DELEGATION_SHAPE_TIERS}
    assert {"scoped-impl", "novel", "mechanical"} <= shapes
    for row in skills.DELEGATION_SHAPE_TIERS:
        assert row["tier_role"] and row["description"]

    trusts = {row["tier_trust"] for row in skills.DELEGATION_VERIFICATION_DIAL}
    assert {"proven", "unproven", "runtime"} <= trusts
    for row in skills.DELEGATION_VERIFICATION_DIAL:
        assert row["verification"] and row["description"]


def test_both_consumer_skills_import_the_shared_rubric():
    # The logic lives once, in the rubric; each skill loads it by relative path.
    for name in ("execution-decision", "dispatch-decision"):
        skill = next(s for s in skills.SKILLS if s.name == name)
        assert "../delegation-rubric/SKILL.md" in skill.content, name
        assert "restate or fork" in skill.content, name
        # The data-reading logic lives in the rubric, not forked here; each
        # consumer still names the calibration surface it defers to.
        assert "calibration" in skill.content, name
        # Advisory boundary held in each thin consumer.
        assert "never auto" in skill.content or "nothing here auto-runs" in skill.content, name


def test_execution_decision_skill_is_in_project_subagents():
    skill = next(s for s in skills.SKILLS if s.name == "execution-decision")
    assert skill.version == 4
    # Its mode vocabulary + the in-project verification specialization.
    assert "`inline`" in skill.content and "`subagent-plan`" in skill.content
    assert "RUNS the gate at the phase boundary" in skill.content
    assert "TRUSTS the code" in skill.content
    assert "execution_recommendation" in skill.content
    assert "horus datum close" in skill.content
    assert "awaiting explicit owner approval" in skill.content
    assert "fallback or extra" in skill.content


def test_dispatch_decision_skill_is_cockpit_multiproject():
    skill = next(s for s in skills.SKILLS if s.name == "dispatch-decision")
    assert skill.version == 4
    # Its mode vocabulary, account routing, and the overseer verification note.
    assert "`inline-here`" in skill.content
    assert "`dispatched-worker`" in skill.content
    assert "`dispatched-plan`" in skill.content
    assert "away from the overseer account" in skill.content
    assert "horus usage check" in skill.content
    assert "Overseer usage is a cost to weigh, not a presumption" in skill.content
    assert "Cross-project scope alone is insufficient" in skill.content
    assert "Do not dispatch merely to collect a datum" in skill.content
    assert "owner-provided" in skill.content
    assert "spend capacity before its reset" in skill.content
    assert "stop for explicit owner" in skill.content
    assert "provider errors never authorize fallback" in skill.content
    # Observe CI green on the merge SHA; do not re-run the suite.
    assert "required CI check green on the merge SHA" in skill.content
    assert "Do NOT re-run" in skill.content


def test_all_bundled_skills_keep_a_marked_v2_fallback_section():
    # Phase 3 (v3-tooling): every rewritten skill keeps the six-lane guidance
    # reachable under an explicit, clearly-marked fallback heading.
    for s in skills.SKILLS:
        assert "## v2 six-lane projects (fallback)" in s.content, s.name


def test_consolidate_skill_v3_covers_backlog_hygiene_checks():
    consolidate = next(s for s in skills.SKILLS if s.name == "horus-consolidate")
    assert consolidate.version == 12
    assert "PRD.md" in consolidate.content
    assert "no lane-routing/overlap warnings" in consolidate.content
    assert "~250-line cap" in consolidate.content
    assert "Stale frontmatter" in consolidate.content
    assert "Undistilled recovery notes" in consolidate.content
    assert "Duplicate backlog titles" in consolidate.content
    assert "Lingering done items" in consolidate.content
    assert "one line" in consolidate.content and "not a paragraph" in consolidate.content
    # v12: the phase-aware convergence read-out.
    assert "Convergence read-out" in consolidate.content
    assert "vision_facet" in consolidate.content
    assert "phase: explore" in consolidate.content
    # sessions/ and temp/ handoff notes stay unchanged in v3.
    assert "temp/" in consolidate.content


def test_infer_skill_v3_reports_prd_skeleton_gaps():
    infer = next(s for s in skills.SKILLS if s.name == "horus-infer")
    assert infer.version == 4
    assert "Vision" in infer.content and "Backlog" in infer.content
    assert "Shipped" in infer.content and "Rules" in infer.content
    assert "PRD.md" in infer.content
    assert "do not create a starter card" in infer.content
    assert "leave the scaffold blank" in infer.content


def test_distill_history_skill_v3_targets_archive():
    distill = next(s for s in skills.SKILLS if s.name == "horus-distill-history")
    assert distill.version == 3
    assert ".horus/archive/history.md" in distill.content
    assert "PRD.md" in distill.content


def test_execution_skill_requires_real_delegation_for_model_separation():
    execution = next(s for s in skills.SKILLS if s.name == "horus-execution")
    assert execution.version == 13
    assert "testing model separation" in execution.content
    assert "do not implement" in execution.content
    assert "the delegated phase in the supervisor context" in execution.content
    assert "delegation_basis" in execution.content
    assert "worker_tier` is only the intended tier **if delegated**" in execution.content
    assert "A handoff" in execution.content
    assert "written by the supervisor after doing the work" in execution.content
    # Need-first delegation guard + honest review caveat.
    assert "require a concrete dividend" in execution.content
    assert "Do not enter this workflow" in execution.content
    # Bulk-copy/migration phases must reconcile by count and size before acceptance.
    assert "horus verify-inventory" in execution.content
    assert "a retry, not" in execution.content
    assert "never pin durable guidance to current model names" in execution.content
    assert "safety guarantee" in execution.content  # honest review caveat
    assert "does not satisfy the workflow test" in execution.content
    # v5: cross-agent workers — mark a phase for the other CLI and spawn it tracked.
    assert "worker_agent: codex" in execution.content
    assert "horus run --agent codex" in execution.content
    assert "shares no conversation history" in execution.content
    assert "Obtain exact-envelope approval" in execution.content
    assert "horus datum report" in execution.content
    assert "Do not predict task usage" in execution.content
    assert "reproduce the gate yourself" in execution.content
    # v7: signal-based acceptance — required CI green counts as reproduction of the
    # test gate; one runtime probe stays with the supervisor; no proof narratives.
    assert "deterministic signal" in execution.content
    assert "required CI check green" in execution.content
    assert "one runtime probe" in execution.content
    assert "No proof narratives" in execution.content
    assert "pre-existing failure baseline" in execution.content
    # v8: orchestrator > supervisor > worker — the pilot's lessons, encoded.
    assert "orchestrator implements nothing" in execution.content
    assert "One git worktree per worker" in execution.content
    assert "--posture full-auto" in execution.content
    assert "Bounce protocol" in execution.content
    assert "Merge sequencing" in execution.content


def test_execution_template_carries_worker_agent_marking():
    from horus import templates

    doc = templates.execution_md("2026-07-03")
    assert "| worker_tier | worker_agent |" in doc  # Active Phases column
    assert "`worker_agent` marks which agent CLI runs a delegated phase" in doc
    assert "horus run --agent codex --account <alias>" in doc
    assert "cold reader" in doc


def test_missing_or_stale_and_findings(tmp_path):
    assert skills.missing_or_stale(tmp_path) == list(skills.SKILLS)
    assert any(f.level == "warn" for f in skills.skill_findings(tmp_path))

    skills.install_skills(tmp_path)
    assert skills.missing_or_stale(tmp_path) == []
    assert all(f.level == "ok" for f in skills.skill_findings(tmp_path))


def test_skill_states_reports_each_status(tmp_path):
    skills.install_skills(tmp_path)  # all claude skills current
    first, second = skills.SKILLS[0], skills.SKILLS[1]
    # Downgrade one, unversion another, remove a third.
    skills.skill_path(first, tmp_path).write_text(
        "<!-- horus-skill-version: 0 -->\n", encoding="utf-8"
    )
    skills.skill_path(second, tmp_path).write_text("no marker here\n", encoding="utf-8")
    third = skills.SKILLS[2]
    skills.skill_path(third, tmp_path).unlink()

    states = {s.name: s for s in skills.skill_states(tmp_path)}
    assert states[first.name].status == skills.SKILL_OUTDATED
    assert states[first.name].installed_version == 0
    assert states[first.name].bundled_version == first.version
    assert states[second.name].status == skills.SKILL_UNVERSIONED
    assert states[second.name].installed_version is None
    assert states[third.name].status == skills.SKILL_MISSING
    # Everything else installed at the bundled version.
    installed = [s for s in states.values() if s.status == skills.SKILL_INSTALLED]
    assert installed and all(s.installed_version == s.bundled_version for s in installed)


def test_skill_states_are_target_specific_and_carry_refresh_command(tmp_path):
    skills.install_skills(tmp_path, targets=("codex",))
    states = skills.skill_states(tmp_path, targets=("claude", "codex"))
    claude = [s for s in states if s.target == "claude"]
    codex = [s for s in states if s.target == "codex"]
    assert all(s.status == skills.SKILL_MISSING for s in claude)
    assert all(s.status == skills.SKILL_INSTALLED for s in codex)
    assert claude[0].refresh_command == "horus upgrade-project --apply --target claude"
    assert codex[0].refresh_command == "horus upgrade-project --apply --target codex"


def test_skill_findings_match_skill_states(tmp_path):
    skills.install_skills(tmp_path)
    skills.skill_path(skills.SKILLS[0], tmp_path).write_text(
        "<!-- horus-skill-version: 0 -->\n", encoding="utf-8"
    )
    states = skills.skill_states(tmp_path)
    findings = skills.skill_findings(tmp_path)
    # One finding per state, and the ok/warn levels agree with the structured status.
    assert len(findings) == len(states)
    for state, finding in zip(states, findings):
        expected = "ok" if state.status == skills.SKILL_INSTALLED else "warn"
        assert finding.level == expected


def test_missing_or_stale_is_target_specific(tmp_path):
    skills.install_skills(tmp_path, targets=("codex",))
    assert skills.missing_or_stale(tmp_path, target="codex") == []
    assert skills.missing_or_stale(tmp_path, target="claude") == list(skills.SKILLS)


def test_stale_install_is_flagged(tmp_path):
    skills.install_skills(tmp_path)  # all current
    s = skills.SKILLS[0]
    skills.skill_path(s, tmp_path).write_text("<!-- horus-skill-version: 0 -->\n", encoding="utf-8")
    assert skills.missing_or_stale(tmp_path) == [s]  # only the downgraded one
    assert any("outdated" in f.message for f in skills.skill_findings(tmp_path))


def test_user_scope_uses_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    s = skills.SKILLS[0]
    assert skills.write_skill(s, tmp_path, user=True).status == "created"
    assert (tmp_path / "home" / ".claude" / "skills" / s.name / "SKILL.md").is_file()
    # project scope under tmp_path is untouched
    assert not (tmp_path / ".claude").exists()


def test_init_scaffolds_all_skills_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    initialize.init_project(tmp_path / "a", assume_yes=True)
    for s in skills.SKILLS:
        assert (tmp_path / "a" / ".claude" / "skills" / s.name / "SKILL.md").exists()
        assert (tmp_path / "a" / ".agents" / "skills" / s.name / "SKILL.md").exists()


def test_init_no_skills_opts_out(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    initialize.init_project(tmp_path / "b", assume_yes=True, with_skills=False, with_hooks=False)
    assert not (tmp_path / "b" / ".claude").exists()


def test_product_audit_skill_registered_and_projected():
    by_name = {skill.name: skill for skill in skills.SKILLS}
    skill = by_name["product-audit"]
    # Evidence-first questions, native-overlap check, ceremony review, closed verdict set.
    for marker in ("demote", "defer", "retire", "no-change", "last_product_audit", "telemetry"):
        assert marker in skill.content
    assert "never propose new features" in skill.content or "New features are out" in skill.content
    for root in (".claude/skills", ".agents/skills"):
        assert Path(f"{root}/product-audit/SKILL.md").read_text(encoding="utf-8") == skill.content


def test_process_retrospective_skill_registered_and_projected():
    by_name = {skill.name: skill for skill in skills.SKILLS}
    skill = by_name["process-retrospective"]
    assert skill.version == 1
    # Event-driven trigger, never automatic at closure.
    assert "explicit owner request" in skill.content
    assert "Never fires" in skill.content
    # Six-bucket cost attribution.
    for bucket in (
        "Inherent task cost",
        "Delegation tax",
        "Supervisor error",
        "Worker error",
        "Horus/skill defect",
        "External failure",
    ):
        assert bucket in skill.content
    # Cheapest-rung ladder, capped at three, existing-coverage check first.
    assert "No-change" in skill.content
    assert "Guidance clarification" in skill.content
    assert "Deterministic signal" in skill.content
    assert "Hard guard" in skill.content
    assert "capped at" in skill.content.lower() and "three" in skill.content.lower()
    assert "Check existing coverage" in skill.content
    # Advisory boundary: no auto-writes, no token estimates, no model launches, no broad rereads.
    assert "never estimates tokens" in skill.content.lower() or "estimate token" in skill.content.lower()
    assert "no new artifacts" in skill.content.lower() or "never a new" in skill.content.lower()
    assert "Stay inline" in skill.content
    # Distinguished from the periodic product audit and continuity closure.
    assert "product-audit" in skill.content
    assert "horus-consolidate" in skill.content
    assert "## v2 six-lane projects (fallback)" in skill.content
    for root in (".claude/skills", ".agents/skills"):
        assert Path(f"{root}/process-retrospective/SKILL.md").read_text(encoding="utf-8") == skill.content


def test_inline_batch_session_skill_registered_and_batches():
    s = next(x for x in skills.SKILLS if x.name == "inline-batch-session")
    assert s.version == 2
    # posture: per-card delivery safety kept, ALL continuity held to a hard boundary
    assert "delivery safety" in s.content
    assert "hard boundary" in s.content
    # a version release is named as a boundary, and finishing/merging is explicitly NOT one
    assert "version release" in s.content
    assert "NOT a boundary" in s.content and "manufacture a boundary" in s.content
    assert "## v2 six-lane projects (fallback)" in s.content
