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
from datetime import date, datetime, timezone

import pytest

from horus import datums
from horus.cli import main


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


def _store(tmp_path) -> datums.DatumStore:
    return datums.DatumStore(tmp_path / "datums.json")


def _run_datum() -> datums.Datum:
    rows = [datum for datum in datums.DatumStore.default().all() if datum.source == "run"]
    assert len(rows) == 1
    return rows[0]


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


def test_close_supports_void_for_aborted_untested_run(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="aborted-run", model="m"))
    closed = store.close("aborted", outcome="void", shape=None, note="operator aborted pre-test")
    assert closed.outcome == "void"
    assert store.get("aborted-run").outcome == "void"


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
    assert datums.canonical_model_name("gpt-5.6") == "gpt-5.6-sol"


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


def test_canonical_model_name_joins_full_provider_selector_launches_to_the_same_series():
    # A launch with the full provider selector (not a bare alias, so it is NOT a
    # key in ALIAS_TO_CANONICAL) still joins the one canonical calibration series
    # once Claude reports what actually ran — the provider-selector contract must
    # not fork a second series for datums launched with `claude-sonnet-5` instead
    # of the bare `sonnet` alias.
    assert datums.canonical_model_name("claude-sonnet-5", resolved="claude-sonnet-5-20260101") == "sonnet-5"
    assert datums.canonical_model_name("claude-haiku-4-5", resolved="claude-haiku-4-5-20251001") == "haiku-4.5"


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
    assert "gpt-5.6" not in priors
    assert set(priors) >= {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}
    sol = priors["gpt-5.6-sol"]
    assert "token-hungry" in sol["caution"]
    assert sol["guard"] == "do not dispatch near usage ceiling"
    assert (sol["price_in"], sol["price_out"]) == (5.0, 30.0)
    assert (priors["gpt-5.6-terra"]["price_in"], priors["gpt-5.6-terra"]["price_out"]) == (2.5, 15.0)
    assert (priors["gpt-5.6-luna"]["price_in"], priors["gpt-5.6-luna"]["price_out"]) == (1.0, 6.0)
    assert "measured datum" in priors["gpt-5.5"]["capability_note"]


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
    # The legacy generic backfill joins the canonical Sol prior.
    assert "gpt-5.6" not in by_model
    assert "token-hungry" in by_model["gpt-5.6-sol"].caution
    assert by_model["gpt-5.6-sol"].total_datums == 1


def test_rollup_canonicalizes_generic_gpt_datums_and_priors_without_duplicate():
    measured = [
        datums.Datum(session_id="generic", model="gpt-5.6", outcome="clean"),
        datums.Datum(session_id="sol", model="gpt-5.6-sol", outcome="clean"),
        datums.Datum(session_id="terra", model="gpt-5.6-terra", outcome="clean"),
    ]
    priors = {
        "gpt-5.6": {"tier": "legacy", "price_in": 99.0},
        "gpt-5.6-sol": {"tier": "canonical", "price_in": 5.0, "price_out": 30.0},
        "gpt-5.6-terra": {"price_in": 2.5, "price_out": 15.0},
        "gpt-5.6-luna": {"price_in": 1.0, "price_out": 6.0},
    }
    rollups = datums.build_model_rollup(measured, priors)
    by_model = {r.model: r for r in rollups}
    assert set(by_model) == {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}
    assert by_model["gpt-5.6-sol"].total_datums == 2
    assert by_model["gpt-5.6-sol"].tier == "canonical"
    assert (by_model["gpt-5.6-sol"].price_in, by_model["gpt-5.6-sol"].price_out) == (5.0, 30.0)
    assert by_model["gpt-5.6-terra"].total_datums == 1
    assert by_model["gpt-5.6-luna"].total_datums == 0


def test_rollup_last_outcomes_most_recent_first(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="run-a", model="m", launched_at="2026-01-01T00:00:00+00:00"))
    store.record_launch(datums.Datum(session_id="run-b", model="m", launched_at="2026-01-02T00:00:00+00:00"))
    store.close("run-a", outcome="clean", shape=None, note=None)
    store.close("run-b", outcome="bounced", shape=None, note=None)
    r = next(x for x in datums.build_model_rollup(store.all(), {}) if x.model == "m")
    assert r.last_outcomes == ["bounced", "clean"]  # newest first


