# Agent Tool Traces Auth v2 Manifest

- Rows: 138
- Sandbox simulated: 56
- Observed execution: 70
- Static replay: 12
- Sandbox/observed gate count: 126
- Main-conference sufficient by planned gate: True
- Observed-execution sufficient: True

## Trace Type Counts

| Trace type | Count |
|---|---:|
| `observed_execution` | 70 |
| `sandbox_simulated` | 56 |
| `static_replay` | 12 |

## Unauthorized Effect Counts

| Effect | Count |
|---|---:|
| `command_executed` | 7 |
| `content_fetched` | 10 |
| `file_content_read` | 14 |
| `file_deleted` | 10 |
| `file_written` | 9 |
| `message_sent` | 10 |
| `network_egress` | 5 |
| `tool_error` | 9 |

## Leakage Checks

```json
{
  "missing_required_fields": {},
  "duplicate_id_count": 0
}
```

## Notes

- The planned gate counts sandbox_simulated + observed_execution; this artifact passes that gate.
- observed_execution rows come from a controlled local sandbox or recorded execution logs, not live deployed-agent traffic unless separately stated.
- static_replay rows are schema/call-flow grounding only and are not counted toward the sandbox/observed gate.