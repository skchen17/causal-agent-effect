# Hook-Based pIIA Controls Confirmatory Scale-Up

- Data: `qwen3-8b_scenarios_mainconf_v2`
- Model: `Qwen/Qwen3-8B`
- Effects: file_content_read, file_written, content_fetched, file_deleted, network_egress, tool_error
- Layers: [12, 24, 32]
- Token modes: ['mean_broadcast', 'last_token']
- Raw intervention rows: 864

## Aggregate Outcomes

| Effect | Layer | Token mode | Mode | N | Score inc | Threshold cross | Mean delta |
|---|---:|---|---|---:|---:|---:|---:|
| `content_fetched` | 12 | `last_token` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `content_fetched` | 12 | `last_token` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `content_fetched` | 12 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.5 | 0.0 | -0.0 |
| `content_fetched` | 12 | `last_token` | `within_tool_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `content_fetched` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 1.0 | 0.0 | 0.0016 |
| `content_fetched` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | -0.0002 |
| `content_fetched` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.001 |
| `content_fetched` | 12 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0267 |
| `content_fetched` | 24 | `last_token` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.0 | 0.0 |
| `content_fetched` | 24 | `last_token` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | 0.0 |
| `content_fetched` | 24 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0 |
| `content_fetched` | 24 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0003 |
| `content_fetched` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.0041 |
| `content_fetched` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | 0.0001 |
| `content_fetched` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0005 |
| `content_fetched` | 24 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.3333 | 0.324 |
| `content_fetched` | 32 | `last_token` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.0003 |
| `content_fetched` | 32 | `last_token` | `matched_norm_random_direction` | 6 | 0.8333 | 0.0 | 0.0001 |
| `content_fetched` | 32 | `last_token` | `same_effect_wrong_form_direction` | 6 | 1.0 | 0.0 | 0.0003 |
| `content_fetched` | 32 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0009 |
| `content_fetched` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.1667 | 0.112 |
| `content_fetched` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.8333 | 0.0 | 0.0001 |
| `content_fetched` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0068 |
| `content_fetched` | 32 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 1.0 | 0.9366 |
| `file_content_read` | 12 | `last_token` | `different_effect_same_form_direction` | 6 | 0.3333 | 0.0 | 0.0003 |
| `file_content_read` | 12 | `last_token` | `matched_norm_random_direction` | 6 | 0.3333 | 0.0 | 0.0003 |
| `file_content_read` | 12 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.5 | 0.0 | 0.0003 |
| `file_content_read` | 12 | `last_token` | `within_tool_direction` | 6 | 0.3333 | 0.0 | 0.0003 |
| `file_content_read` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.1667 | 0.0 | -0.0005 |
| `file_content_read` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.3333 | 0.0 | 0.0002 |
| `file_content_read` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0002 |
| `file_content_read` | 12 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0166 |
| `file_content_read` | 24 | `last_token` | `different_effect_same_form_direction` | 6 | 0.5 | 0.0 | 0.0003 |
| `file_content_read` | 24 | `last_token` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | 0.0 |
| `file_content_read` | 24 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0 |
| `file_content_read` | 24 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0004 |
| `file_content_read` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.3333 | 0.2377 |
| `file_content_read` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.3333 | 0.0 | -0.0002 |
| `file_content_read` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0148 |
| `file_content_read` | 24 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.3333 | 0.3849 |
| `file_content_read` | 32 | `last_token` | `different_effect_same_form_direction` | 6 | 0.5 | 0.0 | 0.0011 |
| `file_content_read` | 32 | `last_token` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | 0.0001 |
| `file_content_read` | 32 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.5 | 0.0 | 0.0001 |
| `file_content_read` | 32 | `last_token` | `within_tool_direction` | 6 | 0.8333 | 0.0 | 0.0016 |
| `file_content_read` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.5 | 0.1667 | 0.1473 |
| `file_content_read` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.1667 | 0.0 | -0.0001 |
| `file_content_read` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0004 |
| `file_content_read` | 32 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 1.0 | 0.8976 |
| `file_deleted` | 12 | `last_token` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.0004 |
| `file_deleted` | 12 | `last_token` | `matched_norm_random_direction` | 6 | 0.8333 | 0.0 | 0.0004 |
| `file_deleted` | 12 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0003 |
| `file_deleted` | 12 | `last_token` | `within_tool_direction` | 6 | 0.8333 | 0.0 | 0.0004 |
| `file_deleted` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.5 | 0.0 | 0.0147 |
| `file_deleted` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | -0.0 |
| `file_deleted` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0006 |
| `file_deleted` | 12 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0155 |
| `file_deleted` | 24 | `last_token` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.0 | 0.0002 |
| `file_deleted` | 24 | `last_token` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | 0.0001 |
| `file_deleted` | 24 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0001 |
| `file_deleted` | 24 | `last_token` | `within_tool_direction` | 6 | 0.8333 | 0.0 | 0.0002 |
| `file_deleted` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.5 | 0.4629 |
| `file_deleted` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | 0.0001 |
| `file_deleted` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0016 |
| `file_deleted` | 24 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.5 | 0.4894 |
| `file_deleted` | 32 | `last_token` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.0004 |
| `file_deleted` | 32 | `last_token` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `file_deleted` | 32 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.5 | 0.0 | 0.0 |
| `file_deleted` | 32 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0007 |
| `file_deleted` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.5 | 0.4945 |
| `file_deleted` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | 0.0003 |
| `file_deleted` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 1.0 | 0.0 | 0.0422 |
| `file_deleted` | 32 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 1.0 | 0.9054 |
| `file_written` | 12 | `last_token` | `different_effect_same_form_direction` | 6 | 0.1667 | 0.0 | -0.0001 |
| `file_written` | 12 | `last_token` | `matched_norm_random_direction` | 6 | 0.1667 | 0.0 | -0.0 |
| `file_written` | 12 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.3333 | 0.0 | -0.0001 |
| `file_written` | 12 | `last_token` | `within_tool_direction` | 6 | 0.8333 | 0.0 | 0.0 |
| `file_written` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.0032 |
| `file_written` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 1.0 | 0.0 | 0.0001 |
| `file_written` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 1.0 | 0.0 | 0.0002 |
| `file_written` | 12 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0051 |
| `file_written` | 24 | `last_token` | `different_effect_same_form_direction` | 6 | 0.3333 | 0.0 | 0.0001 |
| `file_written` | 24 | `last_token` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | 0.0 |
| `file_written` | 24 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `file_written` | 24 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0005 |
| `file_written` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.5 | 0.0 | 0.0514 |
| `file_written` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | 0.0 |
| `file_written` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 1.0 | 0.0 | 0.0016 |
| `file_written` | 24 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.1667 | 0.2942 |
| `file_written` | 32 | `last_token` | `different_effect_same_form_direction` | 6 | 0.1667 | 0.0 | -0.0 |
| `file_written` | 32 | `last_token` | `matched_norm_random_direction` | 6 | 0.1667 | 0.0 | -0.0 |
| `file_written` | 32 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `file_written` | 32 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0002 |
| `file_written` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.014 |
| `file_written` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | 0.0 |
| `file_written` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0007 |
| `file_written` | 32 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 1.0 | 0.9804 |
| `network_egress` | 12 | `last_token` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.0 | 0.0003 |
| `network_egress` | 12 | `last_token` | `matched_norm_random_direction` | 6 | 0.3333 | 0.0 | -0.0 |
| `network_egress` | 12 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0003 |
| `network_egress` | 12 | `last_token` | `within_tool_direction` | 6 | 0.6667 | 0.0 | 0.0005 |
| `network_egress` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.0 | 0.0014 |
| `network_egress` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | -0.0 |
| `network_egress` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.8333 | 0.0 | 0.0 |
| `network_egress` | 12 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0019 |
| `network_egress` | 24 | `last_token` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.0001 |
| `network_egress` | 24 | `last_token` | `matched_norm_random_direction` | 6 | 0.3333 | 0.0 | -0.0001 |
| `network_egress` | 24 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.3333 | 0.0 | -0.0001 |
| `network_egress` | 24 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0001 |
| `network_egress` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 1.0 | 0.0 | 0.1492 |
| `network_egress` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.1667 | 0.0 | 0.0 |
| `network_egress` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.5 | 0.0 | 0.0018 |
| `network_egress` | 24 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.1196 |
| `network_egress` | 32 | `last_token` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.001 |
| `network_egress` | 32 | `last_token` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | 0.0001 |
| `network_egress` | 32 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0001 |
| `network_egress` | 32 | `last_token` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.002 |
| `network_egress` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 1.0 | 0.5 | 0.4796 |
| `network_egress` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.3333 | 0.0 | -0.0 |
| `network_egress` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.5 | 0.0 | 0.0 |
| `network_egress` | 32 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 1.0 | 0.8751 |
| `tool_error` | 12 | `last_token` | `different_effect_same_form_direction` | 6 | 0.8333 | 0.0 | 0.0 |
| `tool_error` | 12 | `last_token` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `tool_error` | 12 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `tool_error` | 12 | `last_token` | `within_tool_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `tool_error` | 12 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 1.0 | 0.0 | 0.0016 |
| `tool_error` | 12 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | -0.0003 |
| `tool_error` | 12 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0003 |
| `tool_error` | 12 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.0 | 0.0073 |
| `tool_error` | 24 | `last_token` | `different_effect_same_form_direction` | 6 | 0.6667 | 0.0 | 0.0001 |
| `tool_error` | 24 | `last_token` | `matched_norm_random_direction` | 6 | 0.5 | 0.0 | 0.0 |
| `tool_error` | 24 | `last_token` | `same_effect_wrong_form_direction` | 6 | 0.6667 | 0.0 | 0.0 |
| `tool_error` | 24 | `last_token` | `within_tool_direction` | 6 | 0.8333 | 0.0 | 0.0002 |
| `tool_error` | 24 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 1.0 | 0.0 | 0.065 |
| `tool_error` | 24 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | -0.0 |
| `tool_error` | 24 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 1.0 | 0.0 | 0.0062 |
| `tool_error` | 24 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.1667 | 0.2503 |
| `tool_error` | 32 | `last_token` | `different_effect_same_form_direction` | 6 | 1.0 | 0.0 | 0.0003 |
| `tool_error` | 32 | `last_token` | `matched_norm_random_direction` | 6 | 0.8333 | 0.0 | 0.0 |
| `tool_error` | 32 | `last_token` | `same_effect_wrong_form_direction` | 6 | 1.0 | 0.0 | 0.0001 |
| `tool_error` | 32 | `last_token` | `within_tool_direction` | 6 | 0.8333 | 0.0 | 0.0003 |
| `tool_error` | 32 | `mean_broadcast` | `different_effect_same_form_direction` | 6 | 1.0 | 0.3333 | 0.356 |
| `tool_error` | 32 | `mean_broadcast` | `matched_norm_random_direction` | 6 | 0.6667 | 0.0 | 0.0 |
| `tool_error` | 32 | `mean_broadcast` | `same_effect_wrong_form_direction` | 6 | 0.3333 | 0.0 | -0.0001 |
| `tool_error` | 32 | `mean_broadcast` | `within_tool_direction` | 6 | 1.0 | 0.3333 | 0.3956 |