def test_rollup_excludes_death_and_void_from_quality_rate_but_keeps_them_visible():
    measured = [
        datums.Datum(session_id="clean-1", model="m", outcome="clean", launched_at="1"),
        datums.Datum(session_id="clean-2", model="m", outcome="clean", launched_at="2"),
        datums.Datum(session_id="nudged", model="m", outcome="nudged", launched_at="3"),
        datums.Datum(session_id="died", model="m", outcome="died", launched_at="4"),
        datums.Datum(session_id="void", model="m", outcome="void", launched_at="5"),
        datums.Datum(session_id="open", model="m", launched_at="6"),
    ]
    rollup = datums.build_model_rollup(measured, {})[0]
    assert rollup.total_datums == 6 and rollup.closed_datums == 5
    assert rollup.quality_datums == 3 and rollup.clean_count == 2
    assert rollup.died_count == 1 and rollup.void_count == 1
    assert rollup.last_outcomes == ["nudged", "clean", "clean"]
    rendered = datums.render_model_rollup([rollup])
    assert "2/3 clean · 1 died · 1 void" in rendered


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
    d = _run_datum()
    assert d is not None
    assert d.model == "sonnet-5" and d.agent == "fake" and d.posture == "default"
    assert d.exit == "completed" and d.runtime_seconds is not None and d.outcome is None


def test_run_captures_alias_as_canonical_via_fallback_map(tmp_path, monkeypatch):
    # No resolved model in the adapter's stream (fake's default script carries
    # none) -> falls back to the owner-maintained alias map.
    _home(tmp_path, monkeypatch)
    assert main(["run", "hello", "--agent", "fake", "--model", "sonnet", "--path", str(tmp_path)]) == 0
    d = _run_datum()
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
    d = _run_datum()
    assert d is not None and d.model == "haiku-4.5"  # resolved capture, not the static map


def test_datum_close_cli_attaches_outcome(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["run", "hi", "--agent", "fake", "--model", "opus-4.8", "--path", str(tmp_path)])
    rc = main(["datum", "close", _run_datum().session_id, "--outcome", "clean", "--shape", "clear/small/short", "--note", "ok"])
    assert rc == 0
    assert "outcome=clean" in capsys.readouterr().out
    d = _run_datum()
    assert d.outcome == "clean" and d.shape == "clear/small/short" and d.note == "ok"


def test_datum_close_cli_accepts_void(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["run", "hi", "--agent", "fake", "--model", "opus-4.8", "--path", str(tmp_path)])
    assert main(["datum", "close", _run_datum().session_id, "--outcome", "void", "--note", "aborted"]) == 0
    assert "outcome=void" in capsys.readouterr().out
    assert _run_datum().outcome == "void"


