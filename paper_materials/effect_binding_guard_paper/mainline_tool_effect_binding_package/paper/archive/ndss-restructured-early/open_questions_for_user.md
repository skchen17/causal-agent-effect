# Open Questions for User

## Blocking Questions

None currently block this restructured draft. The main version policy follows the prior decision: use E55-v2 as the main pre-commit result and original E55 plus human-corrected sensitivity as audit/sensitivity evidence.

## Questions To Confirm Before Next Writing Pass

1. Should Table 5 stay as original E55 strict ablations, or should we rerun/recompute E55-v2 ablations and make those canonical?
   - Current draft labels Table 5 as original E55 strict because the requested 0.333 / 0.148 / 0.148 / 0.211 values come from that source.
   - E55-v2 strict ablations differ: no multi-resource UPA 0.217, no operation-mode UPA 0.217, no provenance-overlay UPA 0.217, no alias FDeny 0.238.

2. Should ARGUS, AgentVisor, or other provenance/virtualization systems be added to Related Work?
   - I did not add them because the current package does not contain verified BibTeX or source entries for them.

3. Should the final title be:
   - `Tool-Effect Binding in LLM Agents: Counterfactual Measurement and Pre-Commit Authorization`
   - or `Counterfactual Effect Binding for Pre-Commit LLM-Agent Tool Safety`?

4. Do we want E55-v2 to replace original E55 everywhere, including ablations and appendix sensitivity, or should the paper keep the mixed but explicitly labeled policy?

5. Should the consolidated package include an E48/E50 reproduction shim or path-normalized test wrapper?
   - Current E48/E50 result numbers align with JSON artifacts.
   - However, live E48/E50 tests fail in this package because the tests resolve `ROOT` to `tests/` and look for `tests/analysis/results/...`, while the consolidated package stores those artifacts under `results/analysis/results/...`.
   - E55/E56/E57 tests pass in the current package layout.

## Clarified Non-Questions

- Coverage 0.880 and 0.920 are not the same result: 0.880 is E55-v2 strict; 0.920 is original E55 strict and human-corrected sensitivity.
- E57-v2 reference-authorizer agreement and E57 human audit are separate artifacts and are not merged.
- The draft does not treat the old 2-page or 6-page PDFs as submission-ready.
- The E48/E50 numbers are not currently flagged as numeric conflicts; the issue is live reproduction path layout inside the consolidated package.
