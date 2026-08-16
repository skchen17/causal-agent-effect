# E77 Runtime v3 Implementation Note

Status: implemented and unit-tested; full AgentDojo results not yet regenerated.

This revision addresses five code-level causes of low utility in the earlier
runtime:

1. A `NEEDS_REPLAN` result can now invoke a bounded policy-plan revision. The
   candidate revision is accepted only after deterministic completeness,
   grounding, and exact-call checks.
2. Initial and revised plans must bind every registered security field for
   every selected effectful tool. Missing, malformed, unknown, or ungrounded
   bindings fail closed.
3. Grounding uses typed canonical values and boundary-preserving text matches
   instead of token-subset matching.
4. Resolver evidence is a structured provenance ledger. It records the source
   tool and typed output path, excludes free-form output fields, and can enforce
   `source_tools` and `source_fields` restrictions. Network-returned content is
   not authority evidence.
5. Recovery is bounded to three plan revisions by default. An unchanged call
   cannot consume another revision without new structured evidence.

The normal pre-commit decision remains deterministic. A mismatch may invoke a
local LLM on the policy plane to choose `REVISE_PLAN`, `KEEP_PLAN`, or `DENY`;
an LLM revision never directly authorizes execution. Accepted revisions must
pass the deterministic guard for the exact totalized call.

The prior E77/E78 result artifacts were produced by the earlier runtime and
must not be relabeled as v3 results. A new full run is required before reporting
utility, attack success, coverage, or recovery improvements for this revision.
