# Real Tool → Effect Mapping Audit (v2)

Hermes registered tools: 72 | Current experiment tools: 11 effects

## Current Experiment Tools vs Real Hermes Tools

| Exp Tool | Real Tool(s) | Abstract? | Possible Effects | Confidence | Limitation |
|---|---|:---:|---|---|---|
| terminal | terminal | - | command_executed, file_written, file_deleted, file_content_read | medium |  |
| read_file | read_file | - | file_content_read, tool_error | medium |  |
| write_file | write_file | - | file_written, tool_error | medium |  |
| delete_file | terminal | YES | command_executed, file_written, file_deleted, file_content_read | medium | Hermes does not register a standalone 'delete_file' tool. Fi |
| web_fetch | web_extract | YES | content_fetched, network_egress, tool_error | medium | Our experimental 'web_fetch' maps to Hermes 'web_extract'. T |
| web_search | web_search | - | search_performed, network_egress, tool_error | medium |  |
| send_message | send_message | - | message_sent, network_egress, tool_error | medium |  |
| delegate | delegate_task | YES | subagent_spawned, memory_updated, network_egress, tool_error | medium | Our experimental 'delegate' maps to Hermes 'delegate_task'.  |
| memory | memory | - | memory_updated, tool_error | medium |  |

## Key Findings

- **3 abstract tools**: delete_file (no Hermes registration → terminal), web_fetch (→ web_extract), delegate (→ delegate_task)
- **8 real Hermes tools covered** in current experimental data
- **Hermes registers 72 tools** across all toolsets
- All 11 effects have ≥2 surface forms in current data

## Limitations
- pre_state, authorization, and predicted_call_flow are heuristically constructed
- No real agent execution traces; scenarios are schema-and-semantic proxy calls