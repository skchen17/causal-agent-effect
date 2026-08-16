# Registered-Relation Onboarding Gap Audit

- Exact source/target/field groups: `14`
- Groups observed in recovered cases: `2`
- Groups observed in failed cases: `12`
- Runtime-relation failure cases: `7`
- Plan-construction failure cases: `4`

| Source | Target field | Cases | Recovered | Failed | Pathways |
|---|---|---:|---:|---:|---|
| `get_channels` | `add_user_to_channel.channel` | 1 | 0 | 1 | `{"runtime_relation": 1}` |
| `get_channels` | `send_channel_message.channel` | 2 | 0 | 2 | `{"runtime_relation": 2}` |
| `get_day_calendar_events` | `create_calendar_event.participants` | 1 | 0 | 1 | `{"plan_construction": 1}` |
| `get_hotels_address` | `create_calendar_event.location` | 1 | 0 | 1 | `{"plan_construction": 1}` |
| `get_most_recent_transactions` | `send_money.amount` | 1 | 0 | 1 | `{"runtime_relation": 1}` |
| `read_channel_messages` | `get_webpage.url` | 1 | 0 | 1 | `{"plan_construction": 1}` |
| `read_file` | `send_money.amount` | 1 | 1 | 0 | `{}` |
| `read_file` | `send_money.recipient` | 1 | 1 | 0 | `{}` |
| `read_file` | `update_user_info.city` | 1 | 0 | 1 | `{"runtime_relation": 1}` |
| `read_file` | `update_user_info.street` | 1 | 0 | 1 | `{"runtime_relation": 1}` |
| `search_calendar_events` | `create_calendar_event.participants` | 2 | 0 | 2 | `{"plan_construction": 2, "runtime_relation": 1}` |
| `search_emails` | `create_calendar_event.location` | 1 | 0 | 1 | `{"plan_construction": 1}` |
| `search_files_by_filename` | `send_email.attachments` | 1 | 0 | 1 | `{"runtime_relation": 1}` |
| `search_files_by_filename` | `send_email.recipients` | 1 | 0 | 1 | `{"runtime_relation": 1}` |

## Claim Boundary

This post-pilot audit groups historical source/target observations. It does not infer authorization, certify a parser, or estimate open-domain relation prevalence.
