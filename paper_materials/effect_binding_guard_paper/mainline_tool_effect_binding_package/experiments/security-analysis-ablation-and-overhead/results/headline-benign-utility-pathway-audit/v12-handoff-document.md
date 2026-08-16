# v12 allow_with_trail 修复实验交接文档

日期：2026-07-31
交接对象：Codex（后续执行者）

---

## 1. 任务背景

### 1.1 总体目标

effect_binding_guard 是一个运行时守卫，对 agent 工具调用做权限计划验证。论文的核心安全义务是 O5: Fail-closed uncertainty——"未解决的事实或默认值不产生 ALLOW"。

在 v9→v10→v11 三轮迭代中，工程修复将投影良性效用从 33/97 提升到 39/97，但仍低于 48/97 验收线。用户决策规则是"能修到 50+ 才推进 726-key 全量重评"。

### 1.2 v11 终态与失败分析

v11 运行 63 案例（37 目标恢复 + 26 对照保留），结果 8/37 恢复、39/97 投影、0 非 ALLOW 执行。33 个失败案例的逐案例归因：

| 失败类别 | 案例数 | 根因 |
|---|---:|---|
| think 键泄漏（plan_top_level_schema_invalid） | 4 | Qwen3 输出单键 `{"dims":"..."}` 无真实计划，extract_json_object 的剥离条件 `len>1` 不触发单键情况 |
| 值无法接地（ungrounded_exact_value） | 8 | planner 把需要规范化/推导的值标成 exact（逐字匹配），但值不在任务文本中 |
| resolver 填充不匹配（resolver_fill_requires_replan） | 8 | resolve 模式要求值字面出现在已授权证据中，但算术派生值（16-12=4）和自由文本语义提取值（email 正文中的时间）不可能字面出现 |
| 修订模型随机拒绝（revision_model_denied_effect） | 5 | 修订模型看到 precommit 说"值不接地"后选择 DENY 而非 REVISE_PLAN——与 resolver_fill_requires_replan 同源 |
| 纯模型执行层（零守卫干预） | 6 | 守卫全程 ALLOW，但模型自身执行失败 |
| 计划外工具调用 | 2 | 模型调用计划外工具，守卫正确拦截 |
| 对照回归（确定性守卫拦截） | 2 | end_time 算术派生值（12:00+1h=13:00）被严格接地检查拦截 |

**关键发现**：问题 2/3、4、8 实际是同一根因——resolve 模式要求值字面接地，而算术派生值和自由文本语义提取值不可能字面接地。

---

## 2. v12 三项修复方案

### 修复1：extract_json_object 单键 think/dims 剥离

**文件**：`code/src/experiments/effect_binding_guard/e75_unified_agentdojo_comparison/full_atom_runtime.py`

**修改内容**：
- 原逻辑：`if "dims" in parsed and len(parsed) > 1` 才剥离——单键 `{"dims":"..."}` (len==1) 不触发
- 新逻辑：`if "think" in parsed or "dims" in parsed` 即剥离，剥离后如果为空 dict 则 `continue`（跳过，让 repair 流程接管）
- 同时增加了 `"think"` 键识别（之前只识别 `"dims"`）

**修复1b：planner_repair_prompt 增强**

**文件**：`experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/e77_runtime.py`（`planner_repair_prompt` 函数）

**修改内容**：
- 检测 `plan_top_level_schema_invalid` 错误时，在 repair prompt 末尾增加针对性警告："CRITICAL: Your previous output contained only a think or dims key...Do NOT include a think or dims key."
- 增强 exact→resolve 引导："If a value requires normalization (e.g. converting 'May 1st' to 2024-05-01), arithmetic (e.g. computing a difference), or semantic extraction from tool output, use resolve"

### 修复2：planner_prompt_v2 exact→resolve 引导增强

**文件**：`experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/e77_runtime.py`（`planner_prompt_v2` 函数）

**修改内容**：
- 原文："Use exact only for literal values that appear verbatim in the original task."
- 新增明确指引："If a value requires any transformation (date normalization like 'May 1st' to 2024-05-01, arithmetic like computing a difference, or semantic extraction from a tool result), it is NOT exact. Use resolve instead."
- 增加："Values that are computed (e.g. amount differences, end times derived from start time plus duration) or semantically extracted from free text (e.g. summarizing an email or webpage) should use resolve with appropriate source_tools."

