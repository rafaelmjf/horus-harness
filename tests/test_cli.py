"""Integration tests driving commands through the CLI entry point."""

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from horus import adapters, closure, config, github_catalog, launcher, mergewatch, registry, reinstall, remote_start, terminal_sessions, upgrade
from horus.cli import main
from horus.instructions import check_drift
from horus.registry import Registry, SessionRecord


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _run_id() -> str:
    records = Registry.default().all()
    assert len(records) == 1
    return records[0].session_id


def _git(root: Path, *args: str):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("hi\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "init")
    return root


def _write_v2_horus(root: Path):
    hdir = root / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "sessions").mkdir(exist_ok=True)
    (hdir / "temp").mkdir(exist_ok=True)
    (hdir / "project.md").write_text(
        "---\nstatus: active\ncurrent_focus: \"Project focus\"\nlast_updated: 2026-07-01\n---\n"
        "# Project\n\nA focused project vision.\n\n## Boundaries\n\nKeep it small.\n",
        encoding="utf-8",
    )
    (hdir / "roadmap.md").write_text(
        "---\nstatus: active\ncurrent_focus: \"Roadmap focus\"\nnext_action: \"Do next\"\n"
        "next_prompt: \"Resume from the migrated PRD.\"\nexecution_recommendation: \"continue-as-is\"\n"
        "last_updated: 2026-07-02\n---\n# Roadmap\n\n## Now\n\n- [ ] Open task\n- [x] Done task\n"
        "      Done continuation must not leak.\n\n## Later\n\n- [ ] Later task\n",
        encoding="utf-8",
    )
    (hdir / "features.md").write_text(
        "---\nstatus: active\nlast_updated: 2026-07-01\n---\n# Features\n\n## Shipped\n\n"
        "| Capability | Since | Notes |\n|---|---|---|\n| Dashboard | v1 | Shows state |\n\n## Planned\n\n| Capability | Notes |\n|---|---|\n",
        encoding="utf-8",
    )
    (hdir / "decisions.md").write_text(
        "# Decisions\n\n- **Repo-local memory** — continuity lives in git.\n",
        encoding="utf-8",
    )
    (hdir / "history.md").write_text("# History\n\n- One lesson.\n", encoding="utf-8")
    (hdir / "execution.md").write_text("# Execution\n\nIdle.\n", encoding="utf-8")


def _write_codex_rollout(home, project, *, total=910, window=1000):
    path = home / "sessions" / "2026" / "06" / "25" / "rollout-test.jsonl"
    path.parent.mkdir(parents=True)
    events = [
        {
            "timestamp": "2026-06-25T10:00:00Z",
            "type": "turn_context",
            "payload": {"cwd": str(project), "workspace_roots": [str(project)]},
        },
        {
            "timestamp": "2026-06-25T10:01:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {"total_tokens": total},
                    "model_context_window": window,
                },
                "rate_limits": {
                    "primary": {"used_percent": 12, "resets_at": 1782390000},
                    "secondary": {"used_percent": 34, "resets_at": 1782990000},
                },
            },
        },
    ]
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_session_new_creates_file_from_template(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])

    rc = main(["session", "new", "My Title", "--path", str(tmp_path), "--agent", "codex"])
    assert rc == 0
    files = list((tmp_path / ".horus" / "sessions").glob("*-my-title.md"))
    assert files, "session file not created"
    text = files[0].read_text(encoding="utf-8")
    assert "My Title" in text
    assert "status: in-progress" in text
    assert "agent: codex" in text


