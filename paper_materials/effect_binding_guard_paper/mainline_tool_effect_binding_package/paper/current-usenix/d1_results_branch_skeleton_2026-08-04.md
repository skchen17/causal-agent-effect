# D1 分流预案：三分支 Results 结构骨架（N1 基座 + N2/N3 占位）

日期：2026-08-04
产出：research-assistant。依据决策书 `window_execution_decision_2026-08-04.md` §2d、
协议 `strict_atom_representation_attribution_protocol_2026-08-03.md` §2.3 解释矩阵、
accept_path_analysis_2026-08-03.md §4 决策树。

**纪律（R1 overclaim 触发器防御）**：本文档只写结构与主题句，**不预填任何数字**；
所有数字位置以 `[PENDING-FINALIZE]` 占位；分支选择只发生在 finalize 当天按
H1-H5 判定释放（协议 §2.2/§2.3）；数字回填按 B 线顺序 Evaluation→Results→Abstract
（决策书 §2e），claim map 分支 diff 模板另行维护，本骨架不预更新 claim map。

## 0. 分支切换条件（H1-H5 判定 → 分支选择）

判定输入（协议 §2.1）：H1 安全（配对 ASR，629 attack cases，Holm-McNemar）、
H2 良性效用非劣（界 -0.05）、H3 攻击效用非劣（界 -0.05）、H4 非拒绝驱动、
H5 跨族一致性（≥3 suite 且 ≥3 静态攻击 strata，不得全来自单一 injection goal）。

| 判定组合（对应协议 §2.3 矩阵行） | 分支 | 叙事 |
|---|---|---|
| H1∧H2∧H3∧H4∧H5 全过（§2.3 行 3：ASR 更低且效用非劣） | **N2 全量** | atom 表示同时改善安全粒度与效用；新增 Representation Attribution 节，E78 降为全系统对照 |
| H1 过但仅优于 V0、不优于 V2（§2.3 行 1：字段级检查有用，atom 特异性无增益） | **N2 细分 + N3 局部**（混合分支） | 收缩为"已验证字段 + 字段级检查"；granularity 层次细表 |
| H1 过但 H2 或 H3 非劣失败（§2.3 行 4：收益可能来自保守拒绝） | **N2 细分 + N3 局部** | 不得作更优 trade-off 主张；拒绝率/coverage 与 ASR 并列呈现 |
| H1 过但 H5 失败（§2.3 行 5：差异集中单一 suite/goal） | **N1 + 机制 witness 段**（不作普遍主张） | 321-subset 既有边界语升级为唯一归因证据形态 |
| H1 失败或 V3≈V2（§2.3 行 6：无显著或无一致收益） | **N3 全量** | 保留负面结果；"Where the bottleneck is"；论文收缩为表示碰撞、反事实验证与条件性 mediation |
| ASR 相同但效用更高（§2.3 行 2） | **N2 变体** | refinement 主要减少无关字段检查与过拒；支持 utility 贡献而非安全贡献 |

混合分支（accept_path §4）附加动作：用 E2 结果判断混合是否源于 power-set 族过强
（粗族下哪些 qualifier 冗余），写作粒度层次细表。

## 1. N1 基座（无论 V0-V3 正负都成立）

N1 = 现有 results.tex 七小节 + 两个新增小节（E2、override/O6 披露位）。
所有主题句只依赖已冻结/已完成证据，不含任何 V0-V3 结果。

### R.1 Compound Effects Occur in Official Benign Traces（\subsection）

- 段 1 主题句：官方 benign 轨迹中存在复合、跨子系统、多主体效果，
  这是基准内的发生性 witness。
  预期引用：`tables/table_agentdojo_effect_prevalence.tex`。
- 段 2 主题句（边界）：该表证明基准内发生，不证明真实策略需求、
  未见工具覆盖或生态普遍性。

### R.2 Existing Monitors Bind Only Partially（\subsection）

- 段 1 主题句：现有监视器并非单纯工具名分类器，但没有一个同时绑定
  effect/authorization/resource 三轴。
- 段 2 主题句：聚合 UPA 掩盖粒度失效；轴敏感度与行错误率必须分开读。
  预期引用：`tables/table_binding_problem_characterization.tex`（Panel a/b）。

### R.3 Authorization Collisions（\subsection）

- 段 1 主题句：表示不足定理（Thm representation-insufficiency）直接作用于
  受控工件——工具名/仅效果单元强制行错误下界。
- 段 2 主题句：有限域正向结果——typed contract 在声明的 submultiset 权威族下
  无碰撞，但仅对有限域成立。
  预期引用：`tables/table_representation_collisions.tex`（Panel a/b）。

### R.4 Source-Grounded Contract Interventions（\subsection）

- 段 1 主题句：共同字段投影在 80 个干预上未达关系一致——负面结果改变了表示。
- 段 2 主题句：typed qualifier 是失败后的设计修正，其价值在于反事实门拒绝了
  更窄表示而非静默冻结它；不作独立可靠性估计。
  预期引用：无表（正文叙述）；claim map 对应行。

### R.5 Pre-Registered Held-Out Contract Check（\subsection）

