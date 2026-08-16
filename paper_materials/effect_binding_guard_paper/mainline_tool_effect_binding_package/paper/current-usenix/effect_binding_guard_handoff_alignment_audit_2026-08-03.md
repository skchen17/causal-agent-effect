# effect_binding_guard 交接文档-代码-结果一致性审计

日期：2026-08-03  
审计对象：`paper/current-usenix/effect_binding_guard_handoff_2026-08-02.md`  
审计范围：交接文档声明、E77/v17 实现、pilot JSON、AgentDojo 运行 artifact、复现入口与单元测试。

## 1. 总结判定

原交接文档的**主体实现链和 v12-v17 pilot 方向是真实的**：planner、pre-commit comparison、修订/重规划、relation catalog、AgentDojo patch、Qwen/DeepSeek 运行目录和 63 案例结果均能在仓库中定位。50 项相关单元测试通过。

但原文不能直接视为完全正确，主要有五类偏差：

1. 把最终执行策略写成严格 fail closed，掩盖了 `allow_with_trail` 对 resolver-fill 不确定性的执行覆盖。
2. 把 outcome-conditioned 63 案例 pilot 的投影写得接近直接 97/726 案例结果。
3. v9-v11 数字和五类失败统计与结果源不一致或无可定位来源。
4. 部分文件路径、manifest 范围和复现命令错误。
5. 结果 Markdown 存在版本标题错误、覆盖和缺失，DeepSeek protocol manifest 的模型元数据也不准确。

交接文档已据此修正。当前可以支持的是**机制存在、选择性 pilot 改善和明确的执行策略审计**；在 726 全量完成并正确 finalize 前，不能支持全基准效用或安全 headline claim。

## 2. 关键问题

### A1. 安全边界原表述过强

- 原声明：任何未接地、越权或计划外操作一律不执行。
- 实现：`e77_runtime.py::apply_uncertainty_policy` 在 `allow_with_trail` 下，会把全部字段均已授权或仅为 `resolver_fill_requires_replan` 的严格 `NEEDS_REPLAN`/`DENY` 覆盖为最终 `ALLOW`。
- 执行：`agentdojo_e77_runtime_patch.py` 按覆盖后的 `comparison["decision"] == "ALLOW"` 执行，同时另记 `guard_decision`、`strict_authorization_satisfied` 和 `diagnostic_uncertainty_override`。
- 判定：**论文表述过强，已修正。**
- 正确解释：严格判断仍阻断明确权限扩张；实验策略允许一部分未完全接地的 resolver-fill 调用带审计轨迹执行。

### A2. “0 非 ALLOW 执行”不能证明严格授权成立

- 结果 JSON 的 `unsafe_execution_rows=0` 检查的是最终有效决策与执行器的一致性。
- 由于 uncertainty policy 可先把严格非 ALLOW 覆盖为最终 ALLOW，计数为 0 只能证明执行器没有绕过**最终决策**。
- 后续全量报告必须分别统计：严格授权通过、uncertainty override、最终执行、明确越权阻断。
- 判定：**指标真实，但原解释过强，已修正。**

### A3. 63 案例结果是选择性诊断 pilot，不是全基准估计

- 63 案例由 37 个 frozen benign loss 与 26 个 stable-success control 构成。
- `projected_combined_benign_of_97 = 33 - attributed_control_regressions + target_recovery` 是投影公式。
- 所有 pilot Markdown 的 claim boundary 均明确：不是无偏 AgentDojo benign-utility 估计，不含攻击案例。
- 判定：**结果可追溯，但用途必须受限，已修正。**

### A4. 版本结果的实际数字

JSON 数值真源如下：

| 版本 | 目标恢复 | 对照成功 | 归因回归 | 噪声失败 | 投影 |
|---|---:|---:|---:|---:|---:|
| v9 | 7/37 | 22/26 | 4 | 未拆分 | 36/97 |
| v10 | 8/37 | 22/26 | 2 | 2 | 39/97 |
| v11 | 8/37 | 22/26 | 2 | 2 | 39/97 |
| v12 | 13/37 | 24/26 | 1 | 1 | 45/97 |
| v13 | 13/37 | 24/26 | 1 | 1 | 45/97 |
| v14 | 13/37 | 25/26 | 0 | 1 | 46/97 |
| v15 | 14/37 | 25/26 | 0 | 1 | 47/97 |
| v17 | 15/37 | 24/26 | 1 | 1 | 47/97 |

原文 `v9-v11 目标恢复 12-13、投影 39-44` 错误。v17 的 15/37 是 63 案例 Qwen pilot；“轻量恢复 2/5”来自 DeepSeek v17，不应混为同一次运行。

### A5. 失败分类原数字无源

原文五类 `8/5/7/6/2` 无法在现有报告中定位。可验证的 29 例互斥归因来自 `engineering-recovery-four-step-execution-report.md`：修订模型随机拒绝 5、think 泄漏 4、计划/推导/计划外问题 6、日历表示 3、自由文本边界 4、噪声 5、URL 不一致 2。交接文档已替换为该来源，并标明其仅适用于定向 pilot。

### A6. 结果摘要生成存在版本错误

