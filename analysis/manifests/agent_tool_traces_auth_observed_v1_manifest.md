# Agent Tool Traces Auth Observed v1 Manifest

- Rows: 70
- Sandbox simulated: 0
- Observed execution: 70
- Static replay: 0
- Sandbox/observed gate count: 70
- Main-conference sufficient by planned gate: True
- Observed-execution sufficient: True

## Trace Type Counts

| Trace type | Count |
|---|---:|
| `observed_execution` | 70 |

## Unauthorized Effect Counts

| Effect | Count |
|---|---:|
| `command_executed` | 5 |
| `content_fetched` | 5 |
| `file_content_read` | 10 |
| `file_deleted` | 5 |
| `file_written` | 5 |
| `message_sent` | 5 |
| `tool_error` | 5 |

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