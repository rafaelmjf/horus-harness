"""Generic file-tree inventory reconciliation.

Three of four Drive-to-Git bulk migrations copied a source tree into a repo; twice a
directory walk silently returned empty for a non-empty source (a flaky `gio list` on
a large folder), which would have silently dropped every file it was supposed to
carry. It was only caught by a manual staged-count vs produced-count comparison. The
lesson: any bulk copy/migration must reconcile counts and sizes in both directions,
and a walk that yields zero entries for a container known to be non-empty is a
failure to retry, never an accepted empty result.

This module is transport-agnostic — it takes two {path: size} manifests (or walks a
directory into one) and reports the difference. It has no Google-Drive/gvfs-specific
code; staging a remote source into a local, walkable tree is an agent-side technique.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class EmptyWalkError(RuntimeError):
    """A walk of a container expected to be non-empty returned zero files.

    Raised instead of returning an empty manifest so a flaky listing (e.g. a stale
    `gio`/network-mount enumeration) surfaces as a retryable failure, not as if the
    source were legitimately empty.
    """


@dataclass(frozen=True)
class ReconcileResult:
    """Both-directions diff of a source manifest against a produced one."""

    source_not_produced: tuple[str, ...]
    produced_not_source: tuple[str, ...]
    size_mismatches: tuple[tuple[str, int, int], ...]  # (key, source_size, produced_size)

    @property
    def clean(self) -> bool:
        return not (self.source_not_produced or self.produced_not_source or self.size_mismatches)


def walk_manifest(root: Path, *, expect_nonempty: bool = True) -> dict[str, int]:
    """Build a ``{key: size}`` manifest by walking every file under ``root``.

    Keys are POSIX-style paths relative to ``root`` (``Path.as_posix()``), so the
    same file compares equal regardless of host OS path separators — comparison is
    always by this stable key, never by a shell-quoted or platform-native string.

    Raises :class:`EmptyWalkError` when ``expect_nonempty`` is True and the walk
    finds zero files.
    """
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")
    manifest = {
        path.relative_to(root).as_posix(): path.stat().st_size
        for path in root.rglob("*")
        if path.is_file()
    }
    if expect_nonempty and not manifest:
        raise EmptyWalkError(
            f"walk of {root} returned zero files, but a non-empty tree was expected — "
            "treat this as a failed listing and retry, not as an empty result"
        )
    return manifest


def load_manifest_file(path: Path) -> dict[str, int]:
    """Load a ``{key: size}`` manifest from a JSON file.

    Accepts either a ``{"path": size, ...}`` object or a ``[["path", size], ...]``
    list of pairs, whichever shape the caller already has on hand.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(key): int(size) for key, size in data.items()}
    if isinstance(data, list):
        return {str(key): int(size) for key, size in data}
    raise ValueError(f"unrecognized manifest shape in {path}: expected object or list of pairs")


def load_manifest(path: Path, *, expect_nonempty: bool = True) -> dict[str, int]:
    """Load a manifest from ``path``: walk it if it's a directory, else parse it as
    a JSON manifest file."""
    if path.is_dir():
        return walk_manifest(path, expect_nonempty=expect_nonempty)
    return load_manifest_file(path)


def reconcile(source: Mapping[str, int], produced: Mapping[str, int]) -> ReconcileResult:
    """Compare two ``{key: size}`` manifests both directions by stable key."""
    source_keys = set(source)
    produced_keys = set(produced)
    size_mismatches = tuple(
        (key, source[key], produced[key])
        for key in sorted(source_keys & produced_keys)
        if source[key] != produced[key]
    )
    return ReconcileResult(
        source_not_produced=tuple(sorted(source_keys - produced_keys)),
        produced_not_source=tuple(sorted(produced_keys - source_keys)),
        size_mismatches=size_mismatches,
    )


def format_report(result: ReconcileResult) -> list[str]:
    """Human-readable report lines for a :class:`ReconcileResult`."""
    if result.clean:
        return ["reconcile: clean — source and produced agree on count and size"]
    lines = []
    for key in result.source_not_produced:
        lines.append(f"source-not-produced: {key}")
    for key in result.produced_not_source:
        lines.append(f"produced-not-source: {key}")
    for key, source_size, produced_size in result.size_mismatches:
        lines.append(f"size-mismatch: {key} (source={source_size}, produced={produced_size})")
    return lines
