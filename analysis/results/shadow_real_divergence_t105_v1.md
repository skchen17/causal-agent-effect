# T105 Shadow-Real Divergence Diagnostic

## Summary

| n | faithful_n | unsafe_n | faithful_allow | unsafe_nonallow | unsafe_deny | unsafe_abstain |
| --- | --- | --- | --- | --- | --- | --- |
| 400 | 200 | 200 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

## Divergence Rates on Unsafe Substitutions

| effect | host | path | tool |
| --- | --- | --- | --- |
| 0.5250 | 0.2750 | 0.5750 | 0.4000 |

## Family Breakdown

| family | n | faithful_allow | unsafe_nonallow |
| --- | --- | --- | --- |
| api_provider_dry_run | 50 | 1.0000 | 1.0000 |
| browser_form | 50 | 1.0000 | 1.0000 |
| draft_messaging | 50 | 1.0000 | 1.0000 |
| file_cleanup | 60 | 1.0000 | 1.0000 |
| http_status_check | 60 | 1.0000 | 1.0000 |
| local_file_analysis | 70 | 1.0000 | 1.0000 |
| tool_alias | 60 | 1.0000 | 1.0000 |

## Claim Boundary

This is a local substitution diagnostic over T102 authorized intents. It checks whether changed resources/endpoints/actions are denied or abstained before commit under the existing F_c guard. It does not prove that a production sandbox faithfully predicts provider-backed behavior.
