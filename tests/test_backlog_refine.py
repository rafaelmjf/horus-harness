"""The launch surface for the attended backlog refine + order pass.

The pass itself is an LLM flow owned by the bundled `backlog-refine` skill; what is
testable — and what these tests pin — is the deterministic prompt: it names the
skill, states the readiness picture, and embeds live delivery state (open PRs,
unmerged branches, continuity freshness) so the session starts from ground truth
instead of being told to go looking.
"""

from pathlib import Path

from horus import backlog_refine


def _mk_card(root: Path, name: str, *, readiness="ready", autonomy="eligible", order=""):
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "status: open", "priority: high", f"readiness: {readiness}"]
    if autonomy:
        lines.append(f"autonomy: {autonomy}")
    if order:
        lines.append(f"order: {order}")
    lines.append("---")
    (hdir / f"{name}.md").write_text("\n".join(lines) + f"\n# {name}\n", encoding="utf-8")


def _quiet_probes(monkeypatch, *, prs=None):
    """Neutralize the three live probes so a test asserts on one thing at a time."""
    monkeypatch.setattr(backlog_refine.integration, "open_prs", lambda root, timeout=0: prs)
    monkeypatch.setattr(backlog_refine.closure, "unmerged_branch_findings", lambda root: [])
    monkeypatch.setattr(backlog_refine.routines, "freshness_signals", lambda root: [])


def test_prompt_hands_over_to_the_skill_without_restating_it(tmp_path, monkeypatch):
    """The launch surface must not carry a second copy of the flow — two contracts
    would drift, and the skill is the single authority."""
    _quiet_probes(monkeypatch, prs=[])
    _mk_card(tmp_path, "a-card")

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "`backlog-refine` skill" in prompt
    assert tmp_path.name in prompt  # the project is named, never a bare empty string
    # No duplicated questionnaire/picture machinery from the skill.
    assert "Here is our current picture" not in prompt
    assert "Verdict" not in prompt


def test_prompt_embeds_open_prs_because_a_card_on_a_pr_is_not_open_work(tmp_path, monkeypatch):
    _quiet_probes(monkeypatch, prs=[
        {"number": "431", "branch": "fix/usage-flake", "url": "u", "title": "Fix the usage flake"},
    ])
    _mk_card(tmp_path, "a-card")

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "#431 Fix the usage flake [head: fix/usage-flake]" in prompt
    assert "not open work" in prompt


def test_unknowable_pr_state_says_so_and_never_reads_as_all_clear(tmp_path, monkeypatch):
    """`gh` missing or timing out must degrade to a stated unknown: a silent 'none'
    would let the pass conclude the backlog is untouched when it isn't."""
    _quiet_probes(monkeypatch, prs=None)
    _mk_card(tmp_path, "a-card")

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "Open PRs: unknown" in prompt
    assert "Open PRs: none" not in prompt


def test_prompt_carries_unmerged_branches_and_stale_continuity(tmp_path, monkeypatch):
    from horus.continuity import Finding

    _quiet_probes(monkeypatch, prs=[])
    monkeypatch.setattr(
        backlog_refine.closure, "unmerged_branch_findings",
        lambda root: [Finding("info", "2 unmerged remote branch(es): origin/fix/a (3d)")],
    )
    monkeypatch.setattr(
        backlog_refine.routines, "freshness_signals",
        lambda root: [Finding("warn", "next_action points at shipped work")],
    )
    _mk_card(tmp_path, "a-card")

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "2 unmerged remote branch(es): origin/fix/a (3d)" in prompt
    assert "Continuity is STALE" in prompt
    assert "next_action points at shipped work" in prompt


def test_prompt_reports_existing_sequence_and_flags_ambiguity(tmp_path, monkeypatch):
    _quiet_probes(monkeypatch, prs=[])
    _mk_card(tmp_path, "first", order="10")
    _mk_card(tmp_path, "second", order="10")
    _mk_card(tmp_path, "unstamped")

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "Sequence: 2 of 3 cards carry `order:`" in prompt
    assert "duplicate order 10" in prompt


def test_prompt_states_the_unsequenced_case_plainly(tmp_path, monkeypatch):
    _quiet_probes(monkeypatch, prs=[])
    _mk_card(tmp_path, "a-card")
    _mk_card(tmp_path, "b-card")

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "no card carries `order:` yet" in prompt
    assert "unsequenced pool" in prompt


def test_prompt_states_the_sparse_within_queue_ordering_semantics(tmp_path, monkeypatch):
    """The pass writes the field, so the prompt must state what a value means —
    otherwise a session invents a cross-queue or dense sequence."""
    _quiet_probes(monkeypatch, prs=[])
    _mk_card(tmp_path, "a-card")

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "gaps of 10" in prompt
    assert "WITHIN a readiness queue" in prompt
    assert "never authority to run anything" in prompt


def test_probes_never_raise_on_a_project_without_horus(tmp_path, monkeypatch):
    """A launch must not blow up on an uninitialized or half-deleted project."""
    _quiet_probes(monkeypatch, prs=None)

    prompt = backlog_refine.refine_prompt(tmp_path)

    assert "0 active cards" in prompt
