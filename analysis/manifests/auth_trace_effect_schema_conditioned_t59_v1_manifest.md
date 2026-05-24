# Auth Trace Effect-Schema Conditioned Manifest

- Schema version: `auth_trace_effect_schema_conditioned_v1`
- Input: `data/agent_tool_traces_real_agent_tools_t59_v1.jsonl`
- Traces: 48
- Rows: 384
- Conditions: `['full_tool_chain']`

## Trace Types

| Trace type | Traces | Rows | Unauthorized candidate rows |
|---|---:|---:|---:|
| `real_agent_tools_local_execution` | 48 | 384 | 27 |

## Candidate Effects

| Effect | Rows | Present | Unauthorized |
|---|---:|---:|---:|
| `command_executed` | 48 | 30 | 6 |
| `content_fetched` | 48 | 6 | 3 |
| `file_content_read` | 48 | 12 | 3 |
| `file_deleted` | 48 | 6 | 3 |
| `file_written` | 48 | 12 | 6 |
| `message_sent` | 48 | 0 | 0 |
| `network_egress` | 48 | 6 | 0 |
| `tool_error` | 48 | 12 | 6 |

## Leakage Checks

```json
{
  "duplicate_text_count": 64,
  "exact_snakecase_effect_mentions_in_text": {},
  "label_field_mentions_in_text": {}
}
```

## Caveats

- Trace rows come from controlled observed execution, sandbox simulation, and static replay, not deployed-agent traffic.
- candidate_effect_present is derived from trace verifier outputs and used as the execution-level present signal.
- scenario_text excludes gold verified_effects, unauthorized_effects, and effect_diff labels.
