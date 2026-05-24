# Authorization Counterfactuals v2 Manifest

- Rows: 1464
- Base rows from v1: 1184
- Rows added: 280
- Split groups: 611

## Family Counts

| Family | Rows |
|---|---:|
| `same_effect_reframing` | 400 |
| `same_task_effect_substitution` | 154 |
| `same_task_tool_swap` | 210 |
| `same_tool_auth_flip` | 420 |
| `surface_graph_expansion_auth_flip` | 280 |

## Focus Surface Graph Gates

| Effect | Verified tools | Unauthorized tools | Unauthorized tools >=3 |
|---|---:|---:|---|
| `file_content_read` | 3 | 3 | True |
| `file_written` | 3 | 3 | True |
| `file_deleted` | 3 | 3 | True |
| `network_egress` | 5 | 3 | True |
| `content_fetched` | 3 | 3 | True |
| `message_sent` | 3 | 3 | True |
| `tool_error` | 3 | 3 | True |

## Added Surface Counts

| Tool | Rows |
|---|---:|
| `http_get` | 80 |
| `http_post` | 40 |
| `python_repl` | 120 |
| `web_extract` | 40 |

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

- v2 appends targeted synthetic alternate surfaces to v1; it does not overwrite v1 artifacts.
- The expansion is intended to test whether strict train-only projection failures are driven by sparse surface graph connectivity.
- Embeddings must be generated as qwen3-8b_authorization_counterfactuals_v2 before running Auth-SafeInv or mitigation comparisons on v2.
