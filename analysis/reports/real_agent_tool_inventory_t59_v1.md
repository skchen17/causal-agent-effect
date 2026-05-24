# Real-Agent Tools Inventory T59

- Registered tools found statically: 74

## Execution Status Counts

| Status | Count |
|---|---:|
| `agent_loop_state_required` | 4 |
| `external_service_or_api_key_required` | 58 |
| `importable_not_executed` | 6 |
| `local_adapter_executable_missing_runtime_deps` | 3 |
| `missing_runtime_dependency` | 1 |
| `static_name_unresolved` | 2 |

## Manual Intervention / API-Key Candidates

- `AGENT_BROWSER_ENGINE`
- `AGENT_BROWSER_EXECUTABLE_PATH`
- `AUXILIARY_VIDEO_MODEL`
- `AUXILIARY_VISION_MODEL`
- `AUXILIARY_WEB_EXTRACT_MODEL`
- `BRAVE_SEARCH_API_KEY`
- `BROWSER_CDP_URL`
- `BROWSER_INACTIVITY_TIMEOUT`
- `DINGTALK_WEBHOOK_URL`
- `DISCORD_BOT_TOKEN`
- `EMAIL_ADDRESS`
- `EMAIL_PASSWORD`
- `EMAIL_SMTP_HOST`
- `EMAIL_SMTP_PORT`
- `EXA_API_KEY`
- `FAL_IMAGE_MODEL`
- `FIRECRAWL_API_KEY`
- `FIRECRAWL_API_URL`
- `HASS_TOKEN`
- `HASS_URL`
- `HERMES_EXEC_ASK`
- `HERMES_GATEWAY_SESSION`
- `HERMES_INTERACTIVE`
- `HERMES_KANBAN_CLAIM_LOCK`
- `HERMES_KANBAN_RUN_ID`
- `HERMES_KANBAN_TASK`
- `HERMES_PLATFORM`
- `HERMES_PROFILE`
- `HERMES_RPC_DIR`
- `HERMES_TENANT`
- `HERMES_TIMEZONE`
- `HERMES_VISION_DOWNLOAD_TIMEOUT`
- `LOCALAPPDATA`
- `MATRIX_ACCESS_TOKEN`
- `MATRIX_HOMESERVER`
- `MATTERMOST_TOKEN`
- `MATTERMOST_URL`
- `OPENROUTER_API_KEY`
- `PARALLEL_API_KEY`
- `PARALLEL_SEARCH_MODE`
- `PLAYWRIGHT_BROWSERS_PATH`
- `QQ_APP_ID`
- `QQ_CLIENT_SECRET`
- `SEARXNG_URL`
- `TAVILY_API_KEY`
- `TAVILY_BASE_URL`
- `TERMINAL_CWD`
- `TERMINAL_ENV`
- `TERMINAL_TIMEOUT`
- `TINKER_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_PHONE_NUMBER`
- `WANDB_API_KEY`
- `WANDB_ENTITY`
- `WEIXIN_ACCOUNT_ID`
- `WEIXIN_BASE_URL`
- `WEIXIN_CDN_BASE_URL`
- `WEIXIN_HOME_CHANNEL`
- `WEIXIN_TOKEN`

## Import Blockers

- ModuleNotFoundError: No module named 'agent'
- ModuleNotFoundError: No module named 'hermes_constants'

## Local Adapter Tools Used

- `read_file` from `hermes-agent-tools/tools/file_tools.py:1169` handler `_handle_read_file`
- `write_file` from `hermes-agent-tools/tools/file_tools.py:1170` handler `_handle_write_file`
- `terminal` from `hermes-agent-tools/tools/terminal_tool.py:2341` handler `_handle_terminal`

## Caveats

- Direct Hermes handler import is blocked for several modules because this project snapshot lacks upstream packages such as `agent` and `hermes_constants`.
- T59 local traces therefore execute handler-equivalent local adapters for file and terminal tools, grounded in real tool names, schemas, and source locations.
- External web, messaging, browser, provider, and cloud tools are not invoked without API keys or services.
