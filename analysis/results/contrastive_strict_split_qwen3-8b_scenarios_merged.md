# Contrastive Strict Leave-One-Pair-Out Split

## Two-Form Effects (Not Evaluable in Strict Setting)

These effects have only 2 surface forms. Leaving one pair out removes ALL cross-form training data.

| Effect | Forms | Worst post-FNR (full) | Effect-Avg post-FNR (full) |
|---|---:|---:|---:|
| content_fetched | terminal, web_fetch | 0.1625 | 0.0813 |
| file_content_read | read_file, terminal | 0.1062 | 0.0625 |
| file_deleted | delete_file, terminal | 0.0000 | 0.0000 |
| file_written | terminal, write_file | 0.0424 | 0.0212 |

## Three-Plus-Form Effects (Evaluable in Strict Setting)

These effects have ≥3 surface forms. Transitive alignment through intermediate forms is testable.

| Effect | Forms | Worst post-FNR (full) | Effect-Avg post-FNR (full) |
|---|---:|---:|---:|
| network_egress | send_message, terminal, web_fetch, web_search | 0.0000 | 0.0000 |
| tool_error | delegate, delete_file, read_file, send_message, terminal, web_fetch, web_search, write_file | 0.0000 | 0.0000 |