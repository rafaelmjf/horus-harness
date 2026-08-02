---
name: horus-release
description: >-
  Cut a horus-harness release end to end: the three-file version bump, the PR and
  its required checks, the tag and GitHub release, the PyPI publish, and — the step
  that is NOT implied by any of the others — `scripts/deploy-hosted.sh`, because
  publishing a version does NOT update the hosted dashboard. Use when the owner says
  "release", "cut a version", "publish", or "ship 0.0.x". Owner-gated: a release is
  its own decision, never chained onto the end of other work.
---

<!-- horus-skill-version: 1 -->

# horus-release — cut a version, and land it where people actually run it

## The invariant this skill exists for

**Publishing a version does NOT update the hosted app.** `horus.rafaelfigueiredo.com`
runs a *pinned* uv-tool install that only advances on an explicit upgrade plus a
service restart. A green publish workflow is therefore not a finished release — it is
a finished *publish*. The last action of every release is `scripts/deploy-hosted.sh`.

Nothing else in the chain implies that step, which is exactly why it needs writing down.

## Before you start

A release is its own decision, taken with the owner. Never chain it onto the end of
other work, and never treat "continuity is current" as authorization to cut one.

Confirm first: continuity is checkpointed, `main` is green, and the owner has said to
release *this* version.

## The chain

1. **Bump three files together** — `pyproject.toml`, `horus/__init__.py`, `uv.lock`.
   All three or none; a partial bump ships a package whose own `--version` lies.
2. **Rerun the tests locally**, then open the bump as a PR and let the *required*
   checks go green on the exact commit. `horus merge-watch <pr>` watches them with a
   bounded interval and timeout — do not hand-roll a polling loop.
3. **Merge**, then tag and `gh release create`.
4. **PyPI publish** — trusted publishing runs from the tag. Prove it landed: the
   package JSON *and* the simple index, not just a green job.
5. **`scripts/deploy-hosted.sh`** — refreshed install, `systemctl restart`,
   `/health` reporting the new version, and `/` still 403 behind Access. All four.

## Traps that have actually bitten

- **`uv tool install --force --refresh`, never `uv tool upgrade --reinstall`.** The
  latter re-reads uv's cached index and silently stays on the old version (observed
  0.0.30 -> 0.0.31).
- **`uv tool install horus-harness` without `--python 3.12`** silently resolves an
  ancient version below the floor. Compare `horus --version` with `uv run horus
  --version` when they disagree.
- **Project skills from prospective source before a release cut.** A bundled-skill fix
  reaches the fleet only through a RELEASE, so `upgrade-project --apply` run against
  the *installed* CLI installs the pre-fix version. Use `uv run horus skill install
  --force`, or repeat the projection after installing.
- **`0.1` is reserved** for the first version the owner considers stable enough to hand
  to someone else to test. Until then releases stay on `0.0.x` however structural the
  change — so do not read a patch bump as "small", and never propose `0.1` to signal
  architecture.

## Three OS targets

Windows, Linux and macOS. Claude and Codex projections move together, and each is
compared against the CLI, never against its peer.

## Boundaries

- Owner-gated at the release decision itself; the steps after that are mechanical.
- This skill does not automate any step and does not own `scripts/deploy-hosted.sh`.
- A self-hosted-runner/webhook that makes the deploy step a hard guarantee rather than
  an instruction is tracked in the backlog; until it exists, this text IS the guarantee.
