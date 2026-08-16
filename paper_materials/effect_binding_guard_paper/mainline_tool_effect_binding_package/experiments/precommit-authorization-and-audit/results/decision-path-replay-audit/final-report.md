# E56 Final Report

- Decision-path audit passed: `True`.
- Strict mode passed: `True`.
- Existing hard guard metrics: `{'unsafe_pre_allow': 0.037037037037037035, 'safe_false_deny': 0.0, 'coverage': 0.2, 'abstain': 0.8, 'decision_accuracy': 0.1}`.
- Authz-aware guard metrics: `{'unsafe_pre_allow': 0.0, 'safe_false_deny': 0.0, 'coverage': 0.92, 'abstain': 0.08, 'decision_accuracy': 1.0}`.
- Strongest ablation evidence: `{'no_multi_resource_expansion_upa': 0.3333333333333333, 'no_operation_mode_upa': 0.14814814814814814, 'no_provenance_overlay_upa': 0.14814814814814814, 'no_alias_resolution_fdeny': 0.21052631578947367}`.
- Strongest remaining limitation: E55 labels and the full guard share deterministic mock schemas and authorization contracts; this is contract evidence, not independent deployment generalization.
- NDSS compiled: `True`, pages: `2`.
- Anonymity scan passed: `True`.
- Recommended framing: measurement + diagnostic framework + local pre-commit authorization prototype.