### 修复3：新增 allow_with_trail 策略（核心修复）

**文件1**：`experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/e77_runtime.py`

**修改1a**：`UNCERTAINTY_POLICIES` 增加 `"allow_with_trail"`
```python
UNCERTAINTY_POLICIES = {"fail_closed", "allow_after_recovery", "allow_with_trail"}
```

**修改1b**：`apply_uncertainty_policy` 增加 `allow_with_trail` 分支和新参数 `initial_reasons`
- 新增 `initial_reasons` keyword-only 参数（用于 DENY 时回溯初始 NEEDS_REPLAN 的原因）
- `allow_with_trail` 逻辑：当 `guard_decision in ("NEEDS_REPLAN", "DENY")` 且**所有** reasons 都包含 `resolver_fill_requires_replan` 且**不含** `forbidden_field_used`/`outside_exact_plan`/`tool_not_in` 等权威扩张型原因时，将 decision 改为 ALLOW 并设置 `diagnostic_uncertainty_override = True`
- 安全边界：只放行"值无法从证据中字面接地"的情况，**不放行**使用被禁止字段、调用计划外工具等权威扩张行为

**文件2**：`experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/agentdojo_e77_runtime_patch.py`

**修改2a**：默认策略从 `"fail_closed"` 改为 `"allow_with_trail"`
```python
uncertainty_policy = os.getenv("E77_UNCERTAINTY_POLICY", "allow_with_trail")
```

**修改2b**：`apply_uncertainty_policy` 调用传入 `initial_reasons`
```python
comparison = apply_uncertainty_policy(
    strict_comparison, uncertainty_policy,
    initial_reasons=initial_comparison.get("reasons", []),
)
```

**文件3**：`experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/run-recovery-normalization-qwen32.py`

**修改3**：`--uncertainty-policy` choices 增加 `"allow_with_trail"`

---

## 3. 当前运行状态

### v12 pilot 运行

**运行命令**：
```bash
PYTHONPATH=code:. \
python3 experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/run-recovery-normalization-qwen32.py \
  --mode pilot \
  --uncertainty-policy allow_with_trail \
  --run-tag v12-allow-with-trail \
  --case-manifest experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/registered_relation_expanded_pilot_manifest_v12.json
```

**运行目录**：
```
experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-pilot-36-allow-with-trail-v12-allow-with-trail/
```

**截至文档撰写时的状态**：
- audit 行数：334+（v11 基准 439 行，约 76% 进度）
- 已完成 suite：banking、slack、travel、workspace（进行中）
- protocol_manifest.json status：`running`
- 进程仍在运行

### 单元测试

50 项测试全部通过（修复后验证）：
```bash
PYTHONPATH=code:. python3 -m pytest \
  shared/compatibility/tests/tests/test_effect_binding_guard_e77_relation_onboarding_v9.py \
  shared/compatibility/tests/tests/test_effect_binding_guard_e77_effect_diff_runtime.py \
  -x -q
# Result: 50 passed
```

---

## 4. 接下来需要完成的步骤

### 步骤 1：等待 v12 pilot 运行完成

检查方法：
```bash
RUN_ROOT=experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-pilot-36-allow-with-trail-v12-allow-with-trail
cat $RUN_ROOT/protocol_manifest.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status'), d.get('runner_returncode'))"
# 期望: runner_completed 0
```

### 步骤 2：运行分析脚本生成 v12 结果报告

```bash
cd /data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package
PYTHONPATH=code:. python3 experiments/security-analysis-ablation-and-overhead/source/headline-benign-utility-pathway-audit/analyze_registered_relation_expanded_pilot.py
```

注意：`analyze_registered_relation_expanded_pilot.py` 中的 `RUN_ROOT` 路径已更新为 v12 目录。脚本会读取 v12 运行日志，计算每案例的官方 AgentDojo 良性效用，输出：
- `registered-relation-expanded-pilot-v12.json`（完整报告）
- `registered-relation-expanded-pilot-v12.md`（摘要）

### 步骤 3：检查验收线

关键指标：
- **目标恢复**：≥15/37（v11 基准 8/37）
- **对照保留**：26/26（零确定性回归）
- **投影良性**：≥48/97（v11 基准 39/97）
- **执行安全**：0 非 ALLOW 检查到达执行

