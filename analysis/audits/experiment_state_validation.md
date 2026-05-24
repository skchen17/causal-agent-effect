# Experiment State Validation Report

> 2026-05-15 | Generated after causal-chain v2 embedding/evaluation rerun and contrastive multiseed v2 rerun.

> 2026-05-15 update: validator still checks the original 459-row core pipeline. Mainconf v2 is validated separately by `analysis/mainconf_v2_repair_report.md` and `analysis/statistical_uncertainty_audit_mainconf_v2.md`.

## Overall: OK

| Check | Status | Detail |
|------|:---:|------|
| Embedding consistency | ✅ | Main Qwen3-8B scenario embeddings: X(459,4096), Y(459,11), texts(459) are length-consistent |
| Real-tool semantics | ✅ | 0 schema errors, 0 missing flow fields, 0 semantic conflicts in v2 proxy scenarios |
| Legacy wrong-chain coverage | ⚠️ | Old `data/causal_chain_conditioning.jsonl` lacks `authorization_flip`; retained only as legacy context |
| Causal-chain v2 input | ✅ | `data/causal_chain_conditioning_v2.jsonl` has typed wrong-chain coverage |
| Causal-chain v2 results | ✅ | `analysis/causal_chain_mechanism_qwen3-8b_causal_chain_conditioning_v2.json` is schema v2 and covers required typed groups |
| Citation audit | ✅ | 0 null URLs, 0 `Anonymous` authors, 0 placeholder authors |
| Strict LOPO consistency | ✅ | Pair rows recompute to 2 evaluable effects, 68 cases, 40 improved, mean DeltaFNR=0.1567 |
| Contrastive multiseed | ✅ | `contrastive_multiseed_v2`, seeds `[0,1,2,3,4]`, full-training protocol |
| Paper claim scan | ✅ | `real-agent validation` forbidden phrase and stale strict taxonomy-only claims are cleared |

## Validator JSON Snapshot

`analysis/experiment_state_validation.json` currently reports:

```json
{
  "causal_chain_v2_results": {
    "schema_version": "causal_chain_mechanism_v2",
    "n_samples": 2290,
    "wrong_chain_type_counts": {
      "effect_omission": 153,
      "authorization_flip": 153,
      "effect_flip": 152
    },
    "all_clear": true
  },
  "strict_lopo": {
    "num_evaluable_effects": 2,
    "num_strict_tool_cases": 68,
    "num_improved": 40,
    "mean_delta_fnr": 0.1567,
    "all_clear": true
  },
  "contrastive_multiseed": {
    "schema_version": "contrastive_multiseed_v2",
    "seeds": [0, 1, 2, 3, 4],
    "train_protocol": "full_training",
    "n_effects": 6,
    "all_clear": true
  },
  "paper_forbidden_claims": [],
  "paper_stale_claims": [],
  "overall": "ok"
}
```

## Remaining Cautions

1. Real-tool calibration is proxy validation, not execution-trace validation.
2. Citation numbers are primary-source reported claims, not independent reproductions.
3. Causal-chain conditioning is a mechanism diagnostic/candidate method; avoid claiming it proves robust overreach prevention.
4. Mainconf v2 static replay traces are not covered by this legacy validator; use the v2 manifest and statistical audit for that chain.
