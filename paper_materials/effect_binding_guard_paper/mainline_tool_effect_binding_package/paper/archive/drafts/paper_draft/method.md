# Method

The audit formalizes the safety decision as:

```text
d = f(realized_effect, resource, authorization_context, evidence, provenance)
```

Section 3 now includes a main-text TikZ Figure 1 with the caption:

> Counterfactual tool-effect lattice used to separate surface invariance from safety-relevant sensitivity.

The lattice isolates five axes:

- same effect, different surface;
- same tool or surface, different effect;
- same effect, different authorization;
- same effect, different resource;
- data/control provenance shifts where applicable.

The running `send_email` example instantiates these axes through tool aliases/wrappers, draft-vs-send effect changes, recipient-resource shifts, read-only-vs-send authorization flips, and private-output control provenance.

The central Phase 4 lattice contains 528 cases across 24 semantic groups. The finalized Phase 6 human audit is authoritative over older copied summaries that still describe the audit as pending.

Metrics:

- same-effect decision consistency;
- same-tool different-effect correctness;
- authorization sensitivity;
- resource mismatch error;
- unsafe pre-allow;
- safe false denial;
- abstain rate and coverage;
- structural invariance, topology consistency, exact DAG consistency, and normalized DAG consistency for graph outputs.

Evidence scopes:

- `baseline`: rule or local-LLM diagnostic;
- `official-checkpoint custom stress`: released checkpoint on E47 inputs, not original-paper numeric reproduction;
- `component stress`: released mechanism component on E47 custom core;
- `local-pipeline feasibility`: compatibility only when local non-paper model floors dominate;
- `diagnostic`: added mapper or evidence diagnostic;
- `upper bound`: oracle or execution-evidence ceiling, not deployable.
