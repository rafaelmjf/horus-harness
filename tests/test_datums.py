"""Tests for the empirical model-calibration datums — Slice 1 spine.

Covers: the mechanical store (backfill seeding, launch/completion, close), the
exit classifier + usage-death heuristic, owner-priors seeding, the roll-up join
across both layers, and the CLI end-to-end (`horus run --agent fake` writes a
row, `horus datum close` attaches the qualitative half, `horus capabilities
--models` renders the backfilled roll-up including the gpt-5.6 caution flag).

The hard boundary — outcome is agent-supplied, never auto-scored, and the roll-up
recommends nothing — is asserted directly.
"""

from __future__ import annotations

import json

import pytest

from horus import datums
from horus.cli import main


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _store(tmp_path) -> datums.DatumStore:
    return datums.DatumStore(tmp_path / "datums.json")


# --- exit classification -----------------------------------------------------

def test_classify_exit_maps_status_to_condition():
    assert datums.classify_exit("exited", saw_usage_signal=False) == "completed"
    assert datums.classify_exit("failed", saw_usage_signal=False) == "crashed"


def test_usage_signal_wins_over_status():
    # A window death must read as usage-death, not quality-crash, whatever the raw status.
    assert datums.classify_exit("failed", saw_usage_signal=True) == "usage-death"
    assert datums.classify_exit("exited", saw_usage_signal=True) == "usage-death"


def test_looks_like_usage_death_matches_walls_not_prose():
    assert datums.looks_like_usage_death("Error: usage limit reached, resets in 3h")
    assert datums.looks_like_usage_death("HTTP 429 too many requests")
    assert datums.looks_like_usage_death("insufficient_quota")
    assert not datums.looks_like_usage_death("the test suite failed")
    assert not datums.looks_like_usage_death(None)


# --- store: backfill, launch, completion, close ------------------------------

def test_backfill_is_seeded_when_file_absent(tmp_path):
    store = _store(tmp_path)
    rows = store.all()
    # 10 Sonnet + 1 each for Opus/Fable/gpt-5.6/gpt-5.5 = 14; Haiku has no datum.
    assert len(rows) == 14
    sonnet = [d for d in rows if d.model == "sonnet-5"]
    assert len(sonnet) == 10 and all(d.outcome == "clean" for d in sonnet)
    assert all(d.source == "backfill" for d in rows)
    assert not any(d.model == "haiku-4.5" for d in rows)  # unproven, 0 datums


def test_record_launch_then_completion(tmp_path):
    store = _store(tmp_path)
    store.record_launch(
        datums.Datum(session_id="run-1", model="sonnet-5", agent="claude", posture="full-auto", worker=True)
    )
    d = store.get("run-1")
    assert d is not None and d.source == "run" and d.exit is None and d.outcome is None

    store.record_completion("run-1", exit="completed", runtime_seconds=12.5, returncode=0)
    d = store.get("run-1")
    assert d.exit == "completed" and d.runtime_seconds == 12.5 and d.completed_at
    # Backfill persisted alongside the live row once the file exists.
    assert store.path.exists() and len(store.all()) == 15


def test_completion_no_row_is_noop(tmp_path):
    store = _store(tmp_path)
    store.record_completion("ghost", exit="crashed", runtime_seconds=1.0, returncode=1)
    assert store.get("ghost") is None


def test_close_attaches_qualitative_half_by_prefix(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="abc123def", model="opus-4.8"))
    d = store.close("abc12", outcome="nudged", shape="ambiguous/med/long", note="two nudges")
    assert d.outcome == "nudged" and d.shape == "ambiguous/med/long" and d.note == "two nudges"
    assert d.closed_at
    assert store.get("abc123def").outcome == "nudged"  # persisted


def test_close_rejects_unknown_outcome(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="run-x"))
    with pytest.raises(ValueError):
        store.close("run-x", outcome="great", shape=None, note=None)


def test_close_missing_and_ambiguous_prefix(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="dup-1"))
    store.record_launch(datums.Datum(session_id="dup-2"))
    with pytest.raises(LookupError):
        store.close("nope", outcome="clean", shape=None, note=None)
    with pytest.raises(LookupError):
        store.close("dup", outcome="clean", shape=None, note=None)


def test_relaunch_preserves_qualitative_half(tmp_path):
    # A resume reuses the same session id; a re-recorded launch must not wipe an
    # already-attached outcome.
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="r1", model="sonnet-5"))
    store.close("r1", outcome="clean", shape="s", note="n")
    store.record_launch(datums.Datum(session_id="r1", model="sonnet-5", posture="full-auto"))
    d = store.get("r1")
    assert d.outcome == "clean" and d.posture == "full-auto"


