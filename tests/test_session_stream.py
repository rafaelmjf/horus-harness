"""Tests for the in-app session streaming engine (`horus.session_stream`)."""

import itertools
import json

from horus.session_stream import SessionManager


def _drain(manager, client_id, timeout=5.0):
    """Wait for the current turn's background thread to finish."""
    sess = manager.get(client_id)
    if sess and sess._thread:
        sess._thread.join(timeout)
    return sess


def test_start_runs_a_turn_and_buffers_events(tmp_path):
    mgr = SessionManager()
    cid = mgr.start(agent="fake", project_dir=tmp_path, account="demo", prompt="hello")
    sess = _drain(mgr, cid)

    kinds = [t.kind for t in sess.events]
    assert kinds[0] == "user"                       # typed/seeded prompt echoed first
    assert "text" in kinds and "result" in kinds    # the fake stream's assistant text + result
    assert kinds[-1] == "status" and sess.status == "idle"  # turn done -> idle, ready for more
    assert sess.session_id == "fake-session"        # captured from SESSION_STARTED
    # The assistant text carries the prompt back (fake echoes it).
    assert any(t.kind == "text" and "hello" in (t.text or "") for t in sess.events)


def test_send_input_resumes_and_appends(tmp_path):
    mgr = SessionManager()
    cid = mgr.start(agent="fake", project_dir=tmp_path, prompt="first")
    _drain(mgr, cid)
    before = len(mgr.get(cid).events)

    assert mgr.send_input(cid, "second") is True
    sess = _drain(mgr, cid)
    assert len(sess.events) > before
    assert any(t.kind == "user" and t.text == "second" for t in sess.events)


def test_send_input_rejects_unknown_and_empty(tmp_path):
    mgr = SessionManager()
    cid = mgr.start(agent="fake", project_dir=tmp_path, prompt="x")
    _drain(mgr, cid)
    assert mgr.send_input("nope", "hi") is False     # unknown session
    assert mgr.send_input(cid, "   ") is False        # empty prompt


def test_fresh_session_opens_idle(tmp_path):
    mgr = SessionManager()
    cid = mgr.start(agent="fake", project_dir=tmp_path, prompt="")  # no first turn
    sess = mgr.get(cid)
    assert sess.status == "idle" and sess.events == []
    assert sess.title and sess.client_id == cid


def test_subscribe_yields_sse_frames(tmp_path):
    mgr = SessionManager()
    cid = mgr.start(agent="fake", project_dir=tmp_path, prompt="ping")
    sess = _drain(mgr, cid)

    n = len(sess.events)
    frames = list(itertools.islice(mgr.subscribe(cid, heartbeat=0.05), n))
    assert all(f.startswith("data: ") for f in frames)
    payloads = [json.loads(f[len("data: "):]) for f in frames]
    assert payloads[0]["kind"] == "user"
    assert any(p["kind"] == "text" for p in payloads)


def test_subscribe_unknown_session_emits_error(tmp_path):
    mgr = SessionManager()
    frames = list(itertools.islice(mgr.subscribe("ghost", heartbeat=0.05), 1))
    assert json.loads(frames[0][len("data: "):])["kind"] == "error"
