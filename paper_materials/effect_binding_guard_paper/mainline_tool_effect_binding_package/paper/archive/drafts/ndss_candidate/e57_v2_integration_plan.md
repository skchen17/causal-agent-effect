# E57-v2 NDSS Integration Plan

Recommended short addition.

## Results / Finding 6

Add: "The corrected E55-v2 deterministic resource-name perturbation and independent reference-authorizer check produced stable decisions / high agreement, reducing but not eliminating concern that the result is a naming-template artifact."

Use exact values:

- Perturbation stability passed: `True`.
- Authz-aware UPA delta: `0.0`.
- Authz-aware coverage delta: `0.0`.
- Reference-authorizer decision agreement: `1.0`.
- Spot-audit packet rows: `60`.

## Limitations

Add: "These checks reduce lexical and implementation-coupling concerns, but E55 remains controlled contract evidence because both the labels and guard operate under the same explicit mock authorization contract."

## Appendix

Add the perturbation result table, reference-authorizer agreement table, and spot-audit packet description.