# --- owner priors ------------------------------------------------------------

def test_priors_seeded_and_parsed(tmp_path):
    path = tmp_path / "capabilities.toml"
    priors = datums.load_priors(path)
    assert path.exists()  # seeded on first read
    assert priors["sonnet-5"]["tier"] == "scoped-impl lead"
    gpt = priors["gpt-5.6"]
    assert "token-hungry" in gpt["caution"]
    assert gpt["guard"] == "do not dispatch near usage ceiling"


def test_priors_hand_edits_are_respected(tmp_path):
    path = tmp_path / "capabilities.toml"
    path.write_text('[models."custom-1"]\ntier = "handmade"\n', encoding="utf-8")
    priors = datums.load_priors(path)
    assert priors == {"custom-1": {"tier": "handmade"}}  # no reseed over an existing file


# --- roll-up (join across both layers) ---------------------------------------

def test_rollup_joins_priors_and_datums_and_sorts_by_clean_count(tmp_path):
    store = _store(tmp_path)
    rollups = datums.build_model_rollup(store.all(), datums.load_priors(tmp_path / "priors.toml"))
    by_model = {r.model: r for r in rollups}
    # Sonnet's 10 clean datums sort it first.
    assert rollups[0].model == "sonnet-5" and rollups[0].clean_count == 10
    # Haiku appears from priors alone with zero datums (unproven, still visible).
    assert by_model["haiku-4.5"].total_datums == 0
    assert by_model["haiku-4.5"].tier == "mechanical (unproven)"
    # gpt-5.6's owner flags come through the join.
    assert "token-hungry" in by_model["gpt-5.6"].caution


def test_rollup_last_outcomes_most_recent_first(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="run-a", model="m", launched_at="2026-01-01T00:00:00+00:00"))
    store.record_launch(datums.Datum(session_id="run-b", model="m", launched_at="2026-01-02T00:00:00+00:00"))
    store.close("run-a", outcome="clean", shape=None, note=None)
    store.close("run-b", outcome="bounced", shape=None, note=None)
    r = next(x for x in datums.build_model_rollup(store.all(), {}) if x.model == "m")
    assert r.last_outcomes == ["bounced", "clean"]  # newest first


def test_rollup_render_is_data_only(tmp_path):
    store = _store(tmp_path)
    text = datums.render_model_rollup(datums.build_model_rollup(store.all(), datums.load_priors(tmp_path / "p.toml")))
    assert "DATA ONLY" in text
    assert "token-hungry" in text  # gpt-5.6 caution surfaced
    # Never emits a recommendation/pick.
    lowered = text.lower()
    assert "recommend" not in lowered and "you should use" not in lowered and "best model" not in lowered


# --- CLI end-to-end ----------------------------------------------------------

def test_run_fake_writes_mechanical_datum(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert main(["run", "hello", "--agent", "fake", "--model", "sonnet-5", "--path", str(tmp_path)]) == 0
    d = datums.DatumStore.default().get("fake-session")
    assert d is not None
    assert d.model == "sonnet-5" and d.agent == "fake" and d.posture == "default"
    assert d.exit == "completed" and d.runtime_seconds is not None and d.outcome is None


def test_datum_close_cli_attaches_outcome(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["run", "hi", "--agent", "fake", "--model", "opus-4.8", "--path", str(tmp_path)])
    rc = main(["datum", "close", "fake", "--outcome", "clean", "--shape", "clear/small/short", "--note", "ok"])
    assert rc == 0
    assert "outcome=clean" in capsys.readouterr().out
    d = datums.DatumStore.default().get("fake-session")
    assert d.outcome == "clean" and d.shape == "clear/small/short" and d.note == "ok"


def test_datum_close_cli_bad_id_returns_2(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert main(["datum", "close", "missing", "--outcome", "clean"]) == 2


def test_capabilities_models_rollup_cli(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["capabilities", "--models"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Model calibration roll-up" in out
    assert "sonnet-5" in out and "10 clean" in out
    assert "token-hungry" in out  # gpt-5.6 owner caution rendered


def test_capabilities_models_stdout_is_json(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--models", "--stdout"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "models" in data and any(m["model"] == "gpt-5.6" and m["caution"] for m in data["models"])
    assert "recommend" not in data["note"].lower()
