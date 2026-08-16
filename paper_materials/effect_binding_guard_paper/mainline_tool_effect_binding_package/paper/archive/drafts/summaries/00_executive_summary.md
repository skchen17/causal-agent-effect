# Executive Summary

This package supports a measurement plus method-feasibility paper about tool-effect binding in LLM-agent safety. The central finding is that current defenses can be more than tool-name classifiers, yet still fail to stably bind realized effects to resources, authorization context, provenance/control dependency, and available evidence.

The proposed hard Effect-Binding Guard explicitly infers `(effect, resource, authorization_match, provenance_risk)` from label-hidden non-oracle views, then uses multi-view disagreement, selective evidence fallback, and a control-provenance overlay to produce `ALLOW / DENY / ABSTAIN`.

Core numbers:

- E48 full guard: UPA `0.03611111111111111`, FDeny `0.06493506493506493`, coverage `0.9172749391727494`.
- E50 source-balanced mean: UPA `0.051351351351351354`, coverage `0.923076923076923`.
- E50 resource/auth stress: UPA `0.6166666666666667`; this is the dominant unresolved bottleneck.
- E50 expanded provenance stress: UPA `0.0`, FDeny `0.1875`, coverage `0.5446428571428571`.
- E55 local pre-commit authorization: authorization-aware UPA `0.0`, FDeny `0.0`, coverage `0.92`.

Claim boundary: controlled custom-stress robustness and method-feasibility evidence only; not production safety, not a complete permission system, not original-paper benchmark reproduction, and not a real-world deployment safety certificate.
