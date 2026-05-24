# 因果推理在 Agent 安全系统中的可行性分析

## 现状、前景、可实现路径与技术挑战

---

## 一、因果推理在 Agent 安全中的现状

### 1.1 行业全景：三条路线正在并行推进

```
路线 A: 统计转移学习 (关联层)
  SafetyDrift, ProbGuard, CAR 当前
  → 从执行轨迹中学习 P(s' | observe a, s)

路线 B: LLM+因果工具链 (干预层)
  ORCA, Causal-CoT, CausalPulse
  → LLM 做语义理解，因果库(DoWhy/PyAgrum)做 do-calculus

路线 C: 在线因果发现+决策 (干预→反事实层)
  MARLIN, Meta-D²AG, Modular Bayesian Framework
  → 增量式学习因果图结构 + 序贯决策
```

**CAR 当前在路线 A，但命名暗示了路线 C 的野心。** 路线 B 是目前工业落地最成熟的——CausalPulse 已在 Bosch 工厂运行，50-60 秒端到端诊断工作流，98.7% 成功率。

### 1.2 关键判断：路线 A 的竞争窗口正在关闭

2025-2026 年发表的关联层方法已经相当饱和：
- SafetyDrift 的把数学推到了吸收态收敛性证明
- ProbGuard 把保证推到了 PAC 边界
- 更多的统计方法不太可能在这个层面做出突破

**在关联层继续竞争的边际回报递减。** 真正有机会的方向是进入干预层——但这个跳跃的难度被广泛低估了。

---

## 二、可实现路径分析

### 2.1 路径一：贝叶斯先验融合（可行，3-4 周）

**技术原理**: 用 LLM 的语义知识为因果转移提供先验分布，取代当前粗糙的 bootstrap 启发式。

**具体实现**:

```python
# 当前 CAR:
confidence = support / (support + failures + 1)
# 问题：所有 (tool, state) 共享同一个无信息先验 Beta(1,1)

# 改进:
# Step 1: LLM 生成初始先验
prior_effect = llm.estimate_prior_probability(
    tool_name="terminal",
    state={"safe_mode": True, "file_count": "6-20"},
    effect="command_executed"
)
# → 输出 "terminal 在 safe_mode 下产生 command_executed 的可能性是 90%"
# → 映射为 Beta(α=9, β=1)

# Step 2: 贝叶斯更新
alpha_post = prior_alpha + support_count
beta_post = prior_beta + failure_count
confidence = alpha_post / (alpha_post + beta_post)
```

**为什么可行**:
- 脉络一已经证明：LLM 对因果方向的判断即使有约 30% 错误率，作为先验仍然系统性地提升了因果发现的 F1
- 贝叶斯更新天然满足"数据少时先验主导，数据多时观测主导"——这正是冷启动到热运行需要的
- 不需要实时 LLM 调用——先验可以预计算并缓存

**技术挑战**:
1. **先验校准**: LLM 的原始概率输出没有良好校准（脉络二的核心发现）。需要温度缩放或 Platt 缩放
2. **先验存储**: 对每个 (tool, state_pattern, effect) 存储 α, β 参数——和当前的频率表规模相同
3. **迁移先验**: 当状态空间扩展时（新增一个 flag），已有先验需要迁移到新的状态模式

**评价**: 低垂的果实。3-4 周可实现，效果可量化。

---

### 2.2 路径二：混杂因子识别 + 后门调整（中等可行，8-12 周）

**技术原理**: 从观测到的工具调用数据中识别混杂因子，用后门调整公式计算因果效应的无偏估计。

**具体实现**:

