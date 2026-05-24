# Authorization Counterfactuals v1 Manifest

- Rows: 1184
- Split groups: 471
- Max split group size: 4

## Family Counts

| Family | Rows |
|---|---:|
| `same_effect_reframing` | 400 |
| `same_task_effect_substitution` | 154 |
| `same_task_tool_swap` | 210 |
| `same_tool_auth_flip` | 420 |

## Focus Effect Gates

| Effect | Authorized N | Unauthorized N | Unauth >=30 | Unauthorized tools |
|---|---:|---:|---|---|
| `file_content_read` | 202 | 30 | True | `read_file`, `terminal` |
| `file_written` | 218 | 44 | True | `terminal`, `write_file` |
| `file_deleted` | 202 | 44 | True | `delete_file`, `terminal` |
| `network_egress` | 397 | 58 | True | `terminal`, `web_extract` |
| `content_fetched` | 102 | 44 | True | `terminal`, `web_extract` |
| `message_sent` | 60 | 44 | True | `send_message`, `terminal` |
| `tool_error` | 60 | 44 | True | `web_search`, `write_file` |

## Leakage Checks

```json
{
  "missing_required_fields": {},
  "duplicate_text_count": 0,
  "duplicate_id_count": 0,
  "family_split_group_conflicts": 0,
  "rows_missing_split_group": 0
}
```

## Notes

- This is a controlled synthetic authorization-counterfactual dataset, not observed execution validation.
- split_group must be used for train/test splitting to keep counterfactual families in the same split.
- Embeddings must be regenerated after rebuilding this file because scenario_text includes authorization context.