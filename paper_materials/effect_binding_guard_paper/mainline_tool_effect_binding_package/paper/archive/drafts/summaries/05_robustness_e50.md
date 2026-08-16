# E50 Robustness

E50 audits the E48 hard guard without introducing a new learned method.

- E48 reproduction: UPA `0.03611111111111111`, FDeny `0.06493506493506493`, coverage `0.9172749391727494`.
- Source-balanced mean: UPA `0.051351351351351354`, FDeny `0.05894736842105263`, coverage `0.923076923076923`.
- LOSO is mixed: CaMeL is safe but lower coverage; IPIGuard remains the weakest source.
- Resource/auth stress: UPA `0.6166666666666667`.
- Expanded provenance stress: UPA `0.0` but FDeny `0.1875` and coverage `0.5446428571428571`.

Interpretation: E50 strengthens hard guard robustness but makes resource/authorization binding the central remaining bottleneck and limitation.