- 段 1 主题句：冻结表示在独立公开工具实现上预注册复验，排除窄义事后修补解释。
- 段 2 主题句：与 PACT-L2 风格 argument-role 视图的直接比较隔离出
  state-dependent 粒度区分；不是对 PACT 的评估。
  预期引用：`tables/table_toolsandbox_heldout.tex`。

### R.6 Common-Checkpoint AgentDojo Comparison（\subsection，N1 核心）

- 段 1 主题句：同一 Qwen3-32B checkpoint、726-key 下，\sys{} 相对无防御的
  攻击成功变化及配对统计；不可评估行保留、不折算。
  预期引用：`tables/table_e78_qwen32_baselines.tex`。
- 段 2 主题句：安全收益有代价——benign/attack 效用变化；其他防御构成
  竞争性 trade-off 前沿，而非 Pareto 支配；adapter 行是 common-input 本地实现。
- 段 3 主题句：确定性 pathway audit 把 benign 损失归因于 plan/evidence/recovery
  接口而非效果分解的固有成本；独立随机运行排除因果归因（既有边界句保留）。
- 段 4 主题句（frontier 定位，W 线）：本结果定位为当前前沿上的一个点，
  不声称效用问题已解决（防 reviewer_perspective §4 攻击点 4 措辞）。

### R.7 Granularity Attribution and Saved-Attack Transfer（\subsection）

- 段 1 主题句：321-case 闭环归因是**适用性子集上的机制 witness**；
  选择机制（field-level feedback）在本段第一句先于任何结果陈述
  （与防御性写作草稿 C.1 一致，防攻击点 3）。
  预期引用：`tables/table_granularity_and_transfer.tex` Panel (a)。
- 段 2 主题句：303 个固定公开注入工件的保存-转移实验加强多步转移证据，
  同时重复效用代价；不声称对自适应生成的鲁棒性。Panel (b)。
- 段 3（\paragraph Bounded adaptive sensitivity）：40 hash-locked keys 的
  有界搜索，小样本不显著，细节入附录。

### R.8 Policy-Family Sensitivity（E2，新增小节，两分支共用）

- 段 1 主题句：四个权威族（power-set 基线、effect-kind 商、resource 商、
  {0,1,≥2} 计数截断）在指标计算**之前**由枚举原则固定；族集非按冗余率挑选
  （表注声明，见防御性写作草稿 C.2）。
- 段 2 主题句：5 qualifier × 4 family × 2 域全网格，保留分离对/冗余对/
  overpartition/假拒绝**两个方向**同时报告；verdict 按 domain-qualifier-family
  单元给出。
- 段 3 主题句（claim boundary，双向预注册）：按观测方向选用模板
  （低冗余→qualifier 跨族仍必要；高冗余→表示是 policy-relative 的正面证据；
  混合→逐单元限定）；不外推到未枚举调用、开放工具域或声明外族谱系。
  预期引用：新增表 `table_policy_family_sensitivity.tex`（数据源：
  `experiments/security-analysis-ablation-and-overhead/results/policy-family-sensitivity/`）。

### R.9 Authority, Mechanism, and Cost Diagnostics（\subsection，附录表）

- 段 1 主题句：reviewed authority、机制消融与开销诊断作为次级证据；
  适用性受限处如实标注。
  预期引用：附录 Tables e84/e83 等（`tab:e84-reviewed-authority`—`tab:e83-kernel-overhead`）。
- 段 2 主题句（O6 披露位，若 T2 在投稿前定稿）：override 构成测量
  （结构化/fallback 占比、五类扩权发现排除性检查、证据隔离回写条件）以
  obligation-to-evidence mapping 形式披露；具体数字只允许来自 finalize 后复测。

**N1 不变式清单**（两分支都必须保持）：
1. 每小节末尾保留边界句（不泛化、不外推）；
2. 321-subset 永远标注"applicability subset, selection requires field-level feedback"；
3. E78 效用代价段不得删除或弱化（R5 触发器防御）；
4. 所有不可评估/失败行保留（协议 §5 error policy）；
5. abstract/intro 数字只在 Phase D 按 Results 回填，不提前。

## 2. N2 占位（V0-V3 正结果分支：Representation Attribution 整节）

插入位置：R.6（E78）之前，使 E78 降为全系统对照（accept_path §4 正分支）。
本节**全部数字占位**；进入条件 = §0 表中 N2 判定成立。

### R.A.0 Consistency preamble（\paragraph，防攻击点 3，先于结果）

- 主题句：本节的选择机制与 strata 分解方向在任何 V0-V3 数字之前陈述——
  321-subset 按既有 atom monitor 的 field-level feedback 选择（机制 witness），
  本节将其替换为预冻结全量 726-key 配对设计（协议 §3.1），因此子集选择逻辑
  不依赖本节结果；strata 分解维度（suite、attack_type、injection_task_id）
  在协议 §2.1 H5 预注册，方向固定。
  （正文稿见防御性写作草稿 C.1。）

### R.A.1 主配对表（\subsection Representation Attribution）

