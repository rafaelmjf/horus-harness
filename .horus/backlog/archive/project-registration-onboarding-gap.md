---
status: shipped
priority: medium
readiness: ready
autonomy: eligible
readiness_reason: "Scoped with the owner 2026-07-26: control 3 (the TUI uncached-local fallback) is DROPPED because the owner's own repair path is to ask an agent, which already has a shell. Controls 1 (deterministic unregistered signal + horus-infer guidance) and 2 (context-specific narrow footer) were already evidenced and are now the whole card."
created: 2026-07-25
created_by: owner
last_refined: 2026-07-26
tier: small
type: bug
parallel: safe
phase: converge
vision_facet: "Dashboard / cockpit"
surface: "horus/terminal_tui.py, horus/routines.py (infer/resume signals), horus/initialize.py, tests/test_terminal_tui.py, tests/test_init.py"
shipped_pr: 412
shipped_sha: dee776d
---

# project-registration-onboarding-gap — cloned Horus project stays invisible and mobile hides registration

## Why — live incident

The owner created the independent `fabric-build` repository by cloning another
Horus-enabled repository, then asked for Horus continuity and a clean fresh-session
handoff. The repo already contained a populated `.horus/PRD.md`, instructions, skills,
and hooks. The supervising session therefore ran `horus infer`, refined continuity,
merged it, and reported the repo ready without ever running `horus init`.

The owner then could not see `fabric-build` in the mobile TUI. Running:

```text
horus init --yes --no-skills --no-hooks /home/rafa/projects/fabric-build
```

immediately printed:

```text
[updated] registered project in ~/.horus/config.toml
```

and `horus status`/the TUI could see it. Init also created the missing tracked
`.horus/temp/.gitkeep`, requiring a second cleanup PR before the checkout was truly
clean.

## What actually exists — do not rebuild it

- `initialize.init_project()` already calls `config.register_project()` on every
  successful init, including an existing v3 project. Registration is idempotent and
  the CLI already reports `registered project in ~/.horus/config.toml`.
- The TUI already renders cached remote/local clones as
  `cloned, not registered`; activating that row exits through `_RemoteStart`, which
  reuses `remote_start.start_github_project()` to register it.
- Tests already cover remote-row activation and the shared start primitive.

The missing behavior is detection and discoverability around those primitives.

## Exact defects

1. **Repo-local continuity is mistaken for machine registration.**
   `horus infer` warns to run init only when `.horus/` is absent. It emits no finding
   when a valid cloned `.horus/` exists but the checkout is absent from
   `config.load_projects()`. `horus resume` likewise prints a valid handoff without
   saying the TUI cannot see the project.
2. **The mobile affordance is invisible.**
   On the narrow projects screen, `_footer_text()` renders
   `↑↓ · f fleet · u refresh · …` and omits Enter entirely. The wide footer includes
   generic `Enter`, but neither footer names the selected remote row's real action:
   register a clone or clone+register a remote.
3. **Registration depends on the remote cache for TUI discovery.**
   `_remote_projects()` is intentionally cache-only. An existing local Horus checkout
   that is absent from that cache has no TUI row and no explicit Add/Register action,
   so a phone user must know and run `horus init <path>` in a shell.

## Cost attribution

- **Supervisor error:** the session equated “`.horus/` exists” with “Horus is fully
  initialized on this machine” and skipped the user-requested `init`.
- **Horus/skill defect:** infer/resume expose no registration-state signal, while the
  narrow TUI hides the action that could repair a cached clone.
- **Inherent task, delegation tax, worker error, external failure:** none materially
  contributed.

## Proposed controls — cheapest first

1. **Deterministic signal.** When `infer`, `resume`, and project doctor run inside a
   valid `.horus/` checkout that is not registered, report
   `not visible in Horus fleet/TUI — run horus init <path>`. Update the infer guidance
   to distinguish repo-local continuity from machine-local registration.
2. **Visible mobile action.** Make the projects footer/selected-row action
   context-specific at narrow widths: `Enter open`, `Enter register`, or
   `Enter clone + register`. Do not rely on an unlabeled Enter key that disappears on
   phones.
3. ~~**Uncached local fallback.**~~ **DROPPED 2026-07-26** — see Reviews. The owner's
   repair path for this situation is to ask an agent, which already has a shell and can
   run `horus init <path>`; a TUI registration affordance is human ceremony that the
   actual actor never touches, and it would not have prevented the observed failure.

Guidance alone is insufficient: the existing init behavior was correct, yet both the
agent and owner missed it. A registration-state signal and a visible action are the
cheapest controls that catch the observed failure in the product.

## Acceptance

- `horus init` on an existing populated v3 checkout registers it immediately,
  idempotently, without clobbering continuity; a regression test asserts the registry
  result and action text.
- When a current Horus checkout is not registered, infer/resume/project-doctor output
  names the state, user impact (absent from fleet/TUI), and exact init remedy.
- On a mobile-width projects screen, a selected registered project says
  `Enter open`; a selected cloned/unregistered project says `Enter register`; and a
  remote-only project says `Enter clone + register`.
- Every path uses the existing canonical registry/init/start services, and tests prove
  no duplicate registry writer or second onboarding implementation is introduced.

## Non-goals

- **Do not build a TUI registration path for an uncached local checkout** (dropped
  control 3). The repair actor is an agent with a shell.
- Do not auto-register arbitrary repositories merely because they contain `.horus/`.
- Do not add network work to TUI first paint.
- Do not replace `horus init`, `horus start`, or the remote catalogue.
- Do not make the TUI a filesystem browser.

## Source

Owner-observed `fabric-build` onboarding incident, 2026-07-25. Exact live repair:
idempotent `horus init` registration followed by `horus status` visibility.

## Reviews

- 2026-07-26 — Scoped with the owner. **Control 3 dropped, not deferred.** The owner's
  stated path if this recurs is *"I'll ask the agent to do it"* — and an agent already
  has the only thing needed, a shell running `horus init <path>`. Both shapes considered
  for control 3 (workspace-root discovery, explicit path prompt) are human affordances
  the actual actor never touches, and neither would have prevented the observed failure:
  the card's own cost attribution puts that on the **supervisor** equating "`.horus/`
  exists" with "initialized on this machine".

  So control 1 is the load-bearing control and is explicitly **agent-facing**: the
  deterministic finding must name the state, the user impact (absent from fleet/TUI) and
  the exact remedy, and the `horus-infer` guidance must stop a session conflating
  repo-local continuity with machine-local registration. This also satisfies the repo's
  agent-first boundary — structure earns its place by making a fresh agent session act
  more correctly, never by adding human-process ceremony.

  Control 2 (context-specific narrow footer) is kept deliberately: owner visibility on
  the mobile TUI is how the gap was noticed at all, and the narrow footer omitting
  `Enter` entirely is a real defect independent of who performs registration.

  Minted **Ready / eligible**, tier small. Surface note for sequencing: it touches
  `terminal_tui.py` and `routines.py`, so it must not run concurrently with
  `codex-usage-stale-snapshot-gates-dispatch` (same files).
