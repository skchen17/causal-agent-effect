# E60 Held-out Contract Report

- Cases: 480
- Domains: {'maildesk': 96, 'meetroom': 96, 'docvault': 96, 'teamchat': 96, 'paydesk': 96}
- Stress axes: {'multi_resource_expansion': 60, 'operation_mode_shift': 60, 'alias_resolution': 60, 'provenance_control_shift': 60, 'authorization_shift': 60, 'same_effect_surface_variant': 60, 'incomplete_context': 60, 'ambiguous_resource_identity': 60}
- Artifact review status: artifact-level-pass.
- Strict authorship status: blocked-by-external-human-review.
- Gold atoms and labels are stored outside deployable inputs.
- Leakage-free: True
- Full atom mediation UPA: 0.000
- Full atom mediation FDeny: 0.083
- Full atom mediation coverage: 0.854
- Atom exact-set match: 0.812
- Resource canonicalization accuracy: 0.833
- Provenance/control-source accuracy: 0.979
- Operation-mode accuracy: 1.000

Performance declines are retained in the result JSON and should be discussed as transfer degradation rather than filtered away.
The validator supports the wording "independently specified held-out contract"; it does not certify "independently authored" because `e60_artifact_level_review.json` reports `blocked-by-external-human-review`.
