# Paper Outline

## Title Options

- Counterfactual Effect Binding for LLM-Agent Tool Safety
- Measuring and Mitigating Tool-Effect Fragmentation in LLM Agents
- Beyond Tool Names: Counterfactual Effect Binding for Agent Safety

## Abstract Skeleton

Problem: LLM-agent safety monitors often evaluate tool calls through surface forms, but safety depends on realized effects, resources, authorization, and provenance.

Method: Introduce a counterfactual stress-test framework and a hard Effect-Binding Guard that binds candidate actions into explicit tuples and uses disagreement, evidence fallback, and provenance checks.

Results: E47 shows residual gaps in existing methods; E48/E50 show hard-guard feasibility and robustness; E49 shows learned calibration is not yet safer.

Limits: controlled custom stress, not production safety; resource/authorization binding remains the key bottleneck.

## Sections

1. Introduction: effect-level safety target and counterfactual motivation.
2. Related Work: agent safety, prompt-injection defenses, tool-use guardrails, provenance/control-flow systems, OOD and invariance.
3. Stress-Test Framework: E47 counterfactual axes and scope labels.
4. Effect-Binding Guard: tuple inference, disagreement, evidence fallback, provenance overlay.
5. Evaluation: E47 measurement, E48 feasibility, E49 diagnostic, E50 robustness.
6. Failure Analysis: resource/auth, evidence, provenance, and source shift.
7. Limitations and Ethics.
