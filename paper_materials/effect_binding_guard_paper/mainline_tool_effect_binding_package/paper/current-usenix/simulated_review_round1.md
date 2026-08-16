# Simulated USENIX Security Review, Round 1

## Summary and Recommendation

**Current recommendation: Weak Reject, with a credible path to Weak Accept after the frozen final experiments.**

The paper identifies a real systems-security obligation: a pre-commit monitor cannot authorize distinctions erased by its view of a tool call. It contributes a policy-relative effect representation, source-executed counterfactual registration, and a deterministic provenance-origin runtime instance. The paper is unusually direct about negative evidence. However, the current AgentDojo registry retains every field, the strongest runtime result ties Spotlighting on attack success, and five generalization, utility, transfer, or attribution artifacts are still pending.

## Strengths

1. **Clear problem decomposition.** Representation adequacy, provenance, policy, complete mediation, and check--use consistency are separated instead of being bundled into an unconditional safety claim.
2. **Executable representation evidence.** The 56-call finite source domain and frozen 32-context ToolSandbox domain directly expose authorization-separating collisions rather than relying on LLM judgments.
3. **Honest negative results.** The paper reports 67/67 field retention, unresolved interventions, low no-guard attack success, Spotlighting parity, and the historical transfer utility failure.
4. **Auditable runtime.** C1f makes no runtime guard LLM call and reconciles checked and executed call signatures in the sandbox.
5. **Appropriate theorem scope.** The formal claims are conditional and finite-domain where required.

## Major Concerns

### 1. Independent value of the atom representation

The frozen AgentDojo descriptor marks all 67 unique fields security-relevant. Consequently, the current runtime resembles generic structured-field provenance checking. The source-oracle collision results show that typed effect distinctions can matter, but the runtime result alone does not demonstrate successful minimal-field discovery. The paper must keep these claims separate and must not imply that C1f's ASR is caused by learned minimal atoms.

### 2. Runtime comparison is not yet decisive

On the current DeepSeek run, no guard succeeds on only 6/629 official attacks, while Spotlighting and C1f both reach 0/629. C1f has lower attack-task utility than Spotlighting. This can support a mechanism case study, but not a best-defense claim. The frozen 320-case held-out result and matched Qwen result are necessary to determine whether the finding is robust or model-specific.

### 3. Utility evidence is incomplete

The main table currently mixes a four-run no-guard benign mean with single-run values for other methods. The queued interleaved 4-by-3 study and task-clustered non-inferiority analysis must replace that mixed comparison. If the lower confidence bound does not exceed -0.05, the paper must report the utility cost rather than claim non-inferiority.

### 4. Registration coverage is bounded

Only 38/75 suite-scoped field instances receive five valid intervention kinds. Nine lack a committed-effect witness, and 308 attempted mutations are invalid or unresolved. The use of invalid interventions as a reason to retain fields is safe but does not establish necessity. The paper currently states this correctly; the final version should preserve the field-level failure appendix and source hashes.

### 5. External validity and policy scope

The implementation depends on explicit provenance boundaries and literal grounding in the authenticated task. It does not provide ACL, delegation, quota, semantic-intent, or output-only protection. The 303-case saved AgentLAB transfer is useful only if the current C1f profile passes exact mediation reconciliation; it is not an adaptive AgentLAB reproduction.

### 6. Novelty may be perceived as a straightforward representation lemma

The collision theorem is elementary. The systems contribution therefore depends on showing that the representation problem occurs in real benchmark implementations, that source execution finds distinctions missed by conventional views, and that the resulting descriptors can drive a complete pre-commit path. The paper should foreground this evidence chain rather than sell the theorem itself as deep novelty.

## Required Changes for Acceptance Consideration

- Complete and report the five frozen final experiments without deleting unfavorable outcomes, including the current-C1f four-view closed-loop attribution.
- Generate every final number from the fail-fast claim-to-source reproducer.
- Keep “minimal” explicitly relative to the frozen intervention domain and policy family.
- Replace mixed-run benign values with matched repeated results.
- Present Spotlighting parity and any utility disadvantage prominently.
- Keep the four-view retrospective result labeled as interceptability, not closed-loop ASR.
- Include clean-environment artifact instructions and a machine-verifiable anonymization report.

## Provisional Scores

| Criterion | Score (1--5) | Rationale |
|---|---:|---|
| Originality | 3 | Distinct effect-side representation obligation, but close to typed schemas and provenance enforcement unless the source evidence carries the contribution. |
| Technical quality | 3 | Careful bounded theory and executable oracles; final generalization and utility runs pending. |
| Correctness | 4 | Claims are conservative and negative evidence is retained. |
| Clarity | 4 | Main arc is understandable and classic principles are not renamed. |
| Systems-security fit | 4 | Pre-commit mediation, provenance, and tool-state effects are directly relevant. |

## Artifact Questions

- Can a clean environment regenerate all main-paper tables from frozen JSON without local paths or credentials?
- Are exact model, descriptor, manifest, and code hashes retained for every long experiment?
- Does the AgentLAB finalizer prove one checked signature for every executed tool-result call?
- Are output-only attack goals kept outside the scope-aligned denominator but still reported in the all-key table?
