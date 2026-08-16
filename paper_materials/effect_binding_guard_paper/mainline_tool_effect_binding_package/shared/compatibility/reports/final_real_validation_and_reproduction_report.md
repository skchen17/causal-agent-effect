# Final Real Validation and Reproduction Report

## Status

Status: full-run real-model supplement complete.

The artifact now includes deterministic/reference evaluations, E61 saved external replay, B8 comparable local adapter results, real local-LLM judge results, real local-LLM atom-extraction results, and released-checkpoint adapted-baseline results. The unified reproduction gate passes with all required result files present.

Unified reproduction command:

```bash
python scripts/reproduce_all_main_tables.py
```

Observed status: `passed`, `n_rows=573`.

## Completed Artifacts

- E60 independent-review workflow: `evaluation/e60_heldout_contract/independent_author_review_packet.template.json`, `validate_independent_author_review.py`, `e60_artifact_level_review.json`, and `reports/e60_independent_review_status.md`.
- E61 external saved replay pipeline: `evaluation/e61_realistic_trace_replay/{ingest_external_traces.py,normalize_external_traces.py,build_external_sidecars.py,validate_external_trace_leakage.py,evaluate_external_trace_subset.py}`.
- E61 external outputs: `evaluation/e61_realistic_trace_replay/external_trace_subset/{raw_manifest.json,normalized_external_traces.jsonl,deployable_inputs_external.jsonl,gold_labels_external.jsonl,gold_atoms_external.jsonl,leakage_report_external.json,results_external.json}`.
- B8 released-guardrail comparable adapter: `baselines/b8_released_guardrail/` with results for E55-v2, E60, E61 artifact-generated, and E61 external subset.
- E65 real-LLM judge baseline: `evaluation/e65_real_llm_judge/results_e65.json` and per-dataset prediction/result files.
- E66 real-LLM atom extractor: `evaluation/e66_real_llm_atom_extractor/results_e66.json` and per-dataset prediction/result files.
- B8-official/E67 released checkpoint adapted baselines: `baselines/b8_official_checkpoints/results_b8_official.json` and per-model, per-dataset prediction/result files.
- Unified reproduction: `scripts/reproduce_all_main_tables.py` regenerates `reproduction/all_main_tables.{json,csv,md}`, `reproduction/claim_to_source_map.{json,md}`, and `reproduction/reproduction_status.json`.
- Shared real-model deployable-input loader and metrics: `evaluation/real_model_common.py`.

## Real-Model Supplement

Models used:

- Qwen GGUF local model: `Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`.
- TS-Guard local checkpoint: `MurrayTom/TS-Guard`.
- Safiron local checkpoint: `Safiron/Safiron`.

All runs used label-hidden deployable inputs. No run executed external tools or real side effects. Parse failures are retained as `ABSTAIN`; no case is dropped for model-output quality.

### E65 Real-LLM Judge

E65 uses the local Qwen model as a direct `ALLOW/DENY/ABSTAIN` judge over the common deployable input view.

| Dataset | N | Parse-valid | Coverage | Abstain | UPA | FDeny | Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|
| E55-v2 | 600 | 597/600 = 0.995 | 597/600 = 0.995 | 3/600 = 0.005 | 72/276 = 0.261 | 14/252 = 0.056 | 439/600 = 0.732 |
| E60 | 480 | 479/480 = 0.998 | 479/480 = 0.998 | 1/480 = 0.002 | 7/180 = 0.039 | 21/240 = 0.087 | 391/480 = 0.815 |
| E61 artifact-generated | 300 | 299/300 = 0.997 | 299/300 = 0.997 | 1/300 = 0.003 | 0/111 = 0.000 | 97/189 = 0.513 | 202/300 = 0.673 |
| E61 external subset | 156 | 154/156 = 0.987 | 154/156 = 0.987 | 2/156 = 0.013 | 0/134 = 0.000 | 20/22 = 0.909 | 134/156 = 0.859 |

Interpretation boundary: E65 is a real local LLM judge baseline, not a deployed safety mechanism. It provides useful evidence that direct LLM judging is not enough to replace atom-level mediation: E65 has nonzero unsafe pre-allows on E55-v2 and E60, and high false-denial rates on E61 safe cases.

### E66 Real-LLM Atom Extractor

E66 uses the local Qwen model to emit JSON atoms, then passes those atoms to the reference authorizer.

