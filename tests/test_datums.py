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
from datetime import datetime, timezone

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


# --- canonical model-name normalization ---------------------------------------

def test_canonical_model_name_falls_back_to_alias_map():
    assert datums.canonical_model_name("sonnet") == "sonnet-5"
    assert datums.canonical_model_name("haiku") == "haiku-4.5"
    assert datums.canonical_model_name("opus") == "opus-4.8"


def test_canonical_model_name_prefers_resolved_over_alias_map():
    # Family default moves (sonnet -> sonnet-6) would mis-record via the static
    # map; resolved-capture (what the adapter says actually ran) stays correct.
    assert datums.canonical_model_name("sonnet", resolved="claude-sonnet-6-20270101") == "sonnet-6"
    assert datums.canonical_model_name("haiku", resolved="claude-haiku-4-5-20251001") == "haiku-4.5"
    assert datums.canonical_model_name(None, resolved="claude-opus-4-8-20260601") == "opus-4.8"


def test_canonical_model_name_passes_through_unrecognized():
    assert datums.canonical_model_name("gpt-5.6-sol") == "gpt-5.6-sol"
    assert datums.canonical_model_name("sonnet-5") == "sonnet-5"  # already canonical
    assert datums.canonical_model_name(None) is None
    assert datums.canonical_model_name("sonnet", resolved="not-a-recognized-id") == "sonnet-5"


# --- datums.json bare->proper migration ---------------------------------------

def test_migrate_names_merges_bare_into_canonical(tmp_path):
    # Write the fixture straight to disk (bypassing record_launch's virtual
    # backfill-becomes-concrete-on-first-write behavior) so the row count is
    # exactly what this test put there.
    store = _store(tmp_path)
    rows = {}
    for i in range(11):
        rows[f"sonnet-run-{i}"] = {"session_id": f"sonnet-run-{i}", "model": "sonnet"}
    for i in range(2):
        rows[f"haiku-run-{i}"] = {"session_id": f"haiku-run-{i}", "model": "haiku"}
    rows["already-canonical"] = {"session_id": "already-canonical", "model": "sonnet-5"}
    rows["untouched"] = {"session_id": "untouched", "model": "gpt-5.6-sol"}
    store.path.write_text(json.dumps({"datums": rows}, indent=2) + "\n", encoding="utf-8")

    renamed = store.migrate_names()
    assert renamed == {"sonnet": 11, "haiku": 2}

    saved = json.loads(store.path.read_text(encoding="utf-8"))["datums"]
    assert all(saved[f"sonnet-run-{i}"]["model"] == "sonnet-5" for i in range(11))
    assert all(saved[f"haiku-run-{i}"]["model"] == "haiku-4.5" for i in range(2))
    assert saved["already-canonical"]["model"] == "sonnet-5"
    assert saved["untouched"]["model"] == "gpt-5.6-sol"
    # Every record is preserved — nothing dropped by the merge.
    assert len(saved) == 15

    # One merged roll-up row per canonical model — no leftover half-complete row.
    rollups = datums.build_model_rollup(store.all(), {})
    by_model = {r.model: r for r in rollups}
    assert "sonnet" not in by_model and "haiku" not in by_model
    assert by_model["sonnet-5"].total_datums == 12  # 11 migrated + 1 already-canonical
    assert by_model["haiku-4.5"].total_datums == 2


def test_migrate_names_rerun_is_a_byte_stable_noop(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="s1", model="sonnet"))
    store.migrate_names()
    before = store.path.read_text(encoding="utf-8")

    renamed_again = store.migrate_names()

    assert renamed_again == {}
    assert store.path.read_text(encoding="utf-8") == before  # byte-stable no-op


def test_migrate_names_noop_when_no_datums_file(tmp_path):
    store = _store(tmp_path)
    assert store.migrate_names() == {}
    assert not store.path.exists()  # never creates a file just to migrate nothing


