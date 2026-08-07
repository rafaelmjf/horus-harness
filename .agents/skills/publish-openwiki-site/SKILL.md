---
name: publish-openwiki-site
description: >-
  Owner-invoked workflow for publishing, updating, checking, rolling back, or
  removing a project's generated OpenWiki visualizer on a durable hostname.
  Use when the owner says "publish this OpenWiki", "put the wiki on my site",
  "deploy the generated wiki", "update the published wiki", or wants to repeat
  the same OpenWiki deployment across several projects. Reuses an existing
  Cloudflare Tunnel + Access pattern when present, keeps the OpenWiki origin on
  loopback, creates an isolated deploy checkout and systemd service, and proves
  both the local graph API and authenticated public surface. Not for generating
  the OpenWiki content or for deploying a general web application.
---

<!-- horus-skill-version: 1 -->

# Publish an OpenWiki visualizer without rebuilding the deployment each time

This is a publication workflow, separate from OpenWiki generation. The generated
`openwiki/` directory is the content; OpenWiki's visualizer is the runtime. It serves
root-relative `/api/graph` and `/events`, so use one hostname and one loopback port per
project. Do not subpath-multiplex several wikis or build a static exporter unless the
owner explicitly chooses that different product.

## Contract

- **Private by default.** A generated repository wiki can expose architecture,
  operational details, and backlog context. Put a Cloudflare Access application in
  front of it unless the owner explicitly chooses public access.
- **Access before exposure.** Create and verify the Access application/policy before
  adding DNS or tunnel ingress. If the host already has an unprotected route, report
  it and stop before widening or relying on it.
- **Loopback stays loopback.** OpenWiki intentionally binds `127.0.0.1`. Never patch
  it to `0.0.0.0`; Cloudflare Tunnel maps the public hostname to the loopback origin.
- **One isolated deploy checkout.** Never serve a development worktree. Publish an
  exact pushed commit from a separate deploy checkout and update it fast-forward-only.
- **Secrets stay machine-local.** Never commit Cloudflare tokens, tunnel credentials,
  Access secrets, OpenWiki provider credentials, or authenticated curl cookies.
- **External mutations stay owner-scoped.** An explicit request to publish authorizes
  the named project/hostname. If hostname, audience, host, or source ref cannot be
  derived safely, pin that choice with the owner before changing Cloudflare, DNS, or
  systemd. An assessment-only request stops at a proposal.

## 1. Pin the publication record

Fetch first, then print one compact record and resolve every field before mutation:

```text
project slug:       <stable filesystem/systemd-safe slug>
source repository: <URL or absolute canonical checkout>
source ref/SHA:    <default branch or explicitly chosen branch; exact pushed SHA>
wiki directory:    <absolute deploy-checkout>/openwiki
deploy checkout:   <absolute path outside the development checkout>
hostname:          <one hostname dedicated to this wiki>
origin:            http://127.0.0.1:<fixed unused port>
service:           openwiki-<slug>.service
service user:      <non-root owner of the deploy checkout>
Access app/policy: <existing reusable policy or named new app>
tunnel/config:     <existing tunnel id and configuration authority>
OpenWiki binary:   <absolute path and pinned version>
```

Prefer the host's established layout and deployment convention. Read the target
project's deploy docs and the live tunnel configuration before proposing new paths.
On the owner's usual Horus host, sibling deployments such as Keiko and Tabi are
evidence for the pattern, not files to copy blindly.

## 2. Preflight the content and host

1. Run `git fetch --all --prune`. Require a clean source tree and a pushed source SHA.
2. Require `openwiki/`, `openwiki/index.md`, and `openwiki/.last-update.json`. Parse the
   latter and refuse publication unless `status` is `complete`.
3. Validate the wiki's frontmatter and relative links, and run `git diff --check`.
   Scan the publish set for credentials. Do not treat generated prose as a secret-scan
   exemption.
4. Resolve the OpenWiki version from the repository's pinned workflow/package config
   when available; otherwise use the installed version and record it. Bake the
   absolute executable path into systemd: the manager does not inherit an interactive
   shell's package-manager PATH.
