# Final Narrative Revision Report

Date: 2026-08-16.

## Files Modified

The prose revision updates `sections/abstract.tex`, `introduction.tex`,
`method.tex`, `security_analysis.tex`, `evaluation.tex`, `results.tex`,
`limitations.tex`, and `conclusion.tex`. Related Work and the threat model were
audited and left substantively unchanged. PaperSpine's style profile, rationale
matrix, rewrite matrix, and logic-transfer audit were synchronized, together
with `writing_report.md` and `post_experiment_revision_audit.md`.

## Argumentative Structure

The manuscript now advances one causal sequence: a concrete authorization
failure, the observation-interface information bound, executable
falsification, counterexample-guided refinement, frozen-interface conformance,
and pre-commit consumption. Method presents this sequence as an operational
pipeline. Security Analysis states the information bound once and then develops
the witness, refinement, and composition results. Evaluation mirrors that
logic, and Results begin with findings instead of protocol caveats.

## Defensive Patterns Consolidated

The edit removed repeated statements about finite validation, representation
neutrality, module isolation, post-state unavailability, and the narrow runtime
consumer. Negative implementation descriptions were replaced by positive
component responsibilities. The eight core sections decreased from 6,248 to
5,623 words, a 10.0% reduction.

## Caveat Placement

Evaluation defines the interpretation of positive and negative evidence once.
Security Analysis retains theorem and consumer premises. Limitations now carries
the explicit boundaries concerning semantic completeness, same-project
interpretation risk, state freshness and TOCTOU, interface economy, and the
AgentDojo consumer.

## Terminology

`Failure certificate` is the primary term in normal prose. `Effect witness` and
`authorization-separating witness` remain where their formal distinction is
needed. The paper consistently uses `authorization interface`, `candidate` or
`frozen descriptor`, `typed-effect interface`, `state-aware request`,
`policy-separating collision`, `validation record`, and `pre-commit consumer`.

## Intentional Contrasts

Two contrast constructions remain prominent because they carry the paper's
core insight: permission to invoke a tool differs from authorization of each
committed effect, and offline semantic observation differs from pre-commit
authority. The conclusion's statement that authorization is only as
discriminating as its interface is the central information bound, not a scope
disclaimer.

## Technically Sensitive Text

All theorem, proposition, corollary, and definition environments remain
unchanged. Numerical results, citation keys, policy semantics, benchmark
configurations, unfavorable runtime results, and descriptor limitations remain
intact. One duplicate mention of the 11-tool count was removed without changing
the reported experiment.

## Build And Test Status

- Claim reproduction: `passed`, 368 rows, `pending=[]`.
- Reference audit: `passed`, 35 cited keys.
- Submission-source audit: `passed`, 36 included sources and no broken label.
- PaperSpine artifact check: `passed`, with no missing or thin rationale
  artifact.
- LaTeX build: `passed`, 17 pages total.
- Page budget: `passed`, 11 technical-body pages under the 13-page limit.
- PDF/source scan: no broken reference, TODO, local path, project-private label,
  or anonymity finding. Generic uses of “user” in the threat model and Ethics
  statement are legitimate.
- Build log: no undefined reference/citation, overfull box, missing file, or
  fatal error; non-fatal underfull-box warnings remain.

## Remaining Defensive Prose

The remaining negative or contrastive language is required by the collision
theorem, the counterfactual witness definition, experimental controls, or the
Limitations section. Removing it would weaken technical meaning. No remaining
prose issue requires a claim or evidence change.
