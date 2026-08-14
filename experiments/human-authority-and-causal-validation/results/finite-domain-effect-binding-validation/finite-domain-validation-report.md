# Finite-Domain Effect-Binding Validation

## Scope

The audit exhaustively executed 56 valid calls covering 5 AgentDojo v1.1.2 tool instances. A source-specific oracle reconstructed committed security effects from fresh before/after states. Candidate representations were then compared against those effects; the oracle was not generated from the candidate contracts.

The admissible finite policy family contains every submultiset of the observed atomic-effect occurrences. Consequently, any two different concrete effect multisets can be separated by an authority bound. A representation is finite collision-complete exactly when no representation cell contains two different source-effect signatures.

## Results

| Representation | Cells | Collision cells | Separating pairs | Overpartition pairs | Collision-complete | Exact partition |
|---|---:|---:|---:|---:|:---:|:---:|
| tool_name | 5 | 5 | 564 | 0 | no | no |
| source_effect_only | 6 | 6 | 548 | 0 | no | no |
| source_common_fields | 25 | 5 | 118 | 0 | no | no |
| reviewed_common_contract | 25 | 5 | 118 | 0 | no | no |
| reviewed_typed_contract | 56 | 0 | 0 | 0 | yes | yes |
| source_full_effect | 56 | 0 | 0 | 0 | yes | yes |

## Interpretation

Collision completeness is a bounded result for this enumerated domain and authority family. It does not establish completeness for unenumerated calls, hidden effects, changed implementations, or a deployment policy language.

Overpartition pairs are not unsafe by themselves; they identify representations that distinguish contexts with the same observed security effects and may therefore impose unnecessary policy or review burden.

## Integrity

- Source hash verification errors: 0
- Execution errors: 0
- Empty source-effect sets: 0