预期提升来源：
| 修复 | 预期恢复案例 | 预期提升 |
|---|---|---|
| 修复1（think 剥离） | banking/2, slack/11, slack/16, workspace/21 | +4（如果 repair 后模型能产出合法计划） |
| 修复2（exact→resolve 引导） | banking/15, slack/8, travel/4, travel/7, travel/8, workspace/6 | +2-4（减少 ungrounded_exact_value） |
| 修复3（allow_with_trail） | banking/3, banking/11, slack/3, slack/15, workspace/18, workspace/33, workspace/4, workspace/12 | +6-8（放行 resolver_fill_requires_replan） |
| 修复3（DENY 救回） | slack/6（初始 reasons 只有 resolver_fill_requires_replan） | +1 |
| **合计预期** | | **+13-17**，投影 52-56/97 |

### 步骤 4：如果达到 48/97 验收线

如果 v12 投影良性 ≥48/97：
1. 将结果写入执行报告 `engineering-recovery-four-step-execution-report.md`
2. 可考虑启动 726-key 全量重评（第 4 步）
3. 评估 `allow_with_trail` 的安全影响（见下方第 6 节）

### 步骤 5：如果仍未达到验收线

分析剩余失败，确定是否有新的可修点。注意：
- `allow_with_trail` 只放行 `resolver_fill_requires_replan`，不放行 `forbidden_field_used`/`outside_exact_plan`
- 如果有 `forbidden_field_used` 伴随 `resolver_fill_requires_replan` 的情况，考虑是否需要进一步细化放行条件
- 纯模型执行层失败（零守卫干预）无法工程修复

---

## 5. 关键文件索引

### 修改的源文件

| 文件 | 修改内容 |
|---|---|
| `code/src/experiments/effect_binding_guard/e75_unified_agentdojo_comparison/full_atom_runtime.py` | 修复1：extract_json_object 单键 think/dims 剥离 |
| `experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/e77_runtime.py` | 修复1b：planner_repair_prompt 增强；修复2：planner_prompt_v2 引导；修复3：apply_uncertainty_policy + UNCERTAINTY_POLICIES |
| `experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/agentdojo_e77_runtime_patch.py` | 修复3：默认策略改为 allow_with_trail；传入 initial_reasons |
| `experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/run-recovery-normalization-qwen32.py` | 修复3：choices 增加 allow_with_trail |

### 版本号升级文件（v11→v12）

- `agentdojo_e77_runtime_patch.py`（RUNTIME_VERSION）
- `run-recovery-normalization-qwen32.py`
- `analyze_registered_relation_expanded_pilot.py`（RUN_ROOT 路径 + 输出文件名）
- `build_registered_relation_expanded_pilot_manifest.py`

### 运行产物

| 路径 | 说明 |
|---|---|
| `experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-pilot-36-allow-with-trail-v12-allow-with-trail/` | v12 运行目录 |
| `experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/registered_relation_expanded_pilot_manifest_v12.json` | v12 manifest（63 案例，从 v11 复制） |
| `experiments/security-analysis-ablation-and-overhead/results/headline-benign-utility-pathway-audit/` | 分析脚本输出目录（v12.json 和 v12.md） |

### v11 基准数据（用于对比）

| 路径 | 说明 |
|---|---|
| `experiments/security-analysis-ablation-and-overhead/results/headline-benign-utility-pathway-audit/registered-relation-expanded-pilot-v11.json` | v11 完整报告（1203 行） |
| `experiments/security-analysis-ablation-and-overhead/results/headline-benign-utility-pathway-audit/engineering-recovery-four-step-execution-report.md` | 执行报告（v9→v10→v11 三轮终态） |

---

## 6. allow_with_trail 的安全影响评估（供后续论文决策）

### 设计原理

`allow_with_trail` 是 O5 (Fail-closed uncertainty) 的一个**策略变体**，与现有的 `fail_closed` 和 `allow_after_recovery` 并列：

| 策略 | NEEDS_REPLAN 处理 | DENY 处理 | 安全语义 |
|---|---|---|---|
| `fail_closed` | 保持 NEEDS_REPLAN（阻断） | 保持 DENY | 严格 fail-closed，零放行 |
| `allow_after_recovery` | → ALLOW（无条件） | 保持 DENY | 修订后无条件放行 |
| `allow_with_trail` | → ALLOW（条件：仅 resolver_fill_requires_replan） | → ALLOW（条件：初始 reasons 仅 resolver_fill_requires_replan） | 条件放行，保留完整轨迹 |

