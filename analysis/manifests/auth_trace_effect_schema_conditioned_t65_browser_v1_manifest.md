# Auth Trace Effect-Schema Conditioned Manifest

- Schema version: `auth_trace_effect_schema_conditioned_v1`
- Input: `data/agent_tool_traces_headless_browser_t65_v1.jsonl`
- Traces: 120
- Rows: 960
- Conditions: `['full_tool_chain']`

## Trace Types

| Trace type | Traces | Rows | Unauthorized candidate rows |
|---|---:|---:|---:|
| `headless_chrome_file_browser_runtime` | 120 | 960 | 90 |

## Candidate Effects

| Effect | Rows | Present | Unauthorized |
|---|---:|---:|---:|
| `command_executed` | 120 | 0 | 0 |
| `content_fetched` | 120 | 120 | 60 |
| `file_content_read` | 120 | 120 | 0 |
| `file_deleted` | 120 | 0 | 0 |
| `file_written` | 120 | 0 | 0 |
| `message_sent` | 120 | 0 | 0 |
| `network_egress` | 120 | 0 | 0 |
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

- Trace provenance is inherited from the input trace file; inspect trace_type_counts and the source trace manifest before making external-validity claims.
- candidate_effect_present is derived from trace verifier outputs and used as the execution-level present signal.
- scenario_text excludes gold verified_effects, unauthorized_effects, and effect_diff labels.