| Dataset | N | Parse-valid | Coverage | Abstain | UPA | FDeny | Accuracy | Atom exact | Atom count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E60 | 480 | 480/480 = 1.000 | 480/480 = 1.000 | 0/480 = 0.000 | 62/180 = 0.344 | 8/240 = 0.033 | 350/480 = 0.729 | 0/480 = 0.000 | 375/480 = 0.781 |
| E61 artifact-generated | 300 | 300/300 = 1.000 | 300/300 = 1.000 | 0/300 = 0.000 | 21/111 = 0.189 | 0/189 = 0.000 | 279/300 = 0.930 | 0/300 = 0.000 | 285/300 = 0.950 |
| E61 external subset | 156 | 156/156 = 1.000 | 152/156 = 0.974 | 4/156 = 0.026 | 9/134 = 0.067 | 4/22 = 0.182 | 139/156 = 0.891 | 0/156 = 0.000 | 141/156 = 0.904 |

Interpretation boundary: E66 closes the "no real LLM participation" gap for atom extraction, but it also exposes a real extraction bottleneck. Exact atom-set match is zero under the current strict canonical comparison, despite high parse validity and reasonable atom-count match. These results should be reported as evidence that real LLM extraction requires additional normalization, calibration, or constrained decoding before it can replace deterministic/reference atom extraction.

### B8-official / E67 Released Checkpoints

B8-official/E67 runs TS-Guard and Safiron released checkpoints on this paper's adapted common-input stress view.

| Model | Dataset | N | Parse-valid | Coverage | Abstain | UPA | FDeny | Accuracy |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Safiron | E55-v2 | 600 | 600/600 = 1.000 | 600/600 = 1.000 | 0/600 = 0.000 | 26/276 = 0.094 | 159/252 = 0.631 | 343/600 = 0.572 |
| Safiron | E60 | 480 | 480/480 = 1.000 | 480/480 = 1.000 | 0/480 = 0.000 | 165/180 = 0.917 | 29/240 = 0.121 | 226/480 = 0.471 |
| Safiron | E61 artifact-generated | 300 | 300/300 = 1.000 | 300/300 = 1.000 | 0/300 = 0.000 | 7/111 = 0.063 | 41/189 = 0.217 | 252/300 = 0.840 |
| Safiron | E61 external subset | 156 | 156/156 = 1.000 | 156/156 = 1.000 | 0/156 = 0.000 | 24/134 = 0.179 | 4/22 = 0.182 | 128/156 = 0.821 |
| TS-Guard | E55-v2 | 600 | 558/600 = 0.930 | 558/600 = 0.930 | 42/600 = 0.070 | 181/276 = 0.656 | 4/252 = 0.016 | 307/600 = 0.512 |
| TS-Guard | E60 | 480 | 480/480 = 1.000 | 480/480 = 1.000 | 0/480 = 0.000 | 180/180 = 1.000 | 0/240 = 0.000 | 240/480 = 0.500 |
| TS-Guard | E61 artifact-generated | 300 | 298/300 = 0.993 | 298/300 = 0.993 | 2/300 = 0.007 | 21/111 = 0.189 | 0/189 = 0.000 | 277/300 = 0.923 |
| TS-Guard | E61 external subset | 156 | 103/156 = 0.660 | 103/156 = 0.660 | 53/156 = 0.340 | 66/134 = 0.493 | 1/22 = 0.045 | 36/156 = 0.231 |

Interpretation boundary: these are released checkpoints evaluated under an adapted common-input stress view. They are not original ToolSafe, TS-Guard, or Safiron benchmark reproductions and should not be described as such.

## E61 External Saved Replay

- Status: real saved external replay subset integrated.
- Source type: saved AgentDojo-style/IPIGuard replay traces, not real deployed logs.
- Raw manifest: `evaluation/e61_realistic_trace_replay/external_trace_subset/raw_manifest.json`.
- Source hash: `53a44a466fe2f52807b19665b7504fdc0b5e316e3d48a8c3511c36c03c4baf33`.
- Scale: 156 traces across external_workspace 69, external_banking 46, external_chat 31, and external_travel 10.
- Annotation boundary: labels are metadata-derived; atoms are rule-derived sidecar annotations; neither is independent human gold annotation.
- Leakage: `leakage_free=true`, `n_violations=0`.
- Metrics: UPA `0/134 = 0.000`, FDeny `0/22 = 0.000`, coverage `141/156 = 0.904`, abstain `15/156 = 0.096`, atom exact-set match `128/156 = 0.821`.

