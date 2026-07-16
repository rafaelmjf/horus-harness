"""Bulk-migration inventory reconciliation: manifest diffing + the empty-walk guard."""

from __future__ import annotations

import json

import pytest

from horus import verify_inventory
from horus.cli import main


def _make_tree(root, files: dict[str, bytes]):
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


# --- walk_manifest ---

def test_walk_manifest_reports_relative_posix_keys_and_sizes(tmp_path):
    _make_tree(tmp_path, {"a.txt": b"hello", "sub/b.txt": b"hi"})

    manifest = verify_inventory.walk_manifest(tmp_path)

    assert manifest == {"a.txt": 5, "sub/b.txt": 2}


def test_walk_manifest_raises_on_empty_expected_nonempty(tmp_path):
    with pytest.raises(verify_inventory.EmptyWalkError):
        verify_inventory.walk_manifest(tmp_path)


def test_walk_manifest_allows_empty_when_opted_in(tmp_path):
    assert verify_inventory.walk_manifest(tmp_path, expect_nonempty=False) == {}


def test_walk_manifest_rejects_non_directory(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        verify_inventory.walk_manifest(f)


# --- load_manifest_file / load_manifest ---

def test_load_manifest_file_accepts_object_shape(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"a.txt": 5, "sub/b.txt": 2}), encoding="utf-8")

    assert verify_inventory.load_manifest_file(manifest_path) == {"a.txt": 5, "sub/b.txt": 2}


def test_load_manifest_file_accepts_pair_list_shape(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps([["a.txt", 5], ["sub/b.txt", 2]]), encoding="utf-8")

    assert verify_inventory.load_manifest_file(manifest_path) == {"a.txt": 5, "sub/b.txt": 2}


def test_load_manifest_dispatches_on_directory_vs_file(tmp_path):
    src_dir = tmp_path / "src"
    _make_tree(src_dir, {"a.txt": b"hello"})
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"a.txt": 5}), encoding="utf-8")

    assert verify_inventory.load_manifest(src_dir) == {"a.txt": 5}
    assert verify_inventory.load_manifest(manifest_path) == {"a.txt": 5}


# --- reconcile ---

def test_reconcile_clean_1to1():
    source = {"a.txt": 5, "sub/b.txt": 2}
    produced = {"a.txt": 5, "sub/b.txt": 2}

    result = verify_inventory.reconcile(source, produced)

    assert result.clean
    assert result.source_not_produced == ()
    assert result.produced_not_source == ()
    assert result.size_mismatches == ()


def test_reconcile_flags_dropped_file():
    source = {"a.txt": 5, "b.txt": 2}
    produced = {"a.txt": 5}

    result = verify_inventory.reconcile(source, produced)

    assert not result.clean
    assert result.source_not_produced == ("b.txt",)
    assert result.produced_not_source == ()
    assert result.size_mismatches == ()


def test_reconcile_flags_extra_file():
    source = {"a.txt": 5}
    produced = {"a.txt": 5, "extra.txt": 9}

    result = verify_inventory.reconcile(source, produced)

    assert not result.clean
    assert result.produced_not_source == ("extra.txt",)
    assert result.source_not_produced == ()


def test_reconcile_flags_size_mismatch():
    source = {"a.txt": 5}
    produced = {"a.txt": 6}

    result = verify_inventory.reconcile(source, produced)

    assert not result.clean
    assert result.size_mismatches == (("a.txt", 5, 6),)


def test_reconcile_handles_non_ascii_filenames_by_stable_key(tmp_path):
    names = {"§ notes.txt": b"one", "café/résumé.txt": b"two", "日本語.txt": b"three"}
    src_dir = tmp_path / "src"
    produced_dir = tmp_path / "produced"
    _make_tree(src_dir, names)
    _make_tree(produced_dir, names)

    source = verify_inventory.walk_manifest(src_dir)
    produced = verify_inventory.walk_manifest(produced_dir)
    result = verify_inventory.reconcile(source, produced)

    assert result.clean
    assert set(source) == {"§ notes.txt", "café/résumé.txt", "日本語.txt"}


# --- format_report ---

def test_format_report_clean():
    result = verify_inventory.reconcile({"a.txt": 1}, {"a.txt": 1})
    assert verify_inventory.format_report(result) == [
        "reconcile: clean — source and produced agree on count and size"
    ]


def test_format_report_lists_each_discrepancy_kind():
    result = verify_inventory.ReconcileResult(
        source_not_produced=("dropped.txt",),
        produced_not_source=("extra.txt",),
        size_mismatches=(("mismatch.txt", 5, 6),),
    )
    lines = verify_inventory.format_report(result)
    assert "source-not-produced: dropped.txt" in lines
    assert "produced-not-source: extra.txt" in lines
    assert "size-mismatch: mismatch.txt (source=5, produced=6)" in lines


# --- CLI wiring ---

def test_cli_verify_inventory_clean_exits_zero(tmp_path, capsys):
    src_dir, produced_dir = tmp_path / "src", tmp_path / "produced"
    _make_tree(src_dir, {"a.txt": b"hello"})
    _make_tree(produced_dir, {"a.txt": b"hello"})

    rc = main(["verify-inventory", str(src_dir), str(produced_dir)])

    assert rc == 0
    assert "clean" in capsys.readouterr().out


def test_cli_verify_inventory_discrepancy_exits_nonzero(tmp_path, capsys):
    src_dir, produced_dir = tmp_path / "src", tmp_path / "produced"
    _make_tree(src_dir, {"a.txt": b"hello", "dropped.txt": b"x"})
    _make_tree(produced_dir, {"a.txt": b"hello"})

    rc = main(["verify-inventory", str(src_dir), str(produced_dir)])

    assert rc == 1
    assert "source-not-produced: dropped.txt" in capsys.readouterr().out


def test_cli_verify_inventory_empty_walk_is_an_error_not_a_pass(tmp_path, capsys):
    src_dir, produced_dir = tmp_path / "src", tmp_path / "produced"
    src_dir.mkdir()
    produced_dir.mkdir()

    rc = main(["verify-inventory", str(src_dir), str(produced_dir)])

    out = capsys.readouterr().out
    assert rc == 2
    assert "zero files" in out


def test_cli_verify_inventory_allow_empty_flags_opt_out_of_the_error(tmp_path, capsys):
    src_dir, produced_dir = tmp_path / "src", tmp_path / "produced"
    src_dir.mkdir()
    produced_dir.mkdir()

    rc = main([
        "verify-inventory", str(src_dir), str(produced_dir),
        "--allow-empty-source", "--allow-empty-produced",
    ])

    assert rc == 0
    assert "clean" in capsys.readouterr().out
