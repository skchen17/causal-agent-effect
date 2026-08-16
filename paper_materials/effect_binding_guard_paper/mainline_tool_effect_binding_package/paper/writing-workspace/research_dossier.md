# Research Dossier

## Target Scene

The target venue is NDSS Symposium 2027. The official call frames NDSS as a premier security venue for systems design, implementation, measurement, and analysis of practical network and distributed-system security problems. The call also warns that papers primarily about AI or ML without a clear security or real-systems relationship may be out of scope. Therefore, the manuscript should not read as a generic LLM-behavior paper. It should read as a pre-commit mediation and security-evaluation paper for side-effectful tool agents.

The NDSS page limit is 13 pages excluding ethics, references, and appendices. Artifact evaluation is strongly encouraged by the NDSS artifact call, and the final paper should keep result-to-source mapping and rerun commands explicit enough for artifact review.

## Related-Work Pattern Learned

ToolEmu and AgentDojo establish the need for realistic, adversarial evaluation of tool-using agents. CaMeL and IPIGuard represent the line of work that introduces protective layers, capability constraints, control/data-flow reasoning, or dependency graphs around tool use. ToolSafe/TS-Guard and Safiron represent proactive or pre-execution guardrail approaches. Progent and MiniScope are the closest authorization systems: they make least-privilege policies or permission structures explicit and enforce them at the tool boundary. The writing lesson is not to claim these systems are trivial or ineffective. The paper should instead make a narrower systems claim: policy enforcement depends on correctly binding a candidate action to its policy-relevant effect, resource, operation, authorization, and provenance, and the controlled stress lattice measures that prerequisite.

## Venue-Fit Implications

- Lead with the security object: a candidate tool action that can commit side effects.
- Define the mediator's boundary before reporting metrics: ALLOW, DENY, and ABSTAIN are pre-commit decisions.
- Treat abstention as an incomplete-mediation outcome, not a hidden success.
- Put resource and authorization identity at the center because NDSS reviewers will expect a concrete security policy object.
- Keep all local mock-contract claims explicitly scoped; the paper can be credible as controlled infrastructure evidence, but not as deployed SaaS/browser/banking/email validation.

## Evidence Readiness

The local evidence now supports a coherent mainline:

1. E47/E48 define and instantiate counterfactual effect-binding stress tests.
2. E47 official-checkpoint/component rows show existing methods are not merely tool-name classifiers, while still failing some joint-binding dimensions.
3. E48 gives a reference hard guard with bounded improvements and measurable errors.
4. E50 exposes resource/authorization as the central bottleneck.
5. E55-v2 directly targets that bottleneck with explicit authorization infrastructure, improving coverage from 120/600 to 528/600 and reducing observed UPA from 12/276 to 0/276 in the strict E55-v2 table.
6. E57 and E57-v2 reduce, but do not eliminate, label-template and implementation-coupling concerns.

## Reviewer-Risk Notes

- Synthetic/local mock data remains the primary external-validity risk.
- E57 human audit found corrections; perfect-label wording would be false.
- Existing-method rows are not faithful original-benchmark reproductions.
- The E55-v2 contract and the label generator share an explicit mock authorization model; this is useful systems evidence but not independent deployment generalization.
- A stronger NDSS submission would still benefit from an independently authored held-out E55-style contract and a realistic sandbox/replay mediator domain.
