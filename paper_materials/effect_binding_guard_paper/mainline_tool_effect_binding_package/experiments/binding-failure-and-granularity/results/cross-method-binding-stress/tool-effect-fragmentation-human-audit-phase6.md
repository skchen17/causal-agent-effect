# E47 Phase 6 Human Audit

- Status: `complete`
- Primary: `222/222`
- Secondary: `56/56`
- Sources: `{'phase4': 120, 'ipiguard': 48, 'camel': 54}`
- Upgrade gate: `True`
- Decision agreement: `1.0`
- Effect agreement: `1.0`
- Resource agreement: `1.0`
- Authorization agreement: `1.0`
- Primary unresolved/contradictory rows: `0`
- Secondary unresolved/contradictory rows: `0`
- Corrected-label subset rows: `6`

## Protocol

- Primary reviewer fills all 222 rows.
- Secondary reviewer fills the 56-row stratified packet.
- Do not discard ambiguous or contradictory rows; mark them explicitly.
- Required upgrade thresholds: expected-decision agreement >= 0.90; effect/resource/authorization agreement >= 0.85; no unresolved critical pair contradiction.

## Current Interpretation

- Human audit gate passes under the pre-registered thresholds.
- Corrected-label subset by source: `{'camel': 6}`.

Human labels must be completed by human reviewers; model-generated labels do not satisfy this gate.
