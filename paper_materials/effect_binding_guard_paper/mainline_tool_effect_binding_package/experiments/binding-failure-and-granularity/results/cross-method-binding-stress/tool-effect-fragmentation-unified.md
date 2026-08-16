# Unified Tool-Effect Fragmentation Comparison

## Required Questions

- **Does the method detect realized effects or tool surfaces?** Compare tool-name/schema baselines against effect/resource and execution-evidence baselines; high ToolProxyGap indicates surface dependence.
- **Does performance collapse under tool surface shift?** Use held-out-tool FNR and Effect Invariance Gap; v1 reports these per method and system.
- **Which granularity is most robust to fragmentation?** Compare systems by granularity through the system-specific tables; v1 has paper-grade AgentDojo and proxy step/graph diagnostics.
- **Do graph/provenance/evidence-grounded methods reduce fragmentation?** Evidence-grounded rows available: 8 paper-grade rows; graph rows available: 8 proxy rows.
- **Do row-level metrics overestimate action-level safety?** Use intra-action inconsistency, action-level decision error, unsafe pre-allow, and safe false deny together; do not rely on row-level FNR alone.

## Paper-Grade Environment Results

| System | Status | Method | N | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Intra-action inconsistency | Action-level error | Access |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `agentdojo` | `paper_grade` | `arg_schema_classifier` | 1296 | 0.500 | 0.000 | 0.778 | NA | 0.500 | 0.500 | PASS |
| `agentdojo` | `paper_grade` | `effect_resource_abstraction` | 1296 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `execution_evidence_upper_bound` | 1296 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `plan_level_llm_judge` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `static_llm_self_audit` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `step_level_classifier` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `tool_name_classifier` | 1296 | 1.000 | 0.667 | 0.704 | NA | 0.667 | 0.333 | PASS |
| `agentdojo` | `paper_grade` | `trajectory_level_classifier` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |

## Original Method Reproductions

| System | Status | Method | N | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Intra-action inconsistency | Action-level error | Access |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NA | NA | NA | 0 | NA | NA | NA | NA | NA | NA | NA |

## Proxy Diagnostics

| System | Status | Method | N | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Intra-action inconsistency | Action-level error | Access |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `toolsafe` | `proxy_diagnostic` | `arg_schema_classifier` | 216 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `effect_resource_abstraction` | 216 | 0.083 | 0.000 | 0.067 | 0.417 | 0.333 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 216 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `plan_level_llm_judge` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `static_llm_self_audit` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `step_level_classifier` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `tool_name_classifier` | 216 | 1.000 | 0.667 | 0.733 | 0.000 | 0.333 | 0.667 | PASS |
| `toolsafe` | `proxy_diagnostic` | `trajectory_level_classifier` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `arg_schema_classifier` | 135 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `effect_resource_abstraction` | 135 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 135 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `plan_level_llm_judge` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `static_llm_self_audit` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `step_level_classifier` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `tool_name_classifier` | 135 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `trajectory_level_classifier` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `arg_schema_classifier` | 216 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `safiron` | `proxy_diagnostic` | `effect_resource_abstraction` | 216 | 0.267 | 0.000 | 0.222 | 0.333 | 0.417 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 216 | 0.000 | 0.000 | 0.000 | 0.000 | 0.375 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `plan_level_llm_judge` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `static_llm_self_audit` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `step_level_classifier` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `tool_name_classifier` | 216 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `safiron` | `proxy_diagnostic` | `trajectory_level_classifier` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |

## Baselines

| System | Status | Method | N | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Intra-action inconsistency | Action-level error | Access |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `agentdojo` | `paper_grade` | `arg_schema_classifier` | 1296 | 0.500 | 0.000 | 0.778 | NA | 0.500 | 0.500 | PASS |
| `agentdojo` | `paper_grade` | `plan_level_llm_judge` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `static_llm_self_audit` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `step_level_classifier` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `tool_name_classifier` | 1296 | 1.000 | 0.667 | 0.704 | NA | 0.667 | 0.333 | PASS |
| `agentdojo` | `paper_grade` | `trajectory_level_classifier` | 1296 | 0.625 | 0.000 | 0.486 | NA | 0.625 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `arg_schema_classifier` | 216 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `plan_level_llm_judge` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `static_llm_self_audit` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `step_level_classifier` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `tool_name_classifier` | 216 | 1.000 | 0.667 | 0.733 | 0.000 | 0.333 | 0.667 | PASS |
| `toolsafe` | `proxy_diagnostic` | `trajectory_level_classifier` | 216 | 0.083 | 0.000 | 0.075 | 0.865 | 0.417 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `arg_schema_classifier` | 135 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `plan_level_llm_judge` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `static_llm_self_audit` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `step_level_classifier` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `tool_name_classifier` | 135 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `trajectory_level_classifier` | 135 | 0.500 | 0.000 | 0.405 | 0.250 | 0.600 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `arg_schema_classifier` | 216 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `safiron` | `proxy_diagnostic` | `plan_level_llm_judge` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `static_llm_self_audit` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `step_level_classifier` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `tool_name_classifier` | 216 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 1.000 | PASS |
| `safiron` | `proxy_diagnostic` | `trajectory_level_classifier` | 216 | 0.667 | 0.000 | 0.562 | 0.250 | 0.792 | 0.000 | PASS |

## Oracle / Upper-Bound Rows

| System | Status | Method | N | Held-out-tool FNR | ToolProxyGap | Unsafe pre-allow | Safe false deny | Intra-action inconsistency | Action-level error | Access |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `agentdojo` | `paper_grade` | `effect_resource_abstraction` | 1296 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 | PASS |
| `agentdojo` | `paper_grade` | `execution_evidence_upper_bound` | 1296 | 0.000 | 0.000 | 0.000 | NA | 0.000 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `effect_resource_abstraction` | 216 | 0.083 | 0.000 | 0.067 | 0.417 | 0.333 | 0.000 | PASS |
| `toolsafe` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 216 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `effect_resource_abstraction` | 135 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 | PASS |
| `ipiguard` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 135 | 0.000 | 0.000 | 0.000 | 0.000 | 0.200 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `effect_resource_abstraction` | 216 | 0.267 | 0.000 | 0.222 | 0.333 | 0.417 | 0.000 | PASS |
| `safiron` | `proxy_diagnostic` | `execution_evidence_upper_bound` | 216 | 0.000 | 0.000 | 0.000 | 0.000 | 0.375 | 0.000 | PASS |

## Adapter Failures

| System | Status | Repo | Commit | Artifact | Notes |
|---|---|---|---|---|---|
| `camel` | `adapter_failed` | https://github.com/google-research/camel-prompt-injection | `f083b6b396399d3b3c7f2ddaf613a5945eaf32d8` | `/data/CSK/causal-agent-safety-research/external/systems/camel` | Repository is cloned for provenance, but no non-side-effectful Tool-Effect stress adapter is wired in this scaffold. CaMeL remains a structural-defense contrast only; no performance claims are made. |

## Claim Boundary

- Only systems with paper_grade_eligible=true support paper-grade conclusions.
- Proxy diagnostics identify stress-test feasibility and likely failure modes; they are not author-method reproductions.
- Negative results must be separated from adapter/reproduction failures.
