# E14 T63 Broader Local Adapters

## 目的

扩展到 web/search/browser/messaging local-adapter traces，补强 T59/T61 覆盖面不足的问题。

## 主要结论

T63 生成 300 traces / 2400 candidate-effect rows。validation-selected execution verifier test FNR/FPR 为 `0.0351/0.0`，static verifiers FNR/FPR 为 `0.614/0.0132`。该结果增强受控多工具面证据，但仍是 local adapters，不是 provider-backed services。

## 关键产物

- `src/auth/build_broader_agent_tool_traces_t63.py`
- `data/agent_tool_traces_broader_tools_t63_v1.jsonl`
- `data/auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl`
- `analysis/results/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json`
- `analysis/results/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json`

## 论文可支持的 claim

可以作为 broader controlled/proxy trace family 支持 execution evidence 的作用。

## 不能支持的 claim

不能声称覆盖真实 SaaS messaging、provider-backed search 或 HTTP browser automation。

