# Agent Tool Traces Auth v1 Manifest

- Rows: 68
- Sandbox simulated: 56
- Observed execution: 0
- Static replay: 12
- Sandbox/observed gate count: 56
- Main-conference sufficient by planned gate: True
- Observed-execution sufficient: False

## Trace Type Counts

| Trace type | Count |
|---|---:|
| `sandbox_simulated` | 56 |
| `static_replay` | 12 |

## Unauthorized Effect Counts

| Effect | Count |
|---|---:|
| `command_executed` | 2 |
| `content_fetched` | 5 |
| `file_content_read` | 4 |
| `file_deleted` | 5 |
| `file_written` | 4 |
| `message_sent` | 5 |
| `network_egress` | 5 |
| `tool_error` | 4 |

## Leakage Checks

```json
{
  "missing_required_fields": {},
  "duplicate_id_count": 0
}
```

## Notes

- The planned gate counts sandbox_simulated + observed_execution; this artifact passes that gate.
- observed_execution_count is 0, so this is still not real deployed-agent execution validation.
- static_replay rows are schema/call-flow grounding only and are not counted toward the sandbox/observed gate.