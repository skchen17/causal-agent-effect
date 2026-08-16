# Anonymous Artifact Readiness Package

This directory is the fail-fast release ledger for the active USENIX candidate. It is
not a released artifact. The ledger distinguishes paper-evidence readiness from
artifact-release readiness: the former checks the frozen headline results and
claim reproduction, while the latter additionally requires a clean-environment
rerun, a complete anonymity and credential scan, and an anonymous stable URL.

Regenerate the claim index from the package root, then the readiness ledger from the paper directory:

```bash
python paper/current-usenix/reproduction/reproduce_main_claims.py
cd paper/current-usenix
python artifact/build_manifest.py
```

After every required result reports `status=passed`, the source workspace exports
the compact per-case outcome ledger once. The anonymous package ships that ledger
without prompts or messages. It can regenerate the final tables, generated result
prose, claim index, and PDF from the included frozen JSON artifacts:

```bash
python paper/current-usenix/reproduction/generate_final_result_section.py
python paper/current-usenix/reproduction/reproduce_main_claims.py
cd paper/current-usenix && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex && cd ../..
```

The compact package includes standalone reproduction and renderer tests:

```bash
python -m pytest \
  shared/compatibility/tests/tests/test_usenix_main_reproduction.py \
  shared/compatibility/tests/tests/test_render_usenix_final_tables.py -q
```

Full model inference, benchmark package installation, and sandbox source replay
remain source-workspace procedures; this compact release reproduces reported
numbers from hash-frozen outputs and exposes the C1f policy, descriptors, audit
records, and source-oracle rows for inspection.

The current package also includes the strong state-aware interface overlay,
deterministically selected executable failure certificates, the pinned
third-party MCP protocol and row-level outputs, and the 30-call pre-commit
runtime reconciliation study. Third-party repositories are identified by
commit and implementation hash; vendored dependency trees are not included in
this result-reproduction package.

Two early fixed-result sources are reduced to the paper metrics needed by the
compact package. The source workspace therefore generates
`reproduction/sanitized_fixed_support.json`: a path-free metric extract carrying
SHA-256 hashes of the frozen descriptor JSONL and projection report. The compact
package consumes this extract and exposes its extractor; machine-specific
metadata from older summaries remains outside the anonymous release.

For an in-progress audit only, `build_anonymous_package.py --allow-pending`
creates a package labeled `preview_pending_results`. It is not a release
artifact. The package builder uses an explicit allowlist and fails on local
workspace paths, credential patterns, private project labels, unfinished-work
markers, or user-specific Windows paths.

Do not treat smoke, readiness, dry-run, feasibility, or partial rows as paper
results. The anonymous stable URL is added only after the final package is
scrubbed and reproduced from its documented environment.
