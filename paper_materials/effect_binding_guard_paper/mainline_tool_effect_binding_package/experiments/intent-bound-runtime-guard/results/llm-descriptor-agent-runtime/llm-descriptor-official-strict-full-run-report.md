# E76 Strict Official AgentDojo Full-Run Report

- Status: `passed`
- Official keys: `726/726`
- Agent output cap: `4096` tokens per model call
- Context: `65,536` tokens for the full run; six context-overflow cases were cleanly rerun at `131,072` tokens
- Registered side-effect tools: `21/24`
- Attack success: `10/629 = 0.016`
- Benign utility: `34/97 = 0.351`
- Attack-task utility: `207/629 = 0.329`
- Task-plan parse valid: `642/642`
- Precommit decisions: `{"ALLOW": 2271, "ALLOW_EXPLICIT_OVERRIDE": 142, "NEEDS_REPLAN": 1103}`
- Descriptor sources: `{"llm_counterfactual_registered": 541, "read_only_schema_descriptor": 2085, "unregistered_fail_closed": 890}`
- Runtime LLM calls after plan/registration: `0`
- Model commands clean: `true`
- Final imported post-tool empty responses: `0`

## Unregistered Tools

`create_calendar_event`, `invite_user_to_slack`, `update_password`

## Claim Boundary

The run evaluates local-LLM-generated, counterfactually registered tool-effect descriptors in the official AgentDojo v1.1.2 726-key protocol. Unregistered side-effect tools fail closed and cannot be overridden by repeating a call. Read-only tools do not require effect-descriptor registration. The result is a sandbox benchmark evaluation, not a production-safety or deployed-agent guarantee.
