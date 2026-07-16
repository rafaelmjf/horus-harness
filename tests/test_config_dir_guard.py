"""Tests for the config-dir concurrency guard in horus.cli.

Two agent CLIs sharing one CLAUDE_CONFIG_DIR / CODEX_HOME race on its JSON config
and corrupt it, so both can die on startup. The guard refuses a second live process
on a dir already in use; the launching session sharing its own dir only warns.
"""

from __future__ import annotations

from horus import cli, config, registry


def _rec(account, session_id="peer", pid=4321):
    return registry.SessionRecord(
        session_id=session_id, agent="claude", project="/x",
        account=account, status="running", pid=pid,
    )


def _setup(monkeypatch, records, dirs, *, env_alias="work"):
    monkeypatch.setattr(registry, "process_alive", lambda pid: True)

    class _Fake:
        def all(self):
            return records

    monkeypatch.setattr(registry.Registry, "default", classmethod(lambda cls: _Fake()))
    monkeypatch.setattr(config, "load_account_config_dirs", lambda: {k: str(v) for k, v in dirs.items()})
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(dirs[env_alias]))


def test_guard_allows_when_no_live_session(tmp_path, monkeypatch):
    dirs = {"work": tmp_path / "work", "personal": tmp_path / "personal"}
    _setup(monkeypatch, records=[], dirs=dirs)
    assert cli._config_dir_conflict_guard("claude", "personal", force=False) is None


def test_guard_refuses_second_worker_on_same_dir(tmp_path, monkeypatch, capsys):
    """Launching on 'personal' while another live worker already holds personal's dir."""
    dirs = {"work": tmp_path / "work", "personal": tmp_path / "personal"}
    _setup(monkeypatch, records=[_rec("personal", "peerA")], dirs=dirs)  # invoker is 'work'
    assert cli._config_dir_conflict_guard("claude", "personal", force=False) == 2
    out = capsys.readouterr().out
    assert "already in use" in out and "peerA" in out


def test_guard_force_downgrades_refusal_to_warning(tmp_path, monkeypatch, capsys):
    dirs = {"work": tmp_path / "work", "personal": tmp_path / "personal"}
    _setup(monkeypatch, records=[_rec("personal", "peerA")], dirs=dirs)
    assert cli._config_dir_conflict_guard("claude", "personal", force=True) is None
    assert "Warning" in capsys.readouterr().out


def test_guard_warns_but_allows_overseer_self_share(tmp_path, monkeypatch, capsys):
    """The one live peer on the target dir IS the launching session's own dir."""
    dirs = {"work": tmp_path / "work"}
    _setup(monkeypatch, records=[_rec("work", "overseer")], dirs=dirs, env_alias="work")
    assert cli._config_dir_conflict_guard("claude", "work", force=False) is None
    assert "shares" in capsys.readouterr().out.lower()


def test_guard_refuses_when_overseer_dir_has_a_second_worker(tmp_path, monkeypatch):
    """Overseer + another live worker already share the target dir -> not tolerated."""
    dirs = {"work": tmp_path / "work"}
    records = [_rec("work", "overseer"), _rec("work", "peerB", pid=999)]
    _setup(monkeypatch, records=records, dirs=dirs, env_alias="work")
    assert cli._config_dir_conflict_guard("claude", "work", force=False) == 2


def test_guard_ignores_live_session_on_a_different_dir(tmp_path, monkeypatch):
    dirs = {"work": tmp_path / "work", "personal": tmp_path / "personal"}
    _setup(monkeypatch, records=[_rec("work", "peerWork")], dirs=dirs, env_alias="work")
    assert cli._config_dir_conflict_guard("claude", "personal", force=False) is None


def test_guard_skips_non_agent_adapter(tmp_path, monkeypatch):
    dirs = {"work": tmp_path / "work"}
    _setup(monkeypatch, records=[_rec("work", "peer")], dirs=dirs)
    assert cli._config_dir_conflict_guard("fake", "work", force=False) is None
