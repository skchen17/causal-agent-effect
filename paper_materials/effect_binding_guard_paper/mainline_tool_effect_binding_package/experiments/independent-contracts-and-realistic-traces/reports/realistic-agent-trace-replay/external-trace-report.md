# E61 External Trace Subset Report

- Source: saved AgentDojo-style/IPIGuard replay traces (`data/data/tool_effect_fragmentation/ipiguard_phase5_traces.jsonl`).
- Traces: 156.
- Domains: {'external_banking': 46, 'external_chat': 31, 'external_travel': 10, 'external_workspace': 69}.
- Label counts: {'ALLOW': 22, 'DENY': 134}.
- No real external side effects are executed.
- Deployable inputs exclude gold atoms, gold labels, expected decisions, and violation reasons.
- Annotation source: trace metadata for labels plus rule-derived sidecar atoms; this is not independent human annotation.
- Leakage-free: True.
- UPA: 0.000.
- FDeny: 0.000.
- Coverage: 0.904.
- Abstain: 0.096.
- Atom exact-set match: 0.821.
- Resource canonicalization accuracy: 0.904.
- Provenance/control-source accuracy: 0.904.
- Operation-mode accuracy: 1.000.
- Error categories: {'ambiguous_resource_identity': 12, 'control_source_missing': 15, 'untrusted_control_source': 121}.

Claim boundary: this subset supports an `external-trace subset` claim for saved replay traces. It does not support real deployed trace safety, production safety, or independent human gold-label claims.
