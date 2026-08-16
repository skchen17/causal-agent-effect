# Counterfactual Atom-Envelope Guard: Design and Security Obligations

## Why the previous runtime lost utility

The previous guard required a separate LLM to enumerate a complete permission
plan before execution. Concrete calls then had to match literal values or
registered resolver relations. The DeepSeek benign runs show three distinct
failure sources: invalid or incomplete plan JSON, legitimate derived values that
fail literal grounding, and recovery/revision behavior that interrupts the
agent. The atom representation itself is not the main cause: the no-guard atom
description experiment passed the predeclared five-point non-inferiority test
against pristine descriptions.

## Revised runtime boundary

The revised design separates two questions:

1. **Which call dimensions can change a security-relevant effect?** Offline
   counterfactual registration answers this and freezes the descriptor.
2. **Did untrusted control expand one of those dimensions in this concrete
   call?** The runtime answers this from task grounding, structured call values,
   and provenance-separated tool results.

The runtime no longer treats every planner formatting error or derived scalar as
an authorization failure. It blocks only an effect-level or registered-field
expansion attributable to untrusted control. Missing descriptors and calls that
cannot be totalized still abstain.

## Conditional safety statement

Let `F(t)` be the security-relevant fields registered for tool `t`, and let
`A(t,x)` be the effect atoms instantiated by concrete call `x`. Let `U(v)` mean
that concrete value or effect choice `v` is causally influenced by an untrusted
control segment and lacks independent grounding in the original task.

If:

1. counterfactual registration is sound, so every security-relevant call
   dimension is represented in `F(t)` or the registered effect identity;
2. the provenance boundary is sound, so `U` identifies every untrusted control
   influence relevant to the call;
3. every effectful call is mediated before commit; and
4. the checked call is exactly the call that executes;

then C1b does not commit an effect for which the registered effect identity or
any field in `F(t)` is untrusted-control-influenced without independent task
grounding.

This is narrower than general trajectory safety. It does not cover natural
language output manipulation, an unmarked or incorrectly classified provenance
source, or an omitted security-relevant descriptor field.

## Expected utility property

For a totalizable call with a registered descriptor and no untrusted control
influence on the registered effect dimensions, the C1b decision is `ALLOW`.
Consequently, benign utility loss should not arise from planner parse failures,
literal mismatch, resolver incompleteness, or revision refusal. Remaining
differences from no guard can come from model nondeterminism, missing
registration/totalization, or false provenance matches. These causes are
reported separately.

## What counterfactual validation contributes

Without the counterfactual descriptor, a taint monitor must either inspect every
argument indiscriminately or depend on tool-name heuristics. The registered atom
fields restrict enforcement to dimensions shown to alter a security-relevant
effect. The C1-to-C1b correction further tests this specificity: it preserves the
same interception of previously successful tool-effect attacks while reducing
all-attack trajectory interventions from `121/629` to `94/629` in retrospective
Qwen3-32B replay, with no observed benign-call interventions in either variant.
These are mechanism diagnostics, not live ASR estimates.
