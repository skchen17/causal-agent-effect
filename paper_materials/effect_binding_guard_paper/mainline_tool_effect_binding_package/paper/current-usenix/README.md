# USENIX Security '27 Candidate

This tree is the sole active USENIX source and uses the public USENIX conference style file.

The current source contains the narrative, system/threat model,
counterfactual-registration semantics, conditional security analysis, completed
evaluation, limitations, Ethics appendix, and Open Science appendix. Numeric
claims admitted to the PDF are gated by
`reproduction/reproduce_main_claims.py`; required final results remain excluded
until their strict finalizers pass.

Build with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The main technical body must remain within 13 pages under this template. References and appendices are excluded from that submission-body limit.
