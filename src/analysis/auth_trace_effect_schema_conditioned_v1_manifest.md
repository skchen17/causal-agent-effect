# Auth Trace Effect-Schema Conditioned Manifest

- Schema version: `auth_trace_effect_schema_conditioned_v1`
- Input: `/data/CSK/causal-agent-safety-research/data/agent_runtime_traces_v2.jsonl`
- Traces: 24
- Rows: 192
- Conditions: `['full_tool_chain']`

## Trace Types

| Trace type | Traces | Rows | Unauthorized candidate rows |
|---|---:|---:|---:|
| `agent_runtime_execution` | 24 | 192 | 24 |

## Candidate Effects

| Effect | Rows | Present | Unauthorized |
|---|---:|---:|---:|
| `command_executed` | 24 | 12 | 12 |
| `content_fetched` | 24 | 5 | 5 |
| `file_content_read` | 24 | 9 | 0 |
| `file_deleted` | 24 | 1 | 1 |
| `file_written` | 24 | 9 | 0 |
| `message_sent` | 24 | 0 | 0 |
| `network_egress` | 24 | 9 | 3 |
| `tool_error` | 24 | 3 | 3 |

## Leakage Checks

```json
{
  "duplicate_text_count": 24,
  "exact_snakecase_effect_mentions_in_text": {},
  "label_field_mentions_in_text": {}
}
```

## Caveats

- Trace provenance is inherited from the input trace file; inspect trace_type_counts and the source trace manifest before making external-validity claims.
- candidate_effect_present is derived from trace verifier outputs and used as the execution-level present signal.
- scenario_text excludes gold verified_effects, unauthorized_effects, and effect_diff labels.
