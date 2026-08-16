# E58 Writing Package: Effect-Binding Guard Paper

This package consolidates E47-E57 evidence into NDSS-first writing materials for a Tool-Effect Binding paper.

## Status

- Package purpose: writing-material consolidation, not a new experiment.
- Framing: measurement + diagnostic framework + local pre-commit authorization prototype.
- Current NDSS build blocker: `ndss_candidate/main.pdf` is `2` pages, and `ndss_candidate_pre_e56_backup/` exists = `False`.
- Main method: reference hard Effect-Binding Guard, with E55 as a local authorization-aware prototype addressing the E50 resource/auth bottleneck.
- E49 learned calibration: diagnostic appendix only.
- E55/E57: controlled contract evidence only.

## Package Layout

- `tables/`: core numbers, table plans, claim-to-source CSV.
- `figures/`: figure specifications and data references.
- `snippets/`: reusable method/evidence wording.
- `appendix_materials/`: appendix and audit-packet notes.
- `audit/`: audit and validity-check status.
- `logs/`: source discovery and NDSS build diagnosis.

## Main Safe Takeaway

Existing surface-level and tuple-only guards are not enough for stable authorization binding. Explicit authorization context, effect-resource-operation atom expansion, alias handling, multi-resource expansion, provenance overlay, and evidence fallback improve local mock pre-commit mediation, but the evidence remains controlled and does not establish production safety.