def test_datum_close_cli_bad_id_returns_2(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert main(["datum", "close", "missing", "--outcome", "clean"]) == 2


def test_capabilities_models_rollup_cli(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    rc = main(["capabilities", "--models"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Model calibration roll-up" in out
    assert "sonnet-5" in out and "10/10 clean" in out
    assert "token-hungry" in out  # gpt-5.6 owner caution rendered (Notes section)


def test_capabilities_models_stdout_is_json(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--models", "--stdout"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "models" in data and any(m["model"] == "gpt-5.6-sol" and m["caution"] for m in data["models"])
    assert not any(m["model"] == "gpt-5.6" for m in data["models"])
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


def test_capabilities_models_concise_default_omits_last_column(tmp_path, monkeypatch, capsys):
    # sonnet-5 is backfilled with 10 clean datums (see DatumStore.default()'s
    # seed) — its LAST column would read "clean clean clean clean clean" if
    # rendered. The concise default must drop that per-run judgment entirely.
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--models"]) == 0
    out = capsys.readouterr().out
    assert "LAST" not in out
    assert "clean clean" not in out


def test_capabilities_models_verbose_restores_last_column(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--models", "--verbose"]) == 0
    out = capsys.readouterr().out
    assert "LAST" in out
    assert "clean clean clean clean clean" in out  # sonnet-5's backfilled outcomes


def test_capabilities_models_full_is_an_alias_for_verbose(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--models", "--full"]) == 0
    out = capsys.readouterr().out
    assert "LAST" in out


def test_capabilities_matrix_concise_default_omits_last_column(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--matrix"]) == 0
    out = capsys.readouterr().out
    assert "LAST" not in out
    assert "clean clean" not in out


def test_capabilities_matrix_verbose_restores_last_column(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--matrix", "--verbose"]) == 0
    out = capsys.readouterr().out
    assert "LAST" in out
    assert "clean clean clean clean clean" in out


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
    assert r.available is None and r.retires_at is None and r.lifecycle is None
    text = datums.render_model_rollup(rollups)
    assert "price:" not in text and "capability:" not in text and "researched:" not in text
    matrix = datums.render_delegation_matrix(rollups, [], [])
    assert "price:" not in matrix and "capability:" not in matrix and "researched:" not in matrix


def test_lifecycle_priors_render_retired_retiring_soon_and_available(tmp_path):
    path = tmp_path / "capabilities.toml"
    path.write_text(
        '[models."retired"]\navailable = false\n'
        '[models."soon"]\nretires_at = 2026-08-01\n'
        '[models."current"]\navailable = true\n',
        encoding="utf-8",
    )
    rollups = datums.build_model_rollup(
        [], datums.load_priors(path), today=datetime(2026, 7, 14).date()
    )
    by_model = {r.model: r for r in rollups}
    assert by_model["retired"].lifecycle == "retired"
    assert by_model["soon"].retires_at == "2026-08-01"
    assert by_model["soon"].lifecycle == "retires soon 2026-08-01"
    assert by_model["current"].lifecycle == "available"
    text = datums.render_model_rollup(rollups)
    matrix = datums.render_delegation_matrix(rollups, [], [])
    assert "Lifecycle:" in text and "soon: retires soon 2026-08-01" in text
    assert "Lifecycle:" in matrix and "retired: retired" in matrix


def test_lifecycle_absent_keeps_rendering_unchanged():
    rollups = datums.build_model_rollup([], {"plain": {"tier": "manual"}})
    assert "Lifecycle:" not in datums.render_model_rollup(rollups)
    assert "Lifecycle:" not in datums.render_delegation_matrix(rollups, [], [])
    payload = datums.rollup_to_dict(rollups)["models"][0]
    assert payload["available"] is None
    assert payload["retires_at"] is None
    assert payload["lifecycle"] is None


def test_lifecycle_cli_is_non_blocking_and_adds_no_routing_field(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    prior_path = tmp_path / "home" / ".horus" / "capabilities.toml"
    prior_path.parent.mkdir(parents=True, exist_ok=True)
    prior_path.write_text('[models."retired"]\navailable = false\n', encoding="utf-8")
    assert main(["capabilities", "--models", "--stdout"]) == 0
    payload = json.loads(capsys.readouterr().out)
    retired = next(model for model in payload["models"] if model["model"] == "retired")
    assert retired["lifecycle"] == "retired"
    assert not any("pick" in key.lower() or "route" in key.lower() for key in retired)


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
    assert "still strong for scoped mechanical work" in text  # short enough not to truncate
    assert "2026-07-01" not in text  # RESEARCHED column omitted from the concise default
    matrix = datums.render_delegation_matrix(rollups, [], [])
    assert "$1.5/$6" in matrix
    assert "still strong for scoped mechanical work" in matrix
    assert "2026-07-01" not in matrix

    verbose_text = datums.render_model_rollup(rollups, verbose=True)
    assert "2026-07-01" in verbose_text  # --verbose/--full restores RESEARCHED
    verbose_matrix = datums.render_delegation_matrix(rollups, [], [], verbose=True)
    assert "2026-07-01" in verbose_matrix


def test_concise_capability_column_is_word_safe_truncated_when_note_is_long(tmp_path):
    # Mirrors a real ~/.horus/capabilities.toml capability_note (paragraph-length
    # price-for-capability prose) with no dedicated capability_summary set.
    long_note = (
        "PRICE-DOMINATED by gpt-5.6-Terra, newer AND cheaper at comparable "
        "capability; no value case, candidate to drop from roster entirely"
    )
    path = tmp_path / "capabilities.toml"
    path.write_text(
        f'[models."gpt-5.5"]\ntier = "codex (early)"\ncapability_note = "{long_note}"\n',
        encoding="utf-8",
    )
    rollups = datums.build_model_rollup([], datums.load_priors(path))
    cell = datums._capability_cell(rollups[0], verbose=False)
    assert cell != long_note  # concise: not the full paragraph
    assert cell.endswith("…")
    stem_words = cell[:-1].split()  # strip the ellipsis, split the truncated stem
    assert long_note.split()[: len(stem_words)] == stem_words  # a clean word-boundary prefix

    text = datums.render_model_rollup(rollups)
    assert long_note not in text
    # Full text is always in --stdout JSON regardless of table truncation.
    data = datums.rollup_to_dict(rollups)
    assert data["models"][0]["capability_note"] == long_note


def test_capability_summary_field_preferred_over_derived_truncation(tmp_path):
    path = tmp_path / "capabilities.toml"
    path.write_text(
        '[models."old-but-cheap"]\n'
        'tier = "prior-frontier / value"\n'
        'capability_note = "a much longer paragraph of researched price-for-capability prose"\n'
        'capability_summary = "cheap scoped work"\n',
        encoding="utf-8",
    )
    rollups = datums.build_model_rollup([], datums.load_priors(path))
    assert rollups[0].capability_summary == "cheap scoped work"
    text = datums.render_model_rollup(rollups)
    assert "cheap scoped work" in text
    assert "a much longer paragraph" not in text  # concise: summary wins, not the note
    # Full note is still complete in --stdout JSON.
    data = datums.rollup_to_dict(rollups)
    assert data["models"][0]["capability_note"] == (
        "a much longer paragraph of researched price-for-capability prose"
    )
    assert data["models"][0]["capability_summary"] == "cheap scoped work"


def test_capabilities_models_stdout_json_keeps_last_and_capability_note_complete(tmp_path, monkeypatch, capsys):
    # --stdout JSON must stay COMPLETE regardless of the concise default —
    # nothing removed, including per-run LAST outcomes and the full note.
    _home(tmp_path, monkeypatch)
    assert main(["capabilities", "--models", "--stdout"]) == 0
    data = json.loads(capsys.readouterr().out)
    sonnet = next(m for m in data["models"] if m["model"] == "sonnet-5")
    assert sonnet["last_outcomes"] == ["clean"] * 5
    assert "capability_note" in sonnet and "capability_summary" in sonnet


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


def test_capabilities_models_cli_default_seed_is_fresh(tmp_path, monkeypatch, capsys):
    # The canonical GPT-5.6 seed rows carry their source-check date.
    _home(tmp_path, monkeypatch)
    rc = main(["capabilities", "--models"])
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.err == ""


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


# --- supervisor-cost envelope: usage snapshots (2026-07-14 frozen schema) ----

def test_capture_usage_snapshot_unavailable_on_failed_read(tmp_path, monkeypatch):
    # No credentials/rollouts anywhere reachable (isolated fake HOME) -> both
    # targets read as unavailable, never block, never fabricate a percent.
    _home(tmp_path, monkeypatch)
    snap = datums.capture_usage_snapshot("claude", None)
    assert snap["claude"]["freshness"] == "unavailable"
    assert "pct_5h" not in snap["claude"]
    assert snap["codex"]["freshness"] == "unavailable"
    assert "read_at" in snap["claude"] and "read_at" in snap["codex"]


def test_capture_usage_snapshot_claude_fresh_at_read_time(monkeypatch):
    from horus import usage_snapshot

    monkeypatch.setattr(
        usage_snapshot, "cached_usage",
        lambda agent, account, **kw: usage_snapshot.UsageSnapshot(42.0, "1h", 37.0, "3d") if agent == "claude" else None,
    )
    snap = datums.capture_usage_snapshot("claude", "acct-a")
    assert snap["claude"] == {
        "read_at": snap["claude"]["read_at"], "freshness": "fresh",
        "pct_5h": 42.0, "resets_5h": "1h",
        "pct_weekly": 37.0, "resets_weekly": "3d",
    }


def test_capture_usage_snapshot_codex_stale_when_reset_past(monkeypatch):
    from horus import codex_usage

    class _Report:
        primary_percent = 90.0
        primary_resets_at = 1  # epoch second 1 -- always in the past
        context_percent = 47.0
        timestamp = "2026-07-13T00:00:00Z"

    monkeypatch.setattr(codex_usage, "latest_account_usage", lambda home=None: _Report())
    snap = datums.capture_usage_snapshot("claude", None)  # codex read under default account
    assert snap["codex"]["freshness"] == "stale"
    assert snap["codex"]["pct_5h"] == 90.0
    assert snap["codex"]["pct_context"] == 47.0


def test_capture_usage_snapshot_codex_stale_when_cache_predates_run(monkeypatch):
    from horus import codex_usage

    class _Report:
        primary_percent = 10.0
        primary_resets_at = 4102444800  # far future -- reset not expired
        context_percent = 5.0
        timestamp = "2026-07-13T00:00:00+00:00"  # before the run's own launch

    monkeypatch.setattr(codex_usage, "latest_account_usage", lambda home=None: _Report())
    snap = datums.capture_usage_snapshot(None, None, since="2026-07-14T00:00:00+00:00")
    assert snap["codex"]["freshness"] == "stale"  # cached codex read predates this run's launch


def test_capture_usage_snapshot_codex_fresh_when_recent_and_unexpired(monkeypatch):
    from horus import codex_usage

    class _Report:
        primary_percent = 10.0
        primary_resets_at = 4102444800
        context_percent = 5.0
        timestamp = "2026-07-14T01:00:00+00:00"  # after the run's own launch

    monkeypatch.setattr(codex_usage, "latest_account_usage", lambda home=None: _Report())
    snap = datums.capture_usage_snapshot(None, None, since="2026-07-14T00:00:00+00:00")
    assert snap["codex"]["freshness"] == "fresh"


def test_capture_usage_snapshot_never_raises_on_unexpected_failure(monkeypatch):
    from horus import usage_snapshot

    def _boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(usage_snapshot, "cached_usage", _boom)
    snap = datums.capture_usage_snapshot("claude", None)  # must not raise
    assert snap["claude"]["freshness"] == "unavailable"


def test_run_fake_captures_usage_launch_snapshot(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    assert main(["run", "hello", "--agent", "fake", "--model", "sonnet-5", "--path", str(tmp_path)]) == 0
    d = _run_datum()
    assert d.usage_launch is not None
    assert d.usage_close is not None  # second reading lands at process completion
    assert set(d.usage_launch) == {"claude", "codex"}
    assert d.usage_launch["claude"]["freshness"] == "unavailable"  # no real creds in the fake HOME


def _usage_pair(agent="claude", *, start=10.0, end=16.0, reset="window-a"):
    return (
        {agent: {"freshness": "fresh", "pct_5h": start, "resets_5h": reset}},
        {agent: {"freshness": "fresh", "pct_5h": end, "resets_5h": reset}},
    )


def test_usage_accounting_observes_only_isolated_same_window_actuals():
    launch, close = _usage_pair()
    row = datums.Datum(
        session_id="isolated", agent_session_id="native", agent="claude", account="work",
        worker=True, launched_at="2026-07-16T10:00:00+00:00",
        completed_at="2026-07-16T10:10:00+00:00", usage_launch=launch, usage_close=close,
    )
    actual = datums.usage_accounting(row, [row])
    assert actual["status"] == "observed"
    assert actual["deltas"] == {"5h": 6.0}
    assert actual["start"]["pct_5h"] == 10.0 and actual["end"]["pct_5h"] == 16.0


def test_usage_accounting_marks_ambient_worker_shared_and_confounded():
    launch, close = _usage_pair(start=5, end=35)
    row = datums.Datum(
        session_id="ambient", agent="claude", account=None, worker=True,
        launched_at="2026-07-16T10:00:00+00:00",
        completed_at="2026-07-16T10:10:00+00:00", usage_launch=launch, usage_close=close,
    )
    actual = datums.usage_accounting(row, [row])
    assert actual["status"] == "shared-account/confounded"
    assert actual["deltas"] == {}


def test_usage_accounting_marks_tracked_overlap_confounded():
    launch, close = _usage_pair()
    first = datums.Datum(
        session_id="first", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:20:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    second = datums.Datum(
        session_id="second", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:05:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    assert datums.usage_accounting(first, [first, second])["status"] == "concurrent/confounded"


def test_usage_accounting_does_not_cross_reset_windows():
    launch, _ = _usage_pair(reset="window-a")
    _, close = _usage_pair(reset="window-b")
    row = datums.Datum(
        session_id="reset", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    actual = datums.usage_accounting(row, [row])
    assert actual["status"] == "unknown" and actual["deltas"] == {}


# --- stale-datum usage-overlap reconciliation --------------------------------
# The bug: a tracked run whose datum never got `completed_at` used to be treated
# as running "until now" forever, so every later sequential worker looked like it
# overlapped it. These tests cover: naming the exact overlapping peers, bounding
# a missing completion from positive terminal registry/run-event evidence, a
# genuinely running peer still confounding, missing/ambiguous evidence never
# being treated as proof (and surfacing for remediation), and sequential retry
# attempts whose intervals do and do not overlap.

from horus.registry import Registry, SessionRecord  # noqa: E402


def test_usage_accounting_names_overlapping_peer_ids_and_intervals():
    launch, close = _usage_pair()
    first = datums.Datum(
        session_id="first", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:20:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    second = datums.Datum(
        session_id="second", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:05:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    result = datums.usage_accounting(first, [first, second])
    assert result["status"] == "concurrent/confounded"
    assert result["overlap_peers"] == [
        {"session_id": "second", "start": "2026-07-16T10:05:00+00:00", "end": "2026-07-16T10:10:00+00:00", "bounded": True}
    ]
    assert "second" in result["detail"] and "another tracked worker" not in result["detail"]


def test_terminal_registry_evidence_bounds_missing_datum_completion(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    reg = Registry.default()
    # The legacy peer never got a mechanical `completed_at`, but the registry
    # positively reconciled it as `exited` well before the later run launched.
    reg.upsert(SessionRecord(session_id="legacy", agent="claude", project="/proj", account="work", status="exited"),
               now="2026-07-15T09:00:00+00:00")

    legacy = datums.Datum(
        session_id="legacy", agent="claude", account="work", worker=True,
        launched_at="2026-07-15T08:00:00+00:00", completed_at=None,
    )
    launch, close = _usage_pair()
    later = datums.Datum(
        session_id="later", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    result = datums.usage_accounting(later, [legacy, later])
    assert result["status"] != "concurrent/confounded"  # bounded end predates `later`'s launch


def test_genuinely_running_peer_still_confounds_attribution(tmp_path, monkeypatch):
    import os

    _home(tmp_path, monkeypatch)
    reg = Registry.default()
    reg.upsert(SessionRecord(
        session_id="live", agent="claude", project="/proj", account="work", pid=os.getpid(), status="running",
    ))

    live = datums.Datum(
        session_id="live", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at=None,
    )
    launch, close = _usage_pair()
    later = datums.Datum(
        session_id="later", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:05:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    result = datums.usage_accounting(later, [live, later])
    assert result["status"] == "concurrent/confounded"
    assert result["overlap_peers"][0]["session_id"] == "live"
    assert result["overlap_peers"][0]["bounded"] is False


def test_missing_ambiguous_evidence_confounds_and_is_flagged_unresolved(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    # No registry row at all for "ghost" — absence alone is never proof either way.
    ghost = datums.Datum(
        session_id="ghost", agent="claude", account="work", worker=True,
        launched_at="2026-07-01T08:00:00+00:00", completed_at=None,
    )
    launch, close = _usage_pair()
    later = datums.Datum(
        session_id="later", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    result = datums.usage_accounting(later, [ghost, later])
    assert result["status"] == "concurrent/confounded"
    assert result["overlap_peers"][0]["bounded"] is False

    store = datums.DatumStore.default()
    store.record_launch(ghost)
    unresolved = store.unresolved_legacy_runs(now=datetime(2026, 7, 17, tzinfo=timezone.utc))
    assert [d.session_id for d in unresolved] == ["ghost"]


def test_dead_pid_alone_never_confirms_a_datum_completion(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    reg = Registry.default()
    # A PID that is dead (never reused) with no RESULT log/event at all.
    reg.upsert(SessionRecord(session_id="deadpid", agent="claude", project="/proj", account="work",
                              pid=999999999, status="running"))
    store = datums.DatumStore.default()
    store.record_launch(datums.Datum(session_id="deadpid", agent="claude", account="work", worker=True,
                                      launched_at="2026-07-15T08:00:00+00:00"))

    reg.reconcile()  # dead PID -> registry status "stale", but no positive RESULT evidence

    assert reg.get("deadpid").status == "stale"
    assert store.get("deadpid").completed_at is None  # never silently backfilled off a dead PID alone
    backfilled = store.reconcile_missing_completions()
    assert backfilled == []  # "stale" is not positive evidence either


def test_reconcile_missing_completions_backfills_only_from_positive_evidence(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    reg = Registry.default()
    reg.upsert(SessionRecord(session_id="legacy", agent="claude", project="/proj", account="work", status="exited"),
               now="2026-07-15T09:00:00+00:00")

    store = datums.DatumStore.default()
    store.record_launch(datums.Datum(session_id="legacy", agent="claude", account="work", worker=True,
                                      launched_at="2026-07-15T08:00:00+00:00"))

    changed = store.reconcile_missing_completions()
    assert [d.session_id for d in changed] == ["legacy"]
    backfilled = store.get("legacy")
    assert backfilled.completed_at == "2026-07-15T09:00:00+00:00"
    assert backfilled.exit == "completed"

    # A positively reconciled legacy run no longer poisons a later isolated reading.
    later = datums.Datum(
        session_id="later", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
    )
    result = datums.usage_accounting(later, [backfilled, later])
    assert result["status"] != "concurrent/confounded"


def test_sequential_retry_attempts_overlap_only_when_intervals_actually_overlap():
    launch, close = _usage_pair()
    attempt1 = datums.Datum(
        session_id="attempt-1", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:05:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    attempt2 = datums.Datum(
        session_id="attempt-2", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:06:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    attempt3 = datums.Datum(
        session_id="attempt-3", agent="claude", account="work", worker=True,
        launched_at="2026-07-16T10:08:00+00:00", completed_at="2026-07-16T10:15:00+00:00",
        usage_launch=launch, usage_close=close,
    )
    # attempt1/attempt2 are back-to-back and never overlap one another.
    assert datums.usage_accounting(attempt1, [attempt1, attempt2])["status"] != "concurrent/confounded"
    assert datums.usage_accounting(attempt2, [attempt1, attempt2])["status"] != "concurrent/confounded"
    # attempt3 launched (10:08) before attempt2 finished (10:10) -> real overlap.
    assert datums.usage_accounting(attempt3, [attempt2, attempt3])["status"] == "concurrent/confounded"


def test_worker_breakdown_groups_resumed_native_session_as_attempts():
    launch, close = _usage_pair()
    rows = [
        datums.Datum(
            session_id=f"run-{n}", agent_session_id="native-thread", agent="claude",
            model="sonnet-5", account="work", effort="high", worker=True,
            launched_at=f"2026-07-16T10:0{n}:00+00:00",
            completed_at=f"2026-07-16T10:0{n}:30+00:00", runtime_seconds=30,
            usage_launch=launch, usage_close=close,
        )
        for n in (1, 2)
    ]
    report = datums.worker_breakdown(rows)
    assert [(row["attempt"], row["attempts"]) for row in report] == [(1, 2), (2, 2)]
    assert all(row["model"] == "sonnet-5" and row["account"] == "work" for row in report)
    rendered = datums.render_worker_breakdown(report)
    assert "start=5h=10%[fresh]" in rendered and "end=5h=16%[fresh]" in rendered


def test_datum_report_cli_renders_worker_actuals_without_run_id_lookup(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    launch, close = _usage_pair()
    datums.DatumStore.default().record_launch(datums.Datum(
        session_id="report-worker", agent_session_id="native-report", agent="claude",
        model="sonnet-5", account="work", effort="high", worker=True,
        launched_at="2026-07-16T10:00:00+00:00", completed_at="2026-07-16T10:10:00+00:00",
        runtime_seconds=600, exit="completed", outcome="clean",
        usage_launch=launch, usage_close=close,
    ))
    assert main(["datum", "report", "--all", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report[0]["run_id"] == "report-worker"
    assert report[0]["usage"]["status"] == "observed"
    assert report[0]["runtime_seconds"] == 600


# --- supervisor-cost envelope: agent-supplied close flags --------------------

def test_close_persists_new_cost_flags(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="cost-1", model="sonnet-5", agent="claude"))
    d = store.close(
        "cost-1", outcome="clean", shape=None, note=None,
        oversight="moderate", follow_on=1, counterfactual="direct-session", dividend="negative",
    )
    assert d.oversight == "moderate"
    assert d.follow_on == 1
    assert d.counterfactual == "direct-session"
    assert d.dividend == "negative"
    assert store.get("cost-1").dividend == "negative"  # persisted


def test_close_cost_flags_all_optional_existing_datums_stay_valid(tmp_path):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="cost-2"))
    d = store.close("cost-2", outcome="clean", shape=None, note=None)
    assert d.oversight is None and d.follow_on is None
    assert d.counterfactual is None and d.dividend is None


def test_completion_captures_usage_close_snapshot(tmp_path, monkeypatch):
    store = _store(tmp_path)
    calls = []
    monkeypatch.setattr(
        datums, "capture_usage_snapshot",
        lambda *args, **kwargs: calls.append(kwargs) or {
            "claude": {"freshness": "fresh"}, "codex": {"freshness": "unavailable"},
        },
    )
    store.record_launch(datums.Datum(session_id="cost-3", agent="claude", launched_at="2026-07-14T00:00:00+00:00"))
    store.record_completion("cost-3", exit="completed", runtime_seconds=1, returncode=0)
    before_review = store.get("cost-3").usage_close
    d = store.close("cost-3", outcome="clean", shape=None, note=None)
    assert d.usage_close is not None and set(d.usage_close) == {"claude", "codex"}
    assert d.usage_close == before_review
    assert len(calls) == 1 and calls[0]["persist_cache"] is False


@pytest.mark.parametrize(
    "kwargs,bad_kw",
    [
        ({"oversight": "extreme"}, "oversight"),
        ({"counterfactual": "telepathy"}, "counterfactual"),
        ({"dividend": "amazing"}, "dividend"),
        ({"follow_on": -1}, "follow-on"),
    ],
)
def test_close_rejects_out_of_vocabulary_cost_flags(tmp_path, kwargs, bad_kw):
    store = _store(tmp_path)
    store.record_launch(datums.Datum(session_id="bad-cost"))
    with pytest.raises(ValueError, match=bad_kw):
        store.close("bad-cost", outcome="clean", shape=None, note=None, **kwargs)


def test_datum_close_cli_new_flags(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["run", "hi", "--agent", "fake", "--model", "opus-4.8", "--path", str(tmp_path)])
    rc = main([
        "datum", "close", _run_datum().session_id, "--outcome", "clean",
        "--oversight", "heavy", "--follow-on", "2",
        "--counterfactual", "one-worker", "--dividend", "positive",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "oversight=heavy" in out and "follow-on=2" in out
    assert "counterfactual=one-worker" in out and "dividend=positive" in out
    d = _run_datum()
    assert d.oversight == "heavy" and d.follow_on == 2
    assert d.counterfactual == "one-worker" and d.dividend == "positive"


def test_datum_close_cli_rejects_bad_oversight_choice(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["run", "hi", "--agent", "fake", "--path", str(tmp_path)])
    with pytest.raises(SystemExit):
        main(["datum", "close", _run_datum().session_id, "--outcome", "clean", "--oversight", "extreme"])


# --- one-act acceptance: `horus datum close --card` (2026-07-14 frozen schema) --

def _mk_target_card(project_root, slug):
    hdir = project_root / ".horus" / "backlog"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / f"{slug}.md").write_text(
        "---\nstatus: open\npriority: now\ntier: sonnet\ncreated: 2026-07-14\n---\n\n# Card\n",
        encoding="utf-8",
    )


def _write_target_prd(project_root, *, last_updated):
    hdir = project_root / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    (hdir / "PRD.md").write_text(f"---\nlast_updated: {last_updated}\n---\n\n# PRD\n", encoding="utf-8")


def test_datum_close_cli_card_stamps_card_and_stays_quiet_when_fresh(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _mk_target_card(tmp_path, "deliver-me")
    # Card delivery stamps intentionally use the operator's local calendar day.
    # Keep this assertion stable around local-midnight/UTC-date boundaries.
    today = date.today().isoformat()
    _write_target_prd(tmp_path, last_updated=today)  # fresh: matches this run's completion

    main(["run", "hi", "--agent", "fake", "--path", str(tmp_path)])
    rc = main(["datum", "close", _run_datum().session_id, "--outcome", "clean", "--card", "deliver-me"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Stamped" in out and "status: done" in out
    assert "WARNING" not in out

    from horus import backlog
    card = backlog.find_card(tmp_path, "deliver-me")
    assert card.status == "done" and card.shipped == today


def test_datum_close_cli_card_warns_when_target_continuity_stale(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    _mk_target_card(tmp_path, "deliver-me")
    _write_target_prd(tmp_path, last_updated="2020-01-01")  # deliberately ancient

    main(["run", "hi", "--agent", "fake", "--path", str(tmp_path)])
    rc = main(["datum", "close", _run_datum().session_id, "--outcome", "clean", "--card", "deliver-me"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Stamped" in out
    assert "WARNING" in out and "stale" in out

    from horus import backlog
    assert backlog.find_card(tmp_path, "deliver-me").status == "done"  # stamp still lands; probe only warns


def test_datum_close_cli_card_missing_card_returns_2(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    main(["run", "hi", "--agent", "fake", "--path", str(tmp_path)])
    rc = main(["datum", "close", _run_datum().session_id, "--outcome", "clean", "--card", "no-such-card"])
    assert rc == 2
    assert "Could not stamp" in capsys.readouterr().out
    # The datum close itself still went through before the card resolution failed.
    d = _run_datum()
    assert d.outcome == "clean"


# --- supervisor-cost envelope: capabilities --models cost glance -------------

def test_render_cost_notes_absent_when_no_model_has_cost_data(tmp_path):
    rollups = datums.build_model_rollup(_store(tmp_path).all(), {})
    assert datums.render_cost_notes(rollups) == []


def test_render_cost_notes_shows_dividend_and_oversight_median(tmp_path):
    store = _store(tmp_path)
    for i, (oversight, dividend) in enumerate(
        [("light", "positive"), ("light", "positive"), ("heavy", "positive"),
         ("moderate", "neutral"), ("heavy", "negative")]
    ):
        sid = f"m-{i}"
        store.record_launch(datums.Datum(session_id=sid, model="sonnet-5"))
        store.close(sid, outcome="clean", shape=None, note=None, oversight=oversight, dividend=dividend)

    rollups = datums.build_model_rollup(store.all(), {})
    lines = datums.render_cost_notes(rollups)
    assert lines[0] == "Cost:"
    sonnet_line = next(line for line in lines if "sonnet-5" in line)
    assert "dividend +3/~1/-1" in sonnet_line
    assert "oversight median:" in sonnet_line


def test_capabilities_models_cli_renders_cost_glance(tmp_path, monkeypatch, capsys):
    _home(tmp_path, monkeypatch)
    store = datums.DatumStore.default()
    store.record_launch(datums.Datum(session_id="glance-1", model="sonnet-5"))
    store.close("glance-1", outcome="clean", shape=None, note=None, oversight="light", dividend="positive")

    rc = main(["capabilities", "--models"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Cost:" in out and "dividend +1/~0/-0" in out
