# E80 Hardened Runtime Kernel

Status: `kernel_passed_not_integrated`.

- totalize declared defaults and reject unknown/dynamic defaults
- bound LLM proposal by independent source-span/resolver manifest
- check each scalar or list-expanded security-field value
- accept resolver values only from matching typed authorized-read ledger entries
- emit registry and totalized-call hashes without a runtime LLM call

## Claim Boundary

The pure hardened kernel passes controlled unit tests. It is not integrated into the completed E77 run, does not automatically construct trusted manifests from arbitrary language, and has no benchmark metric.
