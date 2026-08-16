# Reproduction Notes

No command in this package is run by the builder. Suggested inspection/rerun order:

```bash
python -m src.experiments.effect_binding_guard.run_e48
python -m src.experiments.effect_binding_guard.run_e50 --bootstrap-iters 2000
python -m src.experiments.effect_binding_guard.e55_precommit_authz.run_e55 --strict-label-hidden --output analysis/results/e55_precommit_authz_results_strict.json
python -m src.experiments.effect_binding_guard.e55_precommit_authz.e57_validity_checks
```

E55/E57 are local deterministic mock pre-commit experiments and do not execute real external side effects. E48 local-Qwen prediction regeneration requires local model infrastructure; package building does not.
