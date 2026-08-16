# 改进方案白皮书（2026-08-03，供 PM 决策）

依据：current-usenix 全部 sections/appendix、`simulated_usenix_review_2026-07-30`、`submission_war_plan`、`strict_atom_representation_attribution_protocol`、`evidence_sufficiency_audit`、`theory_proof_audit`、`claim_to_source_map`。所有建议锚定具体定理/section/实验编号；标注"写作"与"实验"两类，杜绝以写作冒充实验。

**缺口映射**：①效用腰斩→实验 E4/E2 + 叙事 N3；②单模型→实验 E1；③atom 归因→实验 V0-V3 + 叙事 N2/N3；④定理未覆盖实现→理论 T2；⑤"contract 是序列化"→实验 E2 + 理论 T4；⑥非自适应/有限域偏易/26/97 覆盖→实验 E3/E2/E4 与写作边界保留。

---

## 1. 理论增强选项

**T1（推荐）：注册 refinement 的单调终止定理。**
内容：在 Method §3（Counterfactual Contract Registration）的受限 contract 语言下证明：split/bind/trigger/expansion 每次 refinement 都产生分区细化（由 Proposition "Authorization quotient" 诱导的格序），任意有限实例域 D 上分区格有限，故 CEGAR 循环终止于不动点（或 fail-closed）；并证明 refinement 链上 collision 计数单调不增（与 Prop "Ambiguous-cell lower bound" 一致）。把 formal_proofs 的 field-necessity 从单点论证升级为"检索最小充分 contract 的单调优化"框架。可验证性：在 56-call 有限域记录真实 refinement 轨迹（E80 风格模型检查）。
落地：Security Analysis §"Counterfactual Witnesses and Bounded Adequacy" 后新小节 + appendix 证明。
降险：中。把 limitations.tex 的"任意 LLM contract 合成未证明"精确化为"开放语言未证明，受限语言内有界收敛"。
工作量/风险：低-中，纯数学 + 一个 CPU 检查。风险低（与现有命题相容）。

**T2（推荐）：confined 定理扩展 resolver-fill 与 uncertainty-override 路径。**
内容：两个新命题。(a) 将 O2 显式化为"符号关系经 typed resolver 细化后仍保持 bound 约束"，则 Method §"Authority and Totalization" 的 resolver-fill 路径提交效果仍在 B_q 内——这正是 Prop "Trusted evidence refinement" 的 authority 侧实例化，只需把"细化不扩 bound"从条件改成义务的一部分。(b) 对 v17/E77 的 `allow_with_trail`（协议 §5 记录 strict 与 effective decision）：新增义务 **O6（override trail 完整性）**——effective ALLOW 必须携带证明被覆盖效果在 B_q 内的 witness；证明在 O1-O6 下 override 路径仍满足 Single-commit confinement 的包含链，并给出 override 率实证上界（用协议 §7.2 已定义的 override rate）。
落地：Security Analysis §"Conditional Effect Confinement" 扩展；Table e80_obligations 加 O6 行。
降险：中-高。正面回应"headline runtime 未实例化 O1/O2 全部前提"（审稿 Major Concern 2），把"实现做了定理没覆盖的事"改写为"定理覆盖实现"。
工作量/风险：中。**前置核实** `allow_with_trail` 的 trail 字段是否足以支撑 O6，否则命题反噬。

**T3（可选）：原则分离命题（novelty boundary 定理化）。**
内容：构造性命题——(i) 任意实现 least-privilege + complete-mediation 但不保授权等价类的 monitor 仍不安全（Compound-effect binding Corollary 的显式化）；(ii) 存在 authorization-sufficient 的 whole-call 表示（security_analysis.tex 已声明），故两原则不蕴含 atom 表示。这使"不是 rename"（theory_proof_audit Novelty Boundary）成为可构造分离证据，回应"close to argument-provenance and contract work"。
落地：Security Analysis 开头 + related_work 对照段。
降险：中（理论型审稿人）。工作量：低。风险：低。

**T4（可选）：oracle 误差方向性引理。**
内容：把注册的保守性写成引理：oracle 误报（安全不变差异标为 gap）只导致过度细化/overpartition（E85 已测 80/80 无 over-sensitivity），oracle 误漏才导致 unsafe——因此"无 collision 套件"结论的失效方向是漏报而非误报，抽样套件保留 falsification 措辞。可补一个 ε-噪声下 collision 计数界的表述，回应"contract 只是 state-diff 序列化"的质疑（表示必要字段由 policy 分离而非状态字节决定，Method §"A field is operationally necessary" 已有定性版本）。
落地：Method §3 + Security Analysis。工作量：低。降险：中。

