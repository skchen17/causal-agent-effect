# Appendix Slice Table Summary

The canonical slice table is summarized below. Use the original source for exact formatting.

Source: `analysis/results/e55_precommit_authz_slice_table.md`

# E55 Slice Table

| method | slice | n_rows | unsafe_pre_allow | safe_false_deny | coverage | abstain | decision_accuracy | false_allow_count | false_deny_count | abstain_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| allow_all | multi_resource | 516 | 1.0 | 0.0 | 1.0 | 0.0 | 0.37209302325581395 | 288 | 0 | 0 |
| allow_all | alias | 120 | 1.0 | 0.0 | 1.0 | 0.0 | 0.4 | 72 | 0 | 0 |
| allow_all | draft_commit | 204 | 1.0 | 0.0 | 1.0 | 0.0 | 0.35294117647058826 | 84 | 0 | 0 |
| allow_all | public_visibility | 156 | 1.0 | 0.0 | 1.0 | 0.0 | 0.46153846153846156 | 72 | 0 | 0 |
| allow_all | provenance_shift | 108 | 1.0 | None | 1.0 | 0.0 | 0.0 | 60 | 0 | 0 |
| allow_all | evidence_fallback | 24 | None | 0.0 | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| allow_all | safe_draft_or_read_only | 72 | None | 0.0 | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| allow_all | unsafe_extra_recipient | 168 | 1.0 | None | 1.0 | 0.0 | 0.0 | 168 | 0 | 0 |
| allow_all | unsafe_public_link | 24 | 1.0 | None | 1.0 | 0.0 | 0.0 | 24 | 0 | 0 |
| allow_all | unsafe_alias_mismatch | 72 | 1.0 | None | 1.0 | 0.0 | 0.0 | 72 | 0 | 0 |
| allow_all | unsafe_commit_when_draft_only | 60 | 1.0 | None | 1.0 | 0.0 | 0.0 | 60 | 0 | 0 |
| allow_all | unsafe_untrusted_control | 60 | 1.0 | None | 1.0 | 0.0 | 0.0 | 60 | 0 | 0 |
| deny_all | multi_resource | 516 | 0.0 | 1.0 | 1.0 | 0.0 | 0.5581395348837209 | 0 | 192 | 0 |
| deny_all | alias | 120 | 0.0 | 1.0 | 1.0 | 0.0 | 0.6 | 0 | 48 | 0 |
| deny_all | draft_commit | 204 | 0.0 | 1.0 | 1.0 | 0.0 | 0.4117647058823529 | 0 | 72 | 0 |
| deny_all | public_visibility | 156 | 0.0 | 1.0 | 1.0 | 0.0 | 0.46153846153846156 | 0 | 72 | 0 |
| deny_all | provenance_shift | 108 | 0.0 | None | 1.0 | 0.0 | 0.5555555555555556 | 0 | 0 | 0 |
| deny_all | evidence_fallback | 24 | None | 1.0 | 1.0 | 0.0 | 0.0 | 0 | 24 | 0 |
| deny_all | safe_draft_or_read_only | 72 | None | 1.0 | 1.0 | 0.0 | 0.0 | 0 | 72 | 0 |
| deny_all | unsafe_extra_recipient | 168 | 0.0 | None | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| deny_all | unsafe_public_link | 24 | 0.0 | None | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| deny_all | unsafe_alias_mismatch | 72 | 0.0 | None | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| deny_all | unsafe_commit_when_draft_only | 60 | 0.0 | None | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| deny_all | unsafe_untrusted_control | 60 | 0.0 | None | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| tool_name_proxy | multi_resource | 516 | 0.625 | 0.0 | 1.0 | 0.0 | 0.5813953488372093 | 180 | 0 | 0 |
| tool_name_proxy | alias | 120 | 0.6666666666666666 | 0.0 | 1.0 | 0.0 | 0.6 | 48 | 0 | 0 |
| tool_name_proxy | draft_commit | 204 | 0.8571428571428571 | 0.0 | 1.0 | 0.0 | 0.4117647058823529 | 72 | 0 | 0 |
| tool_name_proxy | public_visibility | 156 | 0.8333333333333334 | 0.0 | 1.0 | 0.0 | 0.5384615384615384 | 60 | 0 | 0 |
| tool_name_proxy | provenance_shift | 108 | 0.8 | None | 1.0 | 0.0 | 0.1111111111111111 | 48 | 0 | 0 |
| tool_name_proxy | evidence_fallback | 24 | None | 0.0 | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| tool_name_proxy | safe_draft_or_read_only | 72 | None | 0.0 | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| tool_name_proxy | unsafe_extra_recipient | 168 | 0.5 | None | 1.0 | 0.0 | 0.5 | 84 | 0 | 0 |
| tool_name_proxy | unsafe_public_link | 24 | 0.5 | None | 1.0 | 0.0 | 0.5 | 12 | 0 | 0 |
| tool_name_proxy | unsafe_alias_mismatch | 72 | 0.6666666666666666 | None | 1.0 | 0.0 | 0.3333333333333333 | 48 | 0 | 0 |
| tool_name_proxy | unsafe_commit_when_draft_only | 60 | 0.8 | None | 1.0 | 0.0 | 0.2 | 48 | 0 | 0 |
| tool_name_proxy | unsafe_untrusted_control | 60 | 0.8 | None | 1.0 | 0.0 | 0.2 | 48 | 0 | 0 |
| text_rule_proxy | multi_resource | 516 | 0.5833333333333334 | 0.0 | 0.9069767441860465 | 0.09302325581395349 | 0.6511627906976745 | 168 | 0 | 48 |
| text_rule_proxy | alias | 120 | 1.0 | 0.0 | 1.0 | 0.0 | 0.4 | 72 | 0 | 0 |
| text_rule_proxy | draft_commit | 204 | 0.8571428571428571 | 0.0 | 0.6470588235294118 | 0.35294117647058826 | 0.5294117647058824 | 72 | 0 | 72 |
| text_rule_proxy | public_visibility | 156 | 0.3333333333333333 | 0.0 | 0.8461538461538461 | 0.15384615384615385 | 0.7692307692307693 | 24 | 0 | 24 |
| text_rule_proxy | provenance_shift | 108 | 0.0 | None | 0.5555555555555556 | 0.4444444444444444 | 1.0 | 0 | 0 | 48 |
| text_rule_proxy | evidence_fallback | 24 | None | 0.0 | 0.0 | 1.0 | 0.0 | 0 | 0 | 24 |
| text_rule_proxy | safe_draft_or_read_only | 72 | None | 0.0 | 0.6666666666666666 | 0.3333333333333333 | 0.6666666666666666 | 0 | 0 | 24 |
| text_rule_proxy | unsafe_extra_recipient | 168 | 0.7142857142857143 | None | 1.0 | 0.0 | 0.2857142857142857 | 120 | 0 | 0 |
| text_rule_proxy | unsafe_public_link | 24 | 0.0 | None | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| text_rule_proxy | unsafe_alias_mismatch | 72 | 1.0 | None | 1.0 | 0.0 | 0.0 | 72 | 0 | 0 |
| text_rule_proxy | unsafe_commit_when_draft_only | 60 | 1.0 | None | 1.0 | 0.0 | 0.0 | 60 | 0 | 0 |
| text_rule_proxy | unsafe_untrusted_control | 60 | 0.0 | None | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| existing_hard_effect_binding_guard | multi_resource | 516 | 0.041666666666666664 | 0.0 | 0.18604651162790697 | 0.813953488372093 | 0.09302325581395349 | 12 | 0 | 420 |
| existing_hard_effect_binding_guard | alias | 120 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 0 | 0 | 120 |
| existing_hard_effect_binding_guard | draft_commit | 204 | 0.14285714285714285 | 0.0 | 0.5882352941176471 | 0.4117647058823529 | 0.29411764705882354 | 12 | 0 | 84 |
| existing_hard_effect_binding_guard | public_visibility | 156 | 0.0 | 0.0 | 0.23076923076923078 | 0.7692307692307693 | 0.15384615384615385 | 0 | 0 | 120 |
| existing_hard_effect_binding_guard | provenance_shift | 108 | 0.2 | None | 0.5555555555555556 | 0.4444444444444444 | 0.0 | 12 | 0 | 48 |
| existing_hard_effect_binding_guard | evidence_fallback | 24 | None | 0.0 | 1.0 | 0.0 | 1.0 | 0 | 0 | 0 |
| existing_hard_effect_binding_guard | safe_draft_or_read_only | 72 | None | 0.0 | 0.8333333333333334 | 0.16666666666666666 | 0.8333333333333334 | 0 | 0 | 12 |
| existing_hard_effect_binding_guard | unsafe_
