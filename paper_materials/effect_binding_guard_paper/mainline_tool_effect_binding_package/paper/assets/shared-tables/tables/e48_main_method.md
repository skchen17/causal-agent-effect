# E48 Main Method

| method | unsafe_pre_allow | safe_false_deny | coverage | abstain | effect_accuracy | resource_accuracy | authorization_accuracy | provenance_accuracy | claim_scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rule_tuple_guard | 0.0944444 | 0.0974026 | 0.654501 | 0.345499 | 0.791971 | 0.379562 | 0.503906 | 1 | method-feasibility custom stress |
| local_qwen_tuple_guard | 0.105556 | 0.0670996 | 0.962287 | 0.0377129 | 0.809002 | 0.877129 | 0.929688 | 0.814815 | method-feasibility custom stress |
| multi_view_disagreement_guard | 0.075 | 0.136364 | 0.997567 | 0.00243309 | 0.891727 | 0.753041 | 0.859375 | 0.814815 | method-feasibility custom stress |
| evidence_gated_selective_guard | 0.0638889 | 0.0649351 | 0.924574 | 0.0754258 | 0.835766 | 0.726277 | 0.847656 | 0.722222 | method-feasibility custom stress |
| control_provenance_minimal_check | 0.0944444 | 0.0974026 | 0.654501 | 0.345499 | 0.791971 | 0.379562 | 0.503906 | 1 | method-feasibility custom stress |
| effect_binding_guard_full | 0.0361111 | 0.0649351 | 0.917275 | 0.0827251 | 0.835766 | 0.726277 | 0.847656 | 1 | method-feasibility custom stress |
| always_use_evidence | 0.00277778 | 0.0324675 | 0.138686 | 0.861314 | 0.10219 | 0.0875912 | 0.128906 | 0 | method-feasibility custom stress |
