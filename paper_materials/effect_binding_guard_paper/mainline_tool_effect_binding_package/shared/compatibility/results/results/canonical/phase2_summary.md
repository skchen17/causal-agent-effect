# E47 Phase 2 Summary

## Status

- AgentDojo random/held-out/same-effect stress comparison is complete over the local paper-grade stress environment.
- Non-AgentDojo systems have complete reproduction audits; original-method results require missing model/API/runtime prerequisites to be satisfied.
- Mechanism effect-vs-tool clustering experiment is diagnostic and local-only.

## Answers

- **Does performance degrade from random split to held-out-tool split?** tool_name_classifier random-vs-heldout FNR delta = 0.2438; held-out stress worsens relative to the random subset.
- **Do methods cluster by tool surface or by realized effect?** Effect-vs-tool clustering gap is -0.4239, indicating tool-surface proximity is at least as strong as same-effect proximity in this controlled diagnostic.
- **Does looking at plan/step/trajectory text solve fragmentation?** No automatic guarantee in this diagnostic: text/plan/step/trajectory proxy baselines are reported separately and must be compared against held-out-tool FNR and action-level errors.
- **Do graph/evidence/provenance methods reduce fragmentation?** Effect/resource and execution-evidence rows are more stable in current tests, but they are marked upper-bound unless implemented as non-oracle verifiers.
- **Where do row-level metrics disagree with action-level safety?** See paired_deltas.row_vs_action and failure examples; row FNR and action-level decision error are reported separately.
- **Which results are paper-grade, original-method, proxy-only, or upper-bound?** AgentDojo is paper-grade environment only; current non-AgentDojo systems are proxy diagnostics or complete adapter-failure audits unless reproduction_audit reports original_method_runnable.
- **What still prevents a top-tier paper claim?** Missing exact original-method reproductions, proxy labels for non-AgentDojo systems, upper-bound effect/evidence rows, and limited mechanism evidence prevent broad cross-paper claims.

## Acceptance Gates

- `agentdojo_random_vs_heldout_complete`: `True`
- `non_agentdojo_original_or_complete_audit`: `True`
- `mechanism_gap_reported`: `True`
- `failure_examples_generated`: `True`
- `claim_boundary_present`: `True`

## Claim Boundary

- Can claim: Tool-surface baselines fail under AgentDojo custom stress when reported as paper-grade local stress evidence.
- Can claim: Text/plan/step/trajectory views do not automatically remove fragmentation in current proxy tests.
- Can claim: Effect/resource and execution-evidence upper bounds are more stable in current tests.
- Can claim: Proxy diagnostics identify likely failure modes for step-level, graph-level, and plan-level systems.
- Cannot claim: ToolSafe, IPIGuard, Safiron, or CaMeL original method failure unless an official-method adapter is actually run.
- Cannot claim: Graph/provenance methods generally fail.
- Cannot claim: Execution evidence is a deployable complete safety solution.
