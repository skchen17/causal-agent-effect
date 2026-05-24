# Contrastive Multiseed Results

- Model: `qwen3-8b`
- Data: `qwen3-8b_scenarios_mainconf_v1`
- Seeds: `[0, 1, 2, 3, 4]`
- Projection dim: `128`

| Effect | Tool | Post-FNR mean | Post-FNR std |
|---|---:|---:|---:|
| content_fetched | terminal | 0.0000 | 0.0000 |
| content_fetched | web_fetch | 0.0000 | 0.0000 |
| file_content_read | read_file | 0.0000 | 0.0000 |
| file_content_read | terminal | 0.0179 | 0.0174 |
| file_deleted | delete_file | 0.0000 | 0.0000 |
| file_deleted | terminal | 0.0194 | 0.0158 |
| file_written | terminal | 0.0143 | 0.0190 |
| file_written | write_file | 0.0000 | 0.0000 |
| network_egress | send_message | 0.0000 | 0.0000 |
| network_egress | terminal | 0.0038 | 0.0077 |
| network_egress | web_fetch | 0.0000 | 0.0000 |
| network_egress | web_search | 0.0000 | 0.0000 |
| tool_error | delegate | 0.0000 | 0.0000 |
| tool_error | delete_file | 0.0000 | 0.0000 |
| tool_error | read_file | 0.0000 | 0.0000 |
| tool_error | send_message | 0.0000 | 0.0000 |
| tool_error | terminal | 0.0000 | 0.0000 |
| tool_error | web_fetch | 0.0000 | 0.0000 |
| tool_error | web_search | 0.0000 | 0.0000 |
| tool_error | write_file | 0.0000 | 0.0000 |