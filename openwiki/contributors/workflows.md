---
type: contributor guide
title: Contributor Workflows, Validation, and Release
description: Safe development workflow for Horus source, projected artifacts, tests, package assets, and trusted publishing.
tags: [contributors, testing, release, packaging]
---

# Contributor Workflows, Validation, and Release

## Change workflow

1. Start with the owning page/module and its focused test, not a broad source rewrite. The [architecture overview](../architecture/overview.md) routes common intents.
2. Treat source and tests as authoritative. Repository continuity prose is useful context, but `.horus/archive/` is historical and `.horus/sessions/` is optional local recovery only.
3. Preserve key boundaries: project continuity vs machine-local runtime state; agent account selection vs proxy authentication; dispatch authorization vs worker completion evidence; local GitHub bootstrap vs remote execution.
4. For changes to generated agent surfaces, modify the generator/canonical template first, then refresh projections and run projection-focused tests. Do not hand-edit a generated projection without understanding its generator.
5. Use focused pytest suites during iteration; run the full suite for cross-module/control-plane work.

## Local developer checks

The package requires Python `>=3.12`; runtime dependencies are `prompt-toolkit` and Windows-only `pywinpty`. The package exposes the `horus` console entry point and includes `horus/assets/*.png`, `*.ico`, and vendored xterm files as package data.

```sh
pytest -q tests/test_cli.py                 # parser/command wiring
pytest -q tests/test_closure.py tests/test_backlog.py
pytest -q tests/test_dashboard.py tests/test_terminal_tui.py
pytest -q tests/test_launch.py tests/test_terminal_sessions.py
pytest -q                                # broad regression gate
ruff check horus tests                    # if ruff is installed for the change
```

The GitHub tests workflow runs on Python 3.12 and 3.13 and compiles modules before pytest. Make a change that is valid across both supported versions; do not rely only on the local interpreter.

## Managed projections

`horus init` can install managed blocks, skills, and hooks. `upgrade-project --apply` refreshes those projections but does not write project-specific PRD/card decisions. Relevant source surfaces:

| Surface | Canonical implementation | Focused tests |
|---|---|---|
| Managed instruction block | `instructions.py`, `templates.py` | `test_instructions.py`, `test_reconcile.py` |
| Bundled skills | `skills.py` | `test_skills.py` |
| Native hooks | `native_hooks.py` | `test_native_hooks.py`, checkpoint/usage-hook suites |
| Upgrade/projection status | `upgrade.py`, `projection_sync.py` | `test_upgrade.py`, `test_projection_sync.py` |

The Horus harness commits generated Claude/Codex projections. A source change to `horus/skills.py` generally changes the projection surface too; keep them synchronized and use a PR rather than direct-pushing generator/projection drift to the default branch.

## Distribution and release

`pyproject.toml` owns package identity, Python floor, console entry point, package discovery, and packaged assets. GitHub Actions separates testing from publication:

- `.github/workflows/tests.yml` runs the supported Python matrix and pytest/compile checks.
- `.github/workflows/install-smoke.yml` validates installation behavior.
- `.github/workflows/publish.yml` builds sdist/wheel with `uv build` and publishes when a GitHub Release is created.

Publication uses PyPI trusted-publishing OIDC, so release automation should not add a static PyPI credential to repository files or workflows. Packaging/release changes must preserve this boundary, verify asset inclusion and console invocation, and test the release workflow’s trigger/permissions semantics.

| Change | Minimum validation |
|---|---|
| Package metadata/assets/entry point | build locally when available; run install-smoke-relevant tests and `python -m horus --help` in a clean environment |
| CI matrix/workflow | inspect workflow YAML and run targeted pytest locally; ensure Python 3.12/3.13 compatibility |
| Publish workflow | verify release trigger, `uv build`, artifact handoff, and OIDC trusted-publishing permissions; never test with committed secrets |

For project adoption, see [continuity](../architecture/continuity.md); for external repository onboarding, see [catalog and onboarding](../operations/catalog-and-onboarding.md).