---

## 2. 实验补强选项

**E2（推荐，CPU 零 GPU）：粗 policy 族 + qualifier-deletion。**
回答：typed qualifier 是否只在 power-set family 下必要？（审稿 Question 4 / Major Concern 5）
做法：在 56-call 有限域与 32 ToolSandbox 域上，把 submultiset family 替换为 (a) effect-kind 聚合、(b) resource 聚合、(c) 计数截断 {0,1,≥2}；逐 family 重算 typed contract 的 separating pairs；再逐 qualifier 删除（date/subject/recurrence/payload/visibility），输出"每个 family 下哪些字段变冗余"的必要性敏感性表。
成本：CPU 小时级。影响：高——若粗 family 下部分 qualifier 冗余，直接证明表示是 policy-relative 而非状态序列化，且为 Thm Finite-domain adequacy 提供多 family 实例。

**E1（推荐）：第二模型。**
回答：主安全-效用排序跨模型成立？（Question 5，缺口 2）
做法：按协议 Phase 6 预注册，本地 Qwen3.5-9B-derived（E80 已有 runner 适配）跑 **V3 + no-defense 全 726**（约 25-35 GPU 小时），或先跑 160 stability subset（约 5-10 小时）再决策。同族不同量化（Q8_K）可分离"量化"变量但显存翻倍，不建议同时做。
影响：高。方向一致则把"cross-model generalization"从 Pending Claims 移入 supported（边界：同族 checkpoint）。

**E4（推荐）：authority/resolver 覆盖 pilot（缺口 1 的直接进攻）。**
回答：utility 损失多少可归因于 authority/resolver 接口而非表示？E78 pathway audit 已示 32/37 损失含 runtime feedback、22/32 含 binding/evidence findings、12 例拒绝早期良性结果中出现的 resolver 值。
做法：按 evidence_sufficiency_audit Required #5：系统化 onboarding 剩余 source-to-target 组（16-task pilot 仅恢复 1/12，14 组中 12 组在失败 case），预声明 20-30-task benign pilot（含历史失败层 + 稳定 control），重测 utility；**禁止事后加 parser**。
成本：中（解析器工程 + 小规模 rerun，约 10-20 GPU 小时）。影响：高——若恢复 5+ 任务，"安全增益来自保守拒绝"替代解释显著弱化。

**E3（可选）：adaptive 扩展。**
回答：固定 AgentLAB 重放在 adaptive generation 下是否保持？（Major Concern 7）
做法：对 303 任务子集（40-60 case）跑 AgentLAB attack generation，或扩展 E82 的 40-key 框架到 AgentLAB。
成本：中-高 GPU。影响：中。仅预算剩余时做；否则守固定重放措辞（已兼容 claim boundary）。

**E5（小实验+写作）：12-context 公平性修复。**
统一 12 个 larger-context repair 的处置（保守策略或全方法同口径），回应 evidence_sufficiency_audit Risk #2；可选加 1 个 released-checkpoint common-input 行（约 25-35 GPU 小时）。公平性修复优先于新 baseline。

**E6（零增量）：temperature-0 随机性量化。**
协议 Phase 4 的 160-case repeat 1/2 已含；补充 no-defense 侧 repeat 量化基线 54/627 的模型固有变异，把"单次运行"弱点转为"方差已量化"。

---

## 3. 论文故事线重组

**N1（推荐骨架）：表示义务 + 反事实验证方法论 + 条件性 mediation。**
中心主张：monitor 必须保真授权等价类（Representation insufficiency + Authorization quotient）；counterfactual 是执行可行的 insufficiency witness（Mediation-gap witness）；runtime 是其有限实例。
组织：Theory 前移（threat model 后接 Security Analysis 核心）；Method 注册部分独立为"Offline validation methodology"；runtime 压缩为 feasibility/transfer；E78/E79 篇幅减半。
适用：V0-V3 零/负结果或效用无法修复。与 claim_to_source_map 完全兼容（理论本就是第一贡献）。

**N2（正结果升级）：效果粒度归因叙事。**
中心主张：在预注册全量下，表示粒度本身改变可授权边界（H1 成立且 H2/H3 非劣）。
组织：Results 新增 "Representation Attribution" 整节（V0-V3 表 + suite/strata 分解 + DENY/ABSTAIN/override 分解）；E78 降为全系统对照。
适用：H1-H5 全过；混合结果（V3>V2≈V1）写作成本最高，需细分粒度层次。

