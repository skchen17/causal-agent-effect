# DeepSeek C1f Structured-Provenance Regression

- C1f benign utility: `75/97`.
- C1f benign ALLOW/DENY/ABSTAIN: `372/0/0`.
- Official attack success, no guard/C1f: `6/0` of 629.
- Post-repair confirmation attack success: `6/0` of 628.
- Scope-aligned effectful attack success: `6/0` of 608.
- Scope-aligned exact one-sided McNemar p: `0.015625`.
- Known regression attack success after repair: `False`.
- Attack ALLOW/DENY/ABSTAIN: `2693/90/0`.
- Joint gate passed: `True`.

The full official result retains output-only goals. The scope-aligned result is
reported separately because the guard mediates committed tool effects, not final
natural-language recommendations.
