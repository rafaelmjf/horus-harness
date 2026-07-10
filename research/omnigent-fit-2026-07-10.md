# Omnigent fit as Horus LaunchBackend (2026-07-10)

## Decision

**Adopt Omnigent only as an optional LaunchBackend for Linux native sessions and
supported managed-container providers. Do not treat it as the fleet-wide
RemoteBackend: native Windows Claude Code/Codex terminals are explicitly disabled.
Do not build a full `horus worker` to close that gap under the current strategy; doing
so would require Horus to own the live terminal, reconnect, auth, and execution-control
surfaces that `research/omnigent.md` reserves for an external execution plane.**

For the immediate fleet shape:

- **Hosted Linux hub / Linux hosts:** adoptable behind the seam, provided Omnigent is
  separately installed and configured by the operator.
- **Private containers:** adoptable for Omnigent's concrete providers (especially
  Kubernetes runner Pods and BoxLite on capable Linux/macOS hosts), but not as a
  generic “any Docker engine on any fleet machine” backend.
- **Physical Windows 11 and Windows 11 VM:** not adoptable for the required native
  Claude Code/Codex terminal sessions. Omnigent's Windows SDK harnesses are a different
  execution mode, not a substitute for the stated requirement.
- **Horus:** remains the repo-local memory plane. Omnigent remains absent by default,
  selected per task/target, and owns its own server, runner, terminal, auth, sandbox,
  and session state when selected.

## Scope and evidence standard

This spike evaluates the concrete fleet requirements against Omnigent source at
[`27abc0b8bf7781ced968c718f2a71922f28b3931`][source-commit] (fetched 2026-07-10),
not product positioning alone. “Native” below means Omnigent's terminal-first wrappers
around the official Claude Code or Codex CLI/TUI, not its SDK-based `claude-sdk` or
`codex` harness.

Ratings:

- **Covered** — the checked code/docs implement the requirement for the named target.
- **Partial** — a usable implementation exists, but a stated fleet property needs
  operator glue, a narrower target, or a security condition.
- **Gap** — the checked implementation explicitly cannot meet the requirement.
- **Unknown** — source inspection did not establish the property; the named validation
  is required before relying on it.

The hard boundary from `research/omnigent.md` is assumed throughout: Omnigent may be an
optional per-task execution backend behind LaunchBackend, never a Horus dependency or a
second Horus-owned control plane.

## Fleet-target fit matrix

| Target / requirement | Fit | Evidence checked | LaunchBackend implication |
|---|---|---|---|
| Hosted Linux hub: launch native Claude Code / Codex | **Covered** | Native wrappers require `tmux`; Linux wraps each terminal in mandatory `bwrap`, and the documented commands are `omnigent claude` / `omnigent codex` ([README 108–117][readme-native-prereqs], [198–207][readme-native-launch]). | An optional Omnigent-backed remote target can launch the required native sessions on Linux. |
| Hosted Linux hub: choose host and attach | **Covered** | A machine registers with `omnigent host`; the web UI then selects that machine for a new chat ([README 233–241][readme-host]). Session creation accepts `host_id` + absolute `workspace` and launches a runner there ([API 585–639][api-create]). | `launch(brief)` can select the registered Linux host and workspace without Horus inventing a host protocol. |
| Physical Windows 11: launch native Claude Code / Codex | **Gap** | Windows supports the server, web UI, and **SDK-based** harnesses under a Job Object, but explicitly excludes native `omnigent claude` / `omnigent codex` tmux/PTY wrappers ([README 127–149][readme-windows]); the runner returns a Windows-specific “not supported” error for native terminals ([runner 5155–5177][runner-windows-guard]). | Omnigent cannot be the required RemoteBackend for the physical Windows target. |
| Windows 11 VM: launch native Claude Code / Codex | **Gap** | The restriction is an OS/runtime guard (`IS_WINDOWS`), not a hardware distinction; a Windows VM hits the same disabled native-terminal path ([runner 5166–5174][runner-windows-guard]). | Omnigent cannot be the required RemoteBackend for the Windows VM either. WSL would be a Linux target, not native Windows coverage. |
| Windows native sandbox / process containment | **Partial** | The Job Object backend really is Windows code and provides kill-on-close process-tree containment/resource limits, but explicitly provides no filesystem or network isolation; policy paths/network flags are advisory ([Job Object backend 1–27][jobobject], [139–193][jobobject-policy]). | Useful for SDK harnesses, but it neither unlocks native terminal launch nor supplies the isolation expected from Linux `bwrap`. |
| Private container on a Kubernetes-capable machine | **Covered** | The managed Kubernetes provider creates one runner Pod per `host_type: managed` session; the Pod entrypoint is `omnigent host`, with scoped Pod/Secret RBAC and no `pods/exec` grant ([Kubernetes runner docs 1–41][k8s-runners]). | A ContainerBackend adapter can delegate lifecycle to Omnigent on a private cluster. |
| Private container/micro-VM on a single capable machine | **Partial** | BoxLite local mode provisions OCI-image micro-VMs on the Omnigent server host, but requires KVM on Linux or Hypervisor.framework on macOS and is server-managed only ([BoxLite docs 3–24][boxlite-overview], [33–63][boxlite-local]). Omnigent has no generic local-Docker managed provider in its supported-provider set ([managed providers 126–147][managed-providers]). | Adopt for capable Linux/macOS BoxLite hosts; do not advertise it as “any machine with Docker,” especially not Windows. |

