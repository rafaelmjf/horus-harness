"""Tests for the structure-version floor (`horus_min_version`)."""

from horus import versioning


def test_version_tuple_parses_plain_releases():
    assert versioning.version_tuple("0.0.26") == (0, 0, 26)
    assert versioning.version_tuple("1.2.3") == (1, 2, 3)
    assert versioning.version_tuple("") == (0,)
    # Non-digit pieces count as 0; digits within a piece are concatenated (legacy
    # behavior inherited from selfupdate — deterministic, not semver-aware).
    assert versioning.version_tuple("2.0.dev") == (2, 0, 0)


def test_is_at_least_ordering():
    assert versioning.is_at_least("0.0.26", "0.0.26")
    assert versioning.is_at_least("0.1.0", "0.0.99")
    assert not versioning.is_at_least("0.0.2", "0.0.26")
    assert not versioning.is_at_least("0.0.25", "0.0.26")


def _write_prd(root, floor: str | None):
    hdir = root / ".horus"
    hdir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "status: active"]
    if floor is not None:
        lines.append(f"horus_min_version: {floor}")
    lines += ["last_updated: 2026-07-08", "---", "", "# P"]
    (hdir / "PRD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_read_floor_none_without_prd_or_stamp(tmp_path):
    assert versioning.read_floor(tmp_path) is None  # no .horus/PRD.md
    _write_prd(tmp_path, None)
    assert versioning.read_floor(tmp_path) is None  # PRD without stamp


def test_read_floor_returns_stamp(tmp_path):
    _write_prd(tmp_path, "0.0.30")
    assert versioning.read_floor(tmp_path) == "0.0.30"


def test_enforce_blocks_below_floor(tmp_path):
    _write_prd(tmp_path, "0.0.30")
    msg = versioning.enforce(tmp_path, "0.0.26")
    assert msg is not None
    assert "0.0.30" in msg and "0.0.26" in msg


def test_enforce_allows_at_or_above_floor(tmp_path):
    _write_prd(tmp_path, "0.0.26")
    assert versioning.enforce(tmp_path, "0.0.26") is None
    assert versioning.enforce(tmp_path, "0.1.0") is None


def test_enforce_noop_without_floor(tmp_path):
    _write_prd(tmp_path, None)
    assert versioning.enforce(tmp_path, "0.0.1") is None
