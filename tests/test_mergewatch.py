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


def _git_workflow_responder(files: dict[str, str]):
    """Handlers for ``git ls-tree``/``git show`` simulating the workflow
    files as they existed AT the watched sha — never a real working tree, so
    tests can prove ``pr_only_contexts`` reads exact-sha evidence rather than
    the current checkout. Returns ``None`` for any other command so callers
    can chain it in front of their own responder."""
    def handle(cmd):
        if cmd[:2] == ["git", "ls-tree"]:
            return _Proc(0, "\n".join(f".github/workflows/{name}" for name in files))
        if cmd[:2] == ["git", "show"]:
            path = cmd[2].split(":", 1)[1]
            name = path.rsplit("/", 1)[-1]
            return _Proc(0, files[name]) if name in files else _Proc(1, stderr="not in tree at this sha")
        return None

    return handle


def test_pr_only_contexts_excludes_job_with_both_triggers(monkeypatch):
    monkeypatch.setattr(mergewatch, "_run", lambda cmd, cwd, timeout=20.0: _git_workflow_responder(
        {"tests.yml": _TESTS_WORKFLOW})(cmd))
    assert mergewatch.pr_only_contexts(Path("."), "sha1") == set()


def test_pr_only_contexts_includes_pull_request_only_job(monkeypatch):
    monkeypatch.setattr(mergewatch, "_run", lambda cmd, cwd, timeout=20.0: _git_workflow_responder(
        {"continuity.yml": _CONTINUITY_WORKFLOW})(cmd))
    assert mergewatch.pr_only_contexts(Path("."), "sha1") == {"freshness"}


def test_pr_only_contexts_across_workflows_matches_the_repo_scenario(monkeypatch):
    monkeypatch.setattr(mergewatch, "_run", lambda cmd, cwd, timeout=20.0: _git_workflow_responder(
        {"tests.yml": _TESTS_WORKFLOW, "continuity.yml": _CONTINUITY_WORKFLOW})(cmd))
    assert mergewatch.pr_only_contexts(Path("."), "sha1") == {"freshness"}


def test_pr_only_contexts_ignores_non_pull_request_workflows(monkeypatch):
    monkeypatch.setattr(mergewatch, "_run", lambda cmd, cwd, timeout=20.0: _git_workflow_responder(
        {"release.yml": _RELEASE_WORKFLOW})(cmd))
    assert mergewatch.pr_only_contexts(Path("."), "sha1") == set()


def test_pr_only_contexts_empty_when_ls_tree_unavailable(monkeypatch):
    """Fails safe: sha not present locally (e.g. shallow clone) yields no
    evidence, so nothing gets filtered — never a guess from stale/working-tree
    data."""
    monkeypatch.setattr(mergewatch, "_run", lambda cmd, cwd, timeout=20.0: _Proc(1, stderr="unknown revision"))
    assert mergewatch.pr_only_contexts(Path("."), "deadsha") == set()


def test_pr_only_contexts_empty_when_git_show_unavailable(monkeypatch):
    def responder(cmd, cwd, *, timeout=20.0):
        if cmd[:2] == ["git", "ls-tree"]:
            return _Proc(0, ".github/workflows/continuity.yml")
        if cmd[:2] == ["git", "show"]:
            return _Proc(1, stderr="fatal: path exists on disk, but not in 'sha1'")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(mergewatch, "_run", responder)
    assert mergewatch.pr_only_contexts(Path("."), "sha1") == set()


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


def test_watch_settles_green_on_post_merge_sha_despite_pr_only_freshness(monkeypatch):
    """Reproduces the reported bug: a squash-merge sha linked to an already
    merged PR loads the base branch's required contexts (pytest matrix +
    the PR-only ``freshness`` check). At the exact watched sha, ``freshness``
    was genuinely pull_request-only, so it never posts on the push event and
    must not keep the watch pending forever."""
    fake = _FakeGh()
    fake.required_checks = _json_ok({"contexts": ["pytest (3.12)", "freshness"]})
    git_handler = _git_workflow_responder({"tests.yml": _TESTS_WORKFLOW, "continuity.yml": _CONTINUITY_WORKFLOW})

    def responder(cmd, cwd, *, timeout=20.0):
        handled = git_handler(cmd)
        if handled is not None:
            return handled
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    fake.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "completed", "conclusion": "success"},
    ]})]

    lines: list[str] = []
    outcome = mergewatch.watch(
        Path("."), "28a96c25271fff06a19f858a8a8cf571ac97530b",
        emit=lines.append, sleep=lambda s: pytest.fail("should not sleep"), now=lambda: 0.0,
    )
    assert outcome.state == "success"
    assert not any("freshness" in line for line in lines)


def test_watch_post_merge_sha_still_pending_on_delayed_applicable_check(monkeypatch):
    """A push-triggered required check that simply hasn't posted yet must
    still block success — dropping the PR-only ``freshness`` context must
    not cause an early green for other, genuinely-applicable checks."""
    fake = _FakeGh()
    fake.required_checks = _json_ok({"contexts": ["pytest (3.12)", "freshness"]})
    git_handler = _git_workflow_responder({"tests.yml": _TESTS_WORKFLOW, "continuity.yml": _CONTINUITY_WORKFLOW})

    def responder(cmd, cwd, *, timeout=20.0):
        handled = git_handler(cmd)
        if handled is not None:
            return handled
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    fake.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "in_progress"},
    ]})]

    outcome = mergewatch.watch(
        Path("."), "abc123def", timeout=0.0,
        emit=lambda line: None, sleep=lambda s: None, now=lambda: 0.0,
    )
    assert outcome.state == "timeout"


