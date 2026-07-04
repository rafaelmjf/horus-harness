# Horus Hub Design

## Threat Model First

Remote agent launch is remote code execution. A hosted Horus hub that can start
Claude, Codex, or future agent sessions is not just a dashboard with buttons; it
is a remote command surface against the owner's machines, repos, accounts, local
credentials, and subscription-authenticated CLIs. Authentication and authorization
are therefore non-negotiable gates before the hub exposes any project detail or
launch affordance.

The safe default is a self-hosted, single-owner hub reachable through a private
hostname such as `horus.rafaelfigueiredo.com`, fronted by Cloudflare Tunnel and
Cloudflare Access in the same style as the owner's gym app. The hub process itself
must still enforce local authorization and must treat Access as one layer, not as
the only layer.

### Assets

- Repo contents and repo-local `.horus/` continuity.
- Agent account state under isolated Claude/Codex account directories.
- Session registry rows and run logs, including prompts, command output, paths,
  exit status, and RESULT events.
- Git credentials, SSH agents, editor integrations, shell environment, and any
  local secrets reachable by launched agents.
- The owner's compute budget and subscription/API usage limits.
- The private project inventory: paths, repository names, branches, current focus,
  and recent sessions.

### Attack Surface

- Public DNS, TLS termination, reverse proxy, Cloudflare Tunnel, and Access policy.
- Hub HTTP routes, static assets, forms, JSON endpoints, WebSocket or SSE streams,
  CSRF boundaries, cookies, and session storage.
- Project discovery and path parameters, especially any route that maps a user
  supplied identifier to a filesystem path.
- Reads of `.horus/`, session registry databases, and run logs.
- Agent launch routes that choose project, account, agent, model, working tree,
  environment, prompt, and whether to watch or tail.
- Account selection and configuration surfaces that map to `CODEX_HOME`,
  `CLAUDE_CONFIG_DIR`, or future adapter-specific homes.
- Log and transcript rendering, including terminal escape sequences, HTML/Markdown
  injection, very large files, and secrets printed by tools.
- Background workers, queue state, restart recovery, and stale process cleanup.
- Update/deploy pipeline for the separate hub repo and its service credentials.

### Mitigations

- **Access before app:** require Cloudflare Access or an equivalent private access
  layer for every route, including static assets and health pages that reveal
  project names. The MVP should ship no unauthenticated public route except a
  generic liveness endpoint with no project data, if the platform needs one.
- **App-side owner gate:** validate the Access identity header or a local owner
  session in the app before showing project data. Do not assume the reverse proxy
  is always correctly configured.
- **No launch in MVP:** the first shipped cut is read-only. This removes the RCE
  path until inventory, auth, deploy, and rendering behavior have been exercised.
- **Explicit launch arming:** when launch arrives, put it behind a second
  app-level switch such as `HORUS_HUB_ENABLE_LAUNCH=1`, plus a visible disabled
  state in the UI when unset.
- **Allowlisted projects only:** never accept arbitrary filesystem paths from the
  browser. The hub reads a local config or Horus registry of approved project roots
  and uses opaque project IDs in URLs.
