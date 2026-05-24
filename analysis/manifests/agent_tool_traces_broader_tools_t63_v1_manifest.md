# T63 Broader Tool Trace Manifest

- Schema version: `broader_agent_tool_traces_t63_v1`
- Traces: 300

## Toolsets

| Toolset | Count |
|---|---:|
| `browser` | 120 |
| `messaging` | 60 |
| `web` | 120 |

## Tools

| Tool | Count |
|---|---:|
| `browser_click` | 30 |
| `browser_console` | 30 |
| `browser_navigate` | 30 |
| `browser_snapshot` | 30 |
| `send_message` | 60 |
| `web_extract` | 60 |
| `web_search` | 60 |

## Verified Effects

| Effect | Count | Unauthorized Count |
|---|---:|---:|
| `content_fetched` | 120 | 60 |
| `message_sent` | 60 | 30 |
| `network_egress` | 210 | 60 |
| `tool_error` | 120 | 60 |

## Caveats

- T63 broadens tool-family coverage to web/search/browser/messaging names from real-agent-tools.
- The traces are controlled local adapters over local HTTP and fake messaging sinks, not direct external service calls.
- No browser provider, search provider, messaging credential, or external API key is required or invoked.
- Use this as broader local-adapter external-validity evidence, not live deployed-agent validation.
