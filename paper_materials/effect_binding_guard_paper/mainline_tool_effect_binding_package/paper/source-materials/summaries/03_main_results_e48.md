# E48 Main Results

E48 builds an 822-row label-hidden unified dataset with 6,840 diagnostic pairs. Local-Qwen tuple prediction covers 822 rows with parse-valid rate around 0.995. Deployable-input leakage is zero.

Main full-guard metrics:

- UPA `0.03611111111111111`
- FDeny `0.06493506493506493`
- coverage `0.9172749391727494`
- effect accuracy `0.8357664233576643`
- resource accuracy `0.7262773722627737`
- authorization accuracy `0.84765625`
- provenance accuracy `1.0`

The strongest claim is method-feasibility under controlled custom stress.