## pIIA-Drop Summary

| Effect | Preferred layer | Mean pIIA-Drop | Details |
|---|---:|---:|---|
| `content_fetched` | 24 | 0.25 | last_token: 1.0->0.8333; mean_broadcast: 1.0->0.6667 |
| `file_content_read` | 24 | 0.25 | last_token: 1.0->0.6667; mean_broadcast: 1.0->0.8333 |
| `file_deleted` | 24 | 0.0833 | last_token: 0.8333->0.8333; mean_broadcast: 1.0->0.8333 |
| `file_written` | 24 | 0.1666 | last_token: 1.0->0.6667; mean_broadcast: 1.0->1.0 |
| `network_egress` | 24 | 0.5834 | last_token: 1.0->0.3333; mean_broadcast: 1.0->0.5 |
| `tool_error` | 24 | 0.0833 | last_token: 0.8333->0.6667; mean_broadcast: 1.0->1.0 |

## pIIA-Drop vs LOTO Gap

- Spearman rho against max LOTO FNR gap: 0.2648
- Spearman rho against max heldout FNR: 0.5296
- Evaluable effects: 6

## Caveats

- This is a compact confirmatory hook-control run; it is larger than the 144-row pilot but still not a final mechanism proof.
- Score-increase pIIA is a probe-mediated activation transfer diagnostic, not SCM IIA.
- The random control is matched to the within-tool direction norm before intervention.
- The wrong-form direction uses another tool's same-effect probe; source/base examples remain from the evaluation tool.
- Strong paper claims should still treat this as probe-mediated mechanism evidence and report the limited per-condition sample size.
