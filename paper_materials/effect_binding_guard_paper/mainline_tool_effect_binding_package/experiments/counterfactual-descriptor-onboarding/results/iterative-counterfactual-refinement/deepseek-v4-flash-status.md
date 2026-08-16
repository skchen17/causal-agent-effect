# E63 DeepSeek-V4-Flash Status

Run: `e63_deepseek_v4_flash`

Backend: OpenAI-compatible external API.

Model: `deepseek-v4-flash`.

Base URL: `https://api.deepseek.com`.

The API key was supplied only through the process environment and was not written to the generated artifacts.

## Claim Boundary

This is an external API model run of the E63 iterative counterfactual contract-refinement harness. It is model-participation evidence for this configured API/model on the 15-tool held-out mock suite. It is not local-LLM evidence, production-safety evidence, real external-tool behavior, or a guarantee for arbitrary tools.

## Smoke Run

- Report: `analysis/results/e63_deepseek_v4_flash_smoke_report.json`.
- Tools: `1`.
- Candidate records: `1`.
- Parse-valid: `1/1`.
- Freezeable tools: `0/1`.
- Prompt leakage violations: `0`.
- Feedback leakage violations: `0`.

## Full Run

- Report: `analysis/results/e63_deepseek_v4_flash_report.json`.
- Round metrics: `analysis/results/e63_deepseek_v4_flash_round_metrics.csv`.
- Candidate contracts: `analysis/results/e63_deepseek_v4_flash_candidate_contracts.jsonl`.
- Prompts: `analysis/results/e63_deepseek_v4_flash_prompts.jsonl`.
- Feedback payloads: `analysis/results/e63_deepseek_v4_flash_feedback_payloads.jsonl`.
- Failure examples: `analysis/results/e63_deepseek_v4_flash_failure_examples.jsonl`.
- Final selections: `analysis/results/e63_deepseek_v4_flash_frozen_contracts.jsonl`.

Metrics:

- Held-out tools: `15`.
- Candidate records: `71`.
- Prompt records: `71`.
- Feedback records: `71`.
- Parse-valid candidates: `54/71`.
- Validation-passed candidates: `1/71`.
- Freezeable candidates: `1/71`.
- Freezeable tools: `1/15`.
- Human-review required: `14/15`.
- Prompt leakage violations: `0`.
- Feedback leakage violations: `0`.

All-round aggregate:

- Mean required atom coverage: `0.014`.
- Mean resource-binding coverage: `0.072`.
- Mean target-principal coverage: `0.072`.
- Mean unsafe-pre-allow rate: `0.009`.
- Mean false-deny rate: `0.535`.
- Mean decision accuracy: `0.330`.

Final selected candidates:

- Mean required atom coverage: `0.067`.
- Mean resource-binding coverage: `0.133`.
- Mean target-principal coverage: `0.133`.
- Mean unsafe-pre-allow rate: `0.000`.
- Mean false-deny rate: `0.867`.

The only freezeable tool was `archive_channel` at `round_0_raw`.

## Failure Profile

- `commit_mode_omission`: `53`.
- `missed_side_effect`: `53`.
- `provenance_omission`: `53`.
- `target_resource_confusion`: `53`.
- `over_deny`: `38`.
- `parse_failure`: `17`.
- `ignored_attachment_disclosure`: `11`.
- `ignored_public_visibility`: `10`.
- `malformed_schema`: `3`.
- `unsafe_pre_allow`: `3`.

## Interpretation

DeepSeek can run the E63 harness and often emits parseable JSON, but strict counterfactual validation still rejects nearly all candidates. The result supports the paper's conservative claim that counterfactual validation is needed before freezing LLM-proposed effect contracts. It does not support a claim that this model reliably infers complete contracts for arbitrary tools.

Checks passed: JSON report validation, required artifact presence, secret-like key scan over DeepSeek artifacts, and Python compile checks for the changed backend/runner files.
