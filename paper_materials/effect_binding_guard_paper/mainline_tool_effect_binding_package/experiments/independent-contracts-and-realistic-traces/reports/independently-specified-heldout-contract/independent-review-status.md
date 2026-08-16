# E60 Independent Review Status

- Artifact review status: `artifact-level-pass`.
- Strict authorship status: `blocked-by-external-human-review`.
- Claim boundary: The paper may describe E60 only as an independently specified held-out contract; strict independent authorship/review remains externally uncertified.
- Safe paper wording: We evaluate on a 480-case independently specified held-out contract with different tool names, argument fields, schema family, aliases, and authorization policies from E55.
- Unsafe until certified: We evaluate on an independently authored held-out contract.

## Automatic Checks

| Check | OK | Detail |
|---|---:|---|
| required_fields | True | `[]` |
| reviewed_artifacts_exist | True | `[]` |
| leakage_zero | True | `{"artifact_leakage_report": {"hits": {}, "leakage_free": true, "n_violations": 0, "path": "evaluation/e60_heldout_contract/deployable_inputs.jsonl"}, "packet_data_separation_review": {"deployable_input_contract": "deployable_annotation_free` |
| deployable_input_hidden | True | `{"n_rows": 480, "n_violations": 0, "violations": []}` |
| no_post_evaluation_case_deletion | True | `{"case_deletion_after_evaluation": false, "case_deletion_independently_verified": false, "case_deletion_policy": "No E60 cases are removed or filtered after evaluation based on performance."}` |
| contract_independence | True | `{"checks": {"alias_style_differs_from_e55": true, "argument_fields_differ_from_e55": true, "at_least_three_domains": true, "authorization_policy_format_differs_from_e55": true, "n_cases_at_least_240": true, "resource_identifiers_differ_from` |

This validator does not create or infer an external human reviewer. If the packet does not certify strict independent authorship/review, the manuscript must use `independently specified held-out contract`.
