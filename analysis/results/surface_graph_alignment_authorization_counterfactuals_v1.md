# Surface Graph Alignment

- Data: `authorization_counterfactuals_v1`
- Rows: 1184
- Graph assumption: complete graph over surfaces with positive samples; edges represent available cross-surface positive pairs for representation alignment

## Effect Summary

| Effect | Verified tools | Unauthorized tools | Verified strict identifiable | Unauthorized strict identifiable | Max AuthToolProxyGap |
|---|---:|---:|---|---|---:|
| `command_executed` | 1 | 1 | False | False | 1.0 |
| `content_fetched` | 2 | 2 | False | False | 1.0 |
| `file_content_read` | 2 | 2 | False | False | 0.0 |
| `file_deleted` | 2 | 2 | False | False | 0.4828 |
| `file_written` | 2 | 2 | False | False | 1.0 |
| `memory_updated` | 0 | 0 | False | False | None |
| `message_sent` | 2 | 2 | False | False | 1.0 |
| `network_egress` | 3 | 2 | True | False | 0.6512 |
| `search_performed` | 1 | 0 | False | False | None |
| `subagent_spawned` | 0 | 0 | False | False | None |
| `tool_error` | 3 | 2 | True | False | 1.0 |

## Auth LOTO Rows With Graph Context

| Effect | Heldout tool | N unauth | Heldout FNR | Within FNR | Gap | Bound |
|---|---|---:|---:|---:|---:|---:|
| `command_executed` | `terminal` | 126 | 1.0 | 0.0 | 1.0 | 1.0 |
| `content_fetched` | `terminal` | 29 | 1.0 | 0.0 | 1.0 | 1.0 |
| `content_fetched` | `web_extract` | 15 | 0.0 | 0.0 | 0.0 | 0.0 |
| `file_content_read` | `read_file` | 15 | 0.0 | None | None | 0.0 |
| `file_content_read` | `terminal` | 15 | 0.0 | 0.0 | 0.0 | 0.0 |
| `file_deleted` | `delete_file` | 15 | 1.0 | None | None | 1.0 |
| `file_deleted` | `terminal` | 29 | 0.4828 | 0.0 | 0.4828 | 0.4828 |
| `file_written` | `terminal` | 29 | 1.0 | 0.0 | 1.0 | 1.0 |
| `file_written` | `write_file` | 15 | 1.0 | None | None | 1.0 |
| `message_sent` | `send_message` | 15 | 1.0 | None | None | 1.0 |
| `message_sent` | `terminal` | 29 | 1.0 | 0.0 | 1.0 | 1.0 |
| `network_egress` | `terminal` | 43 | 0.6512 | 0.0 | 0.6512 | 0.6512 |
| `network_egress` | `web_extract` | 15 | 0.0 | None | None | 0.0 |
| `tool_error` | `web_search` | 15 | 1.0 | None | None | 1.0 |
| `tool_error` | `write_file` | 29 | 1.0 | 0.0 | 1.0 | 0.4828 |

## Caveats

- This graph is a diagnostic of pair-holdout identifiability, not evidence that a mitigation succeeds.
- Two-surface effects are not strict-pair identifiable because holding out the only cross-surface pair removes all alignment paths.
- Unauthorized graphs can be less identifiable than verified-effect graphs when authorization violations occur on only two tools.