# Auth Trace Effect-Schema Conditioned Manifest

- Schema version: `auth_trace_effect_schema_conditioned_v1`
- Input: `data/agent_tool_traces_broader_tools_t63_v1.jsonl`
- Traces: 300
- Rows: 2400
- Conditions: `['full_tool_chain']`

## Trace Types

| Trace type | Traces | Rows | Unauthorized candidate rows |
|---|---:|---:|---:|
| `real_agent_tools_broader_local_adapter` | 300 | 2400 | 210 |

## Candidate Effects

| Effect | Rows | Present | Unauthorized |
|---|---:|---:|---:|
| `command_executed` | 300 | 0 | 0 |
| `content_fetched` | 300 | 120 | 60 |
| `file_content_read` | 300 | 0 | 0 |
| `file_deleted` | 300 | 0 | 0 |
| `file_written` | 300 | 0 | 0 |
| `message_sent` | 300 | 60 | 30 |
| `network_egress` | 300 | 210 | 60 |
| `tool_error` | 300 | 120 | 60 |

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