```python
class CausalEstimator:
    """基于后门调整的因果效应估计器"""

    def __init__(self, memory: CausalMemory, llm_backend):
        self.memory = memory
        self.llm = llm_backend

    def estimate_causal_effect(
        self,
        tool_name: str,
        state: dict,
        outcome: str  # 如 "command_executed"
    ) -> tuple[float, float]:  # (causal_effect, standard_error)
        """估计 P(outcome | do(tool=tool_name)) 而非 P(outcome | observe tool)"""

        # Step 1: 让 LLM 识别候选混杂因子
        confounders = self._llm_identify_confounders(tool_name, state, outcome)

        # Step 2: 从 CausalMemory 中验证候选因子
        valid_confounders = self._validate_confounders(confounders, tool_name, outcome)

        # Step 3: 构建调整公式
        # P(outcome | do(tool)) = Σ_z P(outcome | tool, z) × P(z)
        adjusted_prob = self._backdoor_adjust(tool_name, state, outcome, valid_confounders)

        # Step 4: 与 naive (未调整) 对比，量化混杂偏倚
        naive_prob = self.memory.predict(tool_name, state).confidence
        bias = adjusted_prob - naive_prob

        return adjusted_prob, bias

    def _llm_identify_confounders(self, tool_name, state, outcome):
        """利用 LLM 做结构化的混杂因子推理——不是端到端因果推理"""
        prompt = f"""You are identifying potential confounders.

        Context: An AI agent is about to call the tool '{tool_name}'.
        Current state: {json.dumps(state)}
        Outcome of interest: whether '{outcome}' occurs.

        A confounder is a state variable that affects BOTH:
        (a) whether the agent chooses to call '{tool_name}' (vs. other tools), AND
        (b) whether '{outcome}' occurs after the call.

        For each state variable below, answer:
        1. Does it likely affect tool choice? (yes/no)
        2. Does it likely affect the outcome? (yes/no)
        3. If both yes, it's a confounder.

        State variables to check: {list(state.keys())}

        Return JSON array of confounder names only. No explanation needed.
        """
        # 关键：让 LLM 只做变量筛选，不做统计推断
        # 这与脉络二的教训一致——LLM 不适合端到端因果推理

    def _validate_confounders(self, candidates, tool_name, outcome):
        """用观测数据验证候选混杂因子的有效性"""
        valid = []
        for var in candidates:
            # 检验 1: var 与工具选择的关联
            association_tool = self._test_association(var, f"tool={tool_name}")
            # 检验 2: var 与结果的关联（在控制了工具后）
            association_outcome = self._test_conditional_association(
                var, outcome, condition=f"tool={tool_name}"
            )
            if association_tool and association_outcome:
                valid.append(var)
        return valid

    def _backdoor_adjust(self, tool_name, state, outcome, confounders):
        """执行后门调整的核心计算"""
        # 枚举 confounders 的所有观测取值组合
        with self.memory._connect() as con:
            # 对每个 confounder 取值 z
            # P(outcome | tool, z) — 从条件转移统计中查
            # P(z) — confounder 在全体执行中的边际分布

            rows = con.execute("""
                SELECT state_pattern, support_count, failure_count
                FROM car_transitions
                WHERE action_name = ?
            """, (tool_name,)).fetchall()

            # 分组计算
            stratum_probs = []
            stratum_weights = []
            for row in rows:
                pattern = json.loads(row["state_pattern"])
                z = {k: pattern[k] for k in confounders if k in pattern}

                if not self._matches_state(state, pattern, exclude=confounders):
                    continue

                # P(outcome | tool, z)
                support = int(row["support_count"])
                failures = int(row["failure_count"])
                p_outcome_given_tool_z = (support + 1) / (support + failures + 2)

                # P(z) — 需要从全部事件中估计
                p_z = self._estimate_p_z(z, confounders)

                stratum_probs.append(p_outcome_given_tool_z)
                stratum_weights.append(p_z)

            # 归一化权重
            total_weight = sum(stratum_weights)
            if total_weight == 0:
                return self.memory.predict(tool_name, state).confidence, 0.0

            weighted_prob = sum(
                p * w / total_weight
                for p, w in zip(stratum_probs, stratum_weights)
            )
            return weighted_prob
```

**为什么这个路径是可行的**:
1. 核心计算（按 confounder 分层再加权平均）就是一个加权和——不需要训练，不需要复杂的优化
2. `_llm_identify_confounders` 只让 LLM 回答"哪些变量同时影响 X 和 Y"——这是一个比"估计因果效应"窄得多、简单得多的问题。根据脉络二的发现，LLM 在这个窄任务上的可靠性远高于端到端因果推理
3. DoWhy、PyAgrum 等成熟库的存在意味着不需要从零实现 do-calculus 引擎——可以把复杂场景交给它们

