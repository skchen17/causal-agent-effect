# Hook-Based pIIA Controls Pilot

- Data: `qwen3-8b_scenarios_mainconf_v2`
- Model: `Qwen/Qwen3-8B`
- Effects: file_content_read, file_written, content_fetched
- Layers: [12, 24, 32]
- Token modes: ['mean_broadcast', 'last_token']
- Raw intervention rows: 144

## Aggregate Outcomes

| Effect | Layer | Token mode | Mode | N | Score inc | Threshold cross | Mean delta |
|---|---:|---|---|---:|---:|---:|---:|
| `content_fetched` | 12 | `last_token` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `content_fetched` | 12 | `last_token` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `content_fetched` | 12 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `content_fetched` | 12 | `last_token` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `content_fetched` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 1.0 | 0.0 | 0.0002 |
| `content_fetched` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `content_fetched` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 1.0 | 0.0 | 0.0001 |
| `content_fetched` | 12 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0136 |
| `content_fetched` | 24 | `last_token` | `different_effect_same_form_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `content_fetched` | 24 | `last_token` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `content_fetched` | 24 | `last_token` | `same_effect_wrong_form_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `content_fetched` | 24 | `last_token` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `content_fetched` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 1.0 | 0.0 | 0.0001 |
| `content_fetched` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `content_fetched` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `content_fetched` | 24 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0631 |
| `content_fetched` | 32 | `last_token` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `content_fetched` | 32 | `last_token` | `matched_norm_random_direction` | 2 | 0.0 | 0.0 | -0.0 |
| `content_fetched` | 32 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.0 | 0.0 | -0.0 |
| `content_fetched` | 32 | `last_token` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `content_fetched` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 1.0 | 0.0 | 0.0005 |
| `content_fetched` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `content_fetched` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `content_fetched` | 32 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 1.0 | 0.9845 |
| `file_content_read` | 12 | `last_token` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `file_content_read` | 12 | `last_token` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `file_content_read` | 12 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `file_content_read` | 12 | `last_token` | `within_tool_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `file_content_read` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_content_read` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_content_read` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `file_content_read` | 12 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `file_content_read` | 24 | `last_token` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_content_read` | 24 | `last_token` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `file_content_read` | 24 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.5 | 0.0 | -0.0 |
| `file_content_read` | 24 | `last_token` | `within_tool_direction` | 2 | 0.0 | 0.0 | -0.0 |
| `file_content_read` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 1.0 | 0.0 | 0.0027 |
| `file_content_read` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0007 |
| `file_content_read` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 0.5 | 0.0 | 0.0415 |
| `file_content_read` | 24 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.2228 |
| `file_content_read` | 32 | `last_token` | `different_effect_same_form_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `file_content_read` | 32 | `last_token` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_content_read` | 32 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_content_read` | 32 | `last_token` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0 |
| `file_content_read` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 0.0 | 0.0 | -0.0006 |
| `file_content_read` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_content_read` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 0.0 | 0.0 | -0.0019 |
| `file_content_read` | 32 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 1.0 | 0.8728 |
| `file_written` | 12 | `last_token` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | 0.0001 |
| `file_written` | 12 | `last_token` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0001 |
| `file_written` | 12 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.5 | 0.0 | 0.0001 |
| `file_written` | 12 | `last_token` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0001 |
| `file_written` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | 0.0328 |
| `file_written` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.0 | 0.0 | -0.0002 |
| `file_written` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 0.0 | 0.0 | -0.0006 |
| `file_written` | 12 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0182 |
| `file_written` | 24 | `last_token` | `different_effect_same_form_direction` | 2 | 0.0 | 0.0 | -0.0001 |
| `file_written` | 24 | `last_token` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_written` | 24 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.5 | 0.0 | 0.0 |
| `file_written` | 24 | `last_token` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0002 |
| `file_written` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 1.0 | 0.5 | 0.3857 |
| `file_written` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 0.5 | 0.0 | -0.0003 |
| `file_written` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 1.0 | 0.0 | 0.0011 |
| `file_written` | 24 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.3079 |
| `file_written` | 32 | `last_token` | `different_effect_same_form_direction` | 2 | 0.0 | 0.0 | -0.0002 |
| `file_written` | 32 | `last_token` | `matched_norm_random_direction` | 2 | 0.0 | 0.0 | -0.0003 |
| `file_written` | 32 | `last_token` | `same_effect_wrong_form_direction` | 2 | 0.0 | 0.0 | -0.0003 |
| `file_written` | 32 | `last_token` | `within_tool_direction` | 2 | 1.0 | 0.0 | 0.0004 |
| `file_written` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 2 | 0.5 | 0.0 | -0.0011 |
| `file_written` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 2 | 1.0 | 0.0 | 0.0001 |
| `file_written` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 2 | 1.0 | 0.0 | 0.0005 |
| `file_written` | 32 | `mean_broadcast` | `within_tool_direction` | 2 | 1.0 | 1.0 | 0.975 |

## pIIA-Drop Pilot Summary

| Effect | Preferred layer | Mean pIIA-Drop | Details |
|---|---:|---:|---|
| `content_fetched` | 24 | 0.0 | last_token: 1.0->1.0; mean_broadcast: 1.0->1.0 |
| `file_content_read` | 24 | 0.0 | last_token: 0.0->0.5; mean_broadcast: 1.0->0.5 |
| `file_written` | 24 | 0.25 | last_token: 1.0->0.5; mean_broadcast: 1.0->1.0 |

## pIIA-Drop vs LOTO Gap

- Spearman rho against max LOTO FNR gap: 0.0
- Spearman rho against max heldout FNR: 0.0
- Evaluable effects: 3

## Caveats

- This is a pilot hook-control run with very small n per condition.
- Score-increase pIIA is a probe-mediated activation transfer diagnostic, not SCM IIA.
- The random control is matched to the within-tool direction norm before intervention.
- The wrong-form direction uses another tool's same-effect probe; source/base examples remain from the evaluation tool.
- A confirmatory run should increase effects, evaluation tools, and pairs per condition before paper claims are strengthened.
