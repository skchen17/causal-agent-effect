# T102 Future Constraint Dataset Manifest

- tasks: 200

- intents: 600

- compiler outputs: 600

## Task Families

| family | tasks | intent_pairs |
| --- | --- | --- |
| api_provider_dry_run | 25 | 75 |
| browser_form | 25 | 75 |
| draft_messaging | 25 | 75 |
| file_cleanup | 30 | 90 |
| http_status_check | 30 | 90 |
| local_file_analysis | 35 | 105 |
| tool_alias | 30 | 90 |

## Intent Types

| intent_type | count |
| --- | --- |
| adversarial_or_alias | 200 |
| authorized_minimal | 200 |
| plausible_overreach | 200 |

## Allowed Effect Counts

| effect | task_count |
| --- | --- |
| dom_or_storage_mutation | 25 |
| external_api_invoked | 25 |
| file_content_read | 90 |
| file_deleted | 30 |
| file_written | 25 |
| local_computation | 120 |
| network_egress | 55 |

## Unauthorized Effect Counts

| effect | intent_count |
| --- | --- |
| browser_submit | 50 |
| content_fetched | 95 |
| dom_or_storage_mutation | 30 |
| external_api_invoked | 85 |
| external_data_upload | 225 |
| file_content_read | 30 |
| file_deleted | 60 |
| file_written | 90 |
| message_sent | 50 |
| network_egress | 200 |

## Design

Two-stage `A(c)` extraction and `F_c` compilation; 200 tasks x 3 intents; rule baseline outputs are generated locally. LLM structured compiler is intentionally deferred until the schema is stable.
