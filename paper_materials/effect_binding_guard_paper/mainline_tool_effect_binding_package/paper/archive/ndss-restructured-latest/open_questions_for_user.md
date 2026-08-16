# Open Questions for User

## Blocking Questions

1. E60 strict independent-authorship evidence is not certified.
   - The artifact now includes `evaluation/e60_heldout_contract/independent_author_review_packet.{json,md}`, `independent_author_review_packet.template.json`, `validate_independent_author_review.py`, and `e60_artifact_level_review.json`.
   - Current validator decision is `artifact-level-pass` for artifact checks and `blocked-by-external-human-review` for strict authorship.
   - Paper text must use `independently specified held-out contract`, not `independently authored held-out contract`.
   - To upgrade the wording, provide a real non-E55 author/reviewer packet using the template and rerun the validator.

2. Final NDSS submission-format polish remains before submission.
   - The NDSS 2027 CFP requires technical papers to fit 13 pages excluding Ethics, references, and appendices, using the NDSS template.
   - A local NDSS-template technical-body pass now builds at 11 pages, and the full NDSS-template sanity build is 13 pages total.
   - The current NDSS-template build still has two-column formatting warnings, mostly overfull table/figure boxes, so final template polish is still required before submission.

## Optional Evidence Extensions

1. Should B8 be replaced by a full original-system reproduction?
   - Current B8 is implemented as a ToolSafe/TS-Guard-style released-guardrail comparable local adapter.
   - It consumes the same label-hidden deployable views and does not use gold atoms, gold labels, expected decisions, or violation reasons.
   - It is not an original ToolSafe/TS-Guard benchmark or checkpoint reproduction.

2. Should E61 add independently human-labeled external traces?
   - Current E61 includes both the 300 artifact-generated sandbox/replay traces and a 156-trace saved AgentDojo-style/IPIGuard external replay subset.
   - The external subset is sandboxed/no-side-effect, schema-converted, and label-hidden, but its labels are metadata-derived and its atoms are rule-derived sidecar annotations.
   - Independent human annotation would be needed before claiming human-labeled external gold labels.

3. Should the final title remain `Tool-Effect Binding in LLM Agents: Counterfactual Measurement and Pre-Commit Authorization`, or shift toward the atom-level thesis, for example `Atom-Level Pre-Commit Authorization for Tool-Using LLM Agents`?

## Clarified Non-Questions

- Table 5 uses E55-v2 strict ablations as the main ablation result.
- Coverage 0.880 and 0.920 are different result versions: 0.880 is E55-v2 strict; 0.920 is original E55 strict/human-corrected sensitivity.
- E57-v2 reference-authorizer agreement and E57 human audit are separate artifacts and are not merged.
- E47 released-checkpoint rows are not presented as original benchmark reproductions.
- ARGUS and AgentVisor remain only as publicly verifiable Related Work citations, not as evidence for this paper's experiments.
- E60--E64 are artifact-bounded evidence and do not establish deployed-system safety.
- E61 external subset is a saved replay subset, not a real deployment trace corpus.
- B8 is a comparable local adapter, not an original benchmark reproduction.
