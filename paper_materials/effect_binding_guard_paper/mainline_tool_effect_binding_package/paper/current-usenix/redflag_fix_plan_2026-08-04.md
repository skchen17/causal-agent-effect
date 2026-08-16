# 红旗修复方案：多值字段 check 覆盖缺陷（2026-08-04）

状态：**已实施**（2026-08-05 用户确认 B 路径后应用；v17-726-r2 全量重跑运行中）。原状态记录：方案待确认（v17 运行中，按协议红线当前禁止修改 runtime 源码；v17 finalize 后 + 用户确认后实施）

## 1. 缺陷定位（已源码核实）

文件：`experiments/intent-bound-runtime-guard/source/effect-difference-runtime-guard/e77_runtime.py` L188-212 `apply_uncertainty_policy`

```python
for check in checks:
    status = str(check.get("status"))
    field = str(check.get("field") or "?")
    if status in AUTHORIZED_FIELD_STATUSES:
        field_decisions[field] = "ALLOW"          # ← 直接赋值覆盖
    elif status == "resolver_fill_requires_replan":
        field_decisions[field] = "ALLOW_WITH_TRAIL"  # ← 直接赋值覆盖
    else:
        field_decisions[field] = "BLOCK"          # ← 直接赋值覆盖
```

**机制**：`field_decisions` 按字段名 dict 赋值，同一字段出现多个 check（多值字段，如 `attachments=["file_A","file_B"]` 每值一个 check）时，**后到的 check 覆盖先到的**：
- 值 A 状态 `outside_exact_plan`（扩权发现）→ `field_decisions[attachments] = "BLOCK"`
- 值 B 状态 `matched_exact` → `field_decisions[attachments] = "ALLOW"`（**覆盖 BLOCK**）

结果：`blocked` 集合（L201）漏掉该字段 → 不阻断 → 若其余字段均授权则最终 ALLOW，且 override 记录携带本应硬阻断的 `outside_exact_plan`。实测 2 行违规（audit 行 1097/1106，`send_email` attachments）。

## 2. 修复设计（最严格优先聚合）

**聚合语义**（per-field）：`BLOCK > ALLOW_WITH_TRAIL > ALLOW`（任何 check 为 BLOCK 则字段 BLOCK；无 BLOCK 但有 trail 则字段 trail；全 ALLOW 则字段 ALLOW）。

```python
for check in checks:
    status = str(check.get("status"))
    field = str(check.get("field") or "?")
    if status in AUTHORIZED_FIELD_STATUSES:
        # ALLOW 不降级已有更严格判定
        field_decisions.setdefault(field, "ALLOW")
    elif status == "resolver_fill_requires_replan":
        # 仅提升 ALLOW → ALLOW_WITH_TRAIL，不降级 BLOCK
        if field_decisions.get(field) != "BLOCK":
            field_decisions[field] = "ALLOW_WITH_TRAIL"
    else:
        # BLOCK 恒覆盖（最严格优先）
        field_decisions[field] = "BLOCK"
```

**语义正确性论证**：安全属性 = "任何扩权发现（五类）不得被策略层放行"。最严格优先保证该属性在**多 check 字段**与单 check 字段同样成立；`blocked` 集合（L201）与 reasons 过滤（L205-208）逻辑不变，自动受益。

## 3. 修改点清单

| 文件 | 修改 | 说明 |
|---|---|---|
| `e77_runtime.py` L196-200 | 赋值逻辑改为最严格优先聚合 | 核心修复，约 6 行 |
| `shared/compatibility/tests/tests/test_effect_binding_guard_e77_effect_diff_runtime.py` | 新增聚合语义测试 4-6 项 | ① BLOCK+ALLOW→BLOCK；② BLOCK+trail→BLOCK；③ trail+ALLOW→trail；④ 多值全 ALLOW→ALLOW；⑤ reasons 过滤仍只含 blocked 字段；⑥ 修复后 2 行违规场景回归 |
| `agentdojo_e77_runtime_patch.py` | **不改** | 聚合在 runtime 内完成，patch 无对应逻辑 |

