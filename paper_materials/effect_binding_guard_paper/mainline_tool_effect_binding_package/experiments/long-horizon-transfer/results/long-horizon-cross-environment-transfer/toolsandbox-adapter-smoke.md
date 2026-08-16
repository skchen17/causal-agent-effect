# E79 ToolSandbox Native Adapter Smoke

Status: `passed`.

Implementation-readiness evidence only: two frozen native ToolSandbox scenarios, their local tools, exact precommit mediation, and native evaluation.

## Native Replay

| Scenario | Native calls | Effect calls | Milestones | Minefields | Similarity |
|---|---:|---:|---:|---:|---:|
| `modify_contact_with_message_recency` | 5 | 1 | 5 | 0 | 1.0 |
| `send_message_with_contact_content_cellular_off` | 4 | 2 | 4 | 0 | 1.0 |

The native ToolSandbox milestone and minefield evaluator was invoked for each replay. Both selected scenarios have empty native minefield sets, so the zero minefield score does not test positive minefield detection.

## Tool Evidence

| Tool | Class | Defaults | Unsupported schema fields | Mutation path |
|---|---|---|---|---|
| `end_conversation` | `effectful` | none | none | `end_conversation -> update_database` |
| `get_cellular_service_status` | `read_only` | none | none | `none` |
| `get_current_timestamp` | `read_only` | none | none | `none` |
| `modify_contact` | `effectful` | name, phone_number, relationship, is_self | none | `modify_contact -> add_to_database` |
| `search_contacts` | `read_only` | person_id, name, phone_number, relationship, is_self | none | `none` |
| `search_messages` | `read_only` | message_id, sender_person_id, sender_phone_number, recipient_person_id, recipient_phone_number, content, creation_timestamp_lowerbound, creation_timestamp_upperbound | none | `none` |
| `send_message_with_phone_number` | `effectful` | none | none | `send_message_with_phone_number -> add_to_database` |
| `set_cellular_service_status` | `effectful` | none | none | `set_cellular_service_status -> set_boolean_settings -> update_database` |

Classification is derived from native implementation call paths to ToolSandbox database mutation primitives, not from tool names. Field coverage is checked against native ToolSandbox schemas and Python signatures.

## Complete Mediation

- Effectful native calls: `3`.
- Exact precommit records: `3`.
- Signature multiset exact match: `True`.
- Missing/extra precommits: `0`/`0`.
- Rejected before native execution: `2` (one omitted-default call and one unknown-field call).

## Controls

The replay made no LLM or user-simulator calls. Socket connections were disabled, and the selected native tools do not include ToolSandbox external-search tools.

## Claim Boundary

Implementation-readiness evidence only: two frozen native ToolSandbox scenarios, their local tools, exact precommit mediation, and native evaluation.

This smoke does not establish:

- victim-model security or prompt-injection robustness.
- guard effectiveness, authorization soundness, or production complete mediation.
- positive minefield detection because both bounded scenarios have zero native minefields.
- coverage of the remaining 28 frozen scenarios or 20-plus-call horizons.
- remote-service, concurrent-executor, or post-check mutation integrity.