**N3（负结果转化）：representation 不替代 authority reasoning。**
中心主张：atom prompt-only 失败（Round 1-5 已撤回）+ V0-V3 的部分差异本身就是贡献——effect-side 合并与 authority-side 模糊是两个正交义务（ρ_E/ρ_A 分离，Trusted evidence refinement 支撑）。
组织：新增 "Where the bottleneck is: representation vs. authority" 小节：E84 子集（authority 独立）+ pathway audit（utility 损失定位接口）+ V0-V3（表示层贡献）三线构成修复决策图；结论改为"给出区分工具而非系统"。
适用：V0-V3 效用负/部分负。兼容现有边界。

**无论正负都成立的骨架**：以 N1 为基座；V0-V3 结果经协议 §2.3 解释矩阵分流到 N2（正）或 N3（零/负）。两条叙事共用同一套实验，只需重写 Results 归因节与 Abstract 尾句，成本可控。

---

## 4. 风险降低路线图

**档 1：现在就能做（v17 运行中，CPU/写作）**
- W1 写作：Abstract 减数（11→3-4 个数字，作战计划 §4.5）。杠杆：中。
- W2 写作：Intro 加 O1-O5 实例化边界句。杠杆：中。
- E2 实验（CPU）：粗 policy 族 + qualifier-deletion。杠杆：高。
- T2 前置核实 + T1 轨迹记录（CPU，E80 扩展）。杠杆：中-高。
- W3 写作：utility 重定位叙事草稿（pathway audit + frontier 定位 + 26-task 归一化 20→15/26）。杠杆：中。
- W4 写作：granularity 表 v1.1.2/v1.2.1 版本说明（已核实差异）。杠杆：低-中。
- D1 决策：N1/N2/N3 分流预案（配合协议 §2.3）。杠杆：中。

**档 2：v17 落地后**
- v17 finalizer 核对 + 协议 freeze（阻塞项）。杠杆：高。
- 16-case smoke → 4×726 V0-V3 主实验（约 70-110 GPU 小时）。杠杆：高（缺口 3）。
- B 线 Phase D：v17 数字落地正文（Evaluation→Results→Abstract 顺序）。杠杆：中。

**档 3：归因实验后**
- H1-H5 判定 → 故事线选择 → Results 重写。杠杆：高。
- E1 第二模型（9B 全量或 subset，约 25-35 GPU 小时）。杠杆：高（缺口 2）。
- E4 authority/resolver pilot（预注册 20-30 task）。杠杆：高（缺口 1）。
- 协议 Phase 5：26-task reviewed-authority 次级分析（无 GPU）。杠杆：中。

**档 4：投稿前（Cycle 2：注册 2027-01-19 / 提交 2027-01-26）**
- E3 adaptive 扩展（预算剩余时）。杠杆：中。
- Artifact 打包 P0-P2（路径参数化、排除清单、匿名 URL、干净环境复现）。杠杆：高（阻塞）。
- 全文数字一致性 + claim-to-source 更新 + 复现验证。杠杆：中。
- E84 独立人类评审（可选）。杠杆：低-中。

---

## 5. 优先级总排序（TOP 10）

| # | 动作 | 杠杆 | 成本 | Cycle 2 前必须 |
|---|---|---|---|---|
| 1 | V0-V3 4×726 主实验（smoke→full→stability） | 极高 | 70-110 GPU h | ✅ |
| 2 | v17 finalizer + 协议 freeze + 数字落地 | 高 | 近零 | ✅ |
| 3 | E2 粗 policy 族 + qualifier-deletion | 高 | CPU 小时级 | ✅ |
| 4 | T2 定理扩展（resolver/override + O6） | 高 | 中（写作+核实） | ✅ |
| 5 | W1/W2/W3 写作套件（减数/边界句/utility 重定位） | 中-高 | 低 | ✅ |
| 6 | N1 骨架 + N3 预案落地为 Results 结构 | 中-高 | 低 | ✅ |
| 7 | E1 第二模型 | 高 | 25-35 GPU h | ✅（至少 subset） |
| 8 | E4 authority/resolver pilot | 高 | 中（10-20 GPU h） | ✅（视 GPU） |
| 9 | Artifact P0-P2 + 匿名 URL | 高 | 低-中 | ✅ |
| 10 | E3 adaptive 扩展 | 中 | 高 | 可选，否则守固定重放措辞 |

排序逻辑：1/2 是证据基石并决定叙事方向；3/4 是低成本高杠杆（分别反击"序列化"与"定理未覆盖实现"）；5/6 使重心在 V0-V3 落地前即可转向理论-方法论轴，负结果代价可控；7/8 直接打缺口 2/1；9 为提交硬门槛；10 是剩余预算消费项。算力不足时砍单顺序：10 → 8 的全量（保留预注册设计文档）→ 7 降为 subset。