- **Adapter/account allowlists:** expose only configured account aliases and known
  adapters. Launch code maps aliases to existing adapter account homes; the browser
  never sends raw `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, executable paths, or shell
  fragments.
- **Structured launch API:** launch requests are structured fields
  (`project_id`, `agent`, `account_alias`, `mode`, `prompt`, optional branch or
  worktree policy), not shell commands. The server calls Horus adapter APIs or
  `horus run` with argv arrays.
- **CSRF and method discipline:** all mutating routes require POST, CSRF tokens,
  same-site cookies, and PRG redirects. GET routes are read-only.
- **Prompt and log hygiene:** render logs as escaped text, strip or neutralize
  terminal control sequences, cap line counts and bytes, and add explicit
  "may contain secrets" handling rather than making logs shareable artifacts.
- **Least local privilege:** run the hub as the owner user only if native agent
  CLIs require that account. Keep the process out of privileged groups, avoid
  Docker socket access, and do not grant write access to repos beyond what the
  launched native CLIs already have.
- **Audit trail:** every launch request records authenticated owner identity,
  timestamp, project, adapter, account alias, prompt hash or short summary, and
  resulting Horus session id. The audit trail points to the run log; it does not
  duplicate transcripts.
- **Rate and budget controls:** launch routes enforce per-minute launch caps and
  display account usage state already known to Horus. This is not a spend policy
  engine; it is a guard against accidental repeated starts.
- **Fail closed:** if Access headers are missing, project registry cannot be read,
  account aliases are ambiguous, or run-log paths are outside the expected logs
  root, the hub hides the project or disables launch rather than guessing.

## Product Boundary

The hub is a self-hostable web application for one owner who wants one central
place to inspect all Horus projects and, later, start native agent sessions across
configured accounts. It complements the local dashboard by being reachable from
the owner's private domain and by spanning machines or project roots that the
owner chooses to expose.

It is not the Horus control plane. The durable product remains Horus's repo-local
continuity layer: `.horus/`, session notes, registry entries, and run logs. The hub
is a consumer and launcher over those surfaces.

## Interop Seam

The API boundary is existing Horus state:

- **Repo-local `.horus/`:** PRD frontmatter, vision, backlog, shipped lines, rules,
  session summaries, and execution notes provide the project view and resume context.
- **Session registry:** active, finished, stale, failed, and awaiting-review session
  rows provide the live-session index and account/adapter metadata.
- **Run logs:** per-run logs and RESULT events provide tails, completion status, and
  diagnostics.

The hub must not create a second project database that competes with `.horus/`.
It may cache derived summaries for performance, but cache invalidation is simple:
the filesystem, registry, and run logs are authoritative. If the hub cannot
reconcile cache state with source files, it discards the cache.

The same rule applies to writes. Launch creates a normal Horus session through the
existing adapter/session-registry path. Closure remains the native Horus ritual:
agents update `.horus/` and users run the normal close flow. The hub can display
"needs closure" or "awaiting review"; it does not own closure semantics.

## MVP Cut

MVP ships a read-only multi-project dashboard behind auth before any launch
capability exists.

### MVP Scope

- Self-hostable app in a separate repo.
- Deployment docs for a single owner behind Cloudflare Tunnel plus Cloudflare
  Access, with reverse-proxy examples for Caddy or nginx.
- Configured project roots or registry import, using opaque project IDs.
- Project list showing name, path label, branch if cheaply available, current focus,
  next action, last updated, and warning badges for stale or missing `.horus/`.
- Project detail showing PRD sections, recent session summaries, session-registry
  status counts, and recent run-log RESULT events.
- Account read model showing configured adapter/account aliases and coarse usage or
  freshness information already available from Horus.
- No buttons that start agents, edit files, run git, mutate registry rows, or write
  `.horus/`.

### MVP Gate

- Every page requires Access plus app-side owner validation.
- The app can be deployed at the private hostname and shows only allowlisted projects.
- Killing or removing the hub does not affect any repo, session, registry, or log.
- A project can be inspected using only `.horus/`, session registry, and run logs.

## Launch Capability

Launch is a later phase because it crosses the RCE boundary. When enabled, the hub
maps account-scoped launches to Horus's existing adapter/account model:

- `agent=codex` uses the Codex adapter and a configured account alias that resolves
  to an isolated `CODEX_HOME`.
- `agent=claude` uses the Claude adapter and a configured account alias that resolves
  to an isolated `CLAUDE_CONFIG_DIR`.
- Future agents must follow the same pattern: concrete adapter plus concrete account
  alias, not abstract identity profiles.
- Launch records a normal Horus registry session and writes normal run logs under
  the Horus run-log root.

The launch form should start conservative:

- project picker from allowlisted projects;
- agent picker from installed adapters;
- account picker from configured aliases for that adapter;
- mode picker for resume, fresh, brainstorm, or execution-prompt launch where those
  modes already exist locally;
- prompt textarea seeded from `.horus/PRD.md` frontmatter or an explicit user prompt;
- dry-run preview showing project path, adapter, account alias, and exact structured
  argv, with secrets and raw home paths hidden.

The server submits launches through Horus's existing launch path rather than opening
an in-browser shell. Tailing a run log is read-only; interactive PTY hosting,
co-driving, remote attach, forking sessions, and cloud runners are not part of this
hub.

## Deployment Shape

For the single-owner target, the simplest production shape is:

- hub app runs as a systemd user service, container, or small process on the owner's
  machine or home server;
- Caddy/nginx or the app's own HTTP server listens only on localhost or a private
  LAN interface;
- Cloudflare Tunnel exposes `horus.<owner-domain>` to Cloudflare;
- Cloudflare Access restricts the hostname to the owner's identity and device
  policy;
- app-side middleware validates the Access identity header or a local owner session;
- logs stay local, with rotation, and are not shipped to a third-party log service
  by default.

This matches the gym-app precedent: a private owner app on a memorable domain,
protected by Cloudflare Access, without turning the product into SaaS.

## Separate-Repo Scaffold Plan

The hub should live outside the `horus-harness` uv package. Treat it as a reference
framework others can self-host, not as a required runtime for Horus.

Suggested repo shape:

```text
horus-hub/
  README.md
  pyproject.toml
  src/horus_hub/
    app.py
    auth.py
    config.py
    projects.py
    registry.py
    run_logs.py
    launch.py
    templates/
    static/
  tests/
  deploy/
    systemd/
    caddy/
    nginx/
    cloudflare-access.md
  examples/
    config.example.toml
