# Reproducibility Notes

Regenerate the package with:

```bash
python scripts/build_tool_effect_paper_package.py --force
```

Validate an existing package with:

```bash
python scripts/build_tool_effect_paper_package.py --validate-only
```

The package copies canonical final E47 artifacts. It does not rerun experiments. External repos/checkpoints are required only to regenerate original raw experiments, not to use this paper package. Official-checkpoint custom stress, component stress, local-pipeline feasibility, diagnostic, oracle, and upper-bound rows are explicitly separated in `tables/claim_scope_table.*`.

Do not use local-pipeline feasibility as defense-effectiveness evidence when no-defense utility or attack success is low. Do not use oracle or upper-bound rows as deployable methods.
