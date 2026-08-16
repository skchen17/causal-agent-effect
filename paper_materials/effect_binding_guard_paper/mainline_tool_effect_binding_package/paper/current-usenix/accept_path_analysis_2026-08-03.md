# ACCEPT 路径分析报告（2026-08-03）

依据：sections/appendix 全文、improvement_whitepaper_2026-08-03、submission_war_plan §4.5、simulated_usenix_review_2026-07-30、strict_atom_representation_attribution_protocol。

## 0. 结论摘要

Borderline 定位准确：理论（创新 7/技术 8）已是"可辩护贡献"，但三缺口（效用 33/97、单模型、atom 归因窄）使系统审稿人无法 accept。**核心判断：缺的不是"多个中等信号"，而是"一个强信号"**——任一维度推到"审稿人必须承认"的强度即可跨线；最高杠杆强信号是 V0-V3 全量正结果，它把 granularity 从机制 witness 升为全量因果证据。

## 1. USENIX Accept 的审稿决策模型

基于公开惯例的推断：3-4 位独立审稿人 + AC 裁量；accept 通常要求≥2 人给 accept/weak-accept 且无"致命伤"共识。审稿人先找"必须拒的理由"（trigger），找不到才评估"值得接受的理由"（signal）——**消除 trigger 是元条件，强信号决定上限**。本论文场景下权重：理论深度≈系统效能≈问题新颖度，但"影响力"评分（当前 5.5）主要由效能落地驱动。

接受判据（4 条）：
- **J1 无致命伤**（必要条件，缺则必拒）：overclaim、不可复现、baseline 不公平、核心主张缺直接证据、效用问题被回避——任一被 2+ 审稿人确认即拒。
- **J2 一个强贡献**：审稿人能一句话复述的、非 rename/增量的安全贡献。当前理论（Representation insufficiency 下界 + 可执行 counterfactual witness）接近但未达"强"——模拟审稿 Originality 3/5（"接近 argument-provenance 与 contract 工作"）。
- **J3 验证完整性**：核心机制主张有全量、预注册、跨设置的直接证据。当前理论侧强（56-call 有限域无碰撞 + ToolSandbox 32/32 预注册），系统侧弱（321-case 适用性子集）。
- **J4 影响力潜力**：≥2/3 审稿人认为会被引用/影响防御设计。当前最弱（5.5），被效用与单模型共同压低。

## 2. 差距分析（当前 vs Accept）

已满足：J1 大部分关闭——claim boundary 纪律（模拟审稿 Strengths #8）、claim-to-source + fail-fast 复现、负结果/不可评估行保留、all-key bounds，这是"unusually auditable"的既有资本；J3 理论侧（118/41 separating pairs 反证、finite-domain adequacy 实例化）。

未满足（含严重度）：
- **G1 效用（高，必触发系统审稿人）**：63→33/97、180→87；仅 26/97 manifests 编译。"安全增益=保守拒绝"替代解释未击退。pathway audit（32/37 损失含 runtime feedback）已部分缓解，但 MC1 仍判为头号弱点。
- **G2 单模型（高）**：Qwen3-32B 全链唯一（MC3），仅靠写作收缩外推。
- **G3 atom 归因窄（高，机制主张命门）**：321-case 为 feedback-selected，3 个安全差异集中同一 injection goal（MC4）；H1-H5 无全量证据。
- 次级：O1/O2 未端到端实例化（MC2）、minimality 未测粗 policy 族（MC5）、adaptive 未做（MC7）、artifact 未完成（MC8）。

**关键判断**：缺**一个强信号**——弱拒↔弱接受的摇摆来自"所有信号停在中等"，三缺口任一升级为直接证据都会把 2 位审稿人评分从 6 推到 7-8。其中 **G1 是必要条件候选**（处理不当=系统审稿人触发 J1 全拒，缺则必拒）；**V0-V3 正结果是充分条件主件**（同时抬 J2/J3/J4）。G2 是低概率否决、高概率减分项。

## 3. 最高杠杆组合（三个方案）

