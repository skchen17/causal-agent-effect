# Raw-Field Versus Validated-Atom Attribution

| View | Benign utility | Attack utility | Attack success |
|---|---:|---:|---:|
| no_guard | 30/48 | 153/273 | 38/273 |
| whole_call_provenance | 39/48 | 58/273 | 11/273 |
| effect_only | 37/48 | 147/273 | 21/273 |
| registered_field_c1f | 31/48 | 148/273 | 7/273 |
| raw_field_taint | 39/48 | 162/273 | 10/273 |

Paired same-call decision disagreements: `28`/`788`.

Raw-field taint checks every totalized argument with the same provenance and literal task grounding while omitting descriptor effect-label expansion. The 321-case closed-loop rates are selection-conditioned mechanism evidence, not benchmark-wide estimates.
