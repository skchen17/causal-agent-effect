# NDSS Template Page Report

## Official Constraints Used

- NDSS 2027 CFP: technical papers must not exceed 13 pages, excluding Ethics Considerations, references, and appendices.
- NDSS 2027 CFP: submissions must use the NDSS templates and be US-letter, two-column, Times 10pt or larger.
- NDSS templates source used for this pass: the official NDSS templates page, which links `bare_conf_NDSS2026.tex` and `IEEEtran.cls`.

## Local Template Files

The template files were downloaded into:

- `ndss_template/bare_conf_NDSS2026.tex`
- `ndss_template/IEEEtran.cls`

Two entrypoints were added without replacing the article-template source:

- `main_ndss_full.tex`: full sanity build with Ethics, references, and appendices.
- `main_ndss_technical.tex`: technical-body page-count build from Abstract through Conclusion, excluding Ethics, references, and appendices.

## Build Results

| Build | Command | Result | Page Count | Interpretation |
|---|---|---:|---:|---|
| Article sanity | `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` | passed | 19 | Not an NDSS compliance signal. |
| NDSS full sanity | `TEXINPUTS=./ndss_template//: latexmk -pdf -interaction=nonstopmode -halt-on-error main_ndss_full.tex` | passed | 13 | Confirms the full artifact can compile under the downloaded NDSS template files. |
| NDSS technical body | `TEXINPUTS=./ndss_template//: latexmk -pdf -interaction=nonstopmode -halt-on-error main_ndss_technical.tex` | passed for page counting | 11 | Current technical body is under the 13-page target. |

## Caveats

- `main_ndss_technical.tex` intentionally excludes references and appendices, so its log can contain missing citation/reference warnings; use `main_ndss_full.tex` for full cross-reference sanity.
- The NDSS-template build still has two-column formatting warnings, mostly overfull table/figure material. These should be fixed before submission.
- The page-budget result does not justify removing E60--E64 evidence from the main text. Under the current technical-body count, compression is not required.

## Compression Policy

If future content causes the NDSS-template technical body to exceed 13 pages, compress in this order:

1. Related Work.
2. Experimental Setup.
3. Table 6 prose.
4. Appendix verbosity.

Do not compress the atom section, Algorithm 1, Tables 2--4, or main-text visibility of E60--E64 merely to fit pages.
