# E76 LLM Descriptor Registration Report

- Status: `passed`
- AgentDojo version: `v1.1.2`
- Tool views: `24`
- Descriptor candidates: `30`
- Registered tools: `21/24`
- Unregistered tools: `3/24`

## Registered Tools

`add_calendar_event_participants`, `add_user_to_channel`, `append_to_file`, `cancel_calendar_event`, `create_file`, `delete_email`, `delete_file`, `post_webpage`, `remove_user_from_slack`, `reschedule_calendar_event`, `reserve_car_rental`, `reserve_hotel`, `reserve_restaurant`, `schedule_transaction`, `send_channel_message`, `send_direct_message`, `send_email`, `send_money`, `share_file`, `update_scheduled_transaction`, `update_user_info`

## Unregistered Tools

`create_calendar_event`, `invite_user_to_slack`, `update_password`

## Claim Boundary

E76 uses a local LLM only for offline effect recognition and atom descriptor generation. Counterfactual field checks register only descriptors whose tool parameters are either atom-bound or explicitly non-security. Runtime AgentDojo execution must load only the registered descriptor JSONL; unregistered side-effect tools fail closed. This is not a production-safety claim.
