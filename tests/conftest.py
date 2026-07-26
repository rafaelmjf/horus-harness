"""Suite-wide isolation from the ambient agent environment.

Tests fake ``HOME`` (20+ helpers do) to point Horus's config/cache tree at a
tmp dir. That is not sufficient on its own: ``CLAUDE_CONFIG_DIR`` and
``CODEX_HOME`` are resolved *ahead* of ``HOME`` when locating an agent's
config/credentials (``config.agent_config_dir``, ``config.py:787``), and under
Horus account isolation both are always set in the environment a session runs
in. So a faked ``HOME`` alone leaves a real, logged-in account dir reachable.
"""

import pytest

# Resolved ahead of HOME when locating an agent's config/credentials, so a faked
# HOME does not isolate them.
AMBIENT_AGENT_ENV = ("CLAUDE_CONFIG_DIR", "CODEX_HOME")


@pytest.fixture(autouse=True)
def isolate_ambient_agent_env(monkeypatch):
    """Unset the per-account agent config-dir vars for every test.

    Hardening, not a fix for a specific known failure: this closes the gap
    between what a faked ``HOME`` claims to isolate and what it actually does,
    for the whole suite at once rather than per helper.

    Prompted by (but NOT demonstrated to fix)
    ``test_capture_usage_snapshot_unavailable_on_failed_read``, which asserts
    that an isolated fake HOME reads ``unavailable`` and was observed returning
    ``fresh`` twice on unmodified main on 2026-07-26 — blocking a dispatched
    worker whose gate it broke. That flake's mechanism is still unidentified;
    see the backlog card. Clearing these vars was one hypothesis, and the
    symptom did not reproduce afterwards either way.

    A test that genuinely needs one of these set does so itself; this fixture
    runs first, so an explicit ``setenv`` in the test still wins.
    """
    for name in AMBIENT_AGENT_ENV:
        monkeypatch.delenv(name, raising=False)
