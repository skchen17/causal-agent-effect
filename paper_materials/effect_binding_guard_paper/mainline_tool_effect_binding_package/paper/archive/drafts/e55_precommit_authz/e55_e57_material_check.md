# E55/E57 Material Check

Date: 2026-06-18

## Verdict

The newly added E55/E57 materials materially improve the project evidence. The earlier gap "E57 spot-audit packet exists but has no completed human annotation" is now closed, with an important caveat: the human audit found corrected labels and atom/violation-reason corrections. The paper must report corrected-label evidence rather than claiming perfect construction agreement.

## New Or Updated Materials Found

### E55

- `audit/analysis/results/e55_v2_precommit_authz_results_strict.{json,md}`
- `audit/analysis/results/e55_precommit_authz_results_strict_recheck.{json,md}`
- `audit/analysis/results/e55_precommit_authz_strict_recheck_comparison.{json,md}`
- `audit/analysis/results/e55_v2_precommit_authz_leakage_audit.json`
- `data/data/e55_v2_precommit_authz_dataset.jsonl`
- `data/data/e55_precommit_authz_recheck_dataset.jsonl`
- `results/analysis/results/e55_human_corrected_sensitivity.{json,md,csv}`
- `paper_drafts/e55_precommit_authz/e55_human_corrected_sensitivity.{md,csv}`
- `paper_drafts/e55_precommit_authz/e55_v2_corrected_rerun.md`
- `paper_drafts/e55_precommit_authz/e55_main_table.md`

### E57

- `audit/analysis/results/e57_human_audit_validation.{json,md}`
- `audit/analysis/results/e57_spot_audit_packet_human_audited.jsonl`
- `audit/analysis/results/e57_spot_audit_corrected_label_subset.jsonl`
- `audit/analysis/results/e57_v2_validity_checks_report.{json,md}`
- `audit/analysis/results/e57_v2_reference_authorizer_agreement.json`
- `audit/analysis/results/e57_v2_resource_perturbation_results.json`
- `audit/analysis/results/e57_v2_spot_audit_packet.jsonl`
- `paper_drafts/e55_precommit_authz/e57_v2_validity_checks_summary.md`
- `paper_drafts/e55_precommit_authz/e57_v2_claim_boundary.md`
- `paper_drafts/ndss_candidate/e57_v2_integration_plan.md`

## Key Result Changes

### E55-v2 strict rerun

- Rows: 600.
- Domains: email, calendar, file, slack, transaction; 120 rows each.
- Existing hard guard: UPA 0.043, FDeny 0.000, coverage 0.200, abstain 0.800.
- Authorization-aware guard: UPA 0/276 = 0.000, FDeny 0/252 = 0.000, coverage 528/600 = 0.880, abstain 72/600 = 0.120.
- Leakage-free: true.

### E55 human-corrected sensitivity

- Human-audited rows: 60.
- Decision corrections: 6.
- Minimal 600-row correction preserves authz-aware UPA at 0/320 = 0.000 and coverage at 552/600 = 0.920, but introduces FDeny 4/230 = 0.017.
- Writing implication: report "zero unsafe pre-allow under corrected sensitivity, with small false-denial after human correction"; do not claim perfect label confirmation.

### E57 human audit

- Human-audited rows: 60/60.
- Human decision agreement: 54/60 = 0.900.
- All human checks true: 46/60 = 0.767.
- Decision corrections: 6.
- Atom corrections: 13.
- Violation-reason corrections: 10.
- Main caveats: transaction-domain amount handling and unknown-resource fallback.

### E57-v2 validity

- Perturbation stability: true.
- Authz-aware UPA delta: 0.0.
- Authz-aware coverage delta: 0.0.
- Changed decisions: 0.
- Reference-authorizer decision agreement: 1.0.
- Atom count agreement: 1.0.
- Atom resource-set agreement: 1.0.
- Spot-audit packet rows: 60.

## Table Integration Status

- `tables/table4_precommit_authz_prototype.md` now includes original E55, corrected sensitivity, and E55-v2 metrics.
- `tables/table6_e57_validity_checks.md` now includes E57-v2 validity rows.
- `paper_drafts/e55_precommit_authz/e55_main_table.md` still presents original E55 as the main table, with a note pointing to corrected sensitivity. Final paper writing must choose a canonical table policy:
  - either use E55-v2 as primary,
  - or use original E55 with corrected-label sensitivity as a robustness/audit row.

## Remaining Experimental Gaps

Closed:

- E57 no-human-audit gap is closed.
- E55 strict recheck reproducibility is closed for core metrics.
- E57-v2 perturbation/reference-authorizer checks are present.

Still open:

- E55/E57 remain controlled local mock contract evidence, not independent deployment validation.
- There is still no independently authored held-out E55-style dataset/contract.
- There is still no realistic sandbox/replay domain with a mediator protocol.
- E55-v2 still does not by itself evaluate released guardrail baselines on the E55 task distribution.
- Final paper must not claim perfect human label confirmation because the audit found corrections.

## Verification

Targeted tests pass when run from the packaged source root:

```bash
cd code
PYTHONPATH=. python -m pytest ../tests/tests/test_effect_binding_guard_e55_precommit_authz.py ../tests/tests/test_effect_binding_guard_e57_validity.py -q
```

Result: 22 passed.

Running `pytest` directly from the package root failed because the global `pytest` script uses `/usr/bin/python3` without `typing_extensions`; running `python -m pytest` from the package root then failed because tests expect `src/...` paths while this package stores source under `code/src/...`.
