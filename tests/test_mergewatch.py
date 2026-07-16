"""`horus merge-watch <sha|pr>` — poll required checks on the exact sha until
they settle, one line per state change, exit 0 green / 1 red.

All `gh`/`git` subprocess calls go through `mergewatch._run`, monkeypatched
here to a scripted fake so the poll loop is tested without real network or
real waiting (`sleep`/`now` are also injected).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from horus import mergewatch


class _Proc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _json_ok(payload) -> _Proc:
    return _Proc(0, json.dumps(payload))


class _FakeGh:
    """Scripted responder keyed by the command's stable prefix (argv[1:3])."""

    def __init__(self):
        self.calls: list[list[str]] = []
        self.repo_view = _json_ok({"owner": {"login": "acme"}, "name": "widget"})
        self.pr_view_sequence: list[_Proc] = []
        self.check_runs_sequence: list[_Proc] = []
        self.status_sequence: list[_Proc] = []
        self.required_checks = _Proc(1)  # default: no protection info

    def __call__(self, cmd, cwd, *, timeout=20.0):
        self.calls.append(cmd)
        if cmd[:2] == ["gh", "repo"]:
            return self.repo_view
        if cmd[:3] == ["gh", "pr", "view"]:
            return self.pr_view_sequence.pop(0)
        if cmd[:2] == ["gh", "api"] and "check-runs" in cmd[2]:
            return self.check_runs_sequence.pop(0) if self.check_runs_sequence else _json_ok({"check_runs": []})
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/status"):
            return self.status_sequence.pop(0) if self.status_sequence else _json_ok({"statuses": []})
        if cmd[:2] == ["gh", "api"] and "required_status_checks" in cmd[2]:
            return self.required_checks
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([])
        raise AssertionError(f"unexpected command: {cmd}")


@pytest.fixture
def fake_gh(monkeypatch):
    fake = _FakeGh()
    monkeypatch.setattr(mergewatch, "_run", fake)
    return fake


def _sleeper():
    calls = []
    return calls, calls.append


# --- resolve_target ------------------------------------------------------

def test_resolve_target_treats_bare_number_as_pr(fake_gh):
    fake_gh.pr_view_sequence = [_json_ok({"headRefOid": "deadbeef", "baseRefName": "main"})]
    target = mergewatch.resolve_target(Path("."), "42")
    assert target.pr_number == 42
    assert target.sha == "deadbeef"
    assert target.base_branch == "main"


def test_resolve_target_treats_pr_url_as_pr(fake_gh):
    fake_gh.pr_view_sequence = [_json_ok({"headRefOid": "cafef00d", "baseRefName": "main"})]
    target = mergewatch.resolve_target(Path("."), "https://github.com/acme/widget/pull/7")
    assert target.pr_number == 7
    assert target.sha == "cafef00d"


def test_resolve_target_treats_other_strings_as_sha(fake_gh):
    target = mergewatch.resolve_target(Path("."), "abc123def")
    assert target.pr_number is None
    assert target.sha == "abc123def"


def test_resolve_target_looks_up_owning_pr_for_a_sha(monkeypatch, fake_gh):
    def responder(cmd, cwd, *, timeout=20.0):
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake_gh, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    target = mergewatch.resolve_target(Path("."), "abc123def")
    assert target.pr_number == 9
    assert target.base_branch == "main"


def test_resolve_target_raises_when_repo_unresolvable(monkeypatch):
    monkeypatch.setattr(mergewatch, "_run", lambda cmd, cwd, timeout=20.0: _Proc(1, stderr="not a repo"))
    with pytest.raises(mergewatch.MergeWatchError):
        mergewatch.resolve_target(Path("."), "42")


def test_resolve_target_pr_number_defaults_open_when_state_missing(fake_gh):
    fake_gh.pr_view_sequence = [_json_ok({"headRefOid": "deadbeef", "baseRefName": "main"})]
    target = mergewatch.resolve_target(Path("."), "42")
    assert target.is_open_pr is True


