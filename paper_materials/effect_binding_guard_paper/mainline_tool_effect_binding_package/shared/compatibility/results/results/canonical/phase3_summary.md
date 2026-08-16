# E47 Phase 3 Summary

## Status

- AgentDojo Phase 3 balanced stress table generated.
- ToolSafe/TS-Guard and Safiron official checkpoints pass dry-run inference smokes; completed E47 official-checkpoint custom stress results are reported when present.
- IPIGuard and CaMeL pass local-model substitute smokes only.
- Mechanism Phase 3 includes bootstrap, permutation controls, and ablations.
- Evidence Phase 3 separates non-oracle env-diff diagnostic from oracle upper bounds.

## Answers

- **What is paper-grade evidence?** AgentDojo local T122-derived custom stress tables are the current paper-grade environment evidence.
- **What is original-method evidence?** Released official checkpoints have completed E47 custom stress for toolsafe, safiron. This is original-checkpoint evidence on adapted stress inputs, not original-paper benchmark reproduction.
- **What is proxy-only?** IPIGuard and CaMeL use local-Qwen substitute smokes. These results validate dry-run adapter feasibility only and do not establish the original methods' behavior.
- **What is upper-bound?** effect_resource_abstraction and execution_evidence_upper_bound remain oracle/upper-bound rows.
- **Does random split overestimate safety?** Tool-name random-vs-heldout FNR delta is 0.6667; positive values mean random split overestimates held-out safety.
- **Does held-out-tool stress reveal fragmentation?** Yes for tool-surface baselines in AgentDojo Phase 3; see held-out-tool FNR and degradation table.
- **Does plan/step/trajectory text solve fragmentation?** No automatic guarantee; text proxy baselines still show nonzero held-out-tool FNR and action errors.
- **Does representation cluster by tool or effect?** Primary mechanism gap is -0.4239; negative values indicate same-tool proximity is stronger than same-effect proximity.
- **Does non-oracle execution evidence help?** non_oracle_envdiff_verifier held-out-tool FNR is 0.0000 in the saved-evidence diagnostic.
- **What still blocks a top-tier paper?** Non-AgentDojo official-checkpoint custom stress still uses proxy or published-derived expected labels and is not an original-paper benchmark reproduction; upper-bound evidence rows and mechanism diagnostics also remain separate from deployable-method evidence.

## Official-Checkpoint Custom Stress

| System | Cases | Parse-valid | FNR | Safe false deny | Same-effect consistency | Action error | Scope |
|---|---:|---:|---:|---:|---:|---:|---|
| `toolsafe` | 216 | 216 | 0.1750 | 0.1042 | 0.1667 | 0.3750 | `original_method_custom_stress` |
| `safiron` | 216 | 216 | 0.1181 | 0.3194 | 0.3750 | 0.0000 | `original_method_custom_stress` |

## Claim Boundary

- Can claim: AgentDojo custom stress shows tool-surface baselines fail under held-out-tool shift.
- Can claim: Current plan/step/trajectory text baselines do not automatically remove fragmentation.
- Can claim: Mechanism diagnostic suggests tool-surface proximity can dominate same-effect proximity.
- Can claim: Effect/resource and execution-evidence upper bounds are stable in current tests.
- Can claim: Non-oracle evidence helps only to the extent shown by the Phase 3 evidence diagnostic.
- Cannot claim: ToolSafe or Safiron original-paper methods fail from E47 custom stress alone; the released checkpoints ran, but the benchmark and expected labels are adapted.
- Cannot claim: IPIGuard or CaMeL original methods fail; current results are local-model substitutes.
- Cannot claim: Graph/provenance methods generally fail.
- Cannot claim: Execution evidence is a deployable complete safety solution.
- Cannot claim: LLMs do not understand tools at all.
- Cannot claim: All trajectory methods are ineffective.
