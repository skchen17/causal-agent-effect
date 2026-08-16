# Anonymization Readiness

Status: current paper sources and PDF pass; artifact release checks remain.

The current PDF-included LaTeX, BibTeX, candidate Markdown/JSON, and extracted
PDF text contain no local absolute paths, credentials, private repository
labels, or broken-reference markers. Local build intermediates such as
`main.fls` and `main.log` are excluded because TeX records host paths there.

The final release gate repeats the scan over every included source, JSON,
JSONL, manifest, environment lock, generated table, and PDF after packaging.
Git history, raw credentials, host logs, and model files are excluded. Until
that complete scan and clean-environment reproduction pass, the package must
not be uploaded as the anonymous artifact.
