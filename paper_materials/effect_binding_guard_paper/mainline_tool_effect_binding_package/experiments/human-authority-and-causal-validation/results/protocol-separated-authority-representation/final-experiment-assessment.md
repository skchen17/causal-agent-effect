# Final Experiment Assessment

## What the experiment establishes

- The executable descriptors pass 192 counterfactual registration pairs: 168 security-relevant interventions and 24 surface-invariant interventions.
- On 1,024 evaluation contexts generated after descriptor freeze, descriptor-instantiated typed effects exactly match the separately implemented before/after transition oracle.
- Under one shared ACL/capability/delegation authority engine, typed effects achieve full coverage with no unsafe pre-allow or false denial in this frozen domain.
- Tool name, raw arguments, and common-field views contain policy-mixed cells. Typed effects contain none.
- Among 52 argument groups whose ideal decision changes only with pre-state, raw arguments collide in all 52; typed effects collide in none.

These results support a bounded causal claim: the validated typed representation preserves policy-separating distinctions that coarser views erase, and those distinctions improve end-to-end authorization correctness under the studied authority models.

## What it does not establish

- The benchmark, tools, authority state, descriptors, and generator were built by the same research process. Modules and protocol phases are separated, but authorship is not independent.
- The routine slice is generated from fixed value pools; it is not a production distribution or prevalence estimate.
- Descriptor exact match on this finite family does not establish open-world soundness.
- The raw-argument monitor is a documented best-effort adapter, not every possible optimized raw-call authorizer.
- The first two frozen development runs exposed implementation defects. They are retained in the artifact, and the final seed was selected before its contexts were materialized.

The experiment is suitable as controlled evidence for the paper's representation claim when these boundaries are stated. It should complement, not replace, source-executed tool evidence and realistic agent-runtime evaluation.
