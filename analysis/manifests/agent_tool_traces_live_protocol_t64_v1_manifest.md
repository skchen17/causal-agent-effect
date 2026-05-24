# T64 Live/Protocol Trace Manifest

- Schema version: `agent_tool_traces_live_protocol_t64_v1`
- Traces: 300

## Trace Families

| Trace family | Count | Evidence level |
|---|---:|---|
| `live_http_external` | 150 | real outbound HTTPS requests to public endpoints, no search-provider API key |
| `local_protocol_messaging` | 150 | real local HTTP protocol receiver and delivery logs, not SaaS/provider messaging |

## Tools

| Tool | Count |
|---|---:|
| `browser_navigate` | 30 |
| `http_get` | 90 |
| `http_post` | 30 |
| `send_message` | 90 |
| `web_extract` | 60 |

## Verified Effects

| Effect | Count | Unauthorized Count |
|---|---:|---:|
| `content_fetched` | 150 | 150 |
| `message_sent` | 90 | 60 |
| `network_egress` | 150 | 60 |
| `tool_error` | 60 | 60 |

## Live HTTP Status Counts

```json
{
  "200": 120,
  "404": 30
}
```

## Caveats

- T64a validates key-free live HTTP/browser-style I/O, not provider-backed web search.
- T64b validates local protocol messaging boundaries, not Slack/Telegram/Gmail-style SaaS messaging.
- Rows are execution traces from this harness, not deployed-agent runtime logs.
- browser_navigate rows use real external HTTP fetches with browser-style tool names; no Playwright/browser provider is invoked.
