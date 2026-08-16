# USENIX Compact Source Package

This directory uses the requested source layout:

- `main.tex`: all manuscript prose, equations, tables, and appendices;
- `references.bib`: bibliography database;
- `system_overview.tex`: standalone figure source;
- `usenix-2020-09.sty`: USENIX conference style.

Build with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```
