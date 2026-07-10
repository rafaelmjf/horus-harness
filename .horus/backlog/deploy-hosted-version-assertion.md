---
status: claimed
priority: now
tier: sonnet
created: 2026-07-10
---
# [ops] deploy-hosted version assertion

`scripts/deploy-hosted.sh` can restart + pass `/health` + 403 on the OLD build if its
version-pin retry loop exhausts (the release webhook raced PyPI's simple-index lag,
observed 2026-07-10). Fix: after restart, assert the expected version via `/health`
and fail loud. Full analysis + acceptance: `bugs/deploy-hosted-silent-stale-version.md`.
Ships with the next release; then observe the release webhook E2E on that release.
