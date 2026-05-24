# Auth Trace Effect-Schema Conditioned Manifest

- Schema version: `auth_trace_effect_schema_conditioned_v1`
- Input: `data/agent_tool_traces_deepseek_api_t61_v1.jsonl`
- Traces: 120
- Rows: 960
- Conditions: `['full_tool_chain']`

## Trace Types

| Trace type | Traces | Rows | Unauthorized candidate rows |
|---|---:|---:|---:|
| `deepseek_api_observed_execution` | 120 | 960 | 120 |

## Candidate Effects

| Effect | Rows | Present | Unauthorized |
|---|---:|---:|---:|
| `command_executed` | 120 | 0 | 0 |
| `content_fetched` | 120 | 90 | 60 |
| `file_content_read` | 120 | 0 | 0 |
| `file_deleted` | 120 | 0 | 0 |
| `file_written` | 120 | 0 | 0 |
| `message_sent` | 120 | 0 | 0 |
| `network_egress` | 120 | 120 | 30 |
| `tool_error` | 120 | 30 | 30 |

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
