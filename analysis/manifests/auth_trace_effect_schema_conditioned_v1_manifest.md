# Auth Trace Effect-Schema Conditioned Manifest

- Schema version: `auth_trace_effect_schema_conditioned_v1`
- Input: `data/agent_tool_traces_auth_v2.jsonl`
- Traces: 138
- Rows: 1104
- Conditions: `['full_tool_chain']`

## Trace Types

| Trace type | Traces | Rows | Unauthorized candidate rows |
|---|---:|---:|---:|
| `observed_execution` | 70 | 560 | 40 |
| `sandbox_simulated` | 56 | 448 | 28 |
| `static_replay` | 12 | 96 | 6 |

## Candidate Effects

| Effect | Rows | Present | Unauthorized |
|---|---:|---:|---:|
| `command_executed` | 138 | 14 | 7 |
| `content_fetched` | 138 | 20 | 10 |
| `file_content_read` | 138 | 31 | 14 |
| `file_deleted` | 138 | 20 | 10 |
| `file_written` | 138 | 19 | 9 |
| `message_sent` | 138 | 20 | 10 |
| `network_egress` | 138 | 31 | 5 |
| `tool_error` | 138 | 19 | 9 |

## Leakage Checks

```json
{
  "duplicate_text_count": 0,
  "exact_snakecase_effect_mentions_in_text": {},
  "label_field_mentions_in_text": {}
}
```

## Caveats

- Trace rows come from controlled observed execution, sandbox simulation, and static replay, not deployed-agent traffic.
- candidate_effect_present is derived from trace verifier outputs and used as the execution-level present signal.
- scenario_text excludes gold verified_effects, unauthorized_effects, and effect_diff labels.
