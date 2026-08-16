# AgentDojo Effectful Default Applicability Audit

- Status: `passed_no_effect_bearing_nonempty_defaults`
- Default-bearing effectful tool instances: `7`
- Optional fields: `22`
- Nonempty static defaults: `0`
- Dynamic defaults: `0`
- Omitted/explicit default-equivalent tools: `7/7`

## Per-Tool Results

| Tool | Optional fields | Nonempty | Equivalent |
|---|---:|---:|:---:|
| `workspace/send_email` | 3 | 0 | yes |
| `workspace/create_calendar_event` | 3 | 0 | yes |
| `workspace/reschedule_calendar_event` | 1 | 0 | yes |
| `travel/create_calendar_event` | 3 | 0 | yes |
| `travel/send_email` | 3 | 0 | yes |
| `banking/update_scheduled_transaction` | 5 | 0 | yes |
| `banking/update_user_info` | 4 | 0 | yes |

## Interpretation

The current AgentDojo effectful tool schemas exercise only empty or None defaults. They validate omitted/explicit equivalence but cannot empirically test fail-closed handling of nonempty or dynamic effect-bearing defaults.

## Claim Boundary

This is a source-hash-recorded applicability audit for AgentDojo v1.1.2. It does not establish default safety for external APIs, undocumented server defaults, callbacks, or state-dependent defaults.
