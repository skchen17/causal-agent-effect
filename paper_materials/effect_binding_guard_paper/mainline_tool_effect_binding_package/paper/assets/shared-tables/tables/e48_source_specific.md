# E48 Source Specific

| method | unsafe_pre_allow | safe_false_deny | coverage | abstain | effect_accuracy | resource_accuracy | authorization_accuracy | provenance_accuracy | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| held_out_test_full_guard | 0.0510204 | 0.047619 | 0.955357 | 0.0446429 | 0.892857 | 0.8125 | 0.883929 |  | legacy_hashed_test_no_camel |
| human_audited_subset | 0.0322581 | 0.0465116 | 0.896396 | 0.103604 | 0.792793 | 0.752252 | 0.857143 | 1 | audited_subset |
| ipiguard_semantic_core | 0.125 | 0.0833333 | 0.891667 | 0.108333 | 0.879167 | 0.675 | 0.795833 |  | source_specific |
| camel_provenance_core | 0 | 0 | 0.777778 | 0.222222 | 0.648148 | 0.888889 |  | 1 | source_specific |
