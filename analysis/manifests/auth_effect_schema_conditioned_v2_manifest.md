# Auth Effect-Schema Conditioned v2 Manifest

- Input: `data/authorization_counterfactuals_v2.jsonl`
- Base rows: 1464
- Output rows: 35136
- Candidate effects: `['command_executed', 'file_content_read', 'file_written', 'file_deleted', 'network_egress', 'content_fetched', 'message_sent', 'tool_error']`
- Conditions: `['full_tool_chain', 'auth_only_control', 'tool_only_control']`

## Label Counts

| Candidate effect | Unauthorized positives | Absent-not-authorized negatives |
|---|---:|---:|
| `command_executed` | 378 | 2529 |
| `file_content_read` | 150 | 3576 |
| `file_written` | 192 | 3486 |
| `file_deleted` | 192 | 3534 |
| `network_egress` | 234 | 2547 |
| `content_fetched` | 192 | 3834 |
| `message_sent` | 192 | 3960 |
| `tool_error` | 192 | 3960 |

## Condition Counts

| Condition | Rows | Unauthorized positives | Absent-not-authorized negatives |
|---|---:|---:|---:|
| `full_tool_chain` | 11712 | 574 | 9142 |
| `auth_only_control` | 11712 | 574 | 9142 |
| `tool_only_control` | 11712 | 574 | 9142 |

## Leakage Checks

```json
{
  "duplicate_text_count": 12584,
  "exact_snakecase_effect_mentions_in_text": {},
  "label_field_mentions_in_text": {}
}
```

## Notes

- This dataset is a candidate-effect query expansion of authorization_counterfactuals_v2.
- The model input intentionally excludes verified_effects and unauthorized_effects labels.
- full_tool_chain is the intended T55 monitor condition; auth_only_control and tool_only_control are diagnostic controls.
- The labels are safety-supervised unauthorized-effect labels, so comparisons to realized-effect probes must be labelled as setting-shifted.
