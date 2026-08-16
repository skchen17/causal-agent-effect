# E47-E50 Semantic and Statistical Fix Note

Date: 2026-07-14

The pre-fix E49/E50 resource-authorization artifacts are archived under
`analysis/results/archive/e47_e50_pre_semantic_fix_20260714/` and must not be
used as paper evidence.

Two E49/E50 DENY constructions were inconsistent with their visible task
policy: the task authorized the alternate effect or committed effect that the
label denied. In addition, the authorized-alias construction did not
materialize a different candidate identifier. The corrected generators now
use an independent policy oracle, explicit commit-mode denial, and a real alias
mapping. Validation fails if the visible policy and expected decision disagree.

E48 pairwise confidence intervals previously treated thousands of correlated
pairs as independent observations. Pairwise point estimates and intervals now
aggregate within `split_group_id` and bootstrap independent groups. Raw pair
success and total counts remain in the result artifacts for auditability.

The E47 capability matrix now distinguishes a sampled human audit from the
construction-gated remainder. Passing the sampled audit gate no longer labels
the complete custom stress set as fully audited.

These changes correct evidence semantics and uncertainty reporting. They do
not convert the custom stress sets into original-benchmark reproductions or
deployed-system evidence.