5. Confirm the chosen port is unused in the foreground. OpenWiki tries later ports on
   collision, so `--port N` is not proof that it bound N. Publication requires the
   requested port exactly.
6. Inspect the existing Cloudflare Tunnel ingress and catch-all. Preserve every
   unrelated hostname and keep the final catch-all last.

## 3. Install the durable origin

Clone or refresh the deploy checkout at the pinned ref. Use a rendered systemd unit
with resolved absolute values—never install the placeholders below:

```ini
[Unit]
Description=OpenWiki visualizer (<project slug>)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=<service user>
WorkingDirectory=<absolute deploy checkout>
ExecStart=<absolute openwiki binary> visualize <absolute wiki directory> --port <port> --no-open
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Store the project-specific unit or an exact reconstruction runbook in the target
repository when that repository owns its deployment. Host registration and secrets
remain outside git. Install/enable the unit, then independently prove:

- `systemctl is-active` reaches `active`;
- the journal contains the OpenWiki startup banner and the exact requested
  `127.0.0.1:<port>` (a shifted port is a failed deployment);
- `GET /` returns HTML with OpenWiki's Content-Security-Policy;
- `GET /api/graph` returns JSON with a non-empty node set and the expected wiki root;
- `/events` opens as `text/event-stream` and can be closed cleanly.

Stop and account for every foreground/background probe. A process that merely started
is not verified.

## 4. Add the private public route

1. Create or reuse the Cloudflare Access application and its narrow allow policy.
   Prefer the owner's established identity policy. Where the tunnel supports origin
   Access-token validation ("Protect with Access" / required Access audience), enable
   it so a routing mistake cannot bypass the gate; report explicitly if unavailable.
2. From a clean unauthenticated client, prove the hostname is not yet serving the wiki.
3. Back up the exact live tunnel configuration, insert only this hostname before the
   catch-all, and map it to `http://127.0.0.1:<port>`.
4. Run `cloudflared tunnel ingress validate` and inspect the rule match before restart.
5. Create the DNS route for the existing tunnel, restart `cloudflared`, and prove it
   reaches `active` plus its expected connection/health journal signal.

Never create the DNS/tunnel route first and promise to add Access afterwards: that is a
real public exposure window.

## 5. Reproduce the publication gate

The publication is complete only when all of these are observed on the exact deployed
SHA:

1. local service `active` and exact-port journal banner;
2. local `/`, `/api/graph`, and `/events` probes pass;
3. tunnel configuration validates and `cloudflared` is healthy after restart;
4. a clean unauthenticated HTTPS request reaches the Access login/redirect, never a
   `200` OpenWiki page;
5. an authenticated browser reaches the hostname and renders the graph plus one
   Markdown page and one Mermaid diagram when the wiki contains one;
6. the deploy checkout's `git rev-parse HEAD` equals the recorded pushed SHA.

Return a receipt naming the URL, deployed SHA/ref, OpenWiki version, service/unit,
origin port, Access application/policy, tunnel rule, and each observed gate. Never call
an owner-observed browser pass green until the owner actually reports it.

## Updates

Regenerate OpenWiki through its own feature-branch/PR workflow first. After that change
lands, update the deployment checkout with fetch + fast-forward-only merge to the exact
approved SHA. The visualizer watches the wiki directory, but still verify its journal
reported a rebuild and reproduce `/api/graph` plus the authenticated live probe. Restart
only when the OpenWiki binary/unit changed or the watcher did not reload cleanly.

OpenWiki's inference-provider CI secret generates documentation; it does not grant host
deployment authority. Automatic post-merge deployment (webhook or self-hosted runner) is
a separate owner decision and must preserve the same exact-SHA and Access gates.

## Rollback and removal

- **Rollback content:** move the deploy checkout to a previously recorded good SHA,
  restart only if necessary, then reproduce the publication gate and record both SHAs.
- **Remove a site:** destructive and owner-confirmed. Resolve the exact service, hostname,
  DNS record, tunnel rule, Access app ownership, and deploy checkout first. Disable the
  service, remove only that hostname's route/DNS, validate/restart the tunnel, and verify
  the hostname no longer reaches an origin. Preserve shared Access policies and the shared
  tunnel unless the owner explicitly names them for removal.