### 方案 A：理论-方法论主导（对赌理论审稿人）
- 组合：N1 骨架 + T1（refinement 单调终止）+ T2（O6 + resolver/override 覆盖定理）+ T3（novelty 分离命题）+ E2（粗 policy 族 + qualifier-deletion）+ N3 负结果转化；V0-V3 仍跑、定位为边界刻画。
- 逻辑链：T3 构造性证明"least-privilege + complete-mediation 不蕴含 atom 表示"、E2 证明 qualifier 必要性 policy-relative（MC5 关闭）→ 审稿人把论文读作"新的表示义务 + 可执行验证方法论"，J2 3/5→4/5；效用以 N3"给出区分工具而非系统"收口。
- 资源：V0-V3 70-110 GPU h（不可省）+ E2 CPU + T 系写作 3-4 周人日；总 GPU ~100 h。
- 成功概率 ~0.25-0.3：USENIX 是系统会议，纯方法论论文需遇理论友好审稿组（约 1/3），且仍须 E1 subset 关 G2。
- 失败模式：审稿人 2 人问"so what"；降级 weak accept 或转投，损失可控（claim boundary 已兼容）。

### 方案 B：系统效能主导（对赌实证/系统审稿人）
- 组合：V0-V3 全量 + E4（预注册 20-30 task authority/resolver pilot）+ E1 全量（9B）+ N2 归因叙事 + E5 公平性修复 + E2。
- 逻辑链：V0-V3 正（V3 优于 V0/V1/V2，H4 非拒绝驱动、H5 跨 strata）→ J3 闭合；E4 恢复 5+ 任务 → G1 替代解释显著弱化；E1 方向一致 → G2 关闭。三缺口同转正 → J4 随效用上升，审稿人看到"理论下界 + 归因闭环 + 效能可控"。
- 资源：V0-V3 70-110 + E1 25-35 + E4 10-20 GPU h ≈ 105-165 GPU h；E4 工程（parser+onboarding）3-6 周人日；写作 4-6 周。8 月中 V0-V3 → 9 月 E4/E1 → 10 月写作 → 1 月投，日历可行。
- 成功概率 ~0.45-0.55：三缺口全关闭概率约 0.34，但关闭 2/3 + 一缺口诚实定位已是可接受形态。
- 失败模式：E4 工程失败（"禁止事后加 parser"不可操纵结果；onboarding 14 组中 12 组在失败 case，恢复难）→ 降 A 线 N3 定位 + E1 subset，保 weak accept 底。

### 方案 C：均衡路线（推荐执行框架）
- 组合：档 1（E2、T2 前置核实、T1 轨迹、W1-W4、D1 分流预案）→ 档 2（v17 落地 + V0-V3 全量）→ 档 3 按结果分流（正→B；零/负→A + E1 subset）→ 档 4（Artifact P0-P2 + 数字一致性 + claim map）。
- 逻辑链：低成本项先把基础拉到 strong borderline，用 V0-V3 唯一分叉点决定投入方向。增量判断：**E2 提为"必须"**——同时打 MC5 与"contract 是序列化"质疑，CPU 近零，是唯一无论正负都加分的实验。
- 成功概率 ~0.35-0.45（含 V0-V3 正概率加权）。失败模式：V0-V3 运行事故（finalizer/hash 漂移）延误 2-4 周，缓冲内可恢复。

三方案关系：先 C、再按 V0-V3 定 A/B；B 是目标形态、A 是保底、C 是执行框架。

## 4. 关键不确定性的决策树（根=V0-V3）

- **正（V3 显著优于 V0/V1/V2；H4 非拒绝驱动；H5 ≥3 suite/strata）**→ 走 B。叙事 N2；追加 E1 全量 + E4；写作=Results 新增 Representation Attribution 节，E78 降为全系统对照；目标审稿人=实证/系统双面。唯一可直接瞄准 accept 的分支。
- **零/负（V3≈V2 或无优势）**→ 走 A。**诚实判断：此分支下 accept 不现实（≤0.15-0.2）**，现实目标=weak accept + 转投。叙事 N1+N3（ρ_E/ρ_A 正交）；追加 E1 subset + E4（此分支唯一可能翻盘的杠杆）；写作重点="Where the bottleneck is"；目标审稿人=理论型。
- **混合（V3>V2≈V1，或 H2/H3 非劣失败）**→ 最贵分支。叙事 N2 细分（V3 vs V1 归因有效；V2→V3 refinement 增益小 → 收缩为"已验证字段 + 字段级检查"）+ N3 局部；追加 E2 判断混合是否因 power-set family 过强（粗族下哪些字段冗余）；写作=granularity 层次细表；目标审稿人=方法论敏感型。

