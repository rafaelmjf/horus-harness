---
status: open
priority: medium
readiness: shaping
readiness_reason: "Needs an attended owner envelope and bounded probe design before any remote-model execution."
tier: medium
created: 2026-07-16
last_refined: 2026-07-19
vision_facet: "Delegation calibration"
type: feature
parallel: safe
surface: remote Tailscale model host, disposable probe workspace, model datums/adapters only after evidence
---

# Probe smaller open-source workers on a remote Tailscale machine

The owner has open-source models installed on another machine in the private Tailscale
network and wants to learn which low-risk work can be outsourced to them. Claude/Codex
remain the default for important work; this is a measured capability probe, not a new
router or a presumption that a Horus provider integration is worthwhile.

## Acceptance

- Discover the existing runner, protocol, installed model identities, and usable
  context limits without assuming Ollama, llama.cpp, vLLM, or an OpenAI-compatible API.
  Keep host addresses, credentials, and other machine-local details out of git.
- Prove tailnet-only reachability and authentication without opening a public listener,
  changing remote services, or installing/upgrading software.
- Exercise a small synthetic/public fixture across bounded task shapes such as a
  mechanical edit, focused test generation, and documentation extraction, each with a
  deterministic gate and explicit stopping point.
- Record actual model identity, wall time, delivered artifact, gate outcome, corrections,
  and supervisor overhead. Do not estimate provider-style usage percentages or rerun a
  paid model solely to manufacture a comparison.
- Conclude per model: unsuitable, mechanical-only candidate, or scoped-implementation
  candidate, with the required verification depth and evidence limitations.
- Propose an adapter, roster/datum representation, or reusable remote-worker surface
  only as a separate owner-approved follow-up when the probe shows a positive dividend.

## Boundaries

- Card creation does not authorize connecting to the remote machine. Present the exact
  host/model/task/data envelope and obtain owner approval before the probe.
- Do not send repository secrets, credentials, or private source during the first probe;
  use disposable synthetic/public inputs. Important, ambiguous, security-sensitive, and
  final verification work remains on Claude/Codex unless later evidence changes policy.
- No automatic routing, daemon, scheduler, public exposure, or Horus control plane.