## Cross-cutting requirement matrix

| Requirement | Fit | Evidence checked | Consequence / condition |
|---|---|---|---|
| Neutral browser terminal to observe and drive native agents | **Covered** | The browser attaches an xterm.js client over a bidirectional WebSocket to the runner-owned tmux PTY, forwarding terminal output, resize messages, and raw input bytes ([terminal route 1–47][terminal-wire]). The same route works through an out-of-process runner tunnel ([12–30][terminal-runner-proxy]). | This satisfies the vendor-neutral terminal surface for supported POSIX native targets; Horus should link/deep-link to it, not recreate it. |
| Browser-terminal authorization | **Partial** | Read-only attach drops input and uses `tmux attach -r`; write attach is owner-only while non-owners require read access ([terminal route 49–69][terminal-auth-model], [278–353][terminal-auth-code]). However a bare local server defaults to no-login single-user mode; network deploys enable accounts auth by default and can use accounts/OIDC/header auth ([deploy auth 360–383][deploy-auth]). | Treat “secure” as a deployment gate: authenticated HTTPS or tailnet-only exposure, trusted WebSocket origin, and no bare exposed `:6767`. |
| Private network exposure | **Covered** | Tailscale Serve proxies the local server over tailnet-only HTTPS; the docs require a trusted WebSocket origin and public base URL for secure cookies ([Tailscale 23–51][tailscale-private]). | A private browser terminal can be exposed without opening it to the public internet. |
| Subscription auth through official Claude / Codex CLIs | **Covered** | Omnigent recognizes Claude Pro/Max and ChatGPT subscriptions via the official CLIs ([README 249–260][readme-credentials]) and its setup flow invokes `claude auth login --claudeai` / `codex login` interactively ([harness login 483–534][harness-login]). | The adoption path is compatible with subscription-auth-only local native sessions. |
| Per-account isolation on one host (multiple Claude/Codex subscriptions) | **Unknown** | Codex gets a private per-session `CODEX_HOME`, but `auth.json` is bridged from one process-selected source home; Claude native deliberately uses the ambient `~/.claude` login ([Codex executor 662–704][codex-home], [Claude native 393–420][claude-home]). No checked API/config selects a Horus account identity per launch. | Do not claim multi-account coverage. Prove two concurrently registered host contexts with distinct OS user/HOME/config roots and two real subscription logins, including reconnect and stop, before enabling this target class. |
| Credential isolation inside managed containers | **Partial** | Kubernetes projects one named harness-credentials Secret into every runner Pod; subscription tokens can be injected as `CLAUDE_CODE_OAUTH_TOKEN` ([Kubernetes runner docs 50–78][k8s-creds], [105–116][k8s-model-creds]). This is provider/deployment-level secret injection, not Horus account selection, and all Pods share the configured Secret unless the deployment is split. | Suitable for one configured execution identity per provider deployment; per-Horus-account routing requires separate Omnigent deployments/configs or future provider support. |
| Reconnectable sessions | **Covered** | Snapshot + SSE is the explicit reconnect contract: subscribe, fetch snapshot, deduplicate stable item IDs ([API 1218–1237][api-reconnect]); the typical flow states the agent continues through a client disconnect and the client reconnects later ([1239–1272][api-flow]). | `stream(handle)` can recover from browser/network disconnects without Horus owning replay state. Host/runner loss is a separate liveness/fork case. |
| Forkable sessions | **Covered** | `POST /v1/sessions/{source_id}/fork` deep-copies full or truncated history into a new idle session, then lets the client bind a runner ([API 1061–1107][api-fork]). | Fork is available as an Omnigent-only optional capability; it need not enter the minimal LaunchBackend contract. |
| Durable project continuity / memory plane | **Gap** | Core `Memory` remains an in-process key-value store (“in production, this would be backed by Postgres”) ([datamodel 190–211][memory-core]). Omnigent now offers optional external Hindsight long-term-memory tools, but those are agent/conversation banks requiring another service/API key, not committed repo-local project state ([Hindsight 1–31][hindsight]). | Conversation/session persistence does not replace `.horus/`. Horus remains the only project continuity source; export/read interop may feed it into an Omnigent task. |

