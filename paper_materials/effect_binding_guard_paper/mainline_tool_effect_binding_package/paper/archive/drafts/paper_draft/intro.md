# Introduction

Tool-using LLM agents can create external side effects: messages are sent, files are changed, reservations are modified, and services are contacted. A guard therefore needs more than surface robustness over tool names or textual formats.

Running example: an authorized `send_email` action should receive the same decision if expressed as `send_email`, `alias__send_email`, or `wrapper_for_send_email`, because the realized effect and resource are unchanged. The decision should change when the same surface drafts rather than sends, when the recipient changes from approved to out of scope, when the user grants read-only access but the agent sends mail, or when private tool output controls whether the send occurs.

This motivates the target decision:

```text
d = f(e, r, a, v, p)
```

where `e` is realized effect, `r` is resource, `a` is authorization context, `v` is evidence, and `p` is provenance. Tool-effect invariance means invariance to irrelevant surface shifts plus sensitivity to safety-relevant shifts in those variables.

Contributions:

1. A counterfactual tool-effect invariance audit separating surface invariance from effect, resource, authorization, evidence, and provenance sensitivity.
2. A cross-method measurement over weak baselines, released checkpoints, structured components, diagnostics, and upper bounds.
3. Human-audited labels: 222/222 primary and 56/56 secondary rows complete with agreement 1.0 on decision/effect/resource/authorization fields.
4. Evidence that surface robustness and topology stability do not imply joint safety reasoning under the E47 controlled stress.
5. A claim-scoped package separating baseline, official-checkpoint custom stress, component stress, diagnostic, feasibility, oracle, and upper-bound evidence.
