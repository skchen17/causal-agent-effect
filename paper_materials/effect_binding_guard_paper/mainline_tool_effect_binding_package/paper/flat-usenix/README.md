# USENIX Flat Source Package

All manuscript sources are stored in this directory without nested source
folders. `main.tex` is the build entry point. It loads the section, figure,
table, appendix, bibliography, and USENIX style files by local filename.

Build with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The package reflects the current evidence-gated manuscript. Pending experiment
results are not inserted until their artifacts pass the paper's result gates.
