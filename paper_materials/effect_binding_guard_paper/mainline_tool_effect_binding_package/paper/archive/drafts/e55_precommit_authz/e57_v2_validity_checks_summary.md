# E57-v2 Corrected Rerun Validity Checks Report

- Dataset version: `v2`
- Perturbation stability: `True`
- Reference-authorizer agreement gate: `True`
- Spot-audit packet created: `True`
- All validity gates passed: `True`

## Perturbation

- Authz-aware UPA delta: `0.0`
- Authz-aware coverage delta: `0.0`
- Changed decisions: `0`
- Changed decision rate: `0.0`

## Reference Authorizer

- Decision agreement: `1.0`
- Disagreement count: `0`
- Atom count agreement: `1.0`
- Atom resource-set agreement: `1.0`

## Spot Audit Packet

- Rows: `60`
- Domain counts: `{'calendar': 20, 'email': 10, 'file': 10, 'slack': 10, 'transaction': 10}`
- Decision counts: `{'ALLOW': 25, 'DENY': 28, 'ABSTAIN': 7}`
- Slice counts: `{'alias': 12, 'multi_resource': 53, 'draft_commit': 20, 'public_visibility': 23, 'provenance_shift': 11, 'unsafe_extra_recipient_or_multi_recipient': 25}`

## Remaining Limitations

E57 is still a controlled local validity check. It reduces naming-template and implementation-coupling concerns, but it does not turn E55-v2 into independent deployment evidence.

## Recommended Paper Framing

E57 reduces lexical-template and implementation-coupling concerns, but E55-v2 remains controlled local pre-commit contract evidence.