## 4. 受影响条件与重跑计划

**受影响**（凡走 `apply_uncertainty_policy` 的运行）：v17 全量、V0-V3 四 variant 全量、160-case stability、E1 第二模型、E4 pilot。

**实施时序**（严格遵守协议）：
1. **当前（v17 运行中）**：只准备方案，**不改任何源码**（协议红线 + 代码 hash 冻结）
2. **v17 finalize 后**：用户确认方案 → 应用修复 → 跑全量回归（E77 50 项 + 新增聚合测试 + 全量 90 项）
3. **v17 重跑**（修复版）：全量 726 重跑（约 3-5 天），finalizer 复验 → 协议冻结（protocol.json 使用修复版 hash）
4. **V0-V3 主实验**：用修复版运行（与 v17 修复版一致）
5. 论文数字全部基于修复版；旧版运行数据保留取证（不断言）

> ⚠️ **时序更正（2026-08-05，research-assistant 审查）**：步骤 2 实际执行时点为 **r1 runner 完成之后、r1 finalizer 失败排查期间**——r1 finalizer 从未通过（两次失败于 `command_protocol_clean`，非红旗相关），故"v17 finalize 后"的字面表述未发生。协议语义（运行结束后才改 runtime 源码、冻结前完成重跑）仍然满足。详见 `pm_process_review_research_2026-08-05.md` §1.1。

**时间线影响**：v17 重跑 +3-5 天，由 W6（09-07→13）缓冲吸收；不影响 E2/T1/T3/D1/C 线 CPU 工作（全部独立）。

## 5. 备选方案（若用户选择"披露+限定"而非修复）

- v17/V0-V3 同版运行（现状版），论文披露该缺陷：O6 限定为"单值字段的排除式保证"+ 披露多值字段例外（附 2/726 行审计证据与修复路径）
- 风险：审稿人 artifact 复现审计时发现硬阻断失效 → R1 级（overclaim/诚实性）触发面；且与 O6"排除式保证"表述冲突
- **PM 建议：修复（选项①）**——协议 §2.2 明文要求，成本可控（+3-5 天），证据链干净

## 6. 验收标准（修复实施后）

- 全量回归通过（90 项 + 新增聚合测试）
- 修复版 dry-run（16-case smoke）0 违规
- v17 重跑 finalizer：四层决策计数中 override 行零携带五类扩权发现
- protocol.json 冻结（修复版代码 hash）

## 7. 执行后记（2026-08-05，research-assistant 审查补录）

**实施结果**：修复已应用（e77_runtime.py 最严格优先聚合）；聚合测试实际扩至 10 项（方案 6 项 + experimental-researcher 补 4 项顺序无关/回归用例），全量测试 53/53 passed（research-assistant 独立复跑验证）；v17-726-r2 已启动。

**验收偏差记录**（对应方案 §6 第 2 条）：实际 smoke 为 **5-case benign-only**（v17r2-smoke），而非方案写的 16-case 协议 smoke。
- **原因**：runner `--case-manifest` 接口强制 benign-only 冻结 manifest（run-recovery-normalization-qwen32.py L384-385），16-case 协议 smoke 含 attack 案例，无法经该接口执行。
- **当时可行的替代**：用 `--suite/--user-task/--injection-task` 单案例接口手动跑 attack 子集；PM 未评估该替代，偏差成立但已记录。
- **残余风险评估**：低——r2 全量覆盖全部 629 attack 案例；红旗门（finalizer `no_allow_with_expansion_findings`）会在 r2 finalize 时对全量做最终验收。
- **长期建议**：扩展 smoke 接口支持 attack 案例（见审查报告 G-4）。

**关联待办**（来自审查报告，非本方案范围）：
- 🔴 R-1：build-protocol.py 硬编码 r1 目录，r2 自动冻结必失败，需在 r2 finalize 前修正指向；
- 🔴 R-2：400 大概率在 r2 复发（case 级 context 超限，机制见审查报告 §1.4），处理路径见 `pm_process_review_research_2026-08-05.md` §4。
