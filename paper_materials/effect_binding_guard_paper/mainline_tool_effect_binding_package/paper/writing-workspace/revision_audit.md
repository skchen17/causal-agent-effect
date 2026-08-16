# Revision Audit

Generated with:

```bash
python /home/user/.codex/skills/paper-spine/scripts/revision_audit.py paper/writing-workspace/final_paper_legacy_pre_usenix/main.tex paper/current-usenix/main.tex --markdown
```

## Summary

- Original paragraphs: 2
- Revised paragraphs: 52
- Near-identical revised paragraphs: 0 (0.0%)
- Mostly new revised paragraphs: 49 (94.2%)
- Likely deleted original paragraphs: 1 (50.0%)
- Addition-heavy: no
- Shallow-warning: no

## Interpretation

The final manuscript is a section-level rebuild rather than a shallow patch of the seed LaTeX wrapper. Similarity is highest only in structural LaTeX/title material. The revised paragraphs with substantive claims are mostly new and trace to `evidence_bank.md`, `section_blueprints.md`, and `writing_rationale_matrix.md`.