## 5. 必须避免的 reject 触发器

| # | 触发器 | 当前状态 | 剩余风险 | 预防 |
|---|---|---|---|---|
| R1 | overclaim：726 结果直挂 O1-O5 定理 | 已规避（abstract 边界句） | v17 数字落地改写时复发 | B 线顺序（Evaluation→Results→Abstract）+ claim map 同步 |
| R2 | 归因实验缺失却被宣称贡献 | 部分规避（321-case 已标注子集） | 审稿人追问全量贡献（模拟 Q2） | V0-V3 全量必跑（白皮书 #1） |
| R3 | 不可复现：artifact 泄漏/无 URL | 未规避（P0-P2 进行中） | 40+ 硬编码路径、.git 身份、19 个内部 md | C 线 P0 参数化 + 排除清单 + 匿名 URL 插正文 |
| R4 | baseline 不公平 | 部分规避（common-input 标注） | 12 long-context 处置不一致 + denominator 差异 | E5 统一处置 + all-key bounds 相邻呈现 |
| R5 | 效用处理不当→系统审稿人全拒 | 部分规避（pathway audit + frontier 定位） | 33/97 仍是最大触发面 | E4 正面进攻；E4 负则 N3 定位 + 26-task 归一化叙事 |
| R6 | 单模型被当外推 | 已规避（不声称跨模型） | 减分非否决 | E1 至少 subset |
| R7 | 合规事故：Round 1-5 复活/版本不一致 | 已规避（禁令 + W4 说明） | 低 | 维持禁令 + granularity v1.1.2/v1.2.1 说明 |
| R8 | V0-V3 预注册崩塌（中途改阈值/修 bug 不全量重跑） | 已规避（协议 fail-fast） | 中 | 协议 §11 门禁 + 修复后四条件全量重跑 |

## 6. 最终推荐

**推荐战略：C 框架 + B 目标 + A 保底。** 执行顺序：(1) 立即（v17 运行中）：E2、T2 前置核实、T1 轨迹、W1-W4、D1 预案；(2) v17 落地：finalizer/冻结/smoke → V0-V3 全量（阻塞、不可跳过）；(3) 分叉：正→E1 全量 + E4 + N2；零/负→N1/N3 + E1 subset；混合→N2 细分 + E2；(4) 投稿前 6 周：Artifact P0-P2 + 数字一致性 + claim map。

白皮书项调整：**升级** E2（→必须）、T2（→必须）、E1（→至少 subset 必须）；**降级** E3 adaptive（维持可选，固定重放措辞已兼容）、E84 人类评审（可选不阻塞）；E5/E6 按原计划。

**如果只能做 3 件事**（按对 accept 概率的边际贡献）：
1. **V0-V3 4×726 预注册归因全量**（70-110 GPU h）：唯一把"granularity 是安全来源"升为全量证据的实验，决定叙事分叉，是 R2 硬防御。
2. **E4 authority/resolver 覆盖 pilot**（10-20 GPU h + 3-6 周人日）：直接进攻 G1——最大 reject 触发面；恢复 5 个任务即可把"保守拒绝"从主导解释降为并存解释。
3. **E1 第二模型**（25-35 GPU h，至少 160-subset）：关闭 G2，与 V0-V3 共用协议/manifest，边际成本最低、确定性最高。
（若 E4 工程不可行被砍 → 预算转 E1 全量 + E3 adaptive；若 V0-V3 为负 → 第 2/3 项降为 subset，预算转 T1-T3 理论加固。）