**为什么这不是完全成熟的**:
1. CAR 的状态空间是离散化的 bucket——连续变量的信息损失会影响后门调整的精度
2. 混杂因子的边际分布 P(z) 需要从全体执行中估计——单个 agent 的执行数据可能有严重的选择偏倚
3. 当 confounders 很多时，分层会导致数据极度稀疏（各层内的样本量太小）

---

### 2.3 路径三：在线因果图发现（高难度，16-24 周）

**技术原理**: 让 CAR 随着执行数据积累，增量式地发现工具-效果之间的因果图结构，而不是依赖预定义的效果分类。

**2025-2026 年的前沿方法**:

| 方法 | 类型 | 速度 | 精度 | 处理非线性 | 在线能力 |
|------|------|------|------|-----------|---------|
| MARLIN (NEC, 2026) | 多 Agent RL | 快 | 高 | 是 | ✅ 原生 |
| Meta-D²AG (NeurIPS 2025) | 在线元学习 | 中 | 高 | 是 | ✅ 原生 |
| Modular Bayesian (2025) | 贝叶斯更新 | 很快 | 中 | 否 | ✅ 只更新受影响部分 |
| NOTEARS (2018) | 连续优化 | 慢 | 高 | 否 | ❌ 批量 |
| DoWhy-GCM (2024) | 图方法 | 中 | 高 | 是 | ❌ 批量 |

**核心洞察**: Modular Bayesian Framework 的"只更新被干预影响的部分"原则最适配 CAR——CAR 每次工具调用就是一次"干预"，大部分因果图的边不会因为一次调用而改变，所以不需要全局重估。

```python
class IncrementalCausalGraph:
    """增量因果图——借鉴 Modular Bayesian Framework"""

    def __init__(self):
        self.graph = nx.DiGraph()  # 变量间的因果图
        self.edge_posteriors = {}  # 每条边的后验 Beta 分布

    def observe_intervention(self, tool_name, before, after):
        """每次工具调用后增量更新因果图"""
        # Step 1: 识别哪些变量因这次调用改变了
        changed_vars = self._detect_changes(before, after)

        # Step 2: 只更新与 tool_name 或 changed_vars 相关的边
        # (Modular Bayesian 的核心原则)
        affected_edges = self._get_affected_edges(tool_name, changed_vars)

        # Step 3: 对每条受影响的边做贝叶斯更新
        for (cause, effect) in affected_edges:
            new_evidence = self._compute_edge_evidence(cause, effect, before, after)
            self._update_edge_posterior(cause, effect, new_evidence)

        # Step 4: 周期性剪枝——删除后验概率过低的边
        self._prune_low_probability_edges()

    def get_do_effect(self, tool_name, outcome, state):
        """使用当前因果图做 do-calculus"""
        return self._do_calculus(
            graph=self.graph,
            intervention={"tool": tool_name},
            target=outcome,
            observed=state
        )
```

**为什么这是高难度的**:
1. CAR 的状态变量只有约 15 个——因果发现在这个规模上是可行的（MCARLIN 可以处理数百个节点）
2. 但 CAR 的"变量"包括离散化 bucket 和布尔 flag——需要离散因果图方法
3. 最大的挑战不是算法而是数据量——因果发现需要足够多的干预来打破 Markov 等价类，而一个真实的 agent 用户可能不会均匀地探索所有工具

---

## 三、技术挑战全景

### 3.1 挑战等级矩阵

| 挑战 | 严重性 | 解决可能性 | 解决时间 | 对论文的影响 |
|------|--------|-----------|---------|------------|
| 混杂因子识别不完全 | 高 | 中 | 持续 | 可能改变结论方向 |
| 数据稀疏性/选择偏倚 | 高 | 低 | 无法完全解决 | 需要诚实讨论 |
| LLM 先验校准 | 中 | 中 | 3-4 周 | 可量化处理 |
| 隐变量（未观测混杂） | 高 | 低 | 长期 | 只能做敏感性分析 |
| 状态空间组合爆炸 | 中 | 中 | 持续 | 可通过特征工程缓解 |
| 因果图结构的可识别性 | 高 | 中 | 取决于数据 | 需要做不可识别性分析 |

### 3.2 挑战深度分析