def test_resolve_target_pr_number_marks_merged_pr_as_not_open(fake_gh):
    fake_gh.pr_view_sequence = [_json_ok({"headRefOid": "deadbeef", "baseRefName": "main", "state": "MERGED"})]
    target = mergewatch.resolve_target(Path("."), "42")
    assert target.is_open_pr is False


def test_resolve_target_pr_number_marks_open_pr_as_open(fake_gh):
    fake_gh.pr_view_sequence = [_json_ok({"headRefOid": "deadbeef", "baseRefName": "main", "state": "OPEN"})]
    target = mergewatch.resolve_target(Path("."), "42")
    assert target.is_open_pr is True


def test_resolve_target_sha_owned_by_merged_pr_is_not_open(monkeypatch, fake_gh):
    def responder(cmd, cwd, *, timeout=20.0):
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake_gh, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    target = mergewatch.resolve_target(Path("."), "abc123def")
    assert target.pr_number == 9
    assert target.is_open_pr is False


def test_resolve_target_sha_with_no_owning_pr_is_open(fake_gh):
    target = mergewatch.resolve_target(Path("."), "abc123def")
    assert target.pr_number is None
    assert target.is_open_pr is True


# --- required_contexts ----------------------------------------------------

def test_required_contexts_parses_protection_contexts(fake_gh):
    fake_gh.required_checks = _json_ok({"contexts": ["pytest (3.12)", "pytest (3.13)"]})
    contexts = mergewatch.required_contexts(Path("."), "acme", "widget", "main")
    assert contexts == {"pytest (3.12)", "pytest (3.13)"}


def test_required_contexts_none_when_protection_unavailable(fake_gh):
    contexts = mergewatch.required_contexts(Path("."), "acme", "widget", "main")
    assert contexts is None


def test_required_contexts_none_without_a_base_branch(fake_gh):
    assert mergewatch.required_contexts(Path("."), "acme", "widget", None) is None


# --- overall_state ---------------------------------------------------------

def test_overall_state_pending_when_nothing_reported():
    assert mergewatch.overall_state({}, None) == "pending"


def test_overall_state_success_when_all_required_pass():
    states = {"pytest": "success", "freshness": "success"}
    assert mergewatch.overall_state(states, {"pytest", "freshness"}) == "success"


def test_overall_state_failure_wins_over_pending():
    states = {"pytest": "failure", "freshness": "pending"}
    assert mergewatch.overall_state(states, {"pytest", "freshness"}) == "failure"


def test_overall_state_ignores_non_required_checks():
    states = {"pytest": "success", "unrelated-flaky": "failure"}
    assert mergewatch.overall_state(states, {"pytest"}) == "success"


def test_overall_state_pending_when_required_context_never_posted():
    states = {"pytest": "success"}
    assert mergewatch.overall_state(states, {"pytest", "freshness"}) == "pending"


def test_overall_state_falls_back_to_all_checks_when_required_unknown():
    states = {"pytest": "success", "freshness": "success"}
    assert mergewatch.overall_state(states, None) == "success"
    states_with_failure = {"pytest": "success", "freshness": "failure"}
    assert mergewatch.overall_state(states_with_failure, None) == "failure"


# --- pr_only_contexts -------------------------------------------------------

_TESTS_WORKFLOW = """\
name: tests

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  pytest:
    strategy:
      matrix:
        python-version: ['3.12', '3.13']
    steps:
      - name: Run tests
        run: pytest
"""

_CONTINUITY_WORKFLOW = """\
name: continuity

on:
  pull_request:
    branches: [main]

jobs:
  freshness:
    runs-on: ubuntu-latest
    steps:
      - name: Continuity-policy check
        run: python -m horus close --check
"""

_RELEASE_WORKFLOW = """\
name: Install smoke

on:
  release:
    types: [published]

jobs:
  install-smoke:
    name: Install smoke (${{ matrix.os }})
    strategy:
      matrix:
        os: [ubuntu-latest]
    steps:
      - name: Install uv
        run: true
"""


def _write_workflows(tmp_path: Path, **files: str) -> Path:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    for name, content in files.items():
        (workflows_dir / f"{name}.yml").write_text(content)
    return tmp_path


