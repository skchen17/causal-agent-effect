# E79 ToolSandbox Frozen Offline Subset

Subset: `toolsandbox_offline_feasibility_v1`; selected 30 of 91 offline-eligible base scenarios.

Selection hash: `78aee4120ca3616f978d9f8c9953cae84f3ccea622a8ffa3f49671ffa2fc77d0`.

| Scenario | Milestones | Tools | Strata |
|---|---:|---:|---|
| `find_days_till_holiday` | 4 | 4 | canonicalization, multi_tool_high_milestone |
| `find_days_till_holiday_alt` | 4 | 4 | canonicalization, multi_tool_high_milestone |
| `find_days_till_holiday_multiple_user_turn` | 4 | 4 | canonicalization, multi_tool_high_milestone |
| `find_days_till_holiday_wifi_off` | 5 | 6 | state_dependency, canonicalization, multi_tool_high_milestone |
| `find_days_till_holiday_wifi_off_alt` | 5 | 6 | state_dependency, canonicalization, multi_tool_high_milestone |
| `find_days_till_holiday_wifi_off_multiple_user_turn` | 5 | 6 | state_dependency, canonicalization, multi_tool_high_milestone |
| `modify_contact_with_message_recency` | 5 | 5 | canonicalization, multi_tool_high_milestone |
| `modify_contact_with_message_recency_alt` | 5 | 5 | canonicalization, multi_tool_high_milestone |
| `modify_contact_with_message_recency_insufficient_information` | 0 | 4 | insufficient_information |
| `modify_contact_with_message_recency_insufficient_information_alt` | 0 | 4 | insufficient_information |
| `modify_contact_with_message_recency_multiple_user_turn` | 5 | 5 | canonicalization, multi_tool_high_milestone |
| `modify_contact_with_message_recency_multiple_user_turn_alt` | 5 | 5 | canonicalization, multi_tool_high_milestone |
| `modify_reminder_with_recency_latest` | 3 | 6 | multi_tool_high_milestone |
| `modify_reminder_with_recency_latest_alt` | 3 | 6 | multi_tool_high_milestone |
| `modify_reminder_with_recency_latest_insufficient_information` | 0 | 5 | insufficient_information |
| `remove_contact_by_phone_no_remove_contact_insufficient_information` | 1 | 2 | insufficient_information |
| `remove_contact_by_phone_no_remove_contact_insufficient_information_alt` | 1 | 2 | insufficient_information |
| `remove_reminder_with_recency_latest` | 3 | 6 | multi_tool_high_milestone |
| `remove_reminder_with_recency_latest_alt` | 3 | 6 | multi_tool_high_milestone |
| `remove_reminder_with_recency_latest_insufficient_information` | 0 | 5 | insufficient_information |
| `search_reminder_with_creation_recency_yesterday` | 3 | 5 | multi_tool_high_milestone |
| `search_reminder_with_creation_recency_yesterday_implicit` | 3 | 5 | multi_tool_high_milestone |
| `search_reminder_with_recency_upcoming` | 3 | 5 | multi_tool_high_milestone |
| `search_reminder_with_recency_upcoming_implicit` | 3 | 5 | multi_tool_high_milestone |
| `search_reminder_with_recency_yesterday` | 3 | 5 | multi_tool_high_milestone |
| `send_message_with_contact_content_cellular_off` | 4 | 5 | state_dependency, multi_tool_high_milestone |
| `send_message_with_contact_content_cellular_off_alt` | 4 | 5 | state_dependency, multi_tool_high_milestone |
| `send_message_with_contact_content_cellular_off_multiple_user_turn` | 4 | 5 | state_dependency, multi_tool_high_milestone |
| `send_message_with_contact_content_cellular_off_multiple_user_turn_alt` | 4 | 5 | state_dependency, multi_tool_high_milestone |
| `update_contact_relationship_with_relationship_twice_multiple_user_turn` | 5 | 3 | multi_tool_high_milestone |

## Claim Boundary

This is a frozen 30-scenario offline adapter subset. ToolSandbox has at most five milestones in the selected tasks, so it tests stateful compositional utility but does not by itself establish 20+ call horizon behavior.
