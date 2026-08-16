# E55 Claim Boundary

Outcome: `Outcome B`.

## Supported

- Typed authorization context can improve local mock pre-commit decidability.
- Resource/auth failures are partly interface and infrastructure failures, not merely LLM recognition failures.
- Atom-level expansion exposes multi-resource and operation-mode violations.
- Alias resolution, operation modes, multi-resource expansion, provenance metadata, and evidence fallback are useful to the extent supported by E55 ablations.
- Under the E57 human-corrected sensitivity, the full authorization-aware guard preserves zero unsafe pre-allow on the corrected full-600 label map, while a small false-denial rate appears. This should be reported as corrected-label sensitivity, not as a new independent benchmark.
- E55-v2 corrects the transaction `amount` atom and unknown-resource fallback issues found by human audit; it is a corrected rerun of the same controlled mock design.

## Not Supported

- Production safety.
- Complete permission-system coverage.
- Independent deployment generalization.
- Real SaaS/browser/banking/email safety.
- Original benchmark reproduction.
- Real side-effect execution.
- Robustness to adversarially adapted tools beyond the controlled schema.
- Learned calibration as the main method.
- Perfect label correctness for the original E55 construction.
- Full human validation of all 600 E55 rows.
