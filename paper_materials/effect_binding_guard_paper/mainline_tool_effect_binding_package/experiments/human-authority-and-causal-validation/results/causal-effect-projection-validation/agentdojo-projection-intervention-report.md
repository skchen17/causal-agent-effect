# E85 AgentDojo Reviewed-Projection Interventions

Status: `passed_with_projection_gaps`.

- Reviewed and source-verified tool instances: 16
- Executed base calls: 16

## Aggregate By Contract Variant

| Variant | Cases | Eligible | Passed | Rate | Gaps | Over-sensitive | Unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|
| eight_field_projection | 80 | 80 | 65 | 0.812 | 15 | 0 | 0 |
| typed_qualifier_projection | 80 | 80 | 80 | 1.000 | 0 | 0 | 0 |

## Metrics By Variant And Case Type

| Variant | Type | Cases | Eligible | Passed | Rate | Gaps | Over-sensitive | Unsupported |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| eight_field_projection | descriptor_swap | 16 | 16 | 16 | 1.000 | 0 | 0 | 0 |
| eight_field_projection | expansion | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |
| eight_field_projection | interaction | 11 | 11 | 10 | 0.909 | 1 | 0 | 0 |
| eight_field_projection | omitted_default | 1 | 1 | 0 | 0.000 | 1 | 0 | 0 |
| eight_field_projection | single_field | 35 | 35 | 22 | 0.629 | 13 | 0 | 0 |
| eight_field_projection | surface_placebo | 16 | 16 | 16 | 1.000 | 0 | 0 | 0 |
| typed_qualifier_projection | descriptor_swap | 16 | 16 | 16 | 1.000 | 0 | 0 | 0 |
| typed_qualifier_projection | expansion | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |
| typed_qualifier_projection | interaction | 11 | 11 | 11 | 1.000 | 0 | 0 | 0 |
| typed_qualifier_projection | omitted_default | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |
| typed_qualifier_projection | single_field | 35 | 35 | 35 | 1.000 | 0 | 0 | 0 |
| typed_qualifier_projection | surface_placebo | 16 | 16 | 16 | 1.000 | 0 | 0 | 0 |

## Claim Boundary

Source-grounded sandbox interventions over 16 reviewed AgentDojo v1.1.2 tool projections. The check compares the frozen eight-field atom projection with a typed effect-specific qualifier extension on identical generated cases. It does not establish complete contracts, deployed safety, or attack robustness.
