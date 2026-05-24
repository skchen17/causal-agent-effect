# DeepSeek API Traces T60 Manifest

- Traces: 120
- Success calls: 90
- Error calls: 30
- API key env: `DEEPSEEK_API_KEY`
- API key value stored: `False`

## Effects

| Effect | Verified | Unauthorized |
|---|---:|---:|
| `content_fetched` | 90 | 60 |
| `network_egress` | 120 | 30 |
| `tool_error` | 30 | 30 |

## Caveats

- direct external provider API call, not a browser/search/messaging tool
- synthetic task contexts; no private user data is sent
- API key is read from environment and not stored in artifacts
- verified effects are inferred from API request/response status, not from provider-side logs
- DeepSeek provider-call traces cover provider API effects, not browser/search/messaging side effects.
- If all rows are API errors, inspect credentials/model availability before using the result as a method evaluation.