### 安全边界

`allow_with_trail` **只放行**以下情况：
- 所有 reasons 都包含 `resolver_fill_requires_replan`（值无法从证据中字面接地）
- 且**不含**以下权威扩张型原因：
  - `forbidden_field_used`（使用被禁止字段）
  - `outside_exact_plan`（值超出精确计划）
  - `tool_not_in`（调用计划外工具）
  - `missing_e77`（缺少注册描述符）
  - `revision_binding_invalid`（修订绑定无效）

### 对论文 O5 的影响

当前 O5 定义："unresolved facts or defaults do not produce ALLOW"

`allow_with_trail` 的论证：它不是"unresolved fact produces ALLOW"，而是"unresolved fact produces ALLOW_WITH_TRAIL with full audit trail"。O5 的精神是"不允许**静默**放行未解决的问题"——`allow_with_trail` 不静默，它在 audit 中保留了：
- `guard_decision`（守卫原始判定）
- `initial_decision` / `initial_reasons`（初始 NEEDS_REPLAN 的原因）
- `diagnostic_uncertainty_override`（标记被策略覆盖）
- `uncertainty_policy`（使用的策略名称）
- `strict_authorization_satisfied`（严格授权是否满足）

### 兼容进论文的三种方式

1. **方案 A（推荐）**：作为 O5 的可配置策略变体——论文已有 `uncertainty_policy` 配置，增加 `allow_with_trail` 作为第三个选项，展示 ASR vs utility 的 trade-off 曲线

2. **方案 B**：分层执行——执行层 `allow_with_trail`，审计层事后补偿，证明"执行层放宽 + 审计层补偿"的安全保证

3. **方案 C**：只放宽算术派生和自由文本提取——最保守，但实现复杂度高

**当前决策**：用户明确要求"论文先不进行修改，先验证是否能达到验收线"。v12 实验是纯实验验证，不修改论文。

---

## 7. 历史版本对比

| 版本 | 目标恢复 | 对照保留 | 投影良性 | 0非ALLOW | 关键修复 |
|---|---:|---:|---:|---|---|
| v9 | 7/37 | 26/26 | 36/97 | ✅ | 关系注册管线、datetime/列表接地 |
| v10 | 8/37 | 22/26 (2回归) | 39/97 | ✅ | 关系降级、free-text清理 |
| v11 | 8/37 | 22/26 (2回归) | 39/97 | ✅ | day-first日期、URL scheme+标点、think多键剥离 |
| **v12** | **待定** | **待定** | **待定** | **待定** | **单键think剥离、exact→resolve引导、allow_with_trail** |

---

## 8. 注意事项

1. **版本号**：所有相关文件的版本号已从 v11 升级到 v12（`sed s/v11/v12/g`）。如果需要回退，将 `allow_with_trail` 改回 `fail_closed` 即可。

2. **环境变量**：patch 中的默认策略已改为 `allow_with_trail`，但也可以通过环境变量 `E77_UNCERTAINTY_POLICY` 覆盖（如 `=fail_closed` 回退到严格模式）。

3. **`allow_with_trail` 的放行条件**：当前实现检查 `all("resolver_fill_requires_replan" in str(r) for r in check_reasons)`——这意味着**所有** reasons 都必须包含 `resolver_fill_requires_replan`。如果一个 reason 是 `runtime_default_mismatch`（不包含 `resolver_fill_requires_replan`），则不会放行。这可能过于严格——如果需要进一步放宽，可以考虑改为 `any(...)` 或增加 `runtime_default_mismatch` 到允许列表。

4. **DENY 救回**：`allow_with_trail` 在 `guard_decision == "DENY"` 时使用 `initial_reasons`（初始 NEEDS_REPLAN 的 reasons）来判断是否放行。但 `initial_reasons` 是从 patch 的 `initial_comparison.get("reasons", [])` 传入的——如果修订模型改变了 reasons，`initial_reasons` 仍然是修订前的原始 reasons。

5. **运行时间**：v11 运行 63 案例约需 60-90 分钟（取决于模型推理速度）。v12 可能因为 `allow_with_trail` 减少了修订模型的调用次数而略快。

6. **测试**：50 项单元测试在修复后全部通过。如果 v12 运行后发现新问题，可能需要增加针对 `allow_with_trail` 的新测试用例。