## Fit to the LaunchBackend seam

The proposed seam (`launch(brief) → handle`, `status`, `stream`, `stop`) does not need
to be widened for Omnigent:

| LaunchBackend operation | Omnigent mapping | Fit |
|---|---|---|
| `launch(brief) → handle` | Register/upload a native-agent bundle, then `POST /v1/sessions` with `host_id` + `workspace` for a registered host or `host_type: managed` for a configured sandbox; the returned conversation ID is the handle ([API 585–622][api-create]). | **Covered** |
| `status(handle)` | `GET /v1/sessions/{id}` returns lifecycle state and optional runner/host liveness; list responses distinguish dead runner from offline host ([API 676–733][api-status]). | **Covered** |
| `stream(handle)` | `GET /v1/sessions/{id}/stream` is SSE; reconnect is stream-first + snapshot + ID dedupe ([API 1109–1149][api-stream], [1218–1237][api-reconnect]). | **Covered** |
| `stop(handle)` | Post `stop_session`; Omnigent hard-kills external native processes/tmux, stops the host-launched runner, preserves the transcript, and can auto-relaunch on a later message ([API 881–897][api-stop]). | **Covered** |

Two adapter details should stay outside the interface:

1. **Target qualification.** Configuration must mark an Omnigent target's supported
   execution mode (`native-posix`, `managed-kubernetes`, `managed-boxlite`, etc.). The
   adapter must reject `native-windows` before calling Omnigent rather than silently
   falling back to an SDK harness.
2. **Reconnect implementation.** The SSE stream is live-tail only, with no event replay
   or sequence numbers ([API 1142–1149][api-stream]). The adapter must implement the
   documented snapshot reconciliation and stable-item-ID dedupe, then translate it to
   the seam's stream events.

## Build vs adopt

### Adopt: optional Omnigent backend for POSIX remote hosts

Implement an optional `OmnigentBackend` adapter (or an Omnigent driver used by
`RemoteBackend`) for registered Linux hosts. It should consume an operator-provided
server URL, host ID, agent ID/bundle, and auth token; it should never start or embed the
Omnigent server implicitly. If Omnigent is absent, normal Horus operation and the local
backend remain unchanged.

This is adoption of an execution plane, not ceding the LaunchBackend abstraction:
Horus chooses the backend and supplies the brief plus `.horus/` resume context;
Omnigent owns host registration, native PTY, browser attach, auth, policies, and live
session state for that launch.

### Adopt: ContainerBackend only for named Omnigent providers

Use Omnigent as `ContainerBackend` where the operator has configured a supported
managed provider:

- Kubernetes for private-cluster runner Pods;
- BoxLite for local hardware-isolated OCI micro-VMs on Linux/macOS or a private remote
  BoxLite pool;
- optionally Modal/Daytona/E2B/other supported providers for explicitly cloud-backed
  targets.

Do not make “Omnigent container” synonymous with generic Docker execution. The server
deploy image is not an agent runner—the documented split says the server coordinates
while runners execute on registered hosts ([deploy execution model 180–198][execution-model]).

### Do not adopt for native Windows; do not build a full Horus replacement

Both Windows fleet targets remain gaps. A full `horus worker` that closes them would
need to implement at least process-tree ownership, PTY streaming, browser input/output,
authentication/authorization, reconnect, session state, and credential isolation. That
is precisely the live cockpit + security/control-plane surface prohibited by the
strategic drift triggers.

Therefore the recommendation is **not** “build the missing Omnigent Windows runner in
Horus.” Choose one of these without crossing the boundary:

1. If SDK execution is acceptable for a task, explicitly select Omnigent's degraded
   Windows SDK mode and label it non-native.
