"""Tests for the remote input bridge — a session asks, the owner answers."""

from __future__ import annotations

import pytest

from horus import config, input_bridge


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "horus-home")


def test_write_and_list_pending():
    req = input_bridge.write_request("Approach?", ["A", "B"], now=1000.0, project="proj")
    pending = input_bridge.list_pending()
    assert [r.id for r in pending] == [req.id]
    assert pending[0].question == "Approach?" and pending[0].options == ["A", "B"]
    assert pending[0].project == "proj"


def test_a_request_with_a_response_is_no_longer_pending():
    req = input_bridge.write_request("Q", ["A"], now=1.0)
    input_bridge.write_response(req.id, "A", kind="option", now=2.0)
    assert input_bridge.list_pending() == []
    resp = input_bridge.read_response(req.id)
    assert resp.answer == "A" and resp.kind == "option"


def test_write_response_refuses_unknown_and_duplicate():
    assert input_bridge.write_response("nope", "x", kind="text") is False
    req = input_bridge.write_request("Q", free_text=True, now=1.0)
    assert input_bridge.write_response(req.id, "first", kind="text", now=2.0) is True
    assert input_bridge.write_response(req.id, "second", kind="text", now=3.0) is False
    assert input_bridge.read_response(req.id).answer == "first"  # first wins


def test_record_answer_by_option_index():
    req = input_bridge.write_request("Q", ["Yes", "No"], now=1.0)
    ok, msg = input_bridge.record_answer(req.id, "#1", now=2.0)
    assert ok and "No" in msg
    assert input_bridge.read_response(req.id).answer == "No"


def test_record_answer_free_text_binds_to_singleton_without_id():
    req = input_bridge.write_request("Q", free_text=True, now=1.0)
    ok, _ = input_bridge.record_answer(None, "do the safe thing", now=2.0)
    assert ok
    assert input_bridge.read_response(req.id).answer == "do the safe thing"


def test_record_answer_is_ambiguous_when_multiple_open_and_no_id():
    input_bridge.write_request("Q1", ["A"], now=1.0)
    input_bridge.write_request("Q2", ["A"], now=2.0)
    ok, msg = input_bridge.record_answer(None, "#0", now=3.0)
    assert ok is False and "open requests" in msg


def test_record_answer_rejects_free_text_when_not_allowed():
    req = input_bridge.write_request("Q", ["A"], free_text=False, now=1.0)
    ok, msg = input_bridge.record_answer(req.id, "typed", now=2.0)
    assert ok is False and "option" in msg


def test_record_answer_rejects_out_of_range_index():
    req = input_bridge.write_request("Q", ["A"], now=1.0)
    ok, msg = input_bridge.record_answer(req.id, "#5", now=2.0)
    assert ok is False and "range" in msg


def test_await_response_returns_answer_then_times_out():
    req = input_bridge.write_request("Q", ["A"], now=1.0)
    # An immediate answer is returned.
    input_bridge.write_response(req.id, "A", kind="option", now=2.0)
    resp = input_bridge.await_response(req.id, timeout=10, clock=lambda: 0.0, sleep=lambda s: None)
    assert resp is not None and resp.answer == "A"

    # A request with no response times out (fake clock advances past the deadline).
    other = input_bridge.write_request("Q2", ["A"], now=3.0)
    ticks = iter([0.0, 0.0, 5.0, 11.0])
    resp2 = input_bridge.await_response(
        other.id, timeout=10, clock=lambda: next(ticks), sleep=lambda s: None,
    )
    assert resp2 is None


def test_cleanup_removes_request_and_response():
    req = input_bridge.write_request("Q", ["A"], now=1.0)
    input_bridge.write_response(req.id, "A", kind="option", now=2.0)
    input_bridge.cleanup(req.id)
    assert input_bridge.list_pending() == []
    assert input_bridge.read_response(req.id) is None


# --- `horus ask` CLI (session-side blocking primitive) ------------------------


def _ask_args(**kw):
    import argparse
    base = dict(question="Approach?", option=["A", "B"], free_text=False,
                default=None, timeout=None, session=None, project="proj")
    base.update(kw)
    return argparse.Namespace(**base)


def test_cmd_ask_prints_the_answer(monkeypatch, capsys):
    from horus import cli
    monkeypatch.setattr(
        input_bridge, "await_response",
        lambda rid, **k: input_bridge.InputResponse(rid, "B", "option", 2.0),
    )
    rc = cli.cmd_ask(_ask_args())
    assert rc == 0
    assert capsys.readouterr().out.strip() == "B"


def test_cmd_ask_timeout_prints_default_and_exits_3(monkeypatch, capsys):
    from horus import cli
    monkeypatch.setattr(input_bridge, "await_response", lambda rid, **k: None)
    rc = cli.cmd_ask(_ask_args(default="A"))
    assert rc == 3
    assert capsys.readouterr().out.strip() == "A"


def test_cmd_ask_requires_an_option_or_free_text(capsys):
    from horus import cli
    rc = cli.cmd_ask(_ask_args(option=None, free_text=False))
    assert rc == 2
    assert "at least one --option or --free-text" in capsys.readouterr().out