## B8 Comparable Local Adapter

- Adapter: `B8_ToolSafe_TSGuard_style_comparable_local_adapter`.
- Anchor: ToolSafe/TS-Guard-style step-level guardrail framing.
- Scope: comparable local adapter under this paper's label-hidden deployable-input contract, not an original ToolSafe/TS-Guard benchmark, checkpoint, or API reproduction.
- Forbidden fields: gold labels, gold atoms, expected decisions, violation reasons, expanded atom annotations, and result-derived fields.

| Dataset | UPA | FDeny | Coverage | Abstain | Accuracy | Unsupported | Adapter failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| E55-v2 | 0.435 | 0.095 | 0.900 | 0.100 | 0.700 | 60 | 0 |
| E60 | 0.533 | 0.200 | 1.000 | 0.000 | 0.575 | 0 | 0 |
| E61 artifact-generated | 0.189 | 0.222 | 1.000 | 0.000 | 0.790 | 0 | 0 |
| E61 external subset | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 | 0 | 0 |

These values support a common-input baseline comparison only. They do not support claims of global superiority or original external-system reproduction.

## E60 Independent Review Boundary

- Validator output: `evaluation/e60_heldout_contract/e60_artifact_level_review.json`.
- Artifact review status: `artifact-level-pass`.
- Strict authorship status: `blocked-by-external-human-review`.
- Current safe wording: "independently specified held-out contract."
- Disallowed wording until validated human material is provided: the stronger independent-authorship wording.

The current packet proves artifact-level separation and held-out schema differences, but it does not certify strict independent authorship/review. The validator does not infer or create external human facts.

## Unified Reproduction Status

- Command: `python scripts/reproduce_all_main_tables.py`.
- Status: `passed`.
- Rows: `573`.
- Required real-model artifacts present:
  - `evaluation/e65_real_llm_judge/results_e65.json`.
  - `evaluation/e66_real_llm_atom_extractor/results_e66.json`.
  - `baselines/b8_official_checkpoints/results_b8_official.json`.
  - all per-dataset E65/E66 and per-model B8-official result JSON files.
- Generated outputs:
  - `reproduction/all_main_tables.json`.
  - `reproduction/all_main_tables.csv`.
  - `reproduction/all_main_tables.md`.
  - `reproduction/claim_to_source_map.json`.
  - `reproduction/claim_to_source_map.md`.
  - `reproduction/reproduction_status.json`.

## Paper Claim Boundaries

- E60 remains `independently specified`, not `independently authored`.
- E61 external is a saved external replay subset, not production logs or real deployed traces.
- E61 external labels are metadata-derived and atoms are rule-derived sidecars, not independent human gold.
- B8 comparable adapter is not original ToolSafe/TS-Guard reproduction.
- E65 is a real local-LLM judge baseline over label-hidden deployable inputs, not a deployed safety guarantee.
- E66 is real local-LLM atom extraction followed by the reference authorizer, not a replacement for the reference guard main results.
- B8-official/E67 is a released-checkpoint adapted common-input baseline, not original ToolSafe, TS-Guard, or Safiron benchmark reproduction.
- The paper remains artifact-bounded and does not claim production safety, deployed-system guarantees, real SaaS safety, complete authorization infrastructure, or solved authorization.

## Reviewer-Concern Coverage

- Too synthetic: improved by E60 held-out contract, E61 sandboxed realistic traces, and E61 saved external replay subset.
- Circularity: reduced by E60 held-out schema differences and E60 review workflow; strict independent authorship remains externally blocked.
- No realistic traces: addressed by E61 artifact-generated realistic replay and E61 saved external replay subset.
- Weak baselines: improved by E64 B0-B7, B8 comparable adapter, and B8-official/E67 released-checkpoint adapted baselines.
- No real LLM participation: addressed by full-run E65 real-LLM judge and E66 real-LLM atom extractor artifacts.
- Reproducibility: unified reproduction now fail-fast checks deterministic/reference artifacts and full-run real-model artifacts.

## Remaining Human/External Inputs

- Strict E60 independent authorship requires a real non-E55 author/reviewer packet that passes `validate_independent_author_review.py`.
- Human-labeled E61 external validation requires independent annotation material and, ideally, agreement statistics.
- A true ToolSafe/TS-Guard/Safiron original-protocol reproduction would still require following the original public protocol and documenting compatibility; B8-official/E67 only supports adapted common-input checkpoint comparison.