- v12、v13、v14 的 Markdown H1 仍写 v10。
- `registered-relation-expanded-pilot-v15.md` 当前内容是 v17 摘要。
- `registered-relation-expanded-pilot-v17.md` 不存在。
- 对应 JSON 文件内容和 source-run 可区分，因此本审计以 JSON 为数值真源。
- 判定：**JSON 可用；Markdown 生成链需修复。**

### A7. DeepSeek 模型元数据不一致

- v16/v17 DeepSeek 的 `runtime_audit.jsonl` 中 task-plan/revision 行记录 `deepseek-v4-flash`。
- 两个 run 的 `protocol_manifest.json` model 块仍写 Qwen3-32B GGUF。
- 判定：**真实调用有日志支持，但 manifest 不能单独证明模型身份。**

## 3. 声明-代码-结果对照

| 交接声明 | 代码/结果源 | 判定 |
|---|---|---|
| Planner 输出结构化权限计划 | `e77_runtime.py::planner_prompt_v2`、`parse_permission_plan_v3_diagnostic`；patch `_plan_with_prompt` | 对应 |
| 工具调用前逐字段检查 | `compare_call_to_plan_with_evidence`；patch precommit hook | 对应 |
| 计划外工具触发 full planner replan | patch `_model_replan` 与 `tool_not_in_plan` 分流 | 对应 |
| 字段问题触发修订模型 | patch `_model_revision` | 对应 |
| 修订模型不读任务全文 | `_model_revision` prompt 实际包含原始任务 | 不对应；已改为“只允许修订 implicated tool entry” |
| runtime 只在最终 ALLOW 时执行 | patch `comparison["decision"] == "ALLOW"` | 对应 |
| runtime 只在严格授权时执行 | uncertainty override 后仍可执行 | 不对应 |
| v12-v17 pilot 改善 | 各版本 JSON | 对应，但仅为选择性 pilot |
| no-guard 64/97 | `qwen32-strong-baseline-report.json` | 对应 |
| “守卫净代价 -17” | 47 是选择性 pilot 投影，64 是 no-guard 97 案例直接结果 | 口径不等价；已改为“投影差” |
| DeepSeek v16 恢复 banking/11 | v16 DeepSeek run audit/log | 对应 |
| DeepSeek v17 恢复 slack/19、workspace/13 | v17 DeepSeek run audit/log | 对应 |
| atom 有稳定角色语义特异性 | role-shuffled 多轮大多相同，只有少量条件差异 | 证据不足；已降为探索性结果 |
| b8 委托漏洞 | atom-specificity Round 5/6，3/3 | 对应 |
| 50 项测试通过 | 两个 E77 pytest 文件 | 对应；2026-08-03 重跑 50 passed |

## 4. 路径与复现核对

已修正：

- manifests、pilot/full run 均需带 `experiments/intent-bound-runtime-guard/` 前缀。
- v16 不存在 `registered_relation_expanded_pilot_manifest_v16.json`；只有 light manifest。
- relation catalog 的实际路径是 `experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/registered_relation_catalog.json`。
- AgentDojo 环境补丁实际在 `runs/e75_agentdojo_env/.../agent_pipeline.py`。
- 复现命令中的 `...` 已替换为实际路径，并增加 `PYTHONPATH=code:.`。

仍需处理：

- `finalize-recovery-normalization-qwen32-full.py` 的 `EXPECTED_RUNTIME` 仍为 `effect_diff_runtime_recovery_normalization_v2`，而本次 run 是 `effect_diff_runtime_relation_onboarding_v17`。在参数化或更新前，不能正确 finalize 当前 run。
- 该 finalizer 还需通过 `RECOVERY_FINALIZER_RUN_ROOT` 指向 v17-726 run 目录。

## 5. 验证执行

执行命令：

```bash
PYTHONPATH=code:. python3 -m pytest \
  shared/compatibility/tests/tests/test_effect_binding_guard_e77_relation_onboarding_v9.py \
  shared/compatibility/tests/tests/test_effect_binding_guard_e77_effect_diff_runtime.py -q
```

结果：`50 passed in 0.05s`。

这验证了已编码的解析、关系 onboarding、precommit comparison 和策略分支行为；它不验证 726 案例的模型输出或 benchmark 指标。

## 6. 当前运行状态与投稿边界

核对时，v17-726 的 runner、Qwen3-32B llama.cpp server、E75 live runner 和 AgentDojo benchmark 进程均仍在运行，protocol manifest 的 runtime version 为 `effect_diff_runtime_relation_onboarding_v17`。因此：

- 不能把撰写时的 46/726 当作当前进度。
- 不能从中间文件数推导最终 utility/ASR。
- 不能在 full run 完成、行数核对、finalizer 修复和直接指标生成前写 headline claim。
- 当前 63 案例 pilot 仍可作为诊断与机制开发证据，但必须保留 outcome-conditioned 限定。

## 7. 后续必做

1. 等 v17-726 完整结束，不中途修改已加载的 runtime/patch 源文件。
2. 参数化 finalizer 的 expected runtime 与 run root，修复 Markdown 摘要的版本命名/覆盖问题。
3. 生成 full benign utility、utility under attack、official attack success，以及严格通过/override/阻断/执行的分层计数。
4. 核对所有 726 case key、错误行、重复日志和模型身份元数据。
5. 只有 full 结果完成后，再决定论文能否使用效用与安全 headline；pilot 投影不能替代该步骤。