def test_watch_open_pr_still_waits_on_pull_request_only_context(fake_gh):
    """An actually-open PR's head sha legitimately gets a pull_request event
    — its PR-only required context must not be dropped."""
    fake_gh.pr_view_sequence = [
        _json_ok({"headRefOid": "sha1", "baseRefName": "main", "state": "OPEN"}),  # resolve_target
        _json_ok({"headRefOid": "sha1"}),  # head-moved check inside the loop
    ]
    fake_gh.required_checks = _json_ok({"contexts": ["pytest (3.12)", "freshness"]})
    fake_gh.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "completed", "conclusion": "success"},
    ]})]

    outcome = mergewatch.watch(
        Path("."), "42", timeout=0.0, emit=lambda line: None, sleep=lambda s: None, now=lambda: 0.0,
    )
    assert outcome.state == "timeout"


_PUSH_ENABLED_CONTINUITY_WORKFLOW = _CONTINUITY_WORKFLOW.replace(
    "on:\n  pull_request:\n    branches: [main]\n",
    "on:\n  pull_request:\n    branches: [main]\n  push:\n    branches: [main]\n",
)
assert "push:" in _PUSH_ENABLED_CONTINUITY_WORKFLOW  # sanity: genuinely differs from _CONTINUITY_WORKFLOW


def _write_conflicting_checkout_workflow(tmp_path: Path, content: str) -> Path:
    """A REAL file on disk at ``tmp_path`` — used only to prove
    ``pr_only_contexts`` ignores the current checkout entirely and reads
    exclusively via ``git show <sha>:<path>`` (mocked separately)."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "continuity.yml").write_text(content)
    return tmp_path


def test_watch_filters_by_exact_sha_workflow_not_the_current_checkout(tmp_path, monkeypatch):
    """Regression: the CURRENT checkout's ``continuity.yml`` on disk says
    ``freshness`` has push enabled (if the code wrongly read the working
    tree, it would keep the context required and this test would time out).
    At the exact watched sha (``git show``, mocked), it was still
    pull_request-only — filtering must follow the sha's own history, so
    ``freshness`` gets dropped and the watch settles green."""
    root = _write_conflicting_checkout_workflow(tmp_path, _PUSH_ENABLED_CONTINUITY_WORKFLOW)
    fake = _FakeGh()
    fake.required_checks = _json_ok({"contexts": ["pytest (3.12)", "freshness"]})
    git_handler = _git_workflow_responder({
        "tests.yml": _TESTS_WORKFLOW,
        "continuity.yml": _CONTINUITY_WORKFLOW,  # pull_request-only AT this sha
    })

    def responder(cmd, cwd, *, timeout=20.0):
        handled = git_handler(cmd)
        if handled is not None:
            return handled
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    fake.check_runs_sequence = [_json_ok({"check_runs": [
        {"name": "pytest (3.12)", "status": "completed", "conclusion": "success"},
    ]})]  # freshness never posts; only the genuinely push-applicable pytest does

    outcome = mergewatch.watch(
        root, "abc123def", timeout=0.0,
        emit=lambda line: None, sleep=lambda s: None, now=lambda: 0.0,
    )
    assert outcome.state == "success"


def test_watch_does_not_filter_when_exact_sha_workflow_had_push_enabled(tmp_path, monkeypatch):
    """Inverse: the CURRENT checkout's ``continuity.yml`` on disk is
    pull_request-only (if the code wrongly read the working tree, it would
    drop the context and this test would falsely go green). At the exact
    watched sha it still had ``push`` enabled — the required context must
    stay required and never get dropped."""
    root = _write_conflicting_checkout_workflow(tmp_path, _CONTINUITY_WORKFLOW)
    fake = _FakeGh()
    fake.required_checks = _json_ok({"contexts": ["freshness"]})
    git_handler = _git_workflow_responder({"continuity.yml": _PUSH_ENABLED_CONTINUITY_WORKFLOW})

    def responder(cmd, cwd, *, timeout=20.0):
        handled = git_handler(cmd)
        if handled is not None:
            return handled
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    fake.check_runs_sequence = [_json_ok({"check_runs": []})]  # freshness never actually posted

    outcome = mergewatch.watch(
        root, "abc123def", timeout=0.0,
        emit=lambda line: None, sleep=lambda s: None, now=lambda: 0.0,
    )
    assert outcome.state == "timeout"  # still required, still missing -> pending -> timeout, never success


def test_watch_never_filters_when_exact_sha_workflow_evidence_is_unavailable(monkeypatch):
    """Fail-safe: if the exact-sha workflow files can't be read (e.g. a
    shallow clone missing that commit), nothing gets filtered — the original,
    sometimes-stuck-but-never-weakened required set is used as-is."""
    fake = _FakeGh()
    fake.required_checks = _json_ok({"contexts": ["freshness"]})

    def responder(cmd, cwd, *, timeout=20.0):
        if cmd[:2] == ["git", "ls-tree"]:
            return _Proc(1, stderr="fatal: Not a valid object name abc123def")
        if cmd[:2] == ["gh", "api"] and cmd[2].endswith("/pulls"):
            return _json_ok([{"number": 9, "state": "closed", "base": {"ref": "main"}}])
        return _FakeGh.__call__(fake, cmd, cwd, timeout=timeout)

    monkeypatch.setattr(mergewatch, "_run", responder)
    fake.check_runs_sequence = [_json_ok({"check_runs": []})]  # freshness never posted

    outcome = mergewatch.watch(
        Path("."), "abc123def", timeout=0.0,
        emit=lambda line: None, sleep=lambda s: None, now=lambda: 0.0,
    )
    assert outcome.state == "timeout"  # unfiltered required set still blocks on the missing context


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
