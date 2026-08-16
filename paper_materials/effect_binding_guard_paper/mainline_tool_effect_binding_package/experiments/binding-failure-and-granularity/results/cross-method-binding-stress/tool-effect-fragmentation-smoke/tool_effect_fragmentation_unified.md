# Unified Tool-Effect Fragmentation Comparison

## Required Questions

- **Does the method detect realized effects or tool surfaces?** Compare tool-name/schema baselines against effect/resource and execution-evidence baselines; high ToolProxyGap indicates surface dependence.
- **Does performance collapse under tool surface shift?** Use held-out-tool FNR and Effect Invariance Gap; v1 reports these per method and system.
- **Which granularity is most robust to fragmentation?** Compare systems by granularity through the system-specific tables; v1 has paper-grade AgentDojo and proxy step/graph diagnostics.
- **Do graph/provenance/evidence-grounded methods reduce fragmentation?** Evidence-grounded rows available: 8 paper-grade rows; graph rows available: 8 proxy rows.
- **Do row-level metrics overestimate action-level safety?** Use row/action mismatch, unsafe pre-allow, and safe false deny together; do not rely on row-level FNR alone.

## Comparison Table

| System | Status | Method | N | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Row/action mismatch |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `agentdojo` | `paper_grade` | `arg_schema_classifier` | 216 | 0.500 | 0.000 | 0.778 | NA | 0.500 |
| `agentdojo` | `paper_grade` | `effect_resource_abstraction` | 216 | 0.000 | 0.000 | 0.000 | NA | 0.000 |
| `agentdojo` | `paper_grade` | `execution_evidence_upper_bound` | 216 | 0.000 | 0.000 | 0.000 | NA | 0.000 |
| `agentdojo` | `paper_grade` | `plan_level_llm_judge` | 216 | 0.500 | 0.000 | 0.389 | NA | 0.500 |
| `agentdojo` | `paper_grade` | `static_llm_self_audit` | 216 | 0.500 | 0.000 | 0.389 | NA | 0.500 |
| `agentdojo` | `paper_grade` | `step_level_classifier` | 216 | 0.500 | 0.000 | 0.389 | NA | 0.500 |
| `agentdojo` | `paper_grade` | `tool_name_classifier` | 216 | 1.000 | 1.000 | 0.556 | NA | 1.000 |
| `agentdojo` | `paper_grade` | `trajectory_level_classifier` | 216 | 0.500 | 0.000 | 0.389 | NA | 0.500 |
| `toolsafe` | `proxy_diagnostic` | `arg_schema_classifier` | 36 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| `toolsafe` | `proxy_diagnostic` | `effect_resource_abstraction` | 36 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 |
| `toolsafe` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 36 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 |
| `toolsafe` | `proxy_diagnostic` | `plan_level_llm_judge` | 36 | 0.000 | 0.000 | 0.100 | 0.125 | 0.500 |
| `toolsafe` | `proxy_diagnostic` | `static_llm_self_audit` | 36 | 0.000 | 0.000 | 0.100 | 0.125 | 0.500 |
| `toolsafe` | `proxy_diagnostic` | `step_level_classifier` | 36 | 0.000 | 0.000 | 0.100 | 0.125 | 0.500 |
| `toolsafe` | `proxy_diagnostic` | `tool_name_classifier` | 36 | 1.000 | 1.000 | 0.600 | 0.000 | 0.500 |
| `toolsafe` | `proxy_diagnostic` | `trajectory_level_classifier` | 36 | 0.000 | 0.000 | 0.100 | 0.125 | 0.500 |
| `ipiguard` | `proxy_diagnostic` | `arg_schema_classifier` | 36 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| `ipiguard` | `proxy_diagnostic` | `effect_resource_abstraction` | 36 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| `ipiguard` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 36 | 0.000 | 0.000 | 0.000 | 0.000 | 0.250 |
| `ipiguard` | `proxy_diagnostic` | `plan_level_llm_judge` | 36 | 0.667 | 0.000 | 0.536 | 0.250 | 0.750 |
| `ipiguard` | `proxy_diagnostic` | `static_llm_self_audit` | 36 | 0.667 | 0.000 | 0.536 | 0.250 | 0.750 |
| `ipiguard` | `proxy_diagnostic` | `step_level_classifier` | 36 | 0.667 | 0.000 | 0.536 | 0.250 | 0.750 |
| `ipiguard` | `proxy_diagnostic` | `tool_name_classifier` | 36 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| `ipiguard` | `proxy_diagnostic` | `trajectory_level_classifier` | 36 | 0.667 | 0.000 | 0.536 | 0.250 | 0.750 |

## Claim Boundary

- Only systems with paper_grade_eligible=true support paper-grade conclusions.
- Proxy diagnostics identify stress-test feasibility and likely failure modes; they are not author-method reproductions.
- Negative results must be separated from adapter/reproduction failures.
