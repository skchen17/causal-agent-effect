# C1 Code Review Before C1b

## Status

C1 is an immutable development candidate while its 63-case run is active. Its
source files must not change until that run completes. The run is retained even
if C1b supersedes it.

## Confirmed properties

- the complete permission-plan and revision loop is skipped;
- only counterfactually registered security fields are inspected;
- missing descriptors and failed totalization abstain;
- the runtime policy calls no LLM;
- the first corrected live smoke completed without an execution-before-ALLOW
  violation;
- retrospective Qwen3-32B replay intercepted 49 of 53 successful attack
  trajectories and no observed benign trajectory.

## Predeclared C1b corrections

These were identified by source review, not by inspecting the active 63-case
outcomes:

1. Short enum values such as `r` must use token/exact matching rather than raw
   substring matching. Otherwise an unrelated control segment containing that
   character can taint the field.
2. A concrete value explicitly grounded in the original user task is not an
   authority expansion merely because untrusted content repeats it. Field taint
   should require control provenance without independent task grounding.
3. Inactive totalized values (`null`, empty string, empty collection) should not
   become control-taint candidates.

C1b will change only these matching semantics. The descriptor set, task
manifest, model, official evaluators, and advancement gates remain fixed.

## Claim boundary

The observed-trajectory replay is a mechanism diagnostic, not live ASR. The
16-case DeepSeek no-guard attack smoke has zero successful attacks and therefore
cannot establish a security improvement for either C1 or C1b. Full official
attack evaluation remains necessary after a utility-acceptable candidate is
frozen.
