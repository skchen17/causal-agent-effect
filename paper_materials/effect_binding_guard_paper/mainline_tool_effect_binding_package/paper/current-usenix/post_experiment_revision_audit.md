# Post-Experiment Revision Audit

Date: 2026-08-16.

## Artifact Status

All required frozen experiments report `status=passed`. The fresh Qwen3-32B comparison contains the exact same 97 benign and 629 attack keys for no guard, Spotlighting, Prompt Sandwiching, PromptArmor-style, and the provenance monitor. Every row is evaluable, source hashes are frozen, and the monitor records zero execution without an allow decision and zero runtime LLM calls.

## Narrative Integration

- Authorization-interface falsification remains the primary contribution.
- Typed effects remain one candidate interface; the sufficient state-aware request is reported equally.
- Native-delta decisions and descriptor mutations provide mechanically separated positive checks.
- AgentDojo remains a pre-commit integration study.
- Prompt Sandwiching's stronger Qwen security--utility point is visible in the main Results paragraph and the complete appendix table.
- PromptArmor-style's zero observed attack success and large utility cost are both retained.
- All empirical and deployment reservations are consolidated in Limitations.
- The eight core sections were reduced from 6,248 to 5,623 words. Removed text
  consisted of repeated scope statements, duplicated module-isolation details,
  defensive typed/state-aware comparisons, and paragraph-end restatements.
- Formal statements are byte-equivalent to the pre-edit baseline, citation keys
  are unchanged, and no new numerical token was introduced. One repeated mention
  of the 11-tool count was removed; the count remains in Introduction,
  Evaluation, and Results.
- Related Work and the threat model required no substantive restructuring. They
  already locate the missing interface-validation layer and define the TCB in
  the terminology used by the revised narrative.

## Build And Source Audit

- Strict claim reproduction: `passed`, 368 rows, no pending artifact.
- Reference audit: `passed`, 35 cited keys, no missing or uncited entry.
- Submission-source audit: `passed`, 36 included sources, no missing label or
  PDF/source finding.
- PaperSpine artifact audit: `passed`, no missing or content issue.
- Page budget: `passed`, 11 technical-body pages of 13; 17 pages total.
- LaTeX: no undefined citation/reference, overfull box, missing file, or fatal
  error. Remaining diagnostics are non-fatal underfull-box warnings.

## Remaining Human Actions

Authors must perform the final prose/number/citation review, provide submission metadata and conflicts, run the anonymous package in a clean environment, and insert the stable anonymous artifact URL.
