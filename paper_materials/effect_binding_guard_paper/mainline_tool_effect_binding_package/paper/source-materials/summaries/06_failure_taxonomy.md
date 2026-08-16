# Failure Taxonomy

Residual failures should be grouped as:

- Resource alias and near-resource mismatch.
- Broad vs narrow authorization scope.
- Partial authorization and missing authorization.
- Draft/no-effect vs commit side effects.
- Extra recipient, CC, BCC, public-link, or out-of-scope target.
- Evidence unavailable or insufficient evidence.
- Unknown or untrusted provenance causing abstention.
- Safe false denial under broad provenance stress.
- IPIGuard semantic/resource failures and topology-only blind spots.

Use curated examples in `failure_examples/` and avoid long raw logs unless needed for an appendix.
