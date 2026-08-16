# TODO

## Required Before Submission

- Convert to the official NDSS template once the target year template is fixed.
- Add an independently authored held-out E55-style contract or explicitly state that this evidence is absent.
- Add a realistic no-real-side-effect replay/sandbox domain if available.
- Decide whether to rerun E55-v2 ablations and replace the current original-E55 ablation table.
- Add confidence intervals in main tables where space allows, especially for small-count slices.
- Expand appendix slice tables for domains, axes, and human-audit correction categories.
- Add verified BibTeX for provenance/virtualization/audit systems only after source verification.
- Run anonymization and artifact scans on the new `ndss_candidate_restructured/` directory.

## Writing Improvements

- Tighten the threat model into NDSS style after deciding the final template.
- Decide whether Figure 2 should be a lattice figure or a measurement-table schematic.
- Add 2-3 concrete failure examples in the main text, with sanitized snippets.
- Add a reviewer-facing paragraph explaining why abstention is not failure but a required pre-commit state.
- Shorten Related Work after the full paper exceeds the target page budget.

## Experimental Gaps To Keep Visible

- No production safety validation.
- No full real SaaS/browser/banking/email/workspace integration.
- No original benchmark reproduction for all compared external systems.
- No universal tool-schema robustness claim.
- Current local contract remains deterministic and project-authored.
