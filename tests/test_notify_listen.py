"""Tests for the inbound steering channel (horus.notify_listen).

Deterministic, owner-chat-locked, no LLM: a bounded command grammar maps 1:1 onto
existing horus commands, and every other sender/command is refused or ignored.
"""

from __future__ import annotations

from horus import notify, notify_listen
from horus.notify import NotifyConfig


def _cfg(chat_id="8605049070"):
    return NotifyConfig(sink="telegram", token="t", chat_id=chat_id)


def _recording_runner():
    calls: list[list[str]] = []

    def run(argv):
        calls.append(argv)
        return f"ran: {' '.join(argv)}"

    return run, calls


# --------------------------------------------------------------------------- #
# dispatch — the pure grammar
# --------------------------------------------------------------------------- #


def test_dispatch_read_command_runs_mapped_argv():
    run, calls = _recording_runner()
    out = notify_listen.dispatch("sessions", runner=run)
    assert calls == [["sessions"]]
    assert out == "ran: sessions"


def test_dispatch_unknown_command_returns_help_not_error():
    run, calls = _recording_runner()
    out = notify_listen.dispatch("rm -rf /", runner=run)
    assert calls == []  # never runs
    assert "unknown command" in out and "commands:" in out


def test_dispatch_help_and_empty_return_help():
    run, _ = _recording_runner()
    assert "commands:" in notify_listen.dispatch("help", runner=run)
    assert "commands:" in notify_listen.dispatch("/start", runner=run)
    assert "commands:" in notify_listen.dispatch("   ", runner=run)


def test_dispatch_missing_required_arg_shows_usage():
    run, calls = _recording_runner()
    out = notify_listen.dispatch("cancel", runner=run)
    assert calls == []
    assert out.startswith("usage: cancel")


def test_dispatch_rejects_unsafe_argument():
    run, calls = _recording_runner()
    out = notify_listen.dispatch("cancel abc;rm", runner=run)
    assert calls == []
    assert "invalid argument" in out


def test_dispatch_cancel_runs_schedule_cancel():
    run, calls = _recording_runner()
    notify_listen.dispatch("cancel fb46465b", runner=run)
    assert calls == [["schedule", "cancel", "fb46465b"]]


def test_dispatch_usage_reads_all_accounts():
    run, calls = _recording_runner()
    notify_listen.dispatch("usage", runner=run)
    assert calls == [["usage", "all"]]


def test_dispatch_release_runs_schedule_release():
    run, calls = _recording_runner()
    notify_listen.dispatch("release fb46465b", runner=run)
    assert calls == [["schedule", "release", "fb46465b"]]


def test_dispatch_supervise_appends_repo_path():
    run, calls = _recording_runner()
    notify_listen.dispatch("supervise 16fba944", repo="/home/rafa/projects/horus-harness", runner=run)
    assert calls == [["supervise", "16fba944", "--path", "/home/rafa/projects/horus-harness"]]


def test_dispatch_takes_only_first_arg_token():
    run, calls = _recording_runner()
    notify_listen.dispatch("cancel fb46465b extra tokens", runner=run)
    assert calls == [["schedule", "cancel", "fb46465b"]]


# --------------------------------------------------------------------------- #
# handle_update — chat gate + message/callback routing
# --------------------------------------------------------------------------- #


def test_handle_update_ignores_other_chat():
    run, calls = _recording_runner()
    update = {"update_id": 1, "message": {"chat": {"id": 999}, "text": "sessions"}}
    assert notify_listen.handle_update(update, _cfg(), runner=run) is None
    assert calls == []


def test_handle_update_owner_message_dispatches():
    run, calls = _recording_runner()
    update = {"update_id": 1, "message": {"chat": {"id": 8605049070}, "text": "sessions"}}
    reply = notify_listen.handle_update(update, _cfg(), runner=run)
    assert reply is not None and reply.text == "ran: sessions"
    assert reply.answer_callback_id is None
    assert calls == [["sessions"]]


def test_handle_update_callback_dispatches_and_carries_ack_id():
    run, calls = _recording_runner()
    update = {
        "update_id": 2,
        "callback_query": {
            "id": "cbq1", "data": "supervise 16fba944",
            "message": {"chat": {"id": 8605049070}},
        },
    }
    reply = notify_listen.handle_update(update, _cfg(), repo="/repo", runner=run)
    assert reply is not None and reply.answer_callback_id == "cbq1"
    assert calls == [["supervise", "16fba944", "--path", "/repo"]]


def test_handle_update_ignores_non_text_message():
    update = {"update_id": 3, "message": {"chat": {"id": 8605049070}, "photo": [{}]}}
    assert notify_listen.handle_update(update, _cfg()) is None


# --------------------------------------------------------------------------- #
# listen — the loop (transport injected)
# --------------------------------------------------------------------------- #


def test_listen_handles_and_ignores_advancing_offset():
    sent: list[notify_listen.Reply] = []
    batches = [
        [
            {"update_id": 10, "message": {"chat": {"id": 8605049070}, "text": "sessions"}},
            {"update_id": 11, "message": {"chat": {"id": 42}, "text": "sessions"}},  # other chat
        ],
    ]
    offsets: list[int] = []

    def fake_get(cfg, offset):
        offsets.append(offset)
        return batches.pop(0) if batches else []

    def fake_send(cfg, reply):
        sent.append(reply)

    # replace the real horus runner so no subprocess spawns
    import horus.notify_listen as nl
    orig = nl._run_horus
    nl._run_horus = lambda argv, **k: "ok"
    try:
        res = notify_listen.listen(
            _cfg(), get_updates=fake_get, send=fake_send, max_iterations=2,
        )
    finally:
        nl._run_horus = orig

    assert res.handled == 1 and res.ignored == 1
    assert len(sent) == 1
    # second poll uses offset past the highest update_id seen
    assert offsets[0] == 0 and offsets[1] == 12


def test_listen_poll_error_is_counted_not_raised(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)

    def boom(cfg, offset):
        raise RuntimeError("network down")

    # A raising poll is counted as an error and never propagates out of listen().
    res = notify_listen.listen(_cfg(), get_updates=boom, max_iterations=1)
    assert res.errors == 1 and res.handled == 0


# --------------------------------------------------------------------------- #
# outbound inline keyboard on escalations
# --------------------------------------------------------------------------- #


def test_escalation_actions_render_inline_keyboard(monkeypatch):
    captured = {}

    def fake_post(url, payload):
        captured["payload"] = payload
        return 200, '{"ok":true}'

    monkeypatch.setattr(notify, "_post_json", fake_post)
    esc = notify.Escalation(
        event=notify.SUPERVISE_GATE, project="horus-harness", summary="red gate",
        session_id="16fba944", actions=(("Sessions", "sessions"), ("Re-supervise", "supervise 16fba944")),
    )
    result = notify.escalate(esc, cfg=_cfg(), force=True)
    assert result.delivered
    kb = captured["payload"]["reply_markup"]["inline_keyboard"]
    assert kb[0][0] == {"text": "Sessions", "callback_data": "sessions"}
    assert kb[0][1]["callback_data"] == "supervise 16fba944"


def test_escalation_without_actions_has_no_keyboard(monkeypatch):
    captured = {}
    monkeypatch.setattr(notify, "_post_json", lambda url, payload: (captured.setdefault("p", payload), (200, '{"ok":true}'))[1])
    esc = notify.Escalation(event=notify.SUPERVISE_GATE, project="p", summary="s")
    notify.escalate(esc, cfg=_cfg(), force=True)
    assert "reply_markup" not in captured["p"]
