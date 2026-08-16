# Reproduce E48

Commands:

```bash
python -m src.experiments.effect_binding_guard.local_qwen --resume --max-tokens 192
python -m src.experiments.effect_binding_guard.run_e48 --bootstrap-iters 2000
```

Expected key outputs: `analysis/results/e48_tuple_guard_results.json`, `analysis/results/e48_local_qwen_tuple_predictions.jsonl`.
Local-Qwen inference requires the local GGUF/OpenAI-compatible setup used by E48; if predictions already contain exactly 822 unique rows, rerun only `run_e48`.
