# Reproduce E49

Commands:

```bash
python -m src.experiments.effect_binding_calibrator.run_e49 --bootstrap-iters 2000
```

Expected key outputs: `analysis/results/e49_learned_fusion_results.json`, `data/e49_effect_binding_fusion_features.jsonl`.
E49 is diagnostic only and must not replace the E48 hard guard as the main method.
