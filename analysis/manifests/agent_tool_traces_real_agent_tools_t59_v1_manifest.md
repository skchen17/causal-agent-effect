# Real-Agent Tool Traces T59 Manifest

- Traces: 48

## Tools

| Tool | Traces |
|---|---:|
| `read_file` | 12 |
| `terminal` | 30 |
| `write_file` | 6 |

## Effects

| Effect | Verified | Unauthorized |
|---|---:|---:|
| `command_executed` | 30 | 6 |
| `content_fetched` | 6 | 3 |
| `file_content_read` | 12 | 3 |
| `file_deleted` | 6 | 3 |
| `file_written` | 12 | 6 |
| `network_egress` | 6 | 0 |
| `tool_error` | 12 | 6 |

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

## Caveats

- These traces are grounded in real-agent-tools Hermes tool names and source registrations.
- They use local handler-equivalent adapters because direct Hermes handler import is blocked by missing upstream packages in this project snapshot.
- No real external API keys, messaging platforms, browser providers, or cloud sandboxes were invoked.
