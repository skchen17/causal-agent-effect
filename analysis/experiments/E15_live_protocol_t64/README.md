# E15 T64 Live HTTPS / Local Webhook Protocol

## 目的

在没有 search/messaging provider key 的情况下，构造 key-free live/protocol external-validity evidence：真实 outbound HTTPS 和本地 webhook protocol traces。

## 主要结论

T64 生成 300 traces / 2400 rows，并完成 full-precision Qwen3-8B rerun。validation-selected execution verifier held-out test FNR/FPR 为 `0.0/0.0`，N+ = `197`，N- = `1170`；static verifier FNR/FPR 为 `0.6294/0.0462`。这是强 proxy evidence，但不是 provider-backed search/SaaS messaging/deployed runtime。

## 关键产物

- `src/auth/build_live_protocol_tool_traces_t64.py`
- `data/agent_tool_traces_live_protocol_t64_v1.jsonl`
- `data/auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl`
- `analysis/reports/t64_live_protocol_external_validity_report.md`
- `analysis/results/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json`
- `analysis/results/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json`

## 论文可支持的 claim

可以说 live/protocol telemetry 在 key-free setting 中支持 execution evidence 的有效性。

## 不能支持的 claim

不能写成真实 provider-backed search/messaging/browser deployment validation。

