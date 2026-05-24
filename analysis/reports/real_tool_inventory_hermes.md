# Hermes Agent Tool Inventory

Extracted 72 tools | 56 OK | 16 unresolved
37 with required args | 52 with properties

## Core Tools

| Tool Name | Toolset | Required Args | Handler | Gated | Status |
|---|---|---|---|:---:|:---:|
| browser_cdp | browser-cdp |  | None | ✓ | unresolved_schema_var |
| browser_dialog | browser-cdp |  | None | ✓ | unresolved_schema_var |
| browser_navigate | browser |  | None | ✓ | no_schema |
| browser_snapshot | browser |  | None | ✓ | no_schema |
| browser_click | browser |  | None | ✓ | no_schema |
| browser_type | browser |  | None | ✓ | no_schema |
| browser_scroll | browser |  | None | ✓ | no_schema |
| browser_back | browser |  | None | ✓ | no_schema |
| browser_press | browser |  | None | ✓ | no_schema |
| browser_get_images | browser |  | None | ✓ | no_schema |
| browser_vision | browser |  | None | ✓ | no_schema |
| browser_console | browser |  | None | ✓ | no_schema |
| clarify | clarify | question | None | ✓ | ok |
| execute_code | code_execution |  | None | ✓ | unresolved_schema_var |
| computer_use | computer_use |  | None | ✓ | unresolved_schema_var |
| cronjob | cronjob | action | None | ✓ | ok |
| delegate_task | delegation |  | None | ✓ | ok |
| discord | discord |  | None | ✓ | unresolved_schema_var |
| discord_admin | discord_admin |  | None | ✓ | unresolved_schema_var |
| feishu_doc_read | feishu_doc | doc_token | _handle_feishu_doc_read | ✓ | ok |
| feishu_drive_list_comments | feishu_drive | file_token | _handle_list_comments | ✓ | ok |
| feishu_drive_list_comment_replies | feishu_drive | file_token, comment_id | _handle_list_replies | ✓ | ok |
| feishu_drive_reply_comment | feishu_drive | file_token, comment_id, content | _handle_reply_comment | ✓ | ok |
| feishu_drive_add_comment | feishu_drive | file_token, content | _handle_add_comment | ✓ | ok |
| read_file | file | path | _handle_read_file | ✓ | ok |
| write_file | file | path, content | _handle_write_file | ✓ | ok |
| patch | file | mode | _handle_patch | ✓ | ok |
| search_files | file | pattern | _handle_search_files | ✓ | ok |
| ha_list_entities | homeassistant |  | _handle_list_entities | ✓ | ok |
| ha_get_state | homeassistant | entity_id | _handle_get_state | ✓ | ok |
| ha_list_services | homeassistant |  | _handle_list_services | ✓ | ok |
| ha_call_service | homeassistant | domain, service | _handle_call_service | ✓ | ok |
| image_generate | image_gen | prompt | _handle_image_generate | ✓ | ok |
| kanban_show | kanban |  | _handle_show | ✓ | ok |
| kanban_list | kanban |  | _handle_list | ✓ | ok |
| kanban_complete | kanban |  | _handle_complete | ✓ | ok |
| kanban_block | kanban | reason | _handle_block | ✓ | ok |
| kanban_heartbeat | kanban |  | _handle_heartbeat | ✓ | ok |
| kanban_comment | kanban | task_id, body | _handle_comment | ✓ | ok |
| kanban_create | kanban | title, assignee | _handle_create | ✓ | ok |
| kanban_unblock | kanban | task_id | _handle_unblock | ✓ | ok |
| kanban_link | kanban | parent_id, child_id | _handle_link | ✓ | ok |
| memory | memory | action, target | None | ✓ | ok |
| mixture_of_agents | moa | user_prompt | None | ✓ | ok |
| process | terminal | action | _handle_process | - | ok |
| rl_list_environments | rl |  | None | ✓ | ok |
| rl_select_environment | rl | name | None | ✓ | ok |
| rl_get_current_config | rl |  | None | ✓ | ok |
| rl_edit_config | rl | field, value | None | ✓ | ok |
| rl_start_training | rl |  | None | ✓ | ok |
| rl_check_status | rl | run_id | None | ✓ | ok |
| rl_stop_training | rl | run_id | None | ✓ | ok |
| rl_get_results | rl | run_id | None | ✓ | ok |
| rl_list_runs | rl |  | None | ✓ | ok |
| rl_test_inference | rl |  | None | ✓ | ok |
| send_message | messaging |  | send_message_tool | ✓ | ok |
| session_search | session_search |  | None | ✓ | ok |
| skill_manage | skills | action, name | None | - | ok |
| skills_list | skills |  | None | ✓ | ok |
| skill_view | skills | name | _skill_view_with_bump | ✓ | ok |
| terminal | terminal | command | _handle_terminal | ✓ | ok |
| todo | todo |  | None | ✓ | ok |
| text_to_speech | tts | text | None | ✓ | ok |
| vision_analyze | vision | image_url, question | _handle_vision_analyze | ✓ | ok |
| video_analyze | video | video_url, question | _handle_video_analyze | ✓ | ok |
| web_search | web | query | None | ✓ | ok |
| web_extract | web | urls | None | ✓ | ok |
| yb_query_group_info | _TOOLSET | group_code | _handle_yb_query_group_info | ✓ | ok |
| yb_query_group_members | _TOOLSET | group_code, action | _handle_yb_query_group_members | ✓ | ok |
| yb_send_dm | _TOOLSET |  | _handle_yb_send_dm | ✓ | ok |
| yb_search_sticker | _TOOLSET |  | _handle_yb_search_sticker | ✓ | ok |
| yb_send_sticker | _TOOLSET |  | _handle_yb_send_sticker | ✓ | ok |

## Tools with Missing Schemas

- **browser_cdp**: unresolved_schema_var — Schema variable 'BROWSER_CDP_SCHEMA' not found in module-level dicts
- **browser_dialog**: unresolved_schema_var — Schema variable 'BROWSER_DIALOG_SCHEMA' not found in module-level dicts
- **browser_navigate**: no_schema — No schema argument in register call
- **browser_snapshot**: no_schema — No schema argument in register call
- **browser_click**: no_schema — No schema argument in register call
- **browser_type**: no_schema — No schema argument in register call
- **browser_scroll**: no_schema — No schema argument in register call
- **browser_back**: no_schema — No schema argument in register call
- **browser_press**: no_schema — No schema argument in register call
- **browser_get_images**: no_schema — No schema argument in register call
- **browser_vision**: no_schema — No schema argument in register call
- **browser_console**: no_schema — No schema argument in register call
- **execute_code**: unresolved_schema_var — Schema variable 'EXECUTE_CODE_SCHEMA' not found in module-level dicts
- **computer_use**: unresolved_schema_var — Schema variable 'COMPUTER_USE_SCHEMA' not found in module-level dicts
- **discord**: unresolved_schema_var — Schema variable '_STATIC_CORE_SCHEMA' not found in module-level dicts
- **discord_admin**: unresolved_schema_var — Schema variable '_STATIC_ADMIN_SCHEMA' not found in module-level dicts