- 主题句：四条件 V0-V3 在同一 726-key、同一冻结 plan cache、同一 scorer 下
  配对比较；主结论来自官方 case-level 指标与配对统计。
- 表占位 `[T-V0V3-main]`：行 = 4 variants；列 = ASR、benign utility、
  attack utility、discordant counts、Holm-adjusted p、bootstrap 95% CI
  （协议 §6 schema + §7.1 定义）。数字一律 `[PENDING-FINALIZE]`。

### R.A.2 Suite/strata 分解（\paragraph）

- 主题句：安全差异的跨 suite 与静态攻击 strata 分布（H5 判定证据）；
  若集中于单一 injection goal，本段必须显式说明并触发 §0 行 4 的降级。
- 表占位 `[T-V0V3-strata]`。

### R.A.3 非拒绝驱动分解（\paragraph，H4）

- 主题句：ASR 差异分解为字段检查阻止 / 工具未注册阻止 / authority-evidence
  abstain / 模型未尝试攻击目标四类（协议 §7.2 强制分解）；同时报告
  DENY/ABSTAIN、monitor applicability、override rate、strict execution ratio。
- 表占位 `[T-V0V3-decomposition]`。

### R.A.4 Stability repeats（\paragraph）

- 主题句：160-case subset 的 repeat 1/2 给出 per-case flip rate 与方向一致性；
  stability 不替代全量主结果（协议 §Phase 4）。
- 表占位 `[T-stability]`。

### R.A.5 Reviewed-authority 次级分析（\paragraph，Phase 5）

- 主题句：26 条 runtime-ready trusted manifests 上的 authority 独立性次级分析；
  REJECT projection 不静默转可用；报告 common-support subset。
- 表占位 `[T-reviewed-authority-secondary]`。

### R.A.6 Claim boundary（\paragraph）

- 主题句：结论限定为"给定同一 plan-derived authority，表示层的增量作用"
  （协议 §3.3 末句）；不证明 planner 独立或完备；不外推未配对设置。

## 3. N3 占位（零/负结果分支："Where the bottleneck is"）

进入条件 = §0 表中 N3 判定（H1 失败 / V3≈V2 / 无一致收益）。
叙事主轴（accept_path §4 零/负分支）：ρ_E（表示轴）与 ρ_A（授权轴）正交；
给出"区分工具而非系统"的收口。保留负面结果本身作为贡献（协议 §2.3 行 6）。

### R.N.1 零结果陈述与预注册遵守（\subsection Where the Bottleneck Is）

- 主题句：预注册四条件比较未按 H1 方向产生显著差异；我们保留该结果，
  不做事后子集搜索（协议 §2.2 禁止条款的执行证据）。
- 段 2 主题句：报告全部配对统计与 discordant counts，包括不显著的方向。

### R.N.2 瓶颈定位（\paragraph）

- 主题句：沿 V0→V1→V2→V3 的相邻差异定位差异出现/消失的层级——
  工具身份 vs 整调用 vs schema 字段 vs 反事实验证字段；
  即使 V3 不优于 V2，V0/V1 的失败仍刻画表示不足的下界位置。
- 表占位 `[T-bottleneck-ladder]`（相邻条件差异与 CI）。

### R.N.3 表示轴与授权轴的正交性（\paragraph）

- 主题句：表示碰撞结果（R.3/R.5）与授权侧证据（E84、26-task reviewed
  authority）分别成立；负结果说明的是"反事实验证后的 atom 表示未在
  端到端 ASR 上兑现其粒度优势"，而非表示碰撞不存在。

### R.N.4 仍然成立的结果（\paragraph）

- 主题句：有限域定理实例化、held-out 预注册复验、E2 族敏感性、
  O1-O5/O6 义务框架与审计纪律不受 V0-V3 负结果影响；
  论文贡献重述为"表示碰撞的可执行刻画 + 条件性 mediation 方法论"。

### R.N.5 定位收口（\paragraph）

- 主题句：本工作给出区分表示瓶颈的诊断工具与预注册证据，而非端到端
  防御优势主张；对实践的含义是字段级检查的必要性边界（引用 §2.3 行 1/2
  的允许结论措辞）。

## 4. 执行规则（防 R1/R2/R8）

1. 分支选择只在 finalize 当天、按协议 §11 门禁通过后依据 H1-H5 做出；
   在此之前两占位分支均不得预写数字、不得更新 claim map（决策书 §2f 第 1 条）。
2. 数字回填顺序：Evaluation protocol → Results 表 → failure analysis →
   Abstract/Introduction → claim-to-source map → reproduction outputs
   （协议 §13 末段）。
3. 若 finalize 复测发现 override 违例计数 > 0（见 override 构成测量文档 §4.4），
   R.9 段 2 的 O6 披露按处置结论改写；在处置前该段只允许写"测量已预注册"
   级别的中性表述。
4. N2/N3 互斥但可局部叠加（混合分支）：叠加规则以 §0 表为唯一依据。
5. 本文档与 main.tex/sections/ 零耦合：入稿时由写作负责人按 B 线顺序移植，
   移植即触发 claim map diff 审查。
