"""Release-stamped product-audit staleness (deterministic signal only).

The PRD frontmatter stamp ``last_product_audit: <version> <YYYY-MM-DD>`` records
when the owner last ran the bundled ``product-audit`` skill. ``horus close`` /
``horus consolidate`` print one advisory line when that stamp is ≥5 releases or
≥30 days old. Advisory only — no hook, no gate, never blocks; the judgment
(which surfaces to demote/defer/retire) lives in the skill, not here.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import NamedTuple

from horus import frontmatter
from horus.versioning import version_tuple

STAMP_KEY = "last_product_audit"
RELEASE_THRESHOLD = 5
AGE_THRESHOLD_DAYS = 30


class Stamp(NamedTuple):
    version: str
    date: _dt.date


def parse_stamp(value: str) -> Stamp | None:
    """Parse ``<version> <YYYY-MM-DD>`` (extra trailing tokens tolerated)."""
    parts = value.split()
    if len(parts) < 2:
        return None
    version = parts[0].lstrip("v")
    try:
        date = _dt.date.fromisoformat(parts[1])
    except ValueError:
        return None
    if not version:
        return None
    return Stamp(version, date)


def releases_since(stamp_version: str, installed: str) -> int:
    """Deterministic release distance for Horus's linear version stream.

    Sums the component-wise forward distance so ``0.0.30 → 0.0.35`` is 5 and a
    minor bump counts at least 1; never negative.
    """
    a = version_tuple(stamp_version)
    b = version_tuple(installed)
    width = max(len(a), len(b))
    a = a + (0,) * (width - len(a))
    b = b + (0,) * (width - len(b))
    return max(0, sum(y - x for x, y in zip(a, b)))


def advisory_line(
    project_root: Path,
    *,
    installed: str,
    today: _dt.date | None = None,
) -> str | None:
    """One non-blocking advisory line, or None when the audit is fresh.

    Only PRD-structure (v3) projects carry the stamp; anything else is silent.
    """
    doc = frontmatter.parse_file(frontmatter.prd_path(project_root))
    if doc is None:
        return None
    raw = doc.front_matter.get(STAMP_KEY, "").strip()
    if not raw:
        # Opt-in: silent until the owner records a first audit stamp.
        return None
    stamp = parse_stamp(raw)
    if stamp is None:
        return (
            f"product audit: unreadable `{STAMP_KEY}` stamp ({raw!r}); expected "
            "`<version> <YYYY-MM-DD>` (advisory, nothing blocks)"
        )
    today = today or _dt.date.today()
    releases = releases_since(stamp.version, installed)
    age_days = (today - stamp.date).days
    if releases < RELEASE_THRESHOLD and age_days < AGE_THRESHOLD_DAYS:
        return None
    return (
        f"last product audit: v{stamp.version}, {releases} releases and {age_days} days ago "
        "— consider running the product-audit skill (advisory, nothing blocks)"
    )
