# E61 Realistic Trace Replay Report

- Traces: 300
- Domains: {'maildesk': 60, 'meetroom': 60, 'docvault': 60, 'teamchat': 60, 'paydesk': 60}
- Sources: {'A_clean_sandbox': 75, 'B_realistic_noisy': 135, 'C_adversarial_provenance_shift': 90}
- No real external side effects are executed; traces are sandboxed or replayed.
- Leakage-free: True
- Full atom mediation UPA: 0.000
- Full atom mediation FDeny: 0.053
- Full atom mediation coverage: 0.847
- Atom exact-set match: 0.733
- Resource canonicalization accuracy: 0.920
- Provenance/control-source accuracy: 0.900
- Operation-mode accuracy: 0.967
- Resource-id F1: 0.950
- Control-source F1: 0.900
- Commit-mode F1: 0.967
- Error categories: commit_mode_not_authorized=21, control_source_missing=30, resource_authorization=10, untrusted_control_source=60, visibility_missing=19

Failure categories tracked in JSON include schema mismatch, alias ambiguity, missing context, operation-mode error, missed secondary resource, provenance/control-source error, noisy trace parse failure, and policy-dependent atom boundary.

## External Trace Subset

- External subset: 156 saved AgentDojo-style/IPIGuard replay traces across 4 domains.
- External subset UPA 0.000, FDeny 0.000, coverage 0.904, atom exact 0.821.
- The external subset remains replay-only and label-hidden; it is not a real deployment log or human-authored gold annotation.
- Combined accounting rows: 456; source-specific results remain separate.
