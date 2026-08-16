# Reproduce E55

Commands:

```bash
python -m src.experiments.effect_binding_guard.e55_precommit_authz.run_e55 --output analysis/results/e55_precommit_authz_results.json
```

Expected key outputs: `data/e55_precommit_authz_dataset.jsonl`, `analysis/results/e55_precommit_authz_results.json`, and the E55 paper-artifact directory.
E55 is deterministic, local-only, does not call models, and does not execute real external side effects.
