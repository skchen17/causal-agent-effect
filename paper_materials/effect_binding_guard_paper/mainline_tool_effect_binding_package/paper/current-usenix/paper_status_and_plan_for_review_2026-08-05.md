# 论文状态与规划路径文档（供独立审稿评估）

- 日期：2026-08-05
- 用途：为另一位 AI 审稿人对当前规划进行分析与评价提供完整、可核实的状态快照
- 事实来源：所有数字与状态均来自已核实的运行报告/冻结产物（文中标注来源路径）

---

## 1. 论文定位与预期内容

### 1.1 论文标题与核心主张
**"Binding Agent Tool Calls to Effects: Counterfactual Contracts for Pre-Commit Mediation"**（USENIX Security 2027 目标）

三层核心贡献（当前 claim boundary 内）：
1. **表示义务理论**：联合 effect-authority 视图合并授权不等价效果时，任何 monitor 无法避免 unsafe allow 或 withheld authorized work（下界定理）；反事实注册是执行可行的 insufficiency witness
2. **反事实 contract 注册方法论**：counterexample-guided 注册（split/bind/trigger/expansion refinement，有限域内单调收敛）；O1–O6 义务体系（O6 为新增 override trail 完整性义务）
3. **条件性 mediation runtime**：v17 修复版全量实现（pre-commit 逐效果核对 + allow_with_trail 策略 + planner replan）

### 1.2 预期论文结构（Phase D 目标形态）
- Theory 前移：threat model → 表示理论（下界定理 + T1 收敛定理 + T3 分离命题）→ 方法论 → runtime
- Results：E78 主表（v17 merged 数字替换）+ V0–V3 Representation Attribution 整节（分支 N2 正结果形态）或瓶颈定位节（N3 零/负形态）
- 披露义务：context-repair 存在（窗口参数、9 案例、claim boundary）、321-case 适用性子集边界、运行间不可复现差异（绑定 plan_hash）

---

## 2. 已完成实验结果（论文正源候选）

### 2.1 v17 修复版全量（merged，协议冻结，正源）
来源：`experiments/security-analysis-ablation-and-overhead/evaluation/strict-atom-representation-attribution/protocol.json`（protocol-frozen，2026-08-05）；merged 目录 `...-v17-726-r2-context-repaired`

| 指标 | v17 merged | 对比 |
|---|---|---|
| ASR | **11/629 = 1.7%** | no_guard 54/627=8.6%；E78 旧口径 2/627=0.3% |
| Benign utility | **46/97 = 47.4%** | E78 33/97=34%；no_guard 64/97=66% |
| Attack utility | 273/629 = 43.2% | E78 207/627=32.9% |
| 守卫决策分布 | ALLOW 2173 / DENY 84 / NEEDS_REPLAN 415 / override 426 | — |
| 计划质量 | 711 事件 / 577 接受（81.2%） | — |

数据处理链（已闭环）：v17 r2 全量 → 16 门禁 15 过（唯一失败 command_protocol_clean，9 条 HTTP 400）→ detect 枚举截断集 T=9（user_task_35×6 + user_task_38×3）→ 分级 context-repair（73728→81920→122880，9/9 clean）→ 不可变 overlay merge → merged finalizer **16/16 全过** → 冻结。

### 2.2 既有证据体系（论文已引用，08-03 前完成）
- 321-case closed-loop：whole-call 3/273 vs atom 0/273（适用性子集，带边界）
- AgentLAB 固定迁移：303 案例 95→0 ASR，utility 180→87；1,439/1,439 执行对账
- 有限域：56-call 域 118 separating pairs→0（typed contract）；ToolSandbox 32 contexts 41→0
- E84 reviewed-authority：26/97 manifests 编译，20→15/26
- no_guard 强基线：Qwen3-32B 64/97 = 66%

### 2.3 窗口期新增证据（2026-08-04/05，CPU 侧全部完成）
- **E2 粗 policy 族敏感性**（48 行网格，双域）：power-set 族下 7/10 删除行产生分离碰撞；粗族 20/24 非空行冗余率 1.000；唯一例外 payload×resource（0.75）→ "typed qualifier 必要性是 policy-relative"（MC5 关闭）
- **T1 注册收敛定理**：refinement 链 SP [124→60→28→12→4→0] 单调不增、6 步到不动点（56-call 冻结域轨迹检查 9/9 passed）
- **T3 原则分离命题**：least-privilege + complete-mediation 不蕴含 atom 表示（构造性）
- **O6 override trail 义务**：四成分（排除式保证/非肯定性声明/证据隔离/不扩充授权）；fallback 占比 φ=0.000
- **红旗缺陷修复**（多值字段 check 覆盖）：2/2729 calls（0.07%）硬阻断失效，经确认**与 11 个成功攻击零交集**；修复后新门禁 `no_allow_with_expansion_findings` 全量通过

---

## 3. 正在进行的实验