```

Integration options, in order of preference:

1. Use public Horus CLI/library surfaces where they exist for registry and launch.
2. If library APIs are not stable enough, shell out to `horus` with argv arrays and
   parse documented machine-readable output only.
3. Add small read-only export commands to Horus if needed; do not import the whole
   dashboard or make the uv package depend on the hub.

Versioning should be explicit: the hub declares the minimum Horus CLI version it
expects and shows a compatibility warning per project or host when the installed
CLI is older.

## Phased Build Plan

### Phase 0: Repo and Auth Skeleton

- Create the separate repo, config loader, health route, owner-auth middleware, and
  deployment examples.
- Gate: private hostname works behind Cloudflare Access; unauthenticated requests
  see no project data.

### Phase 1: Read-Only Project Inventory

- Read allowlisted project roots and `.horus/PRD.md`.
- Render project list and project detail.
- Gate: all five MVP fields render for at least three local projects, and removing
  the hub leaves repos untouched.

### Phase 2: Registry and Run-Log Read Model

- Read session registry rows and run-log RESULT events.
- Add recent sessions, live/stale/failed counts, and read-only log tail.
- Gate: a killed or completed session is reflected from registry/run-log state
  without writing new hub-owned status.

### Phase 3: Launch Design Hardening

- Add disabled launch UI, structured dry-run preview, account/adapter allowlists,
  CSRF, audit schema, and explicit `HORUS_HUB_ENABLE_LAUNCH` gate.
- Gate: launch remains disabled unless armed; dry run cannot express arbitrary shell.

### Phase 4: Minimal Launch

- Start fresh/resume sessions through Horus adapter APIs or `horus run`.
- Store audit entries and link to session registry/run logs.
- Gate: launch creates a normal Horus session and RESULT-backed run log; no hub-only
  session state is required to inspect it.

### Phase 5: Operational Polish

- Add install/update docs, backup guidance, log retention, compatibility checks,
  and richer read-only warnings.
- Gate: a future delegated batch can own each subsection independently because auth,
  read model, launch, and deployment are separated.

## Non-Goals

- No multi-user SaaS, tenants, organizations, billing, invite flows, or shared
  workspaces.
- No identity abstraction above the existing concrete model of project + agent +
  account + environment + session.
- No agent marketplace or generic harness marketplace.
- No cloud runner, sandbox provider, credential broker, or spend-policy engine.
- No live collaborative session cockpit, browser PTY, remote attach, session fork,
  or co-driving UI.
- No replacement for repo-local `.horus/`, closure, `horus resume`, session
  registry, or run logs.
- No embedding the hub into the `horus-harness` uv package as a default dependency
  or required service.

## Decisions to Carry Forward

- Ship read-only first. Launch is explicitly deferred until the auth and read model
  have been proven in production.
- Keep the hub self-hosted and single-owner. Cloudflare Access is the recommended
  deployment gate, not a product identity layer.
- Treat `.horus/`, the session registry, and run logs as the API. Any hub cache is
  derived and disposable.
- Keep account launches concrete: adapter plus account alias resolving to existing
  isolated homes.
- Keep orchestration boundaries aligned with the Omnigent research: the hub may
  launch native Horus sessions, but it must not become a multi-harness control plane.

## Hard Requirement Trace

1. **Threat model first:** addressed in `Threat Model First`, including RCE framing,
   attack surface, and mitigations.
2. **Read-only MVP before launch:** addressed in `MVP Cut`; launch is deferred to
   `Launch Capability` and later phases.
3. **Interop seam:** addressed in `Interop Seam`; `.horus/`, the session registry,
   and run logs are authoritative.
4. **Separate-repo scaffold:** addressed in `Separate-Repo Scaffold Plan`.
5. **Explicit non-goals:** addressed in `Non-Goals`, aligned to the PRD vision's
   rejection of multi-user SaaS and identity abstraction.
