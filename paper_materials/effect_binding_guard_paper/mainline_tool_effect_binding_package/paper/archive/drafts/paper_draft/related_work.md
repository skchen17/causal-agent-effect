# Related Work

## Agent Safety Benchmarks

AgentDojo provides the dynamic tool-using-agent environment and saved effect artifacts used by the package. The draft uses AgentDojo-derived artifacts and custom counterfactual transformations, but does not present a new aggregate AgentDojo benchmark result.

## Checkpoint and Pre-Execution Guardrails

ToolSafe/TS-Guard and Safiron are treated as released checkpoint guardrails evaluated on E47 custom stress inputs. The draft does not claim original-paper numeric reproduction for TS-Bench, TS-Guard, Safiron, or Pre-Exec Bench.

## Graph, Provenance, and Capability Defenses

IPIGuard and CaMeL motivate the structured-component part of the audit. The claim is component-scoped: topology stability and structural policy checks are useful, but in this package they do not by themselves establish realized-effect authorization decisions over effect, resource, authorization, and provenance.

## Evidence-Grounded Monitoring and Judge-Style Diagnostics

Evidence and semantic-mapper rows are used as diagnostics and upper bounds. Non-oracle versions are incomplete; oracle rows are not deployable.

TODO comments for submission work:

- TODO: add verified broader citations for verifier-style monitoring, LLM-as-judge diagnostics, capability security, and prompt-injection taxonomies.
- TODO: add concrete comparison rows only after source verification; do not insert unverified 2026 bibliography entries.

Verified citations currently kept in `references.bib`: AgentDojo, ToolSafe/TS-Guard, Safiron, IPIGuard, and CaMeL.
