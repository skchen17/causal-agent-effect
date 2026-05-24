# E12 T59 Real-Agent-Tools Local Adapter Stress Test

## 目的

参考 `real-agent-tools/` 中 Hermes agent 工具注册和调用代码，检查当前实验脚本与真实 agent 工具流程之间的差距，并构建可安全执行的 local-adapter traces。

## 主要结论

T59 发现 Hermes 注册工具约 74 个，其中大量 external/API candidates 需要依赖或凭证。安全执行的 local adapters 只覆盖 read/write/terminal 等有限面，生成 48 traces / 384 candidate rows。schema-to-real-agent-local-trace FNR 曾为 `0.25`，说明真实工具语义迁移有漏检风险。

## 关键产物

- `real-agent-tools/`
- `src/auth/build_real_agent_tool_execution_traces_t59.py`
- `analysis/results/real_agent_tool_inventory_t59_v1.json`
- `analysis/reports/real_agent_tool_inventory_t59_v1.md`
- `data/agent_tool_traces_real_agent_tools_t59_v1.jsonl`
- `data/auth_trace_effect_schema_conditioned_t59_v1.jsonl`
- `analysis/results/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json`

## 论文可支持的 claim

可以说真实 agent 工具注册/调用流程暴露了当前合成实验和真实工具语义之间的 fidelity gap。

## 不能支持的 claim

不能写成 full Hermes runtime validation；direct handler import 受缺失依赖阻塞，external tools/API tools 未完整执行。

