# Auth Trace Effect-Schema Conditioned Manifest

- Schema version: `auth_trace_effect_schema_conditioned_v1`
- Input: `data/agent_tool_traces_deepseek_api_t60_v1.jsonl`
- Traces: 8
- Rows: 64
- Conditions: `['full_tool_chain']`

## Trace Types

| Trace type | Traces | Rows | Unauthorized candidate rows |
|---|---:|---:|---:|
| `deepseek_api_observed_execution` | 8 | 64 | 8 |

## Candidate Effects

| Effect | Rows | Present | Unauthorized |
|---|---:|---:|---:|
| `command_executed` | 8 | 0 | 0 |
| `content_fetched` | 8 | 6 | 4 |
| `file_content_read` | 8 | 0 | 0 |
| `file_deleted` | 8 | 0 | 0 |
| `file_written` | 8 | 0 | 0 |
| `message_sent` | 8 | 0 | 0 |
| `network_egress` | 8 | 8 | 2 |
| `tool_error` | 8 | 2 | 2 |

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