#### 挑战 1: 混杂因子识别不完全

**问题**: 即使 LLM 可以识别明显的混杂因子（如 `safe_mode`），总可能存在**未识别的混杂因子**——它们同时影响工具选择和结果，但既不在状态变量中也不在 LLM 的知识中。

**影响**: 如果存在未识别的混杂因子，后门调整给出的 P(outcome | do(tool)) 仍然是有偏的。

**已知的应对方法**:
- **敏感性分析**: 假设存在一个未观测混杂因子 U，量化"U 需要多强才能推翻当前的因果结论"（E-value 框架）
- **负控制**: 如果有一个"不会受工具影响但会受混杂因子影响"的变量（负控制 outcome），可以用来检测残留混杂
- **诚实声明限制**: 在论文中明确声明"我们只能控制已识别的混杂因子"

**具体到 CAR**: 最大的未观测混杂可能是"用户的意图"——一个有恶意意图的用户会选择更危险的参数（工具选择相同但参数不同），且结果也更危险。CAR 当前没有建模工具参数级别的混杂。

#### 挑战 2: 数据稀疏性与选择偏倚

**问题**: 后门调整需要对每个 confounder 取值组合 z 估计 P(outcome | tool, z) × P(z)。但当 confounders 取值多时，每个 z 层内的观测数可能很少。

**影响**: 在小样本层中，条件概率估计的方差很大——导致调整后的因果效应估计非常不稳定。

**已知的应对方法**:
- **CAVS 算法** (Noda & Isozaki, 2025): 选择最小充分调整集（满足后门准则的最小子集）以减少分层
- **正则化**: 对每层的估计做贝叶斯收缩（向全局均值收缩）
- **倾向得分**: 不直接分层，而是估计 P(tool | z)（倾向得分）然后做逆概率加权（IPW）
- **双重鲁棒估计**: 同时建模 outcome 模型和倾向得分模型，只要有一个正确估计就是一致的

**具体到 CAR**: CAR 的执行数据是高度非随机的——用户选择调用哪些工具不是随机的，而是由任务目标驱动的。这使得 P(tool | z) 的估计本身就有偏。在论文中必须诚实讨论"观测数据的选择偏倚"问题。

#### 挑战 3: 隐变量（未观测混杂）

**问题**: 有可能同时影响工具选择和结果的变量根本没有被观测——例如"用户对 agent 的信任程度"。

**影响**: 如果存在足够强的隐变量，do-calculus 的结果仍然不能解释为因果效应。

**已知的应对方法**:
- **前门调整**: 当存在完全中介变量（工具的全部效应通过某个中介传递）时，即使混杂不可观测也能识别因果效应
- **工具变量**: 如果存在一个只影响工具选择不影响结果的变量，可以作为工具变量识别因果效应
- **MAG/PAG 建模**: 使用部分祖先图（Partial Ancestral Graph）表示含有隐变量的因果结构
- **局部学习方法** (NeurIPS 2025): 仅在 Markov Blanket 内搜索调整集，避免全局因果发现的复杂性

**具体到 CAR**: 前门调整可能更适合 CAR——如果每个工具的全部效应都通过"效果"（如 command_executed, file_written）传递，那么效果就是完全中介。这意味着可以通过前门调整公式识别因果效应，即使有未观测混杂。但前提是效果列表确实覆盖了工具的所有因果效应——这是一个强假设。

#### 挑战 4: 因果方向的可识别性

**问题**: 即使我们观察到 tool → effect 总是同时出现，也无法从纯观测数据中确定方向（tool 导致 effect 还是 effect 的预期导致 tool 被选择？）。

**影响**: 如果方向判断错误，因果效应估计将是完全错误的。

**已知的应对方法**:
- **时间先后**: 如果 tool 调用严格在 effect 出现之前，方向是确定的
- **干预**: 如果 agent 随机化某些工具调用，方向是可识别的
- **独立性检验**: 在某些假设下（如 LiNGAM 的非高斯性），方向是可判定的

**具体到 CAR**: CAR 有一个天然优势——工具调用的时间顺序是明确的。pre_tool_check 总是在工具执行之前运行。所以方向性在 CAR 中是给定的（工具调用 → 效果），不需要从数据中学习方向。这是一个重要的简化。

