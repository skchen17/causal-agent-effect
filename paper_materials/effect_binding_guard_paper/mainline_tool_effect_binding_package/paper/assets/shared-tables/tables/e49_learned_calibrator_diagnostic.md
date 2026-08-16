# E49 Learned Calibrator Diagnostic

| method | unsafe_pre_allow | safe_false_deny | coverage | claim_scope | interpretation |
| --- | --- | --- | --- | --- | --- |
| learned_logistic_calibrator_source_balanced | 0.0918919 | 0.0357895 | 0.988166 | diagnostic_not_main_method | Higher coverage but higher UPA than hard guard. |
| hard_full_guard_same_splits | 0.0513514 | 0.0589474 | 0.923077 | main_hard_baseline | Safer baseline retained as main method. |
| e49_resource_auth_stress | 0.741667 | 0.05 | 1 | negative_diagnostic | Resource/auth stress fails; learned calibration is appendix only. |
