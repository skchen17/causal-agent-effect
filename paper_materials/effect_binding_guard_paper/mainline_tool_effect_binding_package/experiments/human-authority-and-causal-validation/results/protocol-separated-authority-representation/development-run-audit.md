# Development Run Audit

The first two frozen runs are retained rather than silently overwritten.

## v2.0

- Evaluation seed: `89173`.
- 256 messaging rows failed compilation because sorted JSON changed dependency order among descriptor `let` bindings.
- Six workspace revoke rows used the requested permission instead of the pre-state ACL permission.
- The complete report and row outputs are retained under `first-frozen-run-v2.0/`; frozen inputs are retained under the evaluation directory's `archive-v2.0/`.

## v2.1

- Evaluation seed: `246813`, selected before its contexts were materialized.
- Descriptor/source exact match reached 1,024/1,024.
- Twenty-three true no-op calls were incorrectly treated as incomplete inventories and mapped to ABSTAIN.
- Outputs are retained under `second-frozen-run-v2.1/`; frozen inputs are retained under `archive-v2.1/`.

## Final protocol version

- Evaluation seed: `97531`, selected before its contexts were materialized.
- The no-op fix is representation-independent: a complete empty transition inventory means no committed transition, while an unknown inventory still abstains.
- No result-dependent cases were removed. The final report is subject to fail-fast acceptance gates.

These development runs mean the benchmark is protocol-separated but not a pristine independently administered blind evaluation. The paper must state this boundary.
