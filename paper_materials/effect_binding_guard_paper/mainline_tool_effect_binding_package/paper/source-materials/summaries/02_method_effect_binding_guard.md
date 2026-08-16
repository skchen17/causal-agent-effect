# Method: Effect-Binding Guard

The guard is a hard, explicit tuple-binding monitor. It receives label-hidden, non-oracle deployable inputs and predicts `(effect, resource, authorization_match, provenance_risk)`.

Main components:

- Rule tuple parser: extracts visible effect/resource/authorization/provenance signals.
- Local-Qwen tuple view: one non-oracle model-based tuple prediction where available.
- Multi-view disagreement: compares tool, schema, plan/call, masked-tool, canonical summary, evidence, and model tuple views.
- Selective evidence fallback: consults non-oracle saved/simulated evidence only when the base view is uncertain or conflicting.
- Control-provenance overlay: denies private control of side-effectful actions and abstains on unresolved untrusted/unknown control.
- Hard policy: outputs `ALLOW`, `DENY`, or `ABSTAIN`.

The method is not a complete permission system and does not claim production readiness.
