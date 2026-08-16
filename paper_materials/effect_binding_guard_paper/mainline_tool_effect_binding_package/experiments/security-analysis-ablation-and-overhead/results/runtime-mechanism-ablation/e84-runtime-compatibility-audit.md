# E84 Runtime Compatibility Audit

- Trusted manifests: `44`
- Resolver specs: `60`
- Typed projection successes: `0/60`
- Runtime-ready manifests: `25/44`
- Manifests with uncompiled canonical transforms: `3`
- External side effects: `0`

## By Read Tool

- `get_most_recent_transactions`: `0/7`
- `get_rating_reviews_for_hotels`: `0/1`
- `read_channel_messages`: `0/1`
- `read_file`: `0/3`
- `read_inbox`: `0/2`
- `search_calendar_events`: `0/14`
- `search_emails`: `0/20`
- `search_files`: `0/12`

## Claim Boundary

This audit executes only independently approved read resolvers in clean AgentDojo sandbox states. It validates query and projection compatibility, not authority correctness, attack robustness, or end-to-end utility. A reviewed manifest remains unavailable to the runtime when any required typed projection or canonical transform is not executable.
