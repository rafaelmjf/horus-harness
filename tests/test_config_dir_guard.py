"""Tests for the config-dir concurrency guard in horus.cli.

Claude Code and Codex both support several concurrent sessions on one
CLAUDE_CONFIG_DIR / CODEX_HOME; settled sessions coexist safely. The one observed
corruption (2026-07-16) was two workers cold-starting simultaneously on a shared
*ambient* dir, a race that per-account isolation has since largely dissolved. So the
guard is advisory: it always proceeds, but names the live peer so a shared config dir
(and its shared rate-limit budget) is never silent.
"""

from __future__ import annotations

from horus import cli, config, registry


def _rec(account, session_id="peer", pid=4321, project="/home/rafa/projects/horus-agent"):
    return registry.SessionRecord(
        session_id=session_id, agent="claude", project=project,
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


def test_guard_allows_when_no_live_session(tmp_path, monkeypatch, capsys):
    dirs = {"work": tmp_path / "work", "personal": tmp_path / "personal"}
    _setup(monkeypatch, records=[], dirs=dirs)
    assert cli._config_dir_conflict_guard("claude", "personal") is None
    assert capsys.readouterr().out == ""  # silent when nothing shares the dir


def test_guard_notes_but_proceeds_on_shared_dir(tmp_path, monkeypatch, capsys):
    """Launching on 'personal' while another live session already holds personal's dir."""
    dirs = {"work": tmp_path / "work", "personal": tmp_path / "personal"}
    _setup(monkeypatch, records=[_rec("personal", "peerA")], dirs=dirs)  # invoker is 'work'
    assert cli._config_dir_conflict_guard("claude", "personal") is None
    out = capsys.readouterr().out
    assert "sharing" in out and "peerA" in out and "proceeding" in out
    assert "horus-agent" in out  # names the peer's project


def test_guard_notes_overseer_self_share(tmp_path, monkeypatch, capsys):
    """The one live peer on the target dir IS the launching session's own dir."""
    dirs = {"work": tmp_path / "work"}
    _setup(monkeypatch, records=[_rec("work", "overseer")], dirs=dirs, env_alias="work")
    assert cli._config_dir_conflict_guard("claude", "work") is None
    out = capsys.readouterr().out.lower()
    assert "sharing" in out and "launching session" in out


def test_guard_proceeds_when_overseer_dir_has_a_second_worker(tmp_path, monkeypatch, capsys):
    """Overseer + another live worker already share the target dir -> still proceeds, noted."""
    dirs = {"work": tmp_path / "work"}
    records = [_rec("work", "overseer"), _rec("work", "peerB", pid=999)]
    _setup(monkeypatch, records=records, dirs=dirs, env_alias="work")
    assert cli._config_dir_conflict_guard("claude", "work") is None
    assert "sharing" in capsys.readouterr().out


def test_guard_ignores_live_session_on_a_different_dir(tmp_path, monkeypatch, capsys):
    dirs = {"work": tmp_path / "work", "personal": tmp_path / "personal"}
    _setup(monkeypatch, records=[_rec("work", "peerWork")], dirs=dirs, env_alias="work")
    assert cli._config_dir_conflict_guard("claude", "personal") is None
    assert capsys.readouterr().out == ""


def test_guard_skips_non_agent_adapter(tmp_path, monkeypatch):
    dirs = {"work": tmp_path / "work"}
    _setup(monkeypatch, records=[_rec("work", "peer")], dirs=dirs)
    assert cli._config_dir_conflict_guard("fake", "work") is None
