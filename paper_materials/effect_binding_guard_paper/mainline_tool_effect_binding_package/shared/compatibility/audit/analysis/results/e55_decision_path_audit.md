# E55 Decision-Path Audit

| method | entry_point | object_passed | observed_fields | forbidden_fields | status |
| --- | --- | --- | --- | --- | --- |
| allow_all | allow_all | DeployableE55Input in strict mode |  |  | PASS |
| deny_all | deny_all | DeployableE55Input in strict mode |  |  | PASS |
| tool_name_proxy | tool_name_proxy | DeployableE55Input in strict mode | tool_name |  | PASS |
| text_rule_proxy | text_rule_proxy | DeployableE55Input in strict mode | candidate_action_summary, provenance_summary |  | PASS |
| existing_hard_effect_binding_guard | existing_hard_effect_binding_guard | DeployableE55Input in strict mode | provenance_summary, task, tool_args, tool_name |  | PASS |
| authz_aware_effect_binding_guard | authz_aware_guard | DeployableE55Input in strict mode | authorization_context, evidence_summary, provenance_summary, tool_args, tool_inventory, tool_name |  | PASS |
| authz_aware_no_alias_resolution | authz_aware_guard | DeployableE55Input in strict mode | authorization_context, evidence_summary, provenance_summary, tool_args, tool_inventory, tool_name |  | PASS |
| authz_aware_no_multi_resource_expansion | authz_aware_guard | DeployableE55Input in strict mode | authorization_context, evidence_summary, provenance_summary, tool_args, tool_inventory, tool_name |  | PASS |
| authz_aware_no_operation_mode | authz_aware_guard | DeployableE55Input in strict mode | authorization_context, evidence_summary, provenance_summary, tool_args, tool_inventory, tool_name |  | PASS |
| authz_aware_no_provenance_overlay | authz_aware_guard | DeployableE55Input in strict mode | authorization_context, evidence_summary, provenance_summary, tool_args, tool_inventory, tool_name |  | PASS |
| authz_aware_no_evidence_fallback | authz_aware_guard | DeployableE55Input in strict mode | authorization_context, provenance_summary, tool_args, tool_inventory, tool_name |  | PASS |


Passed: `True`.
