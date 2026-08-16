# LaTeX Report

## Build Command

```bash
cd paper/current-usenix
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

## Current Result

- Status: passed.
- PDF: `paper/current-usenix/main.pdf`.
- Total pages: 12.
- Technical body through the labeled conclusion end: 9 pages.
- Page size and layout: US letter, two columns, public USENIX conference style.
- Fatal errors, missing files, undefined references/citations, and overfull boxes: none.
- Remaining messages: ordinary underfull-box warnings.

The official 13-page technical-body check must be rerun after the five strict-finalized results and generated tables are inserted.