---

## 四、推荐的实施路线图

```
第 1 阶段 (第 1-3 周): 贝叶斯先验 + 置信度校准
  ├── 实现 LLM 先验估计器 (预计算, 缓存)
  ├── 替换 Laplace 平滑为 Beta 贝叶斯更新
  ├── 增加状态相似度 + 观测充分性的置信度校准
  └── 产出: CAR v0.3 — "LLM-informed Bayesian safety"

第 2 阶段 (第 4-8 周): 后门调整引擎
  ├── 实现 LLM 驱动的混杂因子识别
  ├── 实现分层后门调整估计器
  ├── 实现倾向得分 + 逆概率加权作为备选
  ├── 实现敏感性分析 (E-value)
  └── 产出: CAR v0.4 — "Intervention-level safety with backdoor adjustment"

第 3 阶段 (第 9-16 周): 实验验证
  ├── 构建 agent 安全基准数据集 (人工注入混杂)
  ├── 对比: CAR v0.2 (当前) vs v0.3 vs v0.4
  ├── 对比: SafetyDrift / ProbGuard 的检测性能
  ├── 收集 1000+ 条真实执行轨迹
  └── 产出: 论文实验部分

第 4 阶段 (17 周+): 在线因果发现 (可选)
  ├── 探索 Modular Bayesian 增量图更新
  ├── 探索前门调整来应对隐变量
  └── 产出: 后续论文
```

---

## 五、对论文策略的影响

### 5.1 论文现在可以宣称什么

**阶段 1 完成后**:
> "We present the first agent safety system that uses language model semantic knowledge as Bayesian priors for tool-effect transition learning, replacing traditional hand-crafted bootstrap heuristics with data-driven prior estimation."

**阶段 2 完成后**:
> "We present the first agent safety system that implements do-calculus-based causal effect estimation for runtime tool safety decisions, distinguishing between observed correlations P(effect|observe tool) and causal effects P(effect|do(tool)) via backdoor adjustment."

### 5.2 诚实声明（评审预期你会说的）

1. **"我们的因果效应估计仍然依赖于可观测的混杂因子集合"** —— 承认隐变量的存在
2. **"后门调整的精度受限于每层内的观测样本量"** —— 讨论数据稀疏性
3. **"LLM 提供的混杂因子识别可能不完整"** —— 承认 LLM 因果推理的局限（脉络二）
4. **"我们的因果图假定工具调用在时间上先于效果"** —— 明确因果方向的假设

### 5.3 相对于竞争者的真实差异化

| 竞争者 | 强项 | 弱项 | CAR 阶段 2 的位置 |
|--------|------|------|-----------------|
| SafetyDrift | 收敛性证明 | 纯预测,无干预逻辑 | CAR 有干预+决策+审计 |
| ProbGuard | PAC 保证 | 无混杂控制 | CAR 有后门调整 |
| GuardAgent | LLM 灵活性 | 无因果推理 | CAR 有 do-calculus |
| EPO-Safe | 可审计规范 | 1-bit 信号太稀疏 | CAR 有结构化转移统计 |

**核心定位**: 当前没有任何 agent 安全系统在运行时做 do-calculus。如果 CAR 做到了，它就是这个 niche 的开创者。论文可以声称："我们在 agent 安全和因果推断的交叉点上建立了第一个桥头堡。"

---

## 六、如果只做一件事

如果资源只够做一个改进，**做贝叶斯先验**（路径一）而不是后门调整（路径二）。

理由：
1. 贝叶斯先验直接解决了 CAR 当前最疼的问题（冷启动依赖硬编码 bootstrap）
2. 3 周的投入产出比远高于 8-12 周的后门调整
3. 贝叶斯先验有一个干净的学术叙事——"LLM as imperfect expert"（Long et al., 2023）的 agent 安全版本
4. 后门调整需要更复杂的实验来验证其相对于 naive 频率统计的优势——这个实验本身就很难设计
5. 如果贝叶斯先验的效果已经很显著，论文已经有足够的贡献

后门调整更适合作为后续论文的核心贡献——当 CAR 已经积累了大量执行数据，数据稀疏性问题得到缓解后，后门调整的效果才会真正体现。
