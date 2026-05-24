# T64 Live/Protocol External-Validity Report

Date: 2026-05-21

## Purpose

T64 is a key-free external-validity repair for the T63 limitation. T63 used
web/search/browser/messaging local adapters. T64 adds real I/O evidence without
requiring search or messaging provider API keys:

- `live_http_external`: real outbound HTTPS requests to public endpoints.
- `local_protocol_messaging`: real HTTP POST/GET protocol exchanges against a
  local webhook receiver with receiver-side delivery logs.

This is stronger than local adapters but still not equivalent to provider-backed
search, SaaS messaging, or deployed-agent runtime logs.

## Artifacts

| Artifact | Path |
|---|---|
| Trace builder | `build_live_protocol_tool_traces_t64.py` |
| Raw traces | `data/agent_tool_traces_live_protocol_t64_v1.jsonl` |
| Trace manifest | `analysis/agent_tool_traces_live_protocol_t64_v1_manifest.md` |
| Candidate-effect rows | `data/auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl` |
| Candidate manifest | `analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.md` |
| Qwen3-8B embeddings | `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.npy` |
| T58-style verifier evaluation | `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.md` |
| T62 validation-threshold evaluation | `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.md` |

## Data Summary

| Quantity | Value |
|---|---:|
| Raw traces | 300 |
| `live_http_external` traces | 150 |
| `local_protocol_messaging` traces | 150 |
| Candidate-effect rows | 2400 |
| Live HTTP status 200 | 120 |
| Live HTTP status 404 | 30 |

Unauthorized-effect counts:

| Effect | Unauthorized count |
|---|---:|
| `content_fetched` | 150 |
| `network_egress` | 60 |
| `message_sent` | 60 |
| `tool_error` | 60 |

The key T64 cells meet the N+ >= 30 threshold used for main-table eligibility.

## Embedding Note

The initial run used a Qwen3-8B 4-bit path because GPU 1 had insufficient free
memory. On 2026-05-22, the T64 embeddings were rerun on `CUDA_VISIBLE_DEVICES=1`
with full-precision Qwen3-8B (`use_4bit=false` in
`embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json`).
The T58/T62/T68/T69/T70 downstream reports were regenerated after this rerun.

## Validation-Selected Result

Thresholds were selected on validation trace groups and evaluated on held-out
trace groups.

| Method | Test FNR | Test FPR | Test N+ | Test N- |
|---|---:|---:|---:|---:|
| `execution_trace_sgd_auth_validation_selected` | 0.0000 | 0.0000 | 197 | 1170 |
| `static_trace_semantic_sgd_auth_validation_selected` | 0.6294 | 0.0462 | 197 | 1170 |
| `static_monitored_effect_only_sgd_auth_validation_selected` | 0.6294 | 0.0462 | 197 | 1170 |

Effect-level held-out execution-verifier results:

| Effect | Test FNR | Test FPR | Test N+ | Test N- |
|---|---:|---:|---:|---:|
| `content_fetched` | 0.0000 | 0.0000 | 91 | 89 |
| `message_sent` | 0.0000 | 0.0000 | 35 | 127 |
| `network_egress` | 0.0000 | 0.0000 | 35 | 90 |
| `tool_error` | 0.0000 | 0.0000 | 36 | 144 |

Static verifier failures are concentrated in realistic effect-presence gaps:

- misses fetched content on `http_get`, `web_extract`, and `browser_navigate`;
- misses browser-style external network egress;
- misses local-protocol receiver errors;
- over-predicts external network egress for loopback protocol calls.

## Interpretation

Facts:

- T64 directly improves over T63 on one key dimension: it includes real outbound
  HTTPS requests and real local protocol I/O, rather than only local adapters.
- The verifier-assisted monitor remains strong under validation-selected
  held-out trace groups on this dataset.
- Static tool-call rules remain brittle under live/protocol traces.

Allowed claim:

> Key-free live HTTP and local-protocol messaging traces support the
> verifier-assisted Auth-SafeInv framework beyond purely local-adapter traces;
> static effect-present rules still miss or over-predict important effects.

Disallowed claim:

> The framework has been validated on provider-backed search, SaaS messaging,
> live browser automation, or deployed-agent runtime logs.

Remaining gap:

- T64 still does not call a search provider API.
- T64 local messaging is a real protocol boundary but not Slack/Telegram/email.
- `browser_navigate` uses real external HTTP fetches with a browser-style tool
  name; it does not invoke Playwright or a browser provider.
- The strongest possible next validation remains direct provider-backed
  search/messaging or deployed-agent runtime traces.
