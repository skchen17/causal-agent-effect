# ToolSandbox Held-Out Effect-Binding Validation

Status: `passed`.

- Frozen tools: `5`.
- Executed contexts: `32`.
- Retained execution errors: `8`.
- Typed contract/source relation agreement: `32/32`.

| Representation | Cells | Collision cells | Separating pairs | Overpartition pairs | Exact |
|---|---:|---:|---:|---:|:---:|
| common_fields | 11 | 4 | 41 | 0 | no |
| source_full_effect | 25 | 0 | 0 | 0 | yes |
| tool_name | 5 | 5 | 88 | 16 | no |
| typed_contract | 25 | 0 | 0 | 0 | yes |

## Claim Boundary

This is a pre-registered, source-hash-bound validation on five public ToolSandbox tools held out from the AgentDojo contract design. It uses AI artifact review, not independent human review, and establishes only finite-domain adequacy for the frozen calls, state variants, source oracle, and authority family.