def test_pr_only_contexts_excludes_job_with_both_triggers(tmp_path):
    root = _write_workflows(tmp_path, tests=_TESTS_WORKFLOW)
    assert mergewatch.pr_only_contexts(root) == set()


def test_pr_only_contexts_includes_pull_request_only_job(tmp_path):
    root = _write_workflows(tmp_path, continuity=_CONTINUITY_WORKFLOW)
    assert mergewatch.pr_only_contexts(root) == {"freshness"}


def test_pr_only_contexts_across_workflows_matches_the_repo_scenario(tmp_path):
    root = _write_workflows(tmp_path, tests=_TESTS_WORKFLOW, continuity=_CONTINUITY_WORKFLOW)
    assert mergewatch.pr_only_contexts(root) == {"freshness"}


def test_pr_only_contexts_ignores_non_pull_request_workflows(tmp_path):
    root = _write_workflows(tmp_path, release=_RELEASE_WORKFLOW)
    assert mergewatch.pr_only_contexts(root) == set()


def test_pr_only_contexts_empty_without_workflows_dir(tmp_path):
    assert mergewatch.pr_only_contexts(tmp_path) == set()


# --- fetch_check_states -----------------------------------------------------

def test_fetch_check_states_normalizes_check_runs_and_statuses(fake_gh):
    fake_gh.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "completed", "conclusion": "success"},
        {"name": "pytest (3.13)", "status": "in_progress"},
        {"name": "lint", "status": "completed", "conclusion": "failure"},
    ]})]
    fake_gh.status_sequence = [_json_ok({"statuses": [{"context": "legacy-ci", "state": "success"}]})]
    states = mergewatch.fetch_check_states(Path("."), "acme", "widget", "sha1")
    assert states == {
        "pytest (3.12)": "success",
        "pytest (3.13)": "pending",
        "lint": "failure",
        "legacy-ci": "success",
    }


# --- watch: the full poll loop ----------------------------------------------

def test_watch_settles_green_immediately(fake_gh):
    fake_gh.pr_view_sequence = [
        _json_ok({"headRefOid": "sha1", "baseRefName": "main"}),  # resolve_target
        _json_ok({"headRefOid": "sha1"}),  # head-moved check inside the loop
    ]
    fake_gh.required_checks = _json_ok({"contexts": ["pytest"]})
    fake_gh.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest", "status": "completed", "conclusion": "success"},
    ]})]

    lines: list[str] = []
    outcome = mergewatch.watch(
        Path("."), "42", emit=lines.append, sleep=lambda s: pytest.fail("should not sleep"), now=lambda: 0.0,
    )
    assert outcome.state == "success"
    assert outcome.sha == "sha1"
    assert any("overall unknown -> success" in line for line in lines)


def test_watch_polls_until_red(fake_gh):
    fake_gh.pr_view_sequence = [
        _json_ok({"headRefOid": "sha1", "baseRefName": "main"}),
        _json_ok({"headRefOid": "sha1"}),
        _json_ok({"headRefOid": "sha1"}),
    ]
    fake_gh.required_checks = _json_ok({"contexts": ["pytest"]})
    fake_gh.check_runs_sequence = [
        _json_ok({"check_runs": [{"name": "pytest", "status": "in_progress"}]}),
        _json_ok({"check_runs": [{"name": "pytest", "status": "completed", "conclusion": "failure"}]}),
    ]

    lines: list[str] = []
    sleeps: list[float] = []
    outcome = mergewatch.watch(
        Path("."), "42", interval=5.0, emit=lines.append, sleep=sleeps.append, now=lambda: 0.0,
    )
    assert outcome.state == "failure"
    assert sleeps == [5.0]
    assert any("pytest: unseen -> pending" in line for line in lines)
    assert any("pytest: pending -> failure" in line for line in lines)
    assert any("overall pending -> failure" in line for line in lines)


