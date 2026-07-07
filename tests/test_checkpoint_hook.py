"""Behaviour of the `horus checkpoint --hook` Stop hook (warn default / block opt-in)."""

import json
import uuid

from horus import cli, closure, native_hooks
from horus.continuity import Finding


def _sid() -> str:
    return "chk-" + uuid.uuid4().hex[:8]


def _stub_findings(monkeypatch, findings):
    monkeypatch.setattr(closure, "checkpoint_gate", lambda *a, **k: findings)


def _stub_stdin(monkeypatch, data):
    monkeypatch.setattr(cli, "_read_hook_stdin", lambda: data)


def _use_temp_sentinels(monkeypatch, tmp_path):
    monkeypatch.setattr(native_hooks.tempfile, "gettempdir", lambda: str(tmp_path))


def test_clean_checkpoint_is_silent(tmp_path, monkeypatch, capsys):
    _use_temp_sentinels(monkeypatch, tmp_path)
    _stub_findings(monkeypatch, [Finding("ok", "working tree clean")])
    _stub_stdin(monkeypatch, {"session_id": _sid()})
    assert cli._checkpoint_hook(tmp_path, block=False) == 0
    assert capsys.readouterr().out == ""


def test_dirty_tree_warns_non_blocking(tmp_path, monkeypatch, capsys):
    _use_temp_sentinels(monkeypatch, tmp_path)
    _stub_findings(monkeypatch, [Finding("warn", "3 uncommitted change(s) in the working tree")])
    _stub_stdin(monkeypatch, {"session_id": _sid()})
    assert cli._checkpoint_hook(tmp_path, block=False) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "systemMessage" in payload  # warn = non-blocking notice, not a block
    assert "decision" not in payload
    assert "uncommitted change" in payload["systemMessage"]


def test_block_mode_blocks_the_stop(tmp_path, monkeypatch, capsys):
    _use_temp_sentinels(monkeypatch, tmp_path)
    _stub_findings(monkeypatch, [Finding("warn", "2 local commit(s) not pushed")])
    _stub_stdin(monkeypatch, {"session_id": _sid()})
    assert cli._checkpoint_hook(tmp_path, block=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "not pushed" in payload["reason"]


def test_warns_once_per_rearm_window(tmp_path, monkeypatch, capsys):
    _use_temp_sentinels(monkeypatch, tmp_path)
    _stub_findings(monkeypatch, [Finding("warn", "dirty")])
    sid = _sid()
    _stub_stdin(monkeypatch, {"session_id": sid})
    cli._checkpoint_hook(tmp_path, block=False)
    assert capsys.readouterr().out != ""      # first stop fires
    cli._checkpoint_hook(tmp_path, block=False)
    assert capsys.readouterr().out == ""       # second stop within window is suppressed


def test_stop_hook_active_short_circuits(tmp_path, monkeypatch, capsys):
    """Never re-fire when the agent reports the stop was already hook-driven (loop guard)."""
    _use_temp_sentinels(monkeypatch, tmp_path)
    _stub_findings(monkeypatch, [Finding("warn", "dirty")])
    _stub_stdin(monkeypatch, {"session_id": _sid(), "stop_hook_active": True})
    assert cli._checkpoint_hook(tmp_path, block=True) == 0
    assert capsys.readouterr().out == ""


def test_checker_exception_is_silent(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("git blew up")
    monkeypatch.setattr(closure, "checkpoint_gate", boom)
    assert cli._checkpoint_hook(tmp_path, block=False) == 0
    assert capsys.readouterr().out == ""
