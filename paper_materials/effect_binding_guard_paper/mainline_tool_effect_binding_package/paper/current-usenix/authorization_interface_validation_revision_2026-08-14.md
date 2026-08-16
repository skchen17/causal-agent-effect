# Authorization-Interface Validation Revision

Date: 2026-08-14

## Controlling Identity

The active manuscript now treats the representation at an enforcement boundary as a security-critical authorization interface. That interface induces equivalence classes over executions and therefore upper-bounds the distinctions available to every downstream policy consumer. Typed effect atoms are one candidate interface, not the paper's identity.

## Novelty Boundary

The manuscript does not claim novelty for complete mediation, least privilege, effect terminology, the elementary collision theorem, or CEGAR. Its contribution is to make the authorization-observability obligation explicit for agent tool calls and to turn interface validation into an executable falsification procedure.

The procedure combines three independently interpretable evidence objects:

1. an effect witness from copied-sandbox execution;
2. a policy-separating witness from a distinct policy oracle;
3. a representation collision showing that the candidate pre-commit view merges the pair.

Together they form an executable authorization-interface failure certificate. A single certificate falsifies the interface on any domain containing that pair. Failure to find one supports only bounded conformance on the frozen intervention domain and policy family.

## Oracle Separation

The source oracle uses privileged post-state only during offline registration to determine what committed. The policy oracle determines which committed differences require different decisions. The descriptor determines which distinctions will be observable before commitment. The post-state oracle therefore validates the interface but cannot replace it at runtime; this separation prevents circular validation.

## Evaluation Interpretation

- RQ1 establishes committed-effect facts and authorization-separating witnesses.
- RQ2 tests bounded conformance of candidate interfaces, including typed atoms.
- RQ3 tests whether a deterministic consumer can reproduce a frozen source-derived relation from the interface. It is not an ACL or general authorizer evaluation.
- AgentDojo runtime mediation is a separate integration case study.

No experiment results or source artifacts were changed in this revision.

## Remaining Boundary

The current evidence does not establish open-world descriptor soundness, a universal atom schema, global minimality, complete authority, arbitrary ACL semantics, state freshness under concurrent mutation, or TOCTOU freedom. Those properties remain external assumptions or future validation targets.

## Skeptical Reviewer Test

- **A. Unfinished authorization system?** No. The general diagram is a downstream consumer contract, and the implemented monitor is labeled as a separate integration case.
- **B. Interface-validation methodology?** Yes. The title, abstract, contributions, method, RQ1--RQ3, results synthesis, and conclusion all center authorization observability and executable falsification.
- **C. Novel effect atoms or CEGAR?** No. The manuscript explicitly treats typed atoms as one candidate family and established refinement as a borrowed mechanism.
- **D. Offline-oracle circularity?** Addressed. The copied-sandbox oracle observes privileged post-state only offline; the real boundary must decide before commitment.
- **E. RQ3 as realistic ACL benchmark?** No. It is labeled a finite, source-derived representation stress relation and tests exact consumer realization, not authority generation or policy prevalence.
- **F. Runtime as missing main realization?** No. AgentDojo is absent from the contribution list and appears separately as an operational integration case.
- **G. Positive scientific claim?** Yes. The paper identifies an authorization-observability obligation and provides executable failure certificates plus bounded conformance evidence. Limitations are attached to the claims they delimit rather than repeated as general disclaimers.
