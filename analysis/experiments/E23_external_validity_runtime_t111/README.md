# E23 External-Validity Runtime Proxy T111

## Experiment Purpose

T110 left one important gap: on simple local cases, `no_shadow_prefix_guard_only` and a handcrafted resource-aware boundary matched the full future-constrained pipeline. T111 creates a harder local runtime/protocol proxy to test whether trace locking and safe substitution add value beyond broad effect/resource guards.

The experiment uses six same-resource drift families:

- same provider host but dry-run endpoint changes to commit endpoint;
- same webhook endpoint sends a secret-bearing payload;
- same file path receives unsafe content;
- same browser origin submits hidden sensitive fields;
- same download host follows an external redirect or injected instruction;
- same local resources use a changed command template.

Each family has faithful dynamic-value substitutions and drift variants.

## Main Conclusion

T111 supports this limited mechanism claim:

> In constructed complex local runtime cases, shadow trace locking with safe substitution blocks same-resource drift that broad effect/resource, effect-only, and tool-only guards all miss.

Key counts from `analysis/results/external_validity_runtime_t111_v1.md`:

- `full_shadow_trace_locked`: unauthorized commit `0/300`, false denial `0/300`.
- `exact_trace_lock_no_substitution`: unauthorized commit `0/300`, but false denial `300/300`.
- `effect_resource_prefix_guard`: unauthorized commit `300/300`.
- `effect_only_guard`: unauthorized commit `300/300`.
- `tool_whitelist_only`: unauthorized commit `300/300`.
- `no_staging_posthoc_trace_check`: unauthorized commit `300/300` and unsafe-before-block `300/300`.

The local runtime generated 2,200 local HTTP requests across committed network/browser/webhook/download boundaries.

## Key Artifacts

- Script: `src/auth/external_validity_runtime_t111.py`
- Case data: `data/external_validity_runtime_t111_cases_v1.jsonl`
- Policy rows: `data/external_validity_runtime_t111_v1.jsonl`
- Machine-readable result: `analysis/results/external_validity_runtime_t111_v1.json`
- Readable report: `analysis/results/external_validity_runtime_t111_v1.md`

## Paper Claims Supported

- Trace-locked replay can express endpoint, payload schema, redirect-chain, form-field, content-schema, and command-template constraints that broad effect/resource guards miss.
- Safe substitution is necessary: exact trace locking without substitution over-denies all faithful dynamic-value cases.
- Post-hoc detection without staging is too late in these cases because the local commit boundary has already been crossed.

## Claims Not Supported

- This is not provider-backed search, SaaS messaging/email, real HTTP browser automation, or deployed-agent runtime validation.
- This is a constructed mechanism stress test, not a learned verifier or arbitrary natural-language compiler evaluation.
- It does not prove superiority over a stronger handcrafted guard that also checks exact endpoint, payload schema, redirect chain, form schema, and command template.
- It should be written as complex local external-validity evidence, not as deployment safety certification.