def test_session_new_uses_honest_unknown_when_runtime_is_ambiguous(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.delenv("HORUS_AGENT", raising=False)
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    main(["init", str(tmp_path), "--yes"])

    assert main(["session", "new", "Unknown Runtime", "--path", str(tmp_path)]) == 0
    note = next((tmp_path / ".horus" / "sessions").glob("*-unknown-runtime.md"))
    text = note.read_text(encoding="utf-8")
    assert "agent: unknown" in text
    assert "account: unknown" in text


def test_session_new_refuses_without_horus(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert main(["session", "new", "X", "--path", str(tmp_path)]) == 1


def _stamp_prd(tmp_path, floor: str):
    hdir = tmp_path / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "sessions").mkdir(exist_ok=True)
    (hdir / "PRD.md").write_text(
        f"---\nstatus: active\nhorus_min_version: {floor}\nlast_updated: 2026-07-08\n---\n\n# P\n",
        encoding="utf-8",
    )


def test_version_floor_refuses_mutating_command(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    monkeypatch.delenv("HORUS_IGNORE_VERSION_FLOOR", raising=False)
    _stamp_prd(tmp_path, "9.9.9")

    rc = main(["session", "new", "X", "--path", str(tmp_path)])
    assert rc == 4
    err = capsys.readouterr().err
    assert "9.9.9" in err and "uv tool install" in err
    # Gate ran before the mutation: no session file written.
    assert not list((tmp_path / ".horus" / "sessions").glob("*.md"))


def test_version_floor_override_env_bypasses(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.setenv("HORUS_IGNORE_VERSION_FLOOR", "1")
    _stamp_prd(tmp_path, "9.9.9")

    rc = main(["session", "new", "X", "--path", str(tmp_path)])
    assert rc == 0
    assert list((tmp_path / ".horus" / "sessions").glob("*-x.md"))


def test_version_floor_allows_when_met(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    monkeypatch.delenv("HORUS_IGNORE_VERSION_FLOOR", raising=False)
    _stamp_prd(tmp_path, "0.0.1")

    assert main(["session", "new", "X", "--path", str(tmp_path)]) == 0


def test_doctor_project_warns_for_missing_declared_machine_requirement(
    tmp_path, monkeypatch, capsys
):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills", "--no-hooks"])
    (tmp_path / ".horus" / "requirements.md").write_text(
        """---
kind: machine-requirements
tools:
  - name: Definitely absent CLI
    probe: horus-definitely-absent-cli
    install: install the project CLI
    needed_for: project builds
configs: []
---
""",
        encoding="utf-8",
    )
    capsys.readouterr()

    assert main(["doctor", "project", "--path", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "machine requirement missing: Definitely absent CLI" in out
    assert "needed for project builds" in out
    assert "install: install the project CLI" in out


def test_focus_running_session_calls_raiser(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    Registry.default().upsert(SessionRecord(
        session_id="abc12345def", agent="claude", project="/p",
        account="work", pid=os.getpid(), status="running",  # live pid -> stays running
    ))
    raised = {}
    monkeypatch.setattr(launcher, "focus_window_for_pid", lambda pid: raised.setdefault("pid", pid) or True)

    assert main(["focus", "abc123"]) == 0          # prefix match
    assert raised["pid"] == os.getpid()
    assert "Focused" in capsys.readouterr().out


def test_focus_unknown_and_not_running(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["focus", "nope"]) == 2            # no match
    assert "No session" in capsys.readouterr().out

    Registry.default().upsert(SessionRecord(
        session_id="dead0001", agent="claude", project="/p", pid=None, status="running",
    ))  # pid-less running -> reconcile -> stale -> not focusable
    assert main(["focus", "dead0001"]) == 1
    assert "not running" in capsys.readouterr().out


def test_focus_window_for_pid_safe_on_no_pid():
    assert launcher.focus_window_for_pid(None) is False
    assert launcher.focus_window_for_pid(0) is False


def test_dashboard_reload_delegates_to_lifecycle_helper(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        "horus.cli.companion.reload_dashboard",
        lambda host, port: calls.append((host, port)) or (True, "Dashboard reloaded"),
    )

    assert main(["dashboard", "--host", "127.0.0.1", "--port", "8771", "--reload"]) == 0
    assert calls == [("127.0.0.1", 8771)]
    assert "Dashboard reloaded" in capsys.readouterr().out


def test_fleet_prints_one_line_per_project_with_next_step_and_skips_cockpit(
    tmp_path, monkeypatch, capsys,
):
    project = tmp_path / "widget"
    cockpit = tmp_path / "horus-agent"
    monkeypatch.setattr(config, "load_projects", lambda: [str(project), str(cockpit)])

    def fake_load(path):
        root = Path(path)
        assert root.name != "horus-agent"
        return {
            "name": root.name,
            "git": {
                "branch": "main", "commit": {"rel": "2 hours ago"},
                "upstream": "origin/main", "behind": 1, "ahead": 0, "dirty": False,
            },
            "latest": {"date": "2026-07-10", "summary": "Shipped the widget"},
            "current_focus": "Fleet dispatch",
            "next_action": "Land the next ticket",
            "next_prompt": "Resume the widget.",
            "continuity_source": ".horus/PRD.md (working checkout)",
        }

    monkeypatch.setattr("horus.cli.dashboard.load_project", fake_load)
    monkeypatch.setattr("horus.cli.fetchcheck.fetch_and_state", lambda root, **kw: None)

    assert main(["fleet"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert lines[0] == (
        "widget | git: main · 2 hours ago · behind 1 | "
        "src: .horus/PRD.md (working checkout) | "
        "last: 2026-07-10 — Shipped the widget | focus: Fleet dispatch | "
        "next: Land the next ticket | prompt: Resume the widget."
    )


def test_fleet_and_status_fetch_readonly_before_reading_git_state(tmp_path, monkeypatch, capsys):
    """`fleet` and `status` must refresh remotes (fetch) before rendering git state,
    but only ever fetch — never anything that could mutate the working tree."""
    project = tmp_path / "widget"
    monkeypatch.setattr(config, "load_projects", lambda: [str(project)])
    monkeypatch.setattr("horus.cli.dashboard.load_project", lambda path: {
        "name": Path(path).name, "git": None, "latest": None,
    })
    fetched = []
    monkeypatch.setattr("horus.cli.fetchcheck.fetch_and_state", lambda root, **kw: fetched.append(root) or None)

    assert main(["fleet"]) == 0
    assert main(["status"]) == 0

    assert fetched == [project, project]  # one read-only fetch per project, per command


def test_fleet_and_status_flag_gone_branch_without_mutating_the_working_tree(
    tmp_path, monkeypatch, capsys,
):
    """End-to-end regression for the concrete failure this feature targets: a
    working checkout left on a branch whose upstream was merged and deleted (the
    GitHub squash-merge pattern) must be visibly flagged as `gone`, its continuity
    source named, and reading this state must never fetch-then-pull or otherwise
    touch the working tree.
    """
    _home(tmp_path, monkeypatch)
    from horus import initialize

    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
    project = tmp_path / "widget"
    subprocess.run(["git", "clone", str(origin), str(project)], check=True, capture_output=True)
    _git(project, "config", "user.email", "t@example.com")
    _git(project, "config", "user.name", "Test")
    initialize.init_project(project, assume_yes=True)
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "init")
    _git(project, "push", "origin", "main")

    _git(project, "checkout", "-b", "feature")
    (project / "note.txt").write_text("feature work\n", encoding="utf-8")
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "feature work")
    _git(project, "push", "-u", "origin", "feature")

    # GitHub-style merge: the remote branch is deleted while the local checkout
    # stays on it — exactly the misleading state this feature must catch.
    subprocess.run(["git", "-C", str(origin), "branch", "-D", "feature"], check=True, capture_output=True)

    monkeypatch.setattr(config, "load_projects", lambda: [str(project)])

    before_head = _git(project, "rev-parse", "HEAD").stdout.strip()
    before_branch = _git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    before_status = _git(project, "status", "--porcelain").stdout

    assert main(["fleet"]) == 0
    fleet_out = capsys.readouterr().out
    assert main(["status"]) == 0
    status_out = capsys.readouterr().out

    after_head = _git(project, "rev-parse", "HEAD").stdout.strip()
    after_branch = _git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    after_status = _git(project, "status", "--porcelain").stdout

    # No mutation: same HEAD, same branch, same (clean) status before and after.
    assert after_head == before_head
    assert after_branch == before_branch
    assert after_status == before_status == ""

    # Proof a real fetch happened (not just a stale local read): the deleted
    # remote branch's tracking ref was pruned.
    prune_check = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--verify", "-q", "refs/remotes/origin/feature"],
        capture_output=True, text=True,
    )
    assert prune_check.returncode != 0

    assert "⚠ upstream gone" in fleet_out
    assert "⚠ upstream gone" in status_out
    assert "src: .horus/PRD.md (working checkout)" in fleet_out
    assert "source: .horus/PRD.md (working checkout)" in status_out


def test_sessions_cmd_lists_and_prunes(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus.registry import Registry, SessionRecord
    reg = Registry.default()  # ~/.horus/registry.json under the patched HOME
    reg.upsert(SessionRecord(session_id="abc123", agent="claude", project="/proj", pid=None, status="running"))

    assert main(["sessions"]) == 0
    out = capsys.readouterr().out
    assert "abc123" in out
    assert "stale" in out  # reconcile flipped pid-less "running" -> stale

    assert main(["sessions", "--prune"]) == 0
    assert reg.all() == []


def test_sessions_default_view_hides_long_stale_rows_behind_all_flag(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    reg = Registry.default()
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(timespec="seconds")
    reg.upsert(
        SessionRecord(session_id="ancient", agent="claude", project="/proj", pid=999999, status="exited", returncode=0),
        now=old_ts,
    )
    reg.upsert(SessionRecord(session_id="fresh", agent="claude", project="/proj", pid=os.getpid(), status="running"))

    assert main(["sessions"]) == 0
    out = capsys.readouterr().out
    assert "fresh" in out
    assert "ancient" not in out
    assert "1 older session(s) hidden" in out

    assert main(["sessions", "--all"]) == 0
    out_all = capsys.readouterr().out
    assert "ancient" in out_all and "fresh" in out_all


def test_sessions_running_sorted_before_recent_terminal_rows(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    reg = Registry.default()
    # Upserted in this order so a plain recency sort would put "done-recent"
    # first; the running-first tiebreak must still surface "running-now" above it.
    reg.upsert(SessionRecord(session_id="running-now", agent="claude", project="/proj", pid=os.getpid(), status="running"))
    reg.upsert(SessionRecord(session_id="done-recent", agent="claude", project="/proj", pid=999999, status="exited", returncode=0))

    assert main(["sessions"]) == 0
    out = capsys.readouterr().out
    assert out.index("running-now") < out.index("done-recent")


def _bare_origin_and_worker_clone(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
    worker = tmp_path / "worker"
    subprocess.run(["git", "clone", str(origin), str(worker)], check=True, capture_output=True)
    _git(worker, "config", "user.email", "t@example.com")
    _git(worker, "config", "user.name", "Test")
    (worker / "README.md").write_text("hi\n", encoding="utf-8")
    _git(worker, "add", "-A")
    _git(worker, "commit", "-m", "init")
    _git(worker, "push", "origin", "main")
    return worker


def _patch_gh(monkeypatch, stdout: str) -> None:
    """Fake `gh` only; every `git` call passes through to the real subprocess.run
    (same module object every `import subprocess` binds to, so a blanket patch
    would also swallow this test's own git fixture setup)."""
    from horus import integration as intmod

    real_run = subprocess.run

    def fake(cmd, *a, **k):
        if cmd and cmd[0] == "gh":
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
        return real_run(cmd, *a, **k)

    monkeypatch.setattr(intmod.subprocess, "run", fake)


def test_sessions_renders_delivery_receipt_for_failed_but_delivered_worker(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    worker = _bare_origin_and_worker_clone(tmp_path)
    _git(worker, "checkout", "-b", "worker/feature")
    (worker / "f.txt").write_text("work", encoding="utf-8")
    _git(worker, "add", "-A")
    _git(worker, "commit", "-m", "do work")
    (worker / ".horus").mkdir()
    (worker / ".horus" / "PRD.md").write_text("# PRD\n", encoding="utf-8")
    _git(worker, "add", "-A")
    _git(worker, "commit", "-m", "Update Horus continuity (closure)")
    _git(worker, "push", "-u", "origin", "worker/feature")
    _patch_gh(monkeypatch, '[{"number": 4, "url": "https://gh/pr/4", "state": "OPEN", "title": "x"}]')

    reg = Registry.default()
    reg.upsert(SessionRecord(
        session_id="worker1", agent="claude", project=str(worker), pid=None, status="failed", returncode=1,
    ))

    assert main(["sessions"]) == 0
    out = capsys.readouterr().out
    assert "failed" in out and "worker1" in out  # the real, non-clean status is kept, not papered over
    assert "failed-but-delivered" in out
    assert "pushed " in out
    assert "PR #4" in out
    assert "continuity closed" in out


def test_sessions_plain_failure_when_nothing_delivered(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _patch_gh(monkeypatch, "[]")
    reg = Registry.default()
    reg.upsert(SessionRecord(
        session_id="nodeliver", agent="claude", project=str(tmp_path / "gone"), pid=None,
        status="failed", returncode=1,
    ))

    assert main(["sessions"]) == 0
    out = capsys.readouterr().out
    assert "nodeliver" in out
    assert "but-delivered" not in out


def test_session_new_records_alias_not_email(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")
    main(["init", str(tmp_path), "--yes"])

    assert main(["session", "new", "Alias Test", "--path", str(tmp_path), "--agent", "claude"]) == 0
    text = list((tmp_path / ".horus" / "sessions").glob("*-alias-test.md"))[0].read_text(encoding="utf-8")
    assert "rafael@example.com" not in text  # raw email never written
    assert "account: acct-" in text          # aliased instead


def test_execution_prompt_uses_roadmap_and_target(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    # Fresh init scaffolds structure v3 (PRD.md); the focus/handoff fields are
    # PRD-first, so author them there rather than in a (now absent) roadmap.md.
    (tmp_path / ".horus" / "PRD.md").write_text(
        '---\nnext_action: "Implement phase routing"\n'
        'execution_recommendation: "plan-execution - cross-module work"\n---\n# PRD\n',
        encoding="utf-8",
    )
    (tmp_path / ".horus" / "execution.md").write_text(
        '---\nstatus: active\ncurrent_feature: "Phase routing"\n---\n# Execution\n',
        encoding="utf-8",
    )

    assert main(["execution", "prompt", "--path", str(tmp_path), "--target", "codex"]) == 0
    out = capsys.readouterr().out
    assert "Target agent: codex" in out
    assert "Implement phase routing" in out
    assert "Codex subagents" in out
    assert "testing model separation" in out
    assert "do not implement the delegated phase in the supervisor context" in out
    assert "volume × ambiguity" in out  # decision rubric drives the recommendation
    assert "stay inline for small" in out
    assert "delegation_basis" in out
    assert "worker_tier` alone is only a tier hint" in out


def test_execution_handoff_creates_temp_note_and_refuses_clobber(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])

    rc = main([
        "execution", "handoff", "1A",
        "--path", str(tmp_path),
        "--title", "First phase",
        "--agent", "sonnet-worker",
        "--model-tier", "standard",
    ])

    assert rc == 0
    note = tmp_path / ".horus" / "temp" / "1A.md"
    assert note.is_file()
    text = note.read_text(encoding="utf-8")
    assert "phase: 1A" in text
    assert 'title: "First phase"' in text
    assert "agent: sonnet-worker" in text
    assert "model_tier: standard" in text

    assert main(["execution", "handoff", "1A", "--path", str(tmp_path)]) == 1
    assert "Already exists" in capsys.readouterr().out


def test_execution_handoff_carries_gate_and_prd_durable_updates(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])  # scaffolds structure v3
    assert main(["execution", "handoff", "2B", "--path", str(tmp_path)]) == 0
    text = (tmp_path / ".horus" / "temp" / "2B.md").read_text(encoding="utf-8")
    assert "## Gate" in text
    assert "reruns this verbatim" in text
    assert "Pre-existing failure baseline" in text
    assert "PRD.md backlog:" in text
    assert "features.md:" not in text  # six-lane suggestions dropped on v3


def test_execution_handoff_six_lane_durable_updates_unchanged(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "roadmap.md").write_text("---\nstatus: active\n---\n# R\n", encoding="utf-8")
    assert main(["execution", "handoff", "2B", "--path", str(tmp_path)]) == 0
    text = (hdir / "temp" / "2B.md").read_text(encoding="utf-8")
    assert "## Gate" in text  # the gate contract applies to both structures
    assert "roadmap.md:" in text
    assert "features.md:" in text
    assert "PRD.md backlog:" not in text


def test_session_new_uses_configured_alias(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")
    config.set_account_alias("rafael@example.com", "rafa-personal")
    main(["init", str(tmp_path), "--yes"])

    main(["session", "new", "Named", "--path", str(tmp_path), "--agent", "claude"])
    text = list((tmp_path / ".horus" / "sessions").glob("*-named.md"))[0].read_text(encoding="utf-8")
    assert "account: rafa-personal" in text


def test_session_new_codex_uses_codex_account_alias(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, codex_usage, config
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "wrong-claude")
    monkeypatch.setattr(codex_usage, "current_account", lambda *a, **k: "codex-account-id")
    config.set_account_alias("codex-account-id", "luna-codex")
    main(["init", str(tmp_path), "--yes"])

    main(["session", "new", "Codex Account", "--path", str(tmp_path), "--agent", "codex"])
    text = next((tmp_path / ".horus" / "sessions").glob("*-codex-account.md")).read_text(encoding="utf-8")
    assert "agent: codex" in text
    assert "account: luna-codex" in text
    assert "wrong-claude" not in text


def test_account_command_show_and_set(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")

    assert main(["account", "--set", "rafa-personal"]) == 0
    assert config.load_account_aliases()["rafael@example.com"] == "rafa-personal"

    capsys.readouterr()
    assert main(["account"]) == 0
    out = capsys.readouterr().out
    assert "rafa-personal" in out and "rafael@example.com" in out  # show reveals both locally


def test_run_fake_adapter_tracks_session(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus.registry import Registry

    rc = main(["run", "hello there", "--agent", "fake", "--path", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "(fake) hello there" in out and "exited" in out
    recs = Registry.default().all()
    assert len(recs) == 1 and recs[0].agent == "fake"  # spawned session was tracked
    assert recs[0].session_id != "fake-session" and recs[0].agent_session_id == "fake-session"
    assert recs[0].delivery_status == "unknown" and recs[0].last_activity_at


def test_run_resume_uses_session_id(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["run", "continue", "--agent", "fake", "--resume", "prev-99", "--path", str(tmp_path)])
    assert rc == 0
    rec = Registry.default().all()[0]
    assert rec.agent_session_id == "prev-99" and rec.session_id in capsys.readouterr().out


def test_run_tees_event_stream_to_session_log(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import runlog

    rc = main(["run", "hello there", "--agent", "fake", "--path", str(tmp_path)])
    assert rc == 0
    run_id = _run_id()
    text = runlog.run_log_path(run_id).read_text(encoding="utf-8")
    assert "... session fake-session" in text  # session start marker
    assert "(fake) hello there" in text        # assistant text
    assert f"exited — session {run_id}" in text  # final status line


def test_tail_prints_log_and_final_status(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import runlog

    reg = Registry.default()
    reg.upsert(SessionRecord(
        session_id="fake-session", agent="fake", project=tmp_path.as_posix(),
        status="exited", returncode=0,
    ))
    path = runlog.run_log_path("fake-session")
    path.parent.mkdir(parents=True)
    path.write_text("... session fake-session\n(fake) hello there\n", encoding="utf-8")

    rc = main(["tail", "fake-ses"])  # prefix match, like git short hashes
    assert rc == 0
    out = capsys.readouterr().out
    assert "(fake) hello there" in out                 # the log so far
    assert "exited — session fake-session" in out      # final status from the registry
    assert "rc=0" in out


def test_tail_unknown_session_fails_clearly(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["tail", "nope"]) == 2
    assert "No session matching" in capsys.readouterr().out


def test_tail_no_args_resolves_most_recent_running(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    import pytest
    from horus.cli import _resolve_tail_session

    reg = Registry.default()
    with pytest.raises(LookupError):
        _resolve_tail_session(reg, None)  # nothing running yet

    proj = tmp_path.as_posix()
    reg.upsert(
        SessionRecord(session_id="old-run", agent="fake", project=proj, pid=os.getpid()),
        now="2026-07-03T10:00:00",
    )
    reg.upsert(
        SessionRecord(session_id="new-run", agent="fake", project=proj, pid=os.getpid()),
        now="2026-07-03T11:00:00",
    )
    reg.upsert(SessionRecord(session_id="done-run", agent="fake", project=proj, status="exited"),
               now="2026-07-03T12:00:00")
    assert _resolve_tail_session(reg, None).session_id == "new-run"


def test_run_watch_opens_watcher_terminal(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: calls.append((argv, cwd)) or 4242)

    rc = main(["run", "hello", "--agent", "fake", "--watch", "--path", str(tmp_path)])
    assert rc == 0
    assert len(calls) == 1  # spawned once, on the first event carrying the session id
    argv, cwd = calls[0]
    assert argv == ["horus", "tail", _run_id()]  # console-script spelling only
    assert Path(cwd) == tmp_path.resolve()


def test_run_watch_failure_never_breaks_the_run(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)

    def boom(argv, cwd, env=None):
        raise OSError("no graphical display detected")

    monkeypatch.setattr(launcher, "open_terminal", boom)
    rc = main(["run", "hello", "--agent", "fake", "--watch", "--path", str(tmp_path)])
    assert rc == 0  # the run's exit code is the session's, not the watcher's
    out = capsys.readouterr().out
    assert "continuing headless" in out and "exited" in out


def test_run_detach_requires_managed_tmux_worker(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["run", "hello", "--agent", "fake", "--detach", "--path", str(tmp_path)]) == 2
    assert "requires --worker and --target tmux" in capsys.readouterr().out


def test_run_detach_preallocates_horus_id_before_managed_handoff(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    captured = {}

    def detached(request):
        captured["request"] = request
        return terminal_sessions.launch.LaunchResult(
            True, request.agent, request.project, account=request.account,
            session_id=request.session_id, pid=5150, target_ref=f"horus-{request.session_id[:12]}",
        )

    monkeypatch.setattr(terminal_sessions, "launch_detached_run", detached)
    assert main([
        "run", "hello", "--worker", "codex", "--target", "tmux", "--detach",
        "--resume", "native-thread", "--path", str(tmp_path),
    ]) == 0
    request = captured["request"]
    assert len(request.session_id) == 36 and request.resume == "native-thread"
    assert request.worker is True and request.posture == "auto-edit"
    assert request.dispatch_base_sha is None
    assert request.session_id in capsys.readouterr().out


def test_open_launches_and_tracks_running_session(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import launcher, registry
    from horus.registry import Registry

    monkeypatch.setattr(launcher, "open_terminal", lambda argv, cwd, env=None: 9999)
    monkeypatch.setattr(registry, "process_alive", lambda pid: pid == 9999)
    rc = main(["open", str(tmp_path), "--agent", "fake", "--account", "demo"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Opened fake session" in out and "demo" in out

    recs = Registry.default().all()
    assert len(recs) == 1
    r = recs[0]
    assert r.status == "running" and r.pid == 9999 and r.account == "demo" and r.agent == "fake"


def test_brainstorm_launches_scoped_tracked_session(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus.registry import Registry

    proj = tmp_path / "demo"
    proj.mkdir()
    main(["init", str(proj), "--yes"])

    captured = {}
    monkeypatch.setattr(
        launcher, "open_terminal",
        lambda argv, cwd, env=None: captured.update(argv=argv) or 4321,
    )
    from horus import registry as registry_mod
    monkeypatch.setattr(registry_mod, "process_alive", lambda pid: pid == 4321)
    rc = main(["brainstorm", "offline sync", "--path", str(proj), "--agent", "fake"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Started brainstorm on demo" in out
    assert ".horus/temp/brainstorm-offline-sync.md" in out

    # Same shared launch path: a tracked running session, seeded with the scoped prompt.
    assert captured["argv"][-1].startswith("Brainstorm session for the demo project.")
    recs = Registry.default().all()
    assert len(recs) == 1 and recs[0].status == "running" and recs[0].agent == "fake"
    assert (proj / ".horus" / "temp").is_dir()


def test_brainstorm_without_horus_dir_refuses(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["brainstorm", "a topic", "--path", str(tmp_path)])
    assert rc == 1
    assert "run `horus init` first" in capsys.readouterr().out


def test_run_account_mismatch_refuses(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    import json
    from horus import config

    cfgdir = tmp_path / "work-dir"
    cfgdir.mkdir()
    (cfgdir / ".claude.json").write_text(
        json.dumps({"oauthAccount": {"emailAddress": "real@work.com"}}), encoding="utf-8"
    )
    config.set_account_alias("real@work.com", "actually-work")
    config.set_account_config_dir("work", str(cfgdir))  # "work" maps to a dir logged in as someone else

    rc = main(["run", "hi", "--agent", "claude", "--account", "work", "--path", str(tmp_path)])
    assert rc == 2  # guard refused before any subprocess
    assert "Refusing to run" in capsys.readouterr().out


def test_account_set_dir_maps_config_dir(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import claude_usage, config
    monkeypatch.setattr(claude_usage, "current_account", lambda *a, **k: "rafael@example.com")
    config.set_account_alias("rafael@example.com", "rafa-personal")

    assert main(["account", "--set-dir", "/home/rafa/.claude-personal"]) == 0
    assert config.load_account_config_dirs() == {"rafa-personal": "/home/rafa/.claude-personal"}

    capsys.readouterr()
    assert main(["account"]) == 0
    assert "/home/rafa/.claude-personal" in capsys.readouterr().out  # surfaced in show


def test_close_runs_and_returns_status(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["close", "--path", str(tmp_path)]) in (0, 1)


def test_close_commit_rechecks_post_commit_state(tmp_path, monkeypatch, capsys):
    """A successful git commit is not a successful close when continuity is dirty again."""
    from horus import cli, closure
    from horus.continuity import Finding

    monkeypatch.setattr(cli, "_enforce_version_floor", lambda root: None)
    events = []
    monkeypatch.setattr(
        closure,
        "closure_status",
        lambda *args, **kwargs: (
            events.append("status")
            or [Finding("warn", "1 uncommitted continuity file(s): .horus/PRD.md")]
        ),
    )
    monkeypatch.setattr(
        closure,
        "commit_continuity",
        lambda *args, **kwargs: (
            events.append("commit")
            or (
                True,
                "committed 1 file(s); WARNING: residual dirty continuity after commit: .horus/PRD.md",
            )
        ),
    )

    assert main(["close", "--commit", "--path", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert events == ["commit", "status"]
    assert "residual dirty continuity" in out
    assert "Action needed" in out


def test_close_commit_accepts_fresh_recomputed_state(tmp_path, monkeypatch, capsys):
    from horus import cli, closure
    from horus.continuity import Finding

    monkeypatch.setattr(cli, "_enforce_version_floor", lambda root: None)
    events = []
    monkeypatch.setattr(
        closure,
        "closure_status",
        lambda *args, **kwargs: (
            events.append("status")
            or [Finding("ok", "continuity files committed"), Finding("ok", "working tree clean")]
        ),
    )
    monkeypatch.setattr(
        closure,
        "commit_continuity",
        lambda *args, **kwargs: (
            events.append("commit") or (True, "committed 1 file(s); pushed")
        ),
    )

    assert main(["close", "--commit", "--push", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert events == ["commit", "status"]
    assert "--commit: committed 1 file(s); pushed" in out
    assert "uncommitted continuity" not in out
    assert "Action needed" not in out
    assert "Continuity captured" in out
    assert "Closure ritual" not in out


def test_close_commit_push_real_repo_prints_only_final_state(tmp_path, monkeypatch, capsys):
    """The acting close's user-visible verdict describes the pushed checkpoint."""
    from tests.test_routines import _mk_fresh_v3

    _home(tmp_path, monkeypatch)
    repo = _init_repo(tmp_path / "repo")
    _mk_fresh_v3(repo)
    (repo / ".gitignore").write_text(".horus/.consolidated-to\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "add continuity")

    remote = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")

    prd = repo / ".horus" / "PRD.md"
    prd.write_text(prd.read_text(encoding="utf-8") + "\n<!-- close me -->\n", encoding="utf-8")

    assert main(["close", "--commit", "--push", "--path", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "--commit: committed" in out and "; pushed" in out
    assert "uncommitted continuity" not in out
    assert "uncommitted change" not in out
    assert "Action needed" not in out
    assert "Continuity captured" in out
    assert "Closure ritual" not in out
    assert not _git(repo, "status", "--porcelain").stdout
    assert _git(repo, "rev-parse", "HEAD").stdout == _git(repo, "rev-parse", "origin/main").stdout


def test_close_v3_uses_short_boundary_prompt_not_retired_six_lane_ritual(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    capsys.readouterr()

    main(["close", "--path", str(tmp_path)])
    out = capsys.readouterr().out

    assert "Continuity boundary - fold the campaign once" in out
    assert "Update PRD.md" in out
    assert "project.md `current_focus`" not in out
    assert "roadmap.md" not in out


def test_close_check_gates_on_freshness(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from tests.test_routines import _mk_fresh

    # Fresh lanes (current last_updated, authored NEXT/focus), non-git tmp -> gate passes.
    _mk_fresh(tmp_path)
    assert main(["close", "--check", "--path", str(tmp_path)]) == 0
    assert "Fresh" in capsys.readouterr().out

    # Stale lanes (last_updated older than the session) -> gate fails non-zero.
    _mk_fresh(tmp_path, proj_updated="2026-06-01", road_updated="2026-06-01")
    assert main(["close", "--check", "--path", str(tmp_path)]) == 1
    assert "Stale" in capsys.readouterr().out


def test_usage_check_cli_warns_and_codex_stop_hook_blocks_with_json(tmp_path, monkeypatch, capsys):
    import io

    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    _write_codex_rollout(codex_home, tmp_path)
    monkeypatch.setattr("horus.native_hooks.tempfile.gettempdir", lambda: str(tmp_path))

    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90"]) == 1
    capsys.readouterr()
    monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id":"codex-stop","hook_event_name":"Stop"}'))
    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90", "--hook"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    reason = payload["reason"]
    assert "horus-consolidate" in reason
    assert "ASK" in reason or "ask the user" in reason  # prompt, don't force-close
    assert "horus close --commit --push" in reason  # closure always pushes


def test_usage_check_uses_fresh_account_limits_not_stale_project_limits(tmp_path, monkeypatch, capsys):
    """Rate limits are account-global; project context remains project-scoped."""
    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    _write_codex_rollout(codex_home, tmp_path, total=500)

    # The only rollout for this project has an expired 83% snapshot.
    project_rollout = next((codex_home / "sessions").rglob("rollout-*.jsonl"))
    events = [json.loads(line) for line in project_rollout.read_text(encoding="utf-8").splitlines()]
    events[-1]["payload"]["rate_limits"] = {
        "primary": {"used_percent": 83, "resets_at": 1},
        "secondary": {"used_percent": 83, "resets_at": 1},
    }
    project_rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    # A newer rollout from another project is the account's current snapshot.
    fresh_reset = 2_000_000_000
    account_rollout = codex_home / "sessions" / "2026" / "07" / "12" / "rollout-account.jsonl"
    account_rollout.parent.mkdir(parents=True)
    account_rollout.write_text(json.dumps({
        "timestamp": "2026-07-12T12:00:00Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {"last_token_usage": {"total_tokens": 100}, "model_context_window": 1000},
            "rate_limits": {
                "primary": {"used_percent": 56, "resets_at": fresh_reset},
                "secondary": {"used_percent": 42, "resets_at": fresh_reset},
            },
        },
    }) + "\n", encoding="utf-8")

    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90"]) == 0
    out = capsys.readouterr().out
    assert "Codex context 50.0%" in out
    assert "5h limit 56%" in out
    assert "weekly limit 42%" in out
    assert "83%" not in out


def test_codex_userpromptsubmit_hook_defers_to_user(tmp_path, monkeypatch, capsys):
    import io

    _home(tmp_path, monkeypatch)
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    _write_codex_rollout(codex_home, tmp_path)
    monkeypatch.setattr("horus.native_hooks.tempfile.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO('{"session_id":"codex-prompt","hook_event_name":"UserPromptSubmit"}'),
    )

    assert main(["usage", "check", "--path", str(tmp_path), "--threshold", "90", "--hook"]) == 0
    payload = json.loads(capsys.readouterr().out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "UserPromptSubmit"
    ctx = hso["additionalContext"]
    assert "horus-consolidate" in ctx
    assert "context, not a command" in ctx  # defer to the user's request
    assert "horus close --commit --push" in ctx


def test_hook_install_codex_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert main(["hook", "install", "--path", str(tmp_path), "--target", "codex"]) == 0
    hooks_text = (tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8")
    assert '"Stop"' in hooks_text
    assert "horus usage check" in hooks_text
    assert "commandWindows" in hooks_text  # PowerShell-guarded Windows variant


def test_hook_install_codex_merge_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert main(["hook", "install", "--path", str(tmp_path), "--target", "codex", "--kind", "merge"]) == 0
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash"
    assert group["hooks"][0]["command"] == "horus close --hook || exit 0"
    assert "Get-Command horus" in group["hooks"][0]["commandWindows"]


def test_hook_install_codex_guard_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert main(["hook", "install", "--path", str(tmp_path), "--target", "codex", "--kind", "guard"]) == 0
    data = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    group = data["hooks"]["PreToolUse"][0]
    assert group["matcher"] == "Bash"
    assert group["hooks"][0]["command"] == "horus guard-host --hook || exit 0"
    assert "Get-Command horus" in group["hooks"][0]["commandWindows"]


def test_upgrade_project_cli_dry_run_reports_pending(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".codex" / "hooks.json").unlink(missing_ok=True)

    rc = main(["upgrade-project", "--path", str(tmp_path), "--target", "codex", "--no-skills", "--no-instructions"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "Dry run only" in out
    assert "would-update" in out
    assert not (tmp_path / ".codex" / "hooks.json").exists()


def test_upgrade_project_cli_apply_writes(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    initialize.init_project(tmp_path, assume_yes=True)
    (tmp_path / ".codex" / "hooks.json").unlink(missing_ok=True)

    rc = main(["upgrade-project", "--path", str(tmp_path), "--target", "codex", "--no-skills", "--no-instructions", "--apply"])

    assert rc == 0
    assert (tmp_path / ".codex" / "hooks.json").exists()
    assert "Applying Horus project projections" in capsys.readouterr().out


def test_upgrade_project_apply_untracks_legacy_checkpoint_marker(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Tester"], check=True)
    initialize.init_project(tmp_path, assume_yes=True)
    marker = tmp_path / ".horus" / ".consolidated-to"
    marker.write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", ".horus/.consolidated-to"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "legacy init"], check=True, capture_output=True)
    marker.write_text("new\n", encoding="utf-8")

    rc = main(["upgrade-project", "--path", str(tmp_path), "--apply", "--no-hooks", "--no-skills", "--no-instructions"])

    assert rc == 0
    tracked = subprocess.run(
        ["git", "-C", str(tmp_path), "ls-files", ".horus/.consolidated-to"],
        check=True, capture_output=True, text=True,
    ).stdout
    assert tracked == ""
    assert marker.read_text(encoding="utf-8") == "new\n"
    assert "stopped tracking generated continuity state" in capsys.readouterr().out


def test_upgrade_project_all_applies_to_every_registered_project(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    proj_a = tmp_path / "proj-a"
    proj_b = tmp_path / "proj-b"
    proj_a.mkdir()
    proj_b.mkdir()
    initialize.init_project(proj_a, assume_yes=True)
    initialize.init_project(proj_b, assume_yes=True)
    (proj_a / ".codex" / "hooks.json").unlink(missing_ok=True)
    (proj_b / ".codex" / "hooks.json").unlink(missing_ok=True)

    rc = main(["upgrade-project", "--all", "--apply", "--target", "codex", "--no-skills", "--no-instructions"])

    assert rc == 0
    assert (proj_a / ".codex" / "hooks.json").exists()
    assert (proj_b / ".codex" / "hooks.json").exists()
    out = capsys.readouterr().out
    assert str(proj_a) in out
    assert str(proj_b) in out
    assert "2 project(s) processed, 0 skipped" in out


def test_upgrade_project_all_skips_missing_registered_path(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    proj_a = tmp_path / "proj-a"
    proj_a.mkdir()
    initialize.init_project(proj_a, assume_yes=True)
    config.register_project(tmp_path / "does-not-exist")

    rc = main(["upgrade-project", "--all", "--apply", "--target", "codex", "--no-skills", "--no-instructions"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "does-not-exist" in out
    assert "1 project(s) processed, 1 skipped" in out


def test_upgrade_project_all_rejects_explicit_path(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)

    rc = main(["upgrade-project", "--all", "--path", str(tmp_path)])

    assert rc == 2
    assert "error" in capsys.readouterr().out


def test_upgrade_project_all_empty_registry_returns_ok(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)

    rc = main(["upgrade-project", "--all"])

    assert rc == 0
    assert "No projects registered" in capsys.readouterr().out


def test_upgrade_project_all_dry_run_reports_pending_across_projects(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    proj_a = tmp_path / "proj-a"
    proj_a.mkdir()
    initialize.init_project(proj_a, assume_yes=True)
    (proj_a / ".codex" / "hooks.json").unlink(missing_ok=True)

    rc = main(["upgrade-project", "--all", "--target", "codex", "--no-skills", "--no-instructions"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "would-update" in out
    assert "1 project(s) processed, 0 skipped" in out
    assert not (proj_a / ".codex" / "hooks.json").exists()


def test_upgrade_project_structure_prd_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _write_v2_horus(tmp_path)
    before = (tmp_path / ".horus" / "project.md").read_bytes()

    rc = main(["upgrade-project", "--path", str(tmp_path), "--structure", "prd"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "Dry run only" in out
    assert "would create .horus/PRD.md" in out
    assert not (tmp_path / ".horus" / "PRD.md").exists()
    assert (tmp_path / ".horus" / "project.md").read_bytes() == before


def test_upgrade_project_structure_prd_apply_archives_verbatim_and_maps_prd(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _write_v2_horus(tmp_path)
    originals = {p.name: p.read_bytes() for p in (tmp_path / ".horus").glob("*.md")}

    rc = main(["upgrade-project", "--path", str(tmp_path), "--structure", "prd", "--apply"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "Applying Horus structure migration to PRD" in out
    hdir = tmp_path / ".horus"
    prd = (hdir / "PRD.md").read_text(encoding="utf-8")
    assert 'current_focus: "Roadmap focus"' in prd
    assert 'next_action: "Do next"' in prd
    assert "A focused project vision." in prd
    assert "Open task" in prd and "Later task" in prd and "Done task" not in prd
    assert "Done continuation" not in prd
    assert "- **Dashboard** — v1 — Shows state" in prd
    assert "**Repo-local memory**" in prd
    assert "Agent-polish TODO" in prd
    for name, content in originals.items():
        assert not (hdir / name).exists()
        assert (hdir / "archive" / name).read_bytes() == content
    assert (hdir / "sessions").is_dir()
    assert (hdir / "temp").is_dir()


def test_upgrade_project_structure_prd_is_noop_for_v3(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    initialize.init_project(tmp_path, assume_yes=True, with_skills=False, with_hooks=False)

    rc = main(["upgrade-project", "--path", str(tmp_path), "--structure", "prd", "--apply"])

    assert rc == 0
    assert "already present" in capsys.readouterr().out
    assert (tmp_path / ".horus" / "PRD.md").exists()


def test_upgrade_project_structure_prd_apply_refuses_dirty_git_tree(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "Tester")
    _write_v2_horus(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "v2")
    (tmp_path / "README.md").write_text("dirty\n", encoding="utf-8")

    rc = main(["upgrade-project", "--path", str(tmp_path), "--structure", "prd", "--apply"])

    assert rc == 2
    assert "working tree is dirty" in capsys.readouterr().out
    assert not (tmp_path / ".horus" / "PRD.md").exists()
    assert (tmp_path / ".horus" / "project.md").exists()


def test_upgrade_project_structure_prd_apply_refuses_behind_origin(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    origin = tmp_path / "origin.git"
    a = tmp_path / "a"
    b = tmp_path / "b"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(origin), str(a)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(origin), str(b)], check=True, capture_output=True)
    for clone in (a, b):
        _git(clone, "config", "user.email", "t@example.com")
        _git(clone, "config", "user.name", "Tester")
    _write_v2_horus(a)
    _git(a, "add", "-A")
    _git(a, "commit", "-m", "v2")
    _git(a, "push", "-u", "origin", "HEAD")
    _git(b, "pull", "--ff-only")
    (a / "README.md").write_text("remote newer\n", encoding="utf-8")
    _git(a, "add", "README.md")
    _git(a, "commit", "-m", "remote newer")
    _git(a, "push")

    rc = main(["upgrade-project", "--path", str(b), "--structure", "prd", "--apply"])

    assert rc == 2
    assert "branch is behind" in capsys.readouterr().out
    assert not (b / ".horus" / "PRD.md").exists()
    assert (b / ".horus" / "project.md").exists()


def test_upgrade_project_structure_prd_rejects_all(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)

    rc = main(["upgrade-project", "--all", "--structure", "prd"])

    assert rc == 2
    assert "cannot be combined" in capsys.readouterr().out


def test_app_cli_dispatches_to_companion(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = []

    def fake_run(project_root, **kwargs):
        calls.append((project_root, kwargs))
        return 0

    monkeypatch.setattr("horus.cli.companion.run_companion", fake_run)
    # Don't re-exec under pythonw.exe during the test; exercise inline dispatch.
    monkeypatch.setattr("horus.cli.companion.relaunch_without_console", lambda: False)

    from horus import companion

    assert main(["app", "--path", str(tmp_path), "--port", "9999", "--no-dashboard"]) == 0
    assert calls[0][0] == tmp_path.resolve()
    assert calls[0][1]["port"] == 9999
    assert calls[0][1]["start_dashboard"] is False
    # No mode flag → platform default (owned on Windows, tab elsewhere).
    assert calls[0][1]["open_mode"] == companion.resolve_open_mode()
    assert calls[0][1]["mascot_style"] == "auto"


def test_app_cli_can_request_app_window(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = []

    def fake_run(project_root, **kwargs):
        calls.append((project_root, kwargs))
        return 0

    monkeypatch.setattr("horus.cli.companion.run_companion", fake_run)
    monkeypatch.setattr("horus.cli.companion.relaunch_without_console", lambda: False)

    assert main(["app", "--path", str(tmp_path), "--app-window"]) == 0
    assert calls[0][1]["open_on_start"] is True  # pre-warm is the default now
    assert calls[0][1]["open_mode"] == "owned"  # --app-window forces owned on any platform


def test_app_cli_tab_flag_forces_tab(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = []

    def fake_run(project_root, **kwargs):
        calls.append((project_root, kwargs))
        return 0

    monkeypatch.setattr("horus.cli.companion.run_companion", fake_run)
    monkeypatch.setattr("horus.cli.companion.relaunch_without_console", lambda: False)

    assert main(["app", "--path", str(tmp_path), "--tab"]) == 0
    assert calls[0][1]["open_mode"] == "tab"  # --tab forces a browser tab on any platform


def test_app_cli_no_open_keeps_mascot_only(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = []

    def fake_run(project_root, **kwargs):
        calls.append((project_root, kwargs))
        return 0

    monkeypatch.setattr("horus.cli.companion.run_companion", fake_run)
    monkeypatch.setattr("horus.cli.companion.relaunch_without_console", lambda: False)

    assert main(["app", "--path", str(tmp_path), "--no-open"]) == 0
    assert calls[0][1]["open_on_start"] is False  # --no-open opts out of pre-warm


def test_app_cli_can_request_mascot_style(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    calls = []

    def fake_run(project_root, **kwargs):
        calls.append((project_root, kwargs))
        return 0

    monkeypatch.setattr("horus.cli.companion.run_companion", fake_run)
    monkeypatch.setattr("horus.cli.companion.relaunch_without_console", lambda: False)

    assert main(["app", "--path", str(tmp_path), "--mascot-style", "layered"]) == 0
    assert calls[0][1]["mascot_style"] == "layered"


def test_start_cli_runs_remote_start_and_prints_prompt(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    project = tmp_path / "workspace" / "demo"
    result = remote_start.StartResult(
        project=github_catalog.RemoteProject(
            owner="rafaelmjf",
            name="demo",
            full_name="rafaelmjf/demo",
            url="https://github.com/rafaelmjf/demo",
            clone_url="git@github.com:rafaelmjf/demo.git",
            default_branch="main",
            pushed_at="2026-06-28T12:00:00Z",
            next_prompt="Resume demo",
        ),
        path=project,
        cloned=True,
        registered=True,
        upgrade_actions=[upgrade.UpgradeAction("updated", "refreshed")],
    )
    calls = []

    def fake_start(target, **kwargs):
        calls.append((target, kwargs))
        return result

    monkeypatch.setattr("horus.cli.remote_start.start_github_project", fake_start)
    monkeypatch.setattr("horus.cli.routines.resume_prompt", lambda path: "Resume the cloned demo project.")

    assert main(["start", "github:rafaelmjf/demo", "--workspace-root", str(tmp_path / "workspace")]) == 0

    assert calls[0][0] == "github:rafaelmjf/demo"
    assert calls[0][1]["workspace_root"] == Path(tmp_path / "workspace")
    out = capsys.readouterr().out
    assert "Cloned" in out
    assert "Resume prompt:" in out
    assert "Resume the cloned demo project." in out
    assert f'horus open "{project}"' in out


def test_start_cli_requires_workspace_when_saving_root(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)

    assert main(["start", "github:rafaelmjf/demo", "--set-workspace-root"]) == 2
    assert "--set-workspace-root requires --workspace-root" in capsys.readouterr().out


def test_resume_cli_prints_minimum_context_handoff(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    # Fresh init scaffolds structure v3 (PRD.md); the focus/handoff fields are
    # PRD-first, so author them there rather than in the (now absent) v2 shims.
    (tmp_path / ".horus" / "PRD.md").write_text(
        '---\ncurrent_focus: "Tighten resume flow"\n'
        'next_action: "Ship horus resume"\nnext_prompt: "Implement the resume command."\n'
        'execution_recommendation: "plan-execution - small cross-surface change"\n---\n# PRD\n',
        encoding="utf-8",
    )
    (tmp_path / ".horus" / "execution.md").write_text(
        '---\nstatus: active\n---\n# Execution\n',
        encoding="utf-8",
    )

    assert main(["resume", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "git fetch --all --prune" in out
    assert "`current_focus`: Tighten resume flow" in out
    assert "`execution_status`: active" in out
    assert "Implement the resume command." in out


def test_refresh_cli_refreshes_one_github_owner(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    calls = []

    def fake_refresh(owner, **kwargs):
        calls.append((owner, kwargs))
        return github_catalog.RefreshResult(owner=owner, ok=True, count=2, fetched_at="2026-06-28T21:00:00+00:00")

    monkeypatch.setattr("horus.cli.github_catalog.force_refresh", fake_refresh)

    assert main(["refresh", "github", "rafaelmjf"]) == 0

    assert calls[0][0] == "rafaelmjf"
    assert "Refreshed rafaelmjf: 2 Horus-enabled repo" in capsys.readouterr().out


def test_refresh_cli_refreshes_all_saved_github_owners(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    config.register_github_owner("one")
    config.register_github_owner("two")
    calls = []

    def fake_refresh(owner, **kwargs):
        calls.append(owner)
        return github_catalog.RefreshResult(owner=owner, ok=True, count=1)

    monkeypatch.setattr("horus.cli.github_catalog.force_refresh", fake_refresh)

    assert main(["refresh", "github", "--all"]) == 0

    assert calls == ["one", "two"]
    out = capsys.readouterr().out
    assert "Refreshed one" in out and "Refreshed two" in out


def test_refresh_cli_returns_failure_on_refresh_error(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "horus.cli.github_catalog.force_refresh",
        lambda owner, **kwargs: github_catalog.RefreshResult(owner=owner, ok=False, error="auth required"),
    )

    assert main(["refresh", "github", "rafaelmjf"]) == 1
    assert "auth required" in capsys.readouterr().out


def test_config_workspace_root_cli_sets_and_prints(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    workspace = tmp_path / "projects"

    assert main(["config", "workspace-root", str(workspace)]) == 0
    assert workspace.resolve().as_posix() in capsys.readouterr().out

    assert main(["config", "workspace-root"]) == 0
    assert workspace.resolve().as_posix() in capsys.readouterr().out


def test_reconcile_cli_resolves_drift(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])

    claude = tmp_path / "CLAUDE.md"
    claude.write_text(
        claude.read_text(encoding="utf-8").replace("project continuity", "DRIFTED"),
        encoding="utf-8",
    )
    agents = tmp_path / "AGENTS.md"
    assert check_drift(
        agents.read_text(encoding="utf-8"), "AGENTS.md",
        claude.read_text(encoding="utf-8"), "CLAUDE.md",
    ).status == "drift"

    assert main(["reconcile", "instructions", "--path", str(tmp_path)]) == 0
    assert check_drift(
        agents.read_text(encoding="utf-8"), "AGENTS.md",
        claude.read_text(encoding="utf-8"), "CLAUDE.md",
    ).status == "aligned"


def test_consolidate_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["consolidate", "--path", str(tmp_path)]) == 0


def test_consolidate_cli_prd_project_gets_v3_trailer(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])  # scaffolds structure v3 (PRD.md)
    assert main(["consolidate", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "PRD structure" in out
    assert "features.md" not in out  # no six-lane routing steps on a v3 project
    assert "each lane stays in its lane" not in out


def test_consolidate_cli_six_lane_trailer_unchanged(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    hdir = tmp_path / ".horus"
    hdir.mkdir()
    (hdir / "roadmap.md").write_text("---\nstatus: active\n---\n# R\n", encoding="utf-8")
    assert main(["consolidate", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "each lane stays in its lane" in out
    assert "PRD structure" not in out


def test_distill_history_cli_runs(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["distill-history", "--path", str(tmp_path)]) == 0


def test_distill_history_cli_prd_project_targets_archive(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])  # scaffolds structure v3 (PRD.md)
    assert main(["distill-history", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "archive/history.md" in out
    assert "history.md missing" not in out
    assert "decisions.md" not in out  # v2 trailer cross-references decisions.md


def test_infer_cli_uses_prd_structure_prompt(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    capsys.readouterr()
    assert main(["infer", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "PRD-structure continuity" in out
    assert ".horus/backlog/<slug>.md" in out
    assert "project.md - what it is" not in out


def test_infer_cli_keeps_six_lane_prompt_for_v2(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _write_v2_horus(tmp_path)
    assert main(["infer", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "project.md - what it is" in out
    assert "PRD-structure continuity" not in out


def test_routine_commands_reject_nonexistent_path(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    missing = str(tmp_path / "does-not-exist")
    assert main(["consolidate", "--path", missing]) == 2
    assert main(["infer", "--path", missing]) == 2
    assert main(["distill-history", "--path", missing]) == 2


def test_skill_install_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills", "--no-hooks"])
    assert not (tmp_path / ".claude").exists()  # --no-skills/--no-hooks opted out at init
    assert main(["skill", "install", "--path", str(tmp_path)]) == 0
    assert (tmp_path / ".claude" / "skills" / "horus-consolidate" / "SKILL.md").exists()
    assert (tmp_path / ".agents" / "skills" / "horus-consolidate" / "SKILL.md").exists()


def test_skill_install_codex_target_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills", "--no-hooks"])
    assert main(["skill", "install", "--path", str(tmp_path), "--target", "codex"]) == 0
    assert (tmp_path / ".agents" / "skills" / "horus-consolidate" / "SKILL.md").exists()
    assert not (tmp_path / ".claude").exists()


def _claude_hook_run(monkeypatch, tmp_path, capsys, *, percent, threshold, stdin, reset=None):
    """Drive `usage check --target claude --hook` with a mocked usage snapshot + stdin."""
    import io

    from horus import cli as cli_mod
    from horus import native_hooks, usage_snapshot

    monkeypatch.setattr(
        usage_snapshot, "cached_usage",
        lambda *a, **k: usage_snapshot.UsageSnapshot(percent, reset),
    )
    monkeypatch.setattr(cli_mod, "_usage_account", lambda target: None)
    monkeypatch.setattr(native_hooks.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    rc = main(["usage", "check", "--target", "claude", "--hook", "--threshold", str(threshold)])
    return rc, capsys.readouterr().out


def test_claude_hook_injects_closure_over_threshold(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=92.0, threshold=90,
        stdin='{"session_id":"s1","stop_hook_active":false}',
    )
    assert rc == 0
    payload = json.loads(out.strip())
    assert payload["decision"] == "block"
    reason = payload["reason"]
    assert "horus-consolidate" in reason  # drives the context-aware skill
    # Stop must PROMPT the user (close vs push ahead), not force a closure/stop.
    assert "ASK" in reason or "ask the user" in reason
    assert "do not resume the main task" not in reason
    # Closure always reaches the remote.
    assert "horus close --commit --push" in reason


def test_claude_hook_userpromptsubmit_defers_to_user(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=92.0, threshold=90,
        stdin='{"session_id":"u1","hook_event_name":"UserPromptSubmit"}',
    )
    assert rc == 0
    payload = json.loads(out.strip())
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "horus-consolidate" in ctx  # still offers the context-aware skill
    # Advisory must defer to the user's explicit request, not override it.
    assert "context, not a command" in ctx
    assert "horus close --commit --push" in ctx


def test_claude_hook_quiet_under_threshold(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=40.0, threshold=90,
        stdin='{"session_id":"s2"}',
    )
    assert rc == 0 and out.strip() == ""


def test_claude_hook_fires_once_per_session(tmp_path, monkeypatch, capsys):
    stdin = '{"session_id":"dup","stop_hook_active":false}'
    _, out1 = _claude_hook_run(monkeypatch, tmp_path, capsys, percent=92.0, threshold=90, stdin=stdin)
    _, out2 = _claude_hook_run(monkeypatch, tmp_path, capsys, percent=92.0, threshold=90, stdin=stdin)
    assert out1.strip() and out2.strip() == ""  # second call suppressed by sentinel


def test_claude_advisory_does_not_suppress_stop_block(tmp_path, monkeypatch, capsys):
    """Regression: the soft UserPromptSubmit advisory must not consume the Stop
    hook's closure prompt — they track separate sentinels."""
    _, out1 = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=92.0, threshold=90,
        stdin='{"session_id":"split","hook_event_name":"UserPromptSubmit"}',
    )
    assert "additionalContext" in out1  # advisory fired
    _, out2 = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=93.0, threshold=90,
        stdin='{"session_id":"split","stop_hook_active":false}',
    )
    payload = json.loads(out2.strip())
    assert payload["decision"] == "block"  # Stop prompt still fires


def test_claude_stop_reasks_only_on_band_crossing(tmp_path, monkeypatch, capsys):
    """Within one usage window the Stop prompt escalates by band, not by timer:
    quiet while usage creeps inside the same band, one re-ask past the next band."""
    stdin = '{"session_id":"bands","stop_hook_active":false}'
    _, out1 = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=91.0, threshold=90, stdin=stdin, reset="2026-07-10 04:29")
    assert json.loads(out1.strip())["decision"] == "block"
    _, out2 = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=95.0, threshold=90, stdin=stdin, reset="2026-07-10 04:29")
    assert out2.strip() == ""  # same band (90) — user already answered, stay quiet
    _, out3 = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=98.0, threshold=90, stdin=stdin, reset="2026-07-10 04:29")
    reason = json.loads(out3.strip())["reason"]
    assert "98%" in reason  # emergency band crossed — one concrete re-ask


def test_claude_bands_rearm_on_window_reset(tmp_path, monkeypatch, capsys):
    stdin = '{"session_id":"rollover","stop_hook_active":false}'
    _, out1 = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=92.0, threshold=90, stdin=stdin, reset="2026-07-10 04:29")
    assert out1.strip()
    _, out2 = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=92.0, threshold=90, stdin=stdin, reset="2026-07-10 09:29")
    assert json.loads(out2.strip())["decision"] == "block"  # new window — bands re-armed


def test_claude_hook_respects_stop_hook_active(tmp_path, monkeypatch, capsys):
    rc, out = _claude_hook_run(
        monkeypatch, tmp_path, capsys, percent=99.0, threshold=90,
        stdin='{"session_id":"s3","stop_hook_active":true}',
    )
    assert rc == 0 and out.strip() == ""


def test_forget_cli(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes"])
    assert main(["forget", str(tmp_path)]) == 0
    assert main(["forget", str(tmp_path)]) == 1  # already gone


# --- pre-merge closure gate (`horus close --hook`, a PreToolUse hook) ---

def _merge_hook_run(monkeypatch, capsys, *, tool_input, findings):
    from pathlib import Path

    from horus import cli
    from horus.continuity import Finding

    monkeypatch.setattr(cli, "_read_hook_stdin", lambda: tool_input)
    monkeypatch.setattr(cli.closure, "freshness_gate",
                        lambda root: [Finding(*f) for f in findings])
    rc = cli._close_merge_hook(Path("."))
    return rc, capsys.readouterr().out


def test_merge_hook_blocks_merge_when_lanes_stale(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Bash", "tool_input": {"command": "gh pr merge 15 --squash"}},
        findings=[("warn", "lanes stale")],
    )
    assert rc == 0
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "horus-consolidate" in hso["permissionDecisionReason"]


def test_merge_hook_allows_merge_when_fresh(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Bash", "tool_input": {"command": "gh pr merge 15"}},
        findings=[("ok", "fresh")],
    )
    assert rc == 0
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["permissionDecision"] == "allow"
    assert "closure check passed" in hso["permissionDecisionReason"].lower()


def test_merge_hook_ignores_non_merge_bash(monkeypatch, capsys):
    # Stale lanes, but the command isn't a merge -> never blocked.
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Bash", "tool_input": {"command": "git status"}},
        findings=[("fail", "lanes stale")],
    )
    assert rc == 0 and out.strip() == ""


def test_merge_hook_ignores_quoted_prompt_that_mentions_merge(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch,
        capsys,
        tool_input={
            "tool_name": "Bash",
            "tool_input": {
                "command": 'horus run "Open the PR and STOP; do not gh pr merge"',
            },
        },
        findings=[("fail", "lanes stale")],
    )
    assert rc == 0 and out.strip() == ""


def test_merge_hook_gates_actual_merge_after_shell_operator(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch,
        capsys,
        tool_input={
            "tool_name": "Bash",
            "tool_input": {"command": "cd /tmp/project && gh pr merge 15 --auto"},
        },
        findings=[("warn", "lanes stale")],
    )
    assert rc == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_merge_hook_malformed_shell_text_fails_open(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch,
        capsys,
        tool_input={
            "tool_name": "Bash",
            "tool_input": {"command": 'horus run "mention gh pr merge'},
        },
        findings=[("fail", "lanes stale")],
    )
    assert rc == 0 and out.strip() == ""


def test_merge_hook_ignores_non_shell_tool(monkeypatch, capsys):
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "Edit", "tool_input": {"command": "gh pr merge"}},
        findings=[("fail", "lanes stale")],
    )
    assert rc == 0 and out.strip() == ""


def test_merge_hook_gates_merge_from_powershell_tool(monkeypatch, capsys):
    # On Windows the agent issues git/gh through the PowerShell tool; the gate must
    # fire there exactly as for Bash (field regression: fabric 2026-07-08).
    rc, out = _merge_hook_run(
        monkeypatch, capsys,
        tool_input={"tool_name": "PowerShell", "tool_input": {"command": "gh pr merge 15 --squash"}},
        findings=[("warn", "lanes stale")],
    )
    assert rc == 0
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- hosted-session self-restart guard (`horus guard-host --hook`) ---

def _guard_hook_run(monkeypatch, capsys, *, command, hosted=True, host_pid="4242", tool="Bash"):
    from pathlib import Path

    from horus import cli

    if hosted:
        monkeypatch.setenv("HORUS_HOSTED_SESSION", "1")
        monkeypatch.setenv("HORUS_PTY_HOST_PID", host_pid)
    else:
        monkeypatch.delenv("HORUS_HOSTED_SESSION", raising=False)
        monkeypatch.delenv("HORUS_PTY_HOST_PID", raising=False)
    monkeypatch.setattr(cli, "_read_hook_stdin",
                        lambda: {"tool_name": tool, "tool_input": {"command": command}})
    rc = cli._guard_host_hook(Path("."))
    return rc, capsys.readouterr().out


def _assert_denied(rc, out):
    assert rc == 0
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "hosted" in hso["permissionDecisionReason"].lower()


def test_guard_blocks_app_relaunch_when_hosted(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="horus app"))


def test_guard_blocks_dashboard_relaunch_via_module(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="python -m horus dashboard"))


def test_guard_blocks_taskkill_of_python(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="taskkill /F /IM python.exe"))


def test_guard_blocks_kill_of_host_pid(monkeypatch, capsys):
    _assert_denied(*_guard_hook_run(monkeypatch, capsys, command="kill -9 4242", host_pid="4242"))


def test_guard_blocks_stop_process_from_powershell_tool(monkeypatch, capsys):
    # The PowerShell tool + PowerShell kill idiom — both layers (tool filter and
    # command detection) must cover the Windows spelling.
    _assert_denied(*_guard_hook_run(
        monkeypatch, capsys,
        command="Stop-Process -Id 4242 -Force", host_pid="4242", tool="PowerShell",
    ))


def test_guard_blocks_kill_of_host_by_name(monkeypatch, capsys):
    for cmd in ("pkill -f horus", "taskkill /F /FI \"WINDOWTITLE eq horus dashboard\""):
        _assert_denied(*_guard_hook_run(monkeypatch, capsys, command=cmd))


def test_guard_blocks_service_restart_of_dashboard(monkeypatch, capsys):
    for cmd in (
        "sudo systemctl restart horus-dashboard",
        "systemctl stop horus-dashboard.service",
        "sudo service horus-dashboard restart",
    ):
        _assert_denied(*_guard_hook_run(monkeypatch, capsys, command=cmd))


def test_guard_allows_benign_command_when_hosted(monkeypatch, capsys):
    for cmd in ("git commit -m x", "ls -la", "gh pr merge 15", "kill -9 999"):
        rc, out = _guard_hook_run(monkeypatch, capsys, command=cmd, host_pid="4242")
        assert rc == 0 and out.strip() == "", cmd


def test_guard_allows_mere_mentions_of_the_host(monkeypatch, capsys):
    # Read-only commands that merely *mention* horus/dashboard/pty in paths or
    # patterns must not block (real false positives from a hosted session).
    for cmd in (
        "wc -l /home/u/horus-harness/horus/dashboard.py horus/pty_host.py",
        'grep -rn "dashboard|pty|launch" /home/u/projects/horus-harness',
        "python -m pytest tests/test_dashboard.py -k launch",
        "git -C ~/projects/horus-harness log --oneline -- horus/dashboard.py",
        "systemctl status horus-dashboard",
        'echo "how to kill the horus dashboard"',
        "cat docs/horus-dashboard-runbook.md",
    ):
        rc, out = _guard_hook_run(monkeypatch, capsys, command=cmd, host_pid="4242")
        assert rc == 0 and out.strip() == "", cmd


def test_guard_noop_outside_hosted_session(monkeypatch, capsys):
    # The very commands that would be blocked inside a host are untouched elsewhere.
    rc, out = _guard_hook_run(monkeypatch, capsys, command="horus app", hosted=False)
    assert rc == 0 and out.strip() == ""


def test_guard_ignores_non_bash_tool(monkeypatch, capsys):
    rc, out = _guard_hook_run(monkeypatch, capsys, command="horus app", tool="Edit")
    assert rc == 0 and out.strip() == ""


# --- horus run: --worktree + --worker posture presets (phase E) ---------------

def _capture_run_posture(monkeypatch):
    """Record the posture the SpawnSpec carried into the fake adapter."""
    from horus.adapters.fake import FakeAdapter

    captured = {}
    original = FakeAdapter.spawn

    def spy(self, spec):
        captured["posture"] = spec.posture.value
        captured["project"] = str(spec.project_dir)
        captured["effort"] = spec.effort
        return original(self, spec)

    monkeypatch.setattr(FakeAdapter, "spawn", spy)
    return captured


# --- horus run: --effort passthrough ------------------------------------------

def test_run_effort_reaches_spawn_spec(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = _capture_run_posture(monkeypatch)
    rc = main(["run", "hi", "--agent", "fake", "--effort", "xhigh", "--path", str(tmp_path)])
    assert rc == 0
    assert captured["effort"] == "xhigh"


def test_run_effort_defaults_to_none(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = _capture_run_posture(monkeypatch)
    rc = main(["run", "hi", "--agent", "fake", "--path", str(tmp_path)])
    assert rc == 0
    assert captured["effort"] is None  # default behavior unchanged when --effort omitted


def test_run_effort_rejects_unknown_level(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as exc:
        main(["run", "hi", "--agent", "fake", "--effort", "ultra", "--path", str(tmp_path)])
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_run_worker_preset_maps_claude_to_full_auto(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = _capture_run_posture(monkeypatch)
    rc = main(["run", "hi", "--agent", "fake", "--worker", "claude", "--path", str(tmp_path)])
    assert rc == 0
    assert captured["posture"] == "full-auto"


def test_run_worker_surfaces_dispatch_boundary_and_pending_continuity(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _capture_run_posture(monkeypatch)
    monkeypatch.setattr(
        closure,
        "pending_delivery_commits",
        lambda root: [("a" * 40, "feat: one"), ("b" * 40, "feat: two")],
    )

    assert main(["run", "hi", "--agent", "fake", "--worker", "claude", "--path", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "Dispatch boundary: base unknown · pending continuity 2" in output
    assert "include their relevant state in the worker brief" in output


def test_run_worker_preset_maps_codex_to_auto_edit(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = _capture_run_posture(monkeypatch)
    rc = main(["run", "hi", "--agent", "fake", "--worker", "codex", "--path", str(tmp_path)])
    assert rc == 0
    assert captured["posture"] == "auto-edit"


def test_run_worker_infers_matching_agent_when_agent_omitted(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = _capture_run_posture(monkeypatch)
    selected = {}
    original = adapters.get_adapter

    def capture_agent(name):
        selected["agent"] = name
        return original("fake")

    monkeypatch.setattr(adapters, "get_adapter", capture_agent)
    rc = main(["run", "hi", "--worker", "codex", "--path", str(tmp_path)])
    assert rc == 0
    assert selected["agent"] == "codex"
    assert captured["posture"] == "auto-edit"


def test_run_help_explains_codex_worker_full_auto_requirement(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--help"])
    assert exc.value.code == 0
    out = " ".join(capsys.readouterr().out.split())
    assert "network/socket access off" in out
    assert "fetch/push/PR" in out
    assert "local-server/browser verification require --posture full-auto" in out
    assert "bypasses approvals and sandbox" in out


def test_run_explicit_posture_beats_worker_preset(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = _capture_run_posture(monkeypatch)
    rc = main(["run", "hi", "--agent", "fake", "--worker", "claude",
               "--posture", "read-only", "--path", str(tmp_path)])
    assert rc == 0
    assert captured["posture"] == "read-only"  # explicit --posture wins


def test_run_defaults_to_default_posture_without_worker(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    captured = _capture_run_posture(monkeypatch)
    rc = main(["run", "hi", "--agent", "fake", "--path", str(tmp_path)])
    assert rc == 0
    assert captured["posture"] == "default"


def test_run_worktree_creates_and_records_path(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    repo = _init_repo(tmp_path / "repo")
    captured = _capture_run_posture(monkeypatch)

    rc = main(["run", "hi", "--agent", "fake", "--worktree", "probe-branch", "--path", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    expected = repo.parent / "repo-wt-probe-branch"
    assert f"Created worktree {expected}" in out
    assert expected.is_dir()  # git worktree really created
    # The session ran in the worktree and the registry row records that path.
    assert Path(captured["project"]).resolve() == expected.resolve()
    recs = Registry.default().all()
    assert len(recs) == 1
    assert Path(recs[0].project).resolve() == expected.resolve()


def test_run_worktree_reuses_existing(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    repo = _init_repo(tmp_path / "repo")
    assert main(["run", "hi", "--agent", "fake", "--worktree", "probe-branch", "--path", str(repo)]) == 0
    capsys.readouterr()
    rc = main(["run", "again", "--agent", "fake", "--worktree", "probe-branch", "--path", str(repo)])
    assert rc == 0
    assert "Reusing worktree" in capsys.readouterr().out


def test_run_worktree_refuses_non_worktree_target(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    repo = _init_repo(tmp_path / "repo")
    (repo.parent / "repo-wt-probe-branch").mkdir()  # squatting non-worktree dir
    rc = main(["run", "hi", "--agent", "fake", "--worktree", "probe-branch", "--path", str(repo)])
    assert rc == 2
    assert "Refusing to run" in capsys.readouterr().out
    assert Registry.default().all() == []  # nothing spawned


def _write_backlog_card(root: Path, name: str, **fields):
    hdir = root / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()] + ["---", f"# {name}", ""]
    (hdir / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


def test_backlog_list_shows_parallel_safety_metadata(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(
        tmp_path, "card-a", status="open", priority="later", tier="sonnet",
        parallel="exclusive", surface="horus/dashboard.py",
    )
    _write_backlog_card(tmp_path, "card-b", status="open", priority="later", tier="sonnet")

    assert main(["backlog", "list", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "card-a" in out and "parallel=exclusive" in out
    assert "horus/dashboard.py" in out
    assert "card-b" in out and "parallel=unstated" in out
    assert "surface: unverified" in out


def test_backlog_claim_back_compat_no_new_fields(tmp_path, monkeypatch, capsys):
    """A card without parallel/surface — the pre-existing card shape — still claims."""
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "old-style", status="open", priority="later", tier="sonnet")

    assert main(["backlog", "claim", "old-style", "--path", str(tmp_path)]) == 0
    text = (tmp_path / ".horus" / "backlog" / "old-style.md").read_text(encoding="utf-8")
    assert "status: claimed" in text


def test_backlog_claim_warns_and_blocks_on_surface_overlap(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "a", status="claimed", surface="horus/dashboard.py")
    _write_backlog_card(tmp_path, "b", status="open", surface="horus/dashboard.py")

    rc = main(["backlog", "claim", "b", "--path", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "overlaps" in out
    assert "re-run with --force" in out
    assert (tmp_path / ".horus" / "backlog" / "b.md").read_text(encoding="utf-8").count("status: open") == 1

    rc = main(["backlog", "claim", "b", "--path", str(tmp_path), "--force"])
    assert rc == 0
    text = (tmp_path / ".horus" / "backlog" / "b.md").read_text(encoding="utf-8")
    assert "status: claimed" in text


def test_backlog_list_type_filter(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "a-bug", status="open", priority="high", type="bug")
    _write_backlog_card(tmp_path, "b-feature", status="open", priority="high", type="feature")
    _write_backlog_card(tmp_path, "c-untyped", status="open", priority="high")

    assert main(["backlog", "list", "--path", str(tmp_path), "--type", "bug"]) == 0
    out = capsys.readouterr().out
    assert "a-bug" in out
    assert "b-feature" not in out
    assert "c-untyped" not in out

    assert main(["backlog", "list", "--path", str(tmp_path), "--type", "task"]) == 0
    out = capsys.readouterr().out
    assert "c-untyped" in out  # missing `type` defaults to task
    assert "a-bug" not in out


def test_backlog_list_shows_only_active_cards_and_excludes_archive(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "active", status="open", priority="high")
    _write_backlog_card(tmp_path, "stray-retired", status="retired", priority="high")
    archive = tmp_path / ".horus" / "backlog" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "already-shipped.md").write_text(
        "---\nstatus: shipped\nshipped_pr: 42\nshipped_sha: abc123\n---\n# Shipped\n",
        encoding="utf-8",
    )

    assert main(["backlog", "list", "--path", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "active" in out
    assert "already-shipped" not in out
    assert "stray-retired" not in out


def test_backlog_ship_cli_archives_card_with_provenance(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "to-ship", status="open", priority="high")

    assert main([
        "backlog", "ship", "to-ship", "--pr", "42", "--sha", "abc123", "--path", str(tmp_path),
    ]) == 0
    assert "Shipped: to-ship (PR #42, abc123)" in capsys.readouterr().out
    assert not (tmp_path / ".horus" / "backlog" / "to-ship.md").exists()
    text = (tmp_path / ".horus" / "backlog" / "archive" / "to-ship.md").read_text(encoding="utf-8")
    assert "status: shipped" in text
    assert "shipped_pr: 42" in text
    assert "shipped_sha: abc123" in text


def test_close_check_warns_on_lingering_done_and_shipped_but_open_card(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from tests.test_routines import _mk_fresh

    _mk_fresh(tmp_path)
    _write_backlog_card(
        tmp_path, "drifted-card", status="open", priority="high",
        shipped_pr="42", shipped_sha="abc123",
    )
    card_path = tmp_path / ".horus" / "backlog" / "drifted-card.md"
    card_path.write_text(card_path.read_text(encoding="utf-8") + "- [x] merged work\n", encoding="utf-8")

    assert main(["close", "--check", "--path", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "lingering done" in out
    assert "shipped provenance but status is 'open'" in out


def test_backlog_migrate_dry_run_then_apply(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    prd_path = tmp_path / ".horus" / "PRD.md"
    prd_path.write_text(
        '---\nstatus: active\n---\n\n# demo — PRD\n\n## Backlog\n\n'
        '### Now / next candidates\n\n1. **[bug]** Fix the thing.\n\n## Shipped\n',
        encoding="utf-8",
    )
    for card in (tmp_path / ".horus" / "backlog").glob("*.md"):
        card.unlink()

    rc = main(["backlog", "migrate", "--path", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "would-create" in out
    assert "Dry run only" in out
    assert not any((tmp_path / ".horus" / "backlog").glob("*.md"))

    rc = main(["backlog", "migrate", "--path", str(tmp_path), "--apply"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "created" in out
    cards = list((tmp_path / ".horus" / "backlog").glob("*.md"))
    assert len(cards) == 1

    rc = main(["backlog", "migrate", "--path", str(tmp_path), "--apply"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "noop" in out


def test_backlog_claim_non_overlapping_proceeds_clean(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "a", status="claimed", surface="horus/dashboard.py")
    _write_backlog_card(tmp_path, "b", status="open", surface="horus/pty_host.py")

    rc = main(["backlog", "claim", "b", "--path", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Claimed: b" in out
    assert "warn" not in out.lower()


def test_backlog_review_cli_appends_entry(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "review-me", status="open", priority="high")

    assert main([
        "backlog", "review", "review-me", "--by", "sonnet", "--source", "agent",
        "--verdict", "needs-work", "--note", "Repro still fails on tmux 3.3.",
        "--path", str(tmp_path),
    ]) == 0
    assert "Review appended" in capsys.readouterr().out
    text = (tmp_path / ".horus" / "backlog" / "review-me.md").read_text(encoding="utf-8")
    assert "## Reviews" in text
    assert "— sonnet (agent)" in text
    assert "Verdict: needs-work" in text
    assert "Repro still fails on tmux 3.3." in text


def test_backlog_review_cli_requires_note_or_verdict(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["init", str(tmp_path), "--yes", "--no-skills"])
    _write_backlog_card(tmp_path, "review-me", status="open", priority="high")

    assert main(["backlog", "review", "review-me", "--path", str(tmp_path)]) == 2
    assert "--note and/or --verdict" in capsys.readouterr().out


def test_upgrade_project_untracks_legacy_claim_lock(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    from horus import initialize

    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Tester"], check=True)
    initialize.init_project(tmp_path, assume_yes=True)
    lock = tmp_path / ".horus" / "backlog" / ".claim.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", ".horus/backlog/.claim.lock"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "legacy init"], check=True, capture_output=True)

    rc = main(["upgrade-project", "--path", str(tmp_path), "--apply", "--no-hooks", "--no-skills", "--no-instructions"])

    assert rc == 0
    tracked = subprocess.run(
        ["git", "-C", str(tmp_path), "ls-files", ".horus/backlog/.claim.lock"],
        check=True, capture_output=True, text=True,
    ).stdout
    assert tracked == ""
    assert "stopped tracking generated continuity state" in capsys.readouterr().out


# --- horus merge-watch: CLI wiring (module internals covered by test_mergewatch.py) --

def test_merge_watch_cli_exits_0_on_green(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        mergewatch, "watch",
        lambda root, ref, *, interval, timeout: mergewatch.WatchOutcome(state="success", sha="deadbeef", checks={}),
    )
    rc = main(["merge-watch", "42", "--path", str(tmp_path)])
    assert rc == 0


def test_merge_watch_cli_exits_1_on_red(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mergewatch, "watch",
        lambda root, ref, *, interval, timeout: mergewatch.WatchOutcome(state="failure", sha="deadbeef", checks={}),
    )
    rc = main(["merge-watch", "42", "--path", str(tmp_path)])
    assert rc == 1


def test_merge_watch_cli_exits_1_on_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mergewatch, "watch",
        lambda root, ref, *, interval, timeout: mergewatch.WatchOutcome(state="timeout", sha="deadbeef", checks={}),
    )
    rc = main(["merge-watch", "42", "--path", str(tmp_path)])
    assert rc == 1


def test_merge_watch_cli_exits_2_on_resolution_error(tmp_path, monkeypatch, capsys):
    def raiser(root, ref, *, interval, timeout):
        raise mergewatch.MergeWatchError("gh repo view failed: not a repo")

    monkeypatch.setattr(mergewatch, "watch", raiser)
    rc = main(["merge-watch", "42", "--path", str(tmp_path)])
    assert rc == 2
    assert "not a repo" in capsys.readouterr().out


def test_merge_watch_cli_passes_interval_and_timeout(tmp_path, monkeypatch):
    captured = {}

    def spy(root, ref, *, interval, timeout):
        captured["interval"] = interval
        captured["timeout"] = timeout
        return mergewatch.WatchOutcome(state="success", sha="x", checks={})

    monkeypatch.setattr(mergewatch, "watch", spy)
    main(["merge-watch", "42", "--path", str(tmp_path), "--interval", "3", "--timeout", "60"])
    assert captured == {"interval": 3.0, "timeout": 60.0}


# --- horus reinstall: CLI wiring (module internals covered by test_reinstall.py) --

def test_reinstall_cli_exits_0_when_marker_found(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        reinstall, "reinstall",
        lambda source, marker, *, package, python: reinstall.ReinstallResult(
            ok=True, marker=marker, marker_found=True, detail="found in cli.py", service_notes=[],
        ),
    )
    rc = main(["reinstall", str(tmp_path), "--verify", "MARKER"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FOUND" in out


def test_reinstall_cli_exits_1_when_marker_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        reinstall, "reinstall",
        lambda source, marker, *, package, python: reinstall.ReinstallResult(
            ok=True, marker=marker, marker_found=False, detail="not found", service_notes=[],
        ),
    )
    rc = main(["reinstall", str(tmp_path), "--verify", "MARKER"])
    assert rc == 1
    assert "ABSENT" in capsys.readouterr().out


def test_reinstall_cli_exits_2_on_install_failure(tmp_path, monkeypatch, capsys):
    def raiser(source, marker, *, package, python):
        raise reinstall.ReinstallError("uv tool install failed: boom")

    monkeypatch.setattr(reinstall, "reinstall", raiser)
    rc = main(["reinstall", str(tmp_path), "--verify", "MARKER"])
    assert rc == 2
    assert "boom" in capsys.readouterr().out


def test_reinstall_cli_surfaces_service_notes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        reinstall, "reinstall",
        lambda source, marker, *, package, python: reinstall.ReinstallResult(
            ok=True, marker=marker, marker_found=True, detail="found",
            service_notes=["horus-dashboard.service is active — restart it"],
        ),
    )
    rc = main(["reinstall", str(tmp_path), "--verify", "MARKER"])
    assert rc == 0
    assert "NOTE" in capsys.readouterr().out


def test_reinstall_cli_requires_verify_flag(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["reinstall", str(tmp_path)])
    assert exc.value.code == 2


# --- horus datum close --card: primary-checkout resolution + worktree cleanup ---

def test_datum_close_card_resolves_against_primary_checkout_not_worktree(tmp_path, monkeypatch, capsys):
    """A run under `--worktree` records its `project` as the WORKTREE path;
    `--card` must still stamp the card in the PRIMARY checkout's own
    `.horus/backlog/`, not a (possibly absent) one under the worktree."""
    _home(tmp_path, monkeypatch)
    repo = _init_repo(tmp_path / "repo")
    _write_backlog_card(repo, "deliver-me", status="open", priority="now", tier="sonnet")

    rc = main(["run", "hi", "--agent", "fake", "--worktree", "probe-branch", "--path", str(repo)])
    assert rc == 0
    capsys.readouterr()

    rc = main(["datum", "close", _run_id(), "--outcome", "clean", "--card", "deliver-me"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Stamped" in out
    assert str(repo.resolve()) in out  # stamped under the PRIMARY checkout, not the -wt- path

    from horus import backlog
    assert backlog.find_card(repo, "deliver-me").status == "done"


def test_datum_close_remove_worktree_removes_when_merged(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    repo = _init_repo(tmp_path / "repo")
    _write_backlog_card(repo, "deliver-me", status="open", priority="now", tier="sonnet")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True, text=True)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")
    _git(repo, "remote", "set-head", "origin", "-a")

    rc = main(["run", "hi", "--agent", "fake", "--worktree", "probe-branch", "--path", str(repo)])
    assert rc == 0
    worktree_dir = repo.parent / "repo-wt-probe-branch"
    capsys.readouterr()

    rc = main(["datum", "close", _run_id(), "--outcome", "clean", "--card", "deliver-me", "--remove-worktree"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Removed worktree" in out
    assert not worktree_dir.exists()


def test_datum_close_remove_worktree_keeps_unmerged(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    repo = _init_repo(tmp_path / "repo")
    _write_backlog_card(repo, "deliver-me", status="open", priority="now", tier="sonnet")

    rc = main(["run", "hi", "--agent", "fake", "--worktree", "probe-branch", "--path", str(repo)])
    assert rc == 0
    worktree_dir = repo.parent / "repo-wt-probe-branch"
    capsys.readouterr()

    rc = main(["datum", "close", _run_id(), "--outcome", "clean", "--card", "deliver-me", "--remove-worktree"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Kept worktree" in out
    assert worktree_dir.exists()
