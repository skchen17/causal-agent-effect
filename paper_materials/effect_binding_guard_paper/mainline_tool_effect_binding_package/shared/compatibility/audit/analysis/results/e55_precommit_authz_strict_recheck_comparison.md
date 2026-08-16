# E55 Strict Recheck Comparison

- Canonical: `analysis/results/e55_precommit_authz_results_strict.json`
- Recheck: `analysis/results/e55_precommit_authz_results_strict_recheck.json`
- Core metrics equal: `True`

| Method | Metric | Canonical | Recheck | Equal |
|---|---|---:|---:|---|
| `authz_aware_effect_binding_guard` | `unsafe_pre_allow` | 0.0 | 0.0 | True |
| `authz_aware_effect_binding_guard` | `safe_false_deny` | 0.0 | 0.0 | True |
| `authz_aware_effect_binding_guard` | `coverage` | 0.92 | 0.92 | True |
| `authz_aware_effect_binding_guard` | `abstain_rate` | 0.08 | 0.08 | True |
| `authz_aware_effect_binding_guard` | `decision_accuracy` | 1.0 | 1.0 | True |
| `authz_aware_effect_binding_guard` | `atom_expansion_exact_match` | 1.0 | 1.0 | True |
| `existing_hard_effect_binding_guard` | `unsafe_pre_allow` | 0.037037037037037035 | 0.037037037037037035 | True |
| `existing_hard_effect_binding_guard` | `safe_false_deny` | 0.0 | 0.0 | True |
| `existing_hard_effect_binding_guard` | `coverage` | 0.2 | 0.2 | True |
| `existing_hard_effect_binding_guard` | `abstain_rate` | 0.8 | 0.8 | True |
| `existing_hard_effect_binding_guard` | `decision_accuracy` | 0.1 | 0.1 | True |
| `existing_hard_effect_binding_guard` | `atom_expansion_exact_match` | 0.0 | 0.0 | True |
