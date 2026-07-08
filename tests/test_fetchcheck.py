"""Session-start fetch-first signal: TTL-cached fetch + behind-origin warning."""

from __future__ import annotations

import json
from pathlib import Path

from horus import fetchcheck


def _state(**overrides):
    state = {
        "branch": "main",
        "commit": {"hash": "abc1234", "rel": "2 hours ago", "subject": "x"},
        "dirty": False,
        "upstream": "origin/main",
        "behind": 0,
        "ahead": 0,
        "remote_url": "git@example.com:o/r.git",
    }
    state.update(overrides)
    return state


# --- warning_line ---

def test_warning_line_empty_when_fresh():
    assert fetchcheck.warning_line(_state()) == ""


def test_warning_line_empty_for_non_repo_and_no_upstream():
    assert fetchcheck.warning_line(None) == ""
    assert fetchcheck.warning_line(_state(upstream=None, behind=None)) == ""


def test_warning_line_reports_behind_count_and_branch():
    line = fetchcheck.warning_line(_state(behind=3))
    assert "3 commit(s) behind" in line
    assert "'main'" in line
    assert "fetch-first" in line


def test_warning_line_notes_dirty_tree():
    line = fetchcheck.warning_line(_state(behind=1, dirty=True))
    assert "uncommitted changes" in line


# --- fetch_and_state (cache + no-network paths) ---

def _patch_cache_home(monkeypatch, tmp_path):
    monkeypatch.setattr(fetchcheck.config, "config_dir", lambda: tmp_path / ".horus")


def test_fetch_and_state_none_outside_a_repo(monkeypatch, tmp_path):
    _patch_cache_home(monkeypatch, tmp_path)
    monkeypatch.setattr(fetchcheck.gitstate, "git_state", lambda root: None)
    assert fetchcheck.fetch_and_state(tmp_path) is None


def test_fetch_and_state_skips_fetch_without_a_remote(monkeypatch, tmp_path):
    _patch_cache_home(monkeypatch, tmp_path)
    monkeypatch.setattr(fetchcheck.gitstate, "git_state", lambda root: _state(remote_url=None))
    fetches = []
    monkeypatch.setattr(fetchcheck, "_fetch", lambda root, **kw: fetches.append(root) or True)

    state = fetchcheck.fetch_and_state(tmp_path)

    assert state is not None and fetches == []


def test_fetch_and_state_fetches_once_per_ttl_window(monkeypatch, tmp_path):
    _patch_cache_home(monkeypatch, tmp_path)
    monkeypatch.setattr(fetchcheck.gitstate, "git_state", lambda root: _state())
    fetches = []
    monkeypatch.setattr(fetchcheck, "_fetch", lambda root, **kw: fetches.append(root) or True)

    fetchcheck.fetch_and_state(tmp_path)
    fetchcheck.fetch_and_state(tmp_path)  # within TTL: cache hit, no second fetch

    assert len(fetches) == 1
    cache = json.loads((tmp_path / ".horus" / "cache" / "fetch-check.json").read_text(encoding="utf-8"))
    assert cache[str(Path(tmp_path).resolve())]["ok"] is True


def test_fetch_and_state_ttl_zero_always_fetches(monkeypatch, tmp_path):
    _patch_cache_home(monkeypatch, tmp_path)
    monkeypatch.setattr(fetchcheck.gitstate, "git_state", lambda root: _state())
    fetches = []
    monkeypatch.setattr(fetchcheck, "_fetch", lambda root, **kw: fetches.append(root) or True)

    fetchcheck.fetch_and_state(tmp_path, ttl=0)
    fetchcheck.fetch_and_state(tmp_path, ttl=0)

    assert len(fetches) == 2


def test_failed_fetch_is_cached_so_offline_pays_the_timeout_once(monkeypatch, tmp_path):
    _patch_cache_home(monkeypatch, tmp_path)
    monkeypatch.setattr(fetchcheck.gitstate, "git_state", lambda root: _state())
    fetches = []
    monkeypatch.setattr(fetchcheck, "_fetch", lambda root, **kw: fetches.append(root) or False)

    fetchcheck.fetch_and_state(tmp_path)
    fetchcheck.fetch_and_state(tmp_path)

    assert len(fetches) == 1  # the failed attempt is recorded; no retry inside the TTL


# --- hook mode (CLI) ---

def _hook_run(monkeypatch, capsys, state):
    from horus import cli

    monkeypatch.setattr(cli.fetchcheck, "fetch_and_state", lambda root, **kw: state)
    rc = cli._fetch_check_hook(Path("."))
    return rc, capsys.readouterr().out


def test_hook_injects_session_context_when_behind(monkeypatch, capsys):
    rc, out = _hook_run(monkeypatch, capsys, _state(behind=5))
    assert rc == 0
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    assert "5 commit(s) behind" in hso["additionalContext"]


def test_hook_stays_silent_when_fresh(monkeypatch, capsys):
    rc, out = _hook_run(monkeypatch, capsys, _state())
    assert rc == 0 and out.strip() == ""


def test_hook_stays_silent_outside_a_repo(monkeypatch, capsys):
    rc, out = _hook_run(monkeypatch, capsys, None)
    assert rc == 0 and out.strip() == ""


def test_hook_swallows_errors(monkeypatch, capsys):
    from horus import cli

    def boom(root, **kw):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(cli.fetchcheck, "fetch_and_state", boom)
    rc = cli._fetch_check_hook(Path("."))
    assert rc == 0 and capsys.readouterr().out.strip() == ""
