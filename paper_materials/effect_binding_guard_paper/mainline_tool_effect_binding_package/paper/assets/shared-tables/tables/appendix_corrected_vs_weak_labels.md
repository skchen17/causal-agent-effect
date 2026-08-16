# Appendix Corrected Vs Weak Labels

| conclusion | corrected_label | delta | metric | original_weak_label |
|---|---|---|---|---|
| unchanged | 0.75 | 0 | unsafe_blocked | 0.75 |
| unchanged | 0 | 0 | safe_false_denial | 0 |
| unchanged | 6 | 0 | unsafe_miss_count | 6 |
| taxonomy_changed_only | {"booking_or_financial_mutation": 16, "external_communication": 24, "file_write_share_delete": 8, "no_external_side_effect": 6} | 6 no_side_effect_tool rows move to no_external_side_effect | effect_class_counts | {"booking_or_financial_mutation": 18, "external_communication": 27, "file_write_share_delete": 9} |
