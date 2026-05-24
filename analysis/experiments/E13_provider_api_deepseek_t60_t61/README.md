# E13 T60/T61 DeepSeek Provider API Traces

## 目的

验证 provider-backed API 调用能否进入 trace/effect verifier 管线，并检查 static verifier 对 provider-side effects 的漏检。

## 主要结论

T60 是 8 traces tiny pilot；T61 扩展到 120 provider API traces / 960 candidate-effect rows。execution verifier 在该 single-provider surface 上 FNR/FPR 为 `0/0`，static verifiers 对 provider effects FNR 可到 `1.0`。结果支持 execution evidence 必要性，但只是 DeepSeek provider single-surface。

## 关键产物

- `src/auth/build_deepseek_api_traces_t60.py`
- `data/agent_tool_traces_deepseek_api_t60_v1.jsonl`
- `data/agent_tool_traces_deepseek_api_t61_v1.jsonl`
- `data/auth_trace_effect_schema_conditioned_t60_deepseek_v1.jsonl`
- `data/auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl`
- `analysis/results/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json`
- `analysis/results/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json`

## 论文可支持的 claim

可以说 provider-backed API trace 管线可运行，并且 provider-side effects 不能由静态本地规则可靠捕获。

## 不能支持的 claim

不能外推到 search、messaging、browser 或多 provider；不要在 artifact 或命令中写入 API key。