2. If WSL/Linux guest execution is acceptable, register that as a Linux target; do not
   describe it as native Windows coverage.
3. If native Windows terminal sessions are mandatory, keep the target unsupported and
   evaluate another external execution backend—or wait for Omnigent native Windows
   PTY support. Revisit the strategic boundary explicitly before authorizing a Horus-
   owned worker/cockpit.

A thin Windows process launcher alone is not a solution to the stated requirement: it
would still lack the neutral secure browser terminal and reconnect contract.

## Adoption gates and risks

Before implementing the optional adapter:

1. **Multi-account proof (blocking):** live-test two Claude or two Codex subscription
   accounts on one Linux host using separate OS user/HOME/config contexts; verify launch,
   browser attach, reconnect, stop, and that neither session can read/refresh the other
   account's auth.
2. **Security profile (blocking for remote access):** require authenticated HTTPS or
   tailnet-only access, allowed WebSocket origins, owner-only write attach, and a pinned
   Omnigent server identity/version. Never expose a bare no-login local server.
3. **Adapter conformance:** contract-test create/status/SSE reconnect/stop against a
   pinned Omnigent release. Its Sessions API is explicitly Omnigent's own API rather
   than an external compatibility standard ([API 7–14][api-compat]).
4. **Capability truth:** surface target-specific reasons (`native Windows unsupported`,
   `BoxLite requires KVM`, `managed runner auth mode incompatible`) before launch.
5. **Continuity handoff:** inject only a read/export of `.horus/` into the task context;
   import back only identifiers/status if useful. Never move source-of-truth project
   state into Omnigent conversation history or optional Hindsight memory.

## Unverified requirement

**Same-host, simultaneous per-account isolation for multiple subscription-auth CLI
accounts remains Unknown.** The source establishes per-session Codex state isolation and
ambient official-CLI login reuse, but not an account-selecting host/session contract.
The required evidence is a two-real-account end-to-end test under isolated OS/HOME
contexts, including browser reattach and token refresh. No other matrix requirement is
left Unknown at this source snapshot.

## Source links

[source-commit]: https://github.com/omnigent-ai/omnigent/commit/27abc0b8bf7781ced968c718f2a71922f28b3931
[readme-native-prereqs]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/README.md#L108-L117
[readme-native-launch]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/README.md#L198-L207
[readme-host]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/README.md#L233-L241
[readme-windows]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/README.md#L127-L149
[runner-windows-guard]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/runner/app.py#L5155-L5177
[jobobject]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/inner/windows_jobobject_sandbox.py#L1-L27
[jobobject-policy]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/inner/windows_jobobject_sandbox.py#L139-L193
[k8s-runners]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/kubernetes/overlays/sandbox-runners/README.md#L1-L41
[boxlite-overview]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/boxlite/README.md#L3-L24
[boxlite-local]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/boxlite/README.md#L33-L63
[managed-providers]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/managed_hosts.py#L126-L147
[terminal-wire]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/routes/terminal_attach.py#L1-L47
[terminal-runner-proxy]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/routes/terminal_attach.py#L12-L30
[terminal-auth-model]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/routes/terminal_attach.py#L49-L69
[terminal-auth-code]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/routes/terminal_attach.py#L278-L353
[deploy-auth]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/README.md#L360-L383
[tailscale-private]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/tailscale/README.md#L23-L51
[readme-credentials]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/README.md#L249-L260
[harness-login]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/onboarding/harness_install.py#L483-L534
[codex-home]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/inner/codex_executor.py#L662-L704
[claude-home]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/claude_native.py#L393-L420
[k8s-creds]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/kubernetes/overlays/sandbox-runners/README.md#L50-L78
[k8s-model-creds]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/kubernetes/overlays/sandbox-runners/README.md#L105-L116
[api-reconnect]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L1218-L1237
[api-flow]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L1239-L1272
[api-fork]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L1061-L1107
[memory-core]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/inner/datamodel.py#L190-L211
[hindsight]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/tools/builtins/hindsight.py#L1-L31
[api-create]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L585-L639
[api-status]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L676-L733
[api-stream]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L1109-L1149
[api-stop]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L881-L897
[execution-model]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/deploy/README.md#L180-L198
[api-compat]: https://github.com/omnigent-ai/omnigent/blob/27abc0b8bf7781ced968c718f2a71922f28b3931/omnigent/server/API.md#L7-L14