def test_datum_migrate_names_cli(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    store = datums.DatumStore.default()
    store.record_launch(datums.Datum(session_id="s1", model="sonnet"))
    store.record_launch(datums.Datum(session_id="s2", model="haiku"))

    assert main(["datum", "migrate-names"]) == 0
    out = capsys.readouterr().out
    assert "'sonnet' -> 'sonnet-5'" in out and "'haiku' -> 'haiku-4.5'" in out
    assert store.get("s1").model == "sonnet-5" and store.get("s2").model == "haiku-4.5"

    rc = main(["datum", "migrate-names"])
    assert rc == 0
    assert "No bare-alias datums to migrate" in capsys.readouterr().out


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


def test_run_captures_alias_as_canonical_via_fallback_map(tmp_path, monkeypatch):
    # No resolved model in the adapter's stream (fake's default script carries
    # none) -> falls back to the owner-maintained alias map.
    _home(tmp_path, monkeypatch)
    assert main(["run", "hello", "--agent", "fake", "--model", "sonnet", "--path", str(tmp_path)]) == 0
    d = datums.DatumStore.default().get("fake-session")
    assert d.model == "sonnet-5"


def test_run_prefers_resolved_model_from_adapter_over_alias_map(tmp_path, monkeypatch):
    from horus import adapters

    _home(tmp_path, monkeypatch)
    script = [
        {"event": "init", "session_id": "resolved-session", "model": "claude-haiku-4-5-20251001"},
        {"event": "text", "text": "hi"},
        {"event": "result", "ok": True},
    ]
    monkeypatch.setattr(adapters, "get_adapter", lambda name: adapters.FakeAdapter(script=script))
    assert main(["run", "hello", "--agent", "fake", "--model", "haiku", "--path", str(tmp_path)]) == 0
    d = datums.DatumStore.default().get("resolved-session")
    assert d is not None and d.model == "haiku-4.5"  # resolved capture, not the static map


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
    assert "sonnet-5" in out and "10/10" in out  # aligned table: 10 clean / 10 total
    assert "token-hungry" in out  # gpt-5.6 owner caution rendered (Notes section)


def test_capabilities_models_stdout_is_json(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--models", "--stdout"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "models" in data and any(m["model"] == "gpt-5.6" and m["caution"] for m in data["models"])
    assert "recommend" not in data["note"].lower()


def test_capabilities_matrix_cli_renders_ladder_and_rubric_tables(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["capabilities", "--matrix"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Delegation decision matrix" in out
    assert "DISPLAY-ONLY" in out
    assert "sonnet-5" in out and "10/10" in out  # aligned table: 10 clean / 10 total
    assert "token-hungry" in out  # gpt-5.6 owner caution still surfaces (Notes section)
    assert "scoped-impl" in out and "mechanical" in out and "novel" in out  # shape->tier table
    assert "observe-CI" in out and "CI+probe" in out and "owner-eyeball" in out  # verification dial


def test_capabilities_matrix_stdout_is_json(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--matrix", "--stdout"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert set(data.keys()) >= {"note", "tiers", "roles", "verification_dial"}
    assert any(m["model"] == "sonnet-5" and m["tier"] for m in data["tiers"])
    assert {row["shape"] for row in data["roles"]} >= {"scoped-impl", "novel", "mechanical"}
    assert {row["tier_trust"] for row in data["verification_dial"]} >= {"proven", "unproven", "runtime"}


def test_capabilities_matrix_has_no_pick_or_route_field(tmp_path, monkeypatch, capsys):
    """BOUNDARY TEST: display-only means no key in the payload ever spells out a
    pick/route decision field — the command renders the rubric, it never
    auto-selects or auto-routes a model."""
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--matrix", "--stdout"]) == 0
    data = json.loads(capsys.readouterr().out)

    def _walk_keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert "pick" not in k.lower() and "route" not in k.lower(), f"forbidden field: {k}"
                _walk_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk_keys(item)

    _walk_keys(data)


# --- price-for-capability priors (older-models-in-roster) --------------------

def test_priors_price_capability_fields_parsed(tmp_path):
    path = tmp_path / "capabilities.toml"
    path.write_text(
        '[models."old-but-cheap"]\n'
        'tier = "prior-frontier / value"\n'
        'price_in = 1.5\n'
        'price_out = 6.0\n'
        'capability_note = "still strong for scoped mechanical work"\n'
        'researched_at = "2026-07-01"\n',
        encoding="utf-8",
    )
    rollups = datums.build_model_rollup([], datums.load_priors(path))
    r = rollups[0]
    assert r.price_in == 1.5 and r.price_out == 6.0
    assert r.capability_note == "still strong for scoped mechanical work"
    assert r.researched_at == "2026-07-01"


def test_researched_at_accepts_native_toml_date(tmp_path):
    # TOML lets a hand-editor write an unquoted date; tomllib parses that as a
    # native `date`, not a string — it must still normalize to an ISO string.
    path = tmp_path / "capabilities.toml"
    path.write_text(
        '[models."old-but-cheap"]\n'
        "researched_at = 2026-07-01\n",
        encoding="utf-8",
    )
    rollups = datums.build_model_rollup([], datums.load_priors(path))
    assert rollups[0].researched_at == "2026-07-01"


def test_priors_without_new_fields_render_back_compat(tmp_path):
    # A model prior with none of the new fields must parse and render exactly
    # as before — no price/capability/researched lines, no crash.
    path = tmp_path / "capabilities.toml"
    path.write_text('[models."plain"]\ntier = "handmade"\n', encoding="utf-8")
    rollups = datums.build_model_rollup([], datums.load_priors(path))
    r = rollups[0]
    assert r.price_in is None and r.price_out is None
    assert r.capability_note is None and r.researched_at is None
    text = datums.render_model_rollup(rollups)
    assert "price:" not in text and "capability:" not in text and "researched:" not in text
    matrix = datums.render_delegation_matrix(rollups, [], [])
    assert "price:" not in matrix and "capability:" not in matrix and "researched:" not in matrix


def test_render_model_rollup_shows_price_and_capability_when_present(tmp_path):
    path = tmp_path / "capabilities.toml"
    path.write_text(
        '[models."old-but-cheap"]\n'
        'tier = "prior-frontier / value"\n'
        'price_in = 1.5\n'
        'price_out = 6.0\n'
        'capability_note = "still strong for scoped mechanical work"\n'
        'researched_at = "2026-07-01"\n',
        encoding="utf-8",
    )
    rollups = datums.build_model_rollup([], datums.load_priors(path))
    text = datums.render_model_rollup(rollups)
    assert "$1.5/$6" in text  # price column
    assert "still strong for scoped mechanical work" in text  # capability column
    assert "2026-07-01" in text  # researched column
    matrix = datums.render_delegation_matrix(rollups, [], [])
    assert "$1.5/$6" in matrix
    assert "still strong for scoped mechanical work" in matrix


# --- staleness warning (non-blocking nudge) -----------------------------------

def test_staleness_warning_none_when_fresh():
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    rollups = [datums.ModelRollup(model="m", researched_at="2026-07-05")]  # 7 days old
    assert datums.staleness_warning(rollups, now=now) is None


def test_staleness_warning_at_exact_boundary_is_not_stale():
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    rollups = [datums.ModelRollup(model="m", researched_at="2026-06-28")]  # exactly 14 days
    assert datums.staleness_warning(rollups, now=now) is None


def test_staleness_warning_when_older_than_14_days():
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    rollups = [datums.ModelRollup(model="m", researched_at="2026-06-01")]  # 41 days
    warning = datums.staleness_warning(rollups, now=now)
    assert warning is not None and "41 days old" in warning


def test_staleness_warning_uses_freshest_across_models():
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    rollups = [
        datums.ModelRollup(model="old", researched_at="2026-01-01"),
        datums.ModelRollup(model="fresh", researched_at="2026-07-10"),  # 2 days old
    ]
    assert datums.staleness_warning(rollups, now=now) is None


def test_staleness_warning_when_no_model_has_researched_at():
    rollups = [datums.ModelRollup(model="m")]
    warning = datums.staleness_warning(rollups)
    assert warning is not None and "no researched_at" in warning


def test_staleness_warning_ignores_unparseable_date():
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    rollups = [datums.ModelRollup(model="m", researched_at="not-a-date")]
    warning = datums.staleness_warning(rollups, now=now)
    assert warning is not None and "no researched_at" in warning


# --- CLI: staleness warning is a non-blocking nudge, never a gate ------------

def test_capabilities_models_cli_warns_on_stale_priors_but_exits_ok(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    priors_path = tmp_path / "home" / ".horus" / "capabilities.toml"
    priors_path.parent.mkdir(parents=True, exist_ok=True)
    priors_path.write_text(
        '[models."old-but-cheap"]\ntier = "value"\nresearched_at = "2026-01-01"\n',
        encoding="utf-8",
    )
    rc = main(["capabilities", "--models"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "WARNING:" in captured.err and "days old" in captured.err
    assert "old-but-cheap" in captured.out  # normal output still printed


def test_capabilities_models_cli_default_seed_has_no_researched_at_and_warns(tmp_path, monkeypatch, capsys):
    # The default seeded priors carry no researched_at anywhere yet — that is
    # itself a staleness signal, so the nudge fires even with no fixture.
    _home(tmp_path, monkeypatch)
    rc = main(["capabilities", "--models"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "WARNING:" in captured.err and "no researched_at" in captured.err


def test_capabilities_models_cli_fresh_priors_no_warning(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    priors_path = tmp_path / "home" / ".horus" / "capabilities.toml"
    priors_path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    priors_path.write_text(
        f'[models."old-but-cheap"]\ntier = "value"\nresearched_at = "{today}"\n',
        encoding="utf-8",
    )
    rc = main(["capabilities", "--models"])
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_capabilities_matrix_cli_also_warns_on_stale_priors(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    priors_path = tmp_path / "home" / ".horus" / "capabilities.toml"
    priors_path.parent.mkdir(parents=True, exist_ok=True)
    priors_path.write_text(
        '[models."old-but-cheap"]\ntier = "value"\nresearched_at = "2026-01-01"\n',
        encoding="utf-8",
    )
    rc = main(["capabilities", "--matrix"])
    assert rc == 0
    assert "WARNING:" in capsys.readouterr().err


def test_capabilities_models_stdout_json_unaffected_by_warning(tmp_path, monkeypatch, capsys):
    # --stdout must still emit clean, parseable JSON on stdout; the warning
    # (if any) goes only to stderr.
    _home(tmp_path, monkeypatch)
    rc = main(["capabilities", "--models", "--stdout"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)  # would raise if the warning leaked into stdout
    assert "models" in data
    assert "WARNING:" in captured.err
