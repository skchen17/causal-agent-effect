# E16 T65 Headless Chrome File-Backed Runtime

## 目的

补充 browser runtime proxy：使用 headless Chrome file-backed DOM/JS traces，观察 DOM/JS/runtime effect evidence 是否有助于授权监控。

## 主要结论

T65 生成 120 traces / 960 candidate-effect rows。validation-selected execution verifier FNR/FPR 为 `0.0/0.0`，N+ = `62`，N- = `411`；static verifier FNR/FPR 为 `1.0/0.0`。该结果支持 browser-runtime proxy evidence，但仍不覆盖 HTTP browser networking 或 deployed-agent runtime。

## 关键产物

- `src/auth/build_headless_browser_runtime_traces_t65.py`
- `data/agent_tool_traces_headless_browser_t65_v1.jsonl`
- `data/auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl`
- `analysis/manifests/agent_tool_traces_headless_browser_t65_v1_manifest.json`
- `analysis/results/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json`
- `analysis/results/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json`

## 论文可支持的 claim

可以作为 browser-runtime proxy evidence，说明 runtime traces 可以暴露 static rules 看不到的 effects。

## 不能支持的 claim

不能写成 HTTP browser automation、真实网页服务或部署 agent runtime validation。