### 3.1 V0–V3 严格归因主实验（运行中，核心分叉点）
- **协议**：`strict_atom_representation_attribution_protocol_2026-08-03.md`（protocol-frozen）
- **四变体 × 726**：V0 tool_identity_only / V1 opaque_whole_call / V2 raw_schema_fields / V3 validated_atom_fields
- **状态**：串行驱动（PID 1448380），V0 运行中（~14%），ETA V3 ≈ 2026-08-08 凌晨（≈56 GPU 小时）
- **主假设 H1–H5**：H1 安全（V3 ASR 低于三对照，配对 629）/ H2·H3 非劣（benign/attack utility ≥ -0.05）/ H4 非拒绝驱动 / H5 跨 3 suite + 3 strata
- **判定**：协议 §2.3 解释矩阵 + exact McNemar（双侧 p<0.05）+ paired bootstrap 95% CI

### 3.2 后续规划实验（依赖 V0–V3 结果）
- **16-case smoke** 已完成（四变体全 PASS）→ 全量进行中
- **160-case stability repeat 1/2**（协议 Phase 4，温度随机性量化）
- **E1 第二模型**（本地 Qwen 9B，V3+no-defense，全量约 25-35 GPU h 或 subset 5-10 h）
- **E4 authority/resolver 覆盖 pilot**（预注册 20-30 task，10-20 GPU h——效用缺口正面进攻）

---

## 4. 规划路径与分支决策

### 4.1 分支决策树（V0–V3 结果 → 叙事选择）
| 结果 | 路径 | 论文形态 |
|---|---|---|
| **正**（V3 显著优于 V0/V1/V2 + H4 + H5） | N2 全量归因叙事 + E1 全量 + E4 | Results 新增 Representation Attribution 整节；E78 降为全系统对照；冲击 weak accept |
| **零/负**（V3≈V2 或无优势） | N1+N3 收缩定位 | "表示义务 + 反事实方法论 + 条件性 mediation"；"atom 不替代 authority reasoning"作为边界贡献；目标 weak accept + 转投 |
| **混合**（V3>V2≈V1） | N2 细分 + N3 局部 + E2 判断 | 写作成本最高；需按粒度层次拆分 |

### 4.2 时间线（Cycle 2 目标，注册 2027-01-19 / 提交 2027-01-26）
- 08-08：V0–V3 完成 → finalize → H1–H5 判定
- 08 月中：分支决策 + Phase D 数字替换启动 + E1/E4 决策
- 09 月中旬：主 Results 证据齐备（检查点）
- 10-12 月：写作定稿 + Artifact + 模拟审稿迭代
- 01 月：投稿

### 4.3 ACCEPT 路径评估（paper-reviewer 2026-08-04 校准）
- 当前：Borderline（accept 3-6%）
- CPU 项全套后：6-10%
- +V0–V3 正：15-22%（上限受效用压制）
- 完整方案（+E1+E4）：20-28%
- **核心判断**：缺"一个强信号"；V0–V3 正结果是唯一能把重心推向 weak accept 的实验

---

## 5. 披露义务与已知局限（审稿关注点）

1. **context-repair 存在**：v17 数据经 9 案例修复 + overlay 合并；claim boundary 限定"修复仅覆盖 T 内案例"；引用必须绑定 merged 目录 + plan_hash `ea881cfc…`
2. **运行间不可复现差异**：temperature-0 非确定；同案例（u38 inj1）r1/r2 security 翻转；需披露
3. **Sandwiching 三轴优势**（⚠️ 未处置）：v17 口径下 Prompt Sandwiching（ASR 1.27%/BU 62.9%/UA 58.1%）在三条 headline 轴上同时优于 \sys{}——"competitive tradeoff, not Pareto dominance" 结论句失效；三路径待裁决（口径核查/平面扩展/诚实降级）
4. **planner-replan 污染型放行**：11 个成功攻击中 6 个 slack 案例经 replan 修订后放行（initial tool_not_in）；需 method 披露 replan 安全语义
5. **50-task gate 未达**：benign 46<50
6. **单模型**：Qwen3-32B（E1 备选）
7. **红旗缺陷**：已修复并验证零攻击关联；历史数据保留取证

---

## 6. 待决策项（影响后续路径）

| 项 | 选项 | 截止 |
|---|---|---|
| 投稿轮次 | Cycle 1（08-18 注册）/ Cycle 2（2027-01） | **08-18** |
| Sandwiching 处置 | 口径核查 / 平面扩展 / 诚实降级 | V0–V3 后 |
| E1/E4 是否执行 | 视 V0–V3 结果与 GPU 预算 | 08 月中 |
| C 线 Artifact 实施 | 补丁确认/claim map 进包/README | 10 月前 |

---

## 7. 给审稿人的评价请求（供参考）

建议从以下维度评价当前规划：
1. **证据链完整性**：冻结协议 → 修复 → 重跑 → repair → 冻结 → 主实验的纪律性是否有缺口
2. **V0–V3 结果的正/零/负分支处置是否完备**（含混合分支）
3. **已知弱点（Sandwiching/效用/单模型/不可复现）的处置策略是否可辩护**
4. **披露义务是否充分**（context-repair/planner-replan/红旗历史）
5. **时间线可行性**（Cycle 2 目标 + W6 缓冲）
6. **对 ACCEPT 概率估计的校准**
