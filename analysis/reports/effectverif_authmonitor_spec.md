# EffectVerif-AuthMonitor Spec

> Date: 2026-05-21  
> Task: T67  
> Purpose: define the verifier-assisted method interface clearly enough for paper writing and later implementation.

## Method Object

`EffectVerif-AuthMonitor` separates realized-effect verification from authorization checking.

```text
Inputs:
  c: task context
  A(c): authorized effect envelope
  a: tool call
  S: surface form / tool surface
  x: arguments
  t: execution, protocol, or structured trace

Effect verifier:
  Omega_hat = VerifyEffects(a, S, x, t)

Authorization checker:
  U_hat = Omega_hat \ A(c)

Decision:
  DENY if U_hat is non-empty
  ALLOW otherwise
```

## Required Trace Fields

Minimal common fields:

- `trace_id`
- `task_context`
- `authorized_effects`
- `tool_call.name`
- `arguments`
- `surface_form`
- `execution_status`
- `trace_family`

Evidence fields, depending on tool family:

- `file_diff`
- `http_request`
- `http_response`
- `stdout`
- `stderr`
- `exit_code`
- `provider_status`
- `message_receipt`
- `network_endpoint`

Label fields that must be hidden in independence ablations:

- `effect_name`
- `event_type`
- `policy_decision`
- `verified_effects`
- `unauthorized_effects`
- any direct `candidate_effect_present` label

## Failure Modes to Test

1. Safe-looking tool name, but trace shows network egress.
2. Legitimate call reason, but execution creates an extra side effect.
3. Shell command and API tool produce equivalent effect.
4. Provider API reports success, but static local rules cannot infer remote effect.
5. Partial failure still produces a partial side effect.

## Required Metrics

Candidate-effect metrics remain useful:

- unauthorized-effect FNR
- authorized/absent-effect FPR
- macro effect FNR/FPR

Action-level metrics must be added:

- Unauthorized Action Allow Rate
- Authorized Action False Denial Rate
- per-tool-family allow/deny breakdown

## Claim Boundary

Allowed claim:

> Execution or protocol evidence can reduce unauthorized-effect misses in the tested controlled/API/protocol trace settings.

Not allowed:

> The framework certifies deployed agent safety.

Not yet supported:

> Minimal raw traces are sufficient.

That requires the planned full / label-hidden / minimal-evidence ablation.
