# T65 Headless Chrome Browser-Runtime Trace Manifest

- Traces: 120
- Chrome binary: `/usr/bin/google-chrome`
- Trace types: headless_chrome_file_browser_runtime
- Tools: browser_navigate, browser_snapshot

## Verified Effect Counts

| Effect | Count |
|---|---:|
| `content_fetched` | 120 |
| `file_content_read` | 120 |
| `memory_updated` | 30 |
| `tool_error` | 30 |

## Unauthorized Effect Counts

| Effect | Count |
|---|---:|
| `content_fetched` | 60 |
| `memory_updated` | 30 |
| `tool_error` | 30 |

## Limitations

- Uses actual headless Chrome process execution over file-backed pages.
- Does not use browser HTTP networking, provider-backed search, SaaS messaging, Playwright, Selenium, or deployed-agent runtime handlers.
- Completes only the file-backed browser-runtime part of T65; provider-backed search/SaaS/deployed-runtime remains open.
