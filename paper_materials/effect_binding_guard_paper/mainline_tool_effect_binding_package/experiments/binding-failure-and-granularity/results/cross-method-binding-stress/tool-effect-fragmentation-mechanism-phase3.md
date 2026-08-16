# Tool-Effect Fragmentation Mechanism Phase 3

- Primary backend: `tfidf_svd::full_text`
- Records: `41`

## Ablation Results

| Backend/Ablation | Gap | Gap CI | Same-effect diff-tool | Same-tool diff-effect |
|---|---:|---:|---:|---:|
| `tfidf_svd::full_text` | -0.4239 | [-0.5646, -0.3896] | 0.1598 | 0.5837 |
| `tfidf_svd::tool_name_stripped` | -0.3548 | [-0.4947, -0.3121] | 0.2013 | 0.5561 |
| `tfidf_svd::arg_schema_stripped` | -0.7392 | [-0.7396, -0.5977] | 0.1619 | 0.9011 |
| `tfidf_svd::effect_resource_stripped` | -0.6024 | [-0.6531, -0.5178] | 0.1480 | 0.7504 |
| `tfidf_svd::plan_only` | -0.4584 | [-0.5928, -0.4247] | 0.1577 | 0.6162 |
| `tfidf_svd::step_only` | -0.6643 | [-0.7968, -0.3549] | 0.0460 | 0.7102 |
| `tfidf_svd::trajectory_only` | -0.4198 | [-0.7104, -0.3102] | 0.1116 | 0.5314 |

## Local Encoder

- `{'status': 'ok', 'backend': '/data/CSK/causal-agent-safety-research/models/protectai_deberta-v3-base-prompt-injection-v2', 'similarities': {'same_effect_similarity': {'mean': 0.5575269743874298, 'n': 201, 'min': -0.44456976652145386, 'max': 0.999065101146698}, 'same_tool_similarity': {'mean': 0.774171898762385, 'n': 24, 'min': 0.2972795069217682, 'max': 0.9937508702278137}, 'same_effect_different_tool_similarity': {'mean': 0.5523270758179327, 'n': 192, 'min': -0.44456976652145386, 'max': 0.999065101146698}, 'same_tool_different_effect_similarity': {'mean': 0.8376001516977946, 'n': 15, 'min': 0.5747439861297607, 'max': 0.9937508702278137}, 'effect_vs_tool_clustering_gap': -0.28527307587986184, 'gap_interpretation': 'positive means records are closer by realized effect than by same tool surface'}, 'bootstrap_note': 'Local encoder bootstrap is omitted to keep Phase 3 runtime bounded; tfidf_svd backend carries bootstrap/permutation controls.'}`

## Claim Boundary

- Mechanism Phase 3 is diagnostic: it tests representation/text clustering under controlled records and does not prove causal understanding or deployed safety.