def test_watch_warns_when_pr_head_moves(fake_gh):
    fake_gh.pr_view_sequence = [
        _json_ok({"headRefOid": "sha1", "baseRefName": "main"}),  # resolve_target
        _json_ok({"headRefOid": "sha2"}),  # PR moved on mid-watch
    ]
    fake_gh.required_checks = _json_ok({"contexts": ["pytest"]})
    fake_gh.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest", "status": "completed", "conclusion": "success"},
    ]})]

    lines: list[str] = []
    mergewatch.watch(Path("."), "42", emit=lines.append, sleep=lambda s: None, now=lambda: 0.0)
    assert any("WARNING PR #42 head moved to sha2" in line for line in lines)


def test_watch_settles_green_on_post_merge_sha_despite_pr_only_freshness(tmp_path, monkeypatch):
    """Reproduces the reported bug: a squash-merge sha linked to an already
    merged PR loads the base branch's required contexts (pytest matrix +
    the PR-only ``freshness`` check). ``freshness`` never posts on the push
    event, so it must not keep the watch pending forever."""
    root = _write_workflows(tmp_path, tests=_TESTS_WORKFLOW, continuity=_CONTINUITY_WORKFLOW)
    fake = _FakeGh()
    fake.required_checks = _json_ok({"contexts": ["pytest (3.12)", "freshness"]})

    def responder(cmd, cwd, *, timeout=20.0):
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    fake.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "completed", "conclusion": "success"},
    ]})]

    lines: list[str] = []
    outcome = mergewatch.watch(
        root, "28a96c25271fff06a19f858a8a8cf571ac97530b",
        emit=lines.append, sleep=lambda s: pytest.fail("should not sleep"), now=lambda: 0.0,
    )
    assert outcome.state == "success"
    assert not any("freshness" in line for line in lines)


def test_watch_post_merge_sha_still_pending_on_delayed_applicable_check(tmp_path, monkeypatch):
    """A push-triggered required check that simply hasn't posted yet must
    still block success — dropping the PR-only ``freshness`` context must
    not cause an early green for other, genuinely-applicable checks."""
    root = _write_workflows(tmp_path, tests=_TESTS_WORKFLOW, continuity=_CONTINUITY_WORKFLOW)
    fake = _FakeGh()
    fake.required_checks = _json_ok({"contexts": ["pytest (3.12)", "freshness"]})

    def responder(cmd, cwd, *, timeout=20.0):
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    fake.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "in_progress"},
    ]})]

    outcome = mergewatch.watch(
        root, "abc123def", timeout=0.0,
        emit=lambda line: None, sleep=lambda s: None, now=lambda: 0.0,
    )
    assert outcome.state == "timeout"


def test_watch_open_pr_still_waits_on_pull_request_only_context(tmp_path, fake_gh):
    """An actually-open PR's head sha legitimately gets a pull_request event
    — its PR-only required context must not be dropped."""
    root = _write_workflows(tmp_path, tests=_TESTS_WORKFLOW, continuity=_CONTINUITY_WORKFLOW)
    fake_gh.pr_view_sequence = [
        _json_ok({"headRefOid": "sha1", "baseRefName": "main", "state": "OPEN"}),  # resolve_target
        _json_ok({"headRefOid": "sha1"}),  # head-moved check inside the loop
    ]
    fake_gh.required_checks = _json_ok({"contexts": ["pytest (3.12)", "freshness"]})
    fake_gh.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "completed", "conclusion": "success"},
    ]})]

    outcome = mergewatch.watch(
        root, "42", timeout=0.0, emit=lambda line: None, sleep=lambda s: None, now=lambda: 0.0,
    )
    assert outcome.state == "timeout"


def test_watch_times_out(fake_gh):
    fake_gh.pr_view_sequence = [_json_ok({"headRefOid": "sha1", "baseRefName": "main"})] + [
        _json_ok({"headRefOid": "sha1"}) for _ in range(5)
    ]
    fake_gh.required_checks = _json_ok({"contexts": ["pytest"]})
    fake_gh.check_runs_sequence = [_json_ok({"check_runs": [{"name": "pytest", "status": "in_progress"}]})] * 5

    times = iter([0.0, 0.0, 1.0, 2.0, 10.0, 10.0])
    outcome = mergewatch.watch(
        Path("."), "42", interval=1.0, timeout=5.0,
        emit=lambda line: None, sleep=lambda s: None, now=lambda: next(times),
    )
    assert outcome.state == "timeout"
