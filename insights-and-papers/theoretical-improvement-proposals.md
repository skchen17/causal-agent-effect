# CAR 理论深度改进方案

## 基于《三条脉络_LLM因果推理技术史诗》的交叉分析

---

## 诊断：CAR 在因果之梯上的真实位置

对照 Pearl 的因果之梯重新审视 CAR：

```
第三层：反事实 (Counterfactuals)
  "如果当初没用这个工具会怎样？"
  CAR: ❌ 完全没有

第二层：干预 (Intervention)
  "调用这个工具会产生什么效果？"
  CAR: ⚠️ 宣称是 P(s'|do(a),s)，实际是 P(s'|observe a, s)
      没有区分干预和观测，没有后门调整

第一层：关联 (Association)
  "历史上有多少人调用这个工具后看到这个效果？"
  CAR: ✅ 做到了，就是 Laplace 平滑的频率表
```

**核心问题**: CAR 的 CausalMemory 名字里有 "Causal"，但实际停留在关联层。SafetyDrift/ProbGuard 也停留在这一层——它们会用马尔可夫链来更优雅地计算关联，但同样是 P(s'|observe a, s) 而非 P(s'|do(a), s)。

这意味着：如果在 CAR 的状态中存在**混杂因子**——例如 `safe_mode=true` 同时影响"用户选择调用哪些工具"和"工具调用的结果"——那么 CAR 学到的关联 ≠ 因果效应。

---

## 改进方案

### 方案 A（低风险，立即可做）：LLM 先验贝叶斯更新

**来源**: 脉络一 §1.2–1.3 | Long et al. [2307.02390], Darvariu et al. [2405.13551]

**核心思想**: 将 LLM 的语义知识作为因果转移的贝叶斯先验，替代当前粗糙的 bootstrap 启发式。

**当前 CAR**:
```python
# bootstrap_check: 硬编码的固有风险查找表
inherent = {"terminal": (["command_executed", ...], EffectRisk.HIGH), ...}

# CausalMemory.predict: 纯粹的频率统计
confidence = support / (support + failures + 1)  # Laplace 平滑
```

**改进方案**:
```python
def predict_with_llm_prior(self, tool_name, state, llm_prior):
    """贝叶斯更新：LLM 先验 + 观测数据 → 后验"""
    # 先验: P(effect | tool, state) ~ Beta(α_llm, β_llm)
    # α_llm, β_llm 由 LLM 对"该工具在此状态下是否会产生该效果"的置信度决定
    # 观测: support 次成功, failures 次失败
    # 后验: Beta(α_llm + support, β_llm + failures)
    alpha_posterior = llm_prior.alpha + support
    beta_posterior = llm_prior.beta + failures
    confidence = alpha_posterior / (alpha_posterior + beta_posterior)
    return confidence, alpha_posterior, beta_posterior
```

**为什么更好**:
- Laplace 平滑 (`+1`) 假设效果发生和不发生的先验概率相等——这是一个非常弱的、无信息的先验
- LLM 先验可以利用模型对工具语义的理解：它知道 `terminal` + `rm -rf` 可能导致 `file_deleted`，即使从未观察过
- 当数据稀疏时，LLM 先验主导；当数据充足时，观测主导——与 Darvariu et al. 的贝叶斯框架一致

**实现难度**: 低。只需在 `CausalMemory.predict()` 中增加一个可选的 `prior: dict[str, BetaParams]` 参数。

**竞争价值**: 中。这是 SafetyDrift/ProbGuard 没有的东西——它们不用 LLM 做先验。

---

### 方案 B（中风险，核心差异化）：do-calculus 干预层

**来源**: 脉络三 §3.3 | Han et al. [2408.06849], 脉络一 §0.1 (后门调整)

**核心思想**: 让 CAR 真正区分 P(s'|observe a, s) 和 P(s'|do(a), s)。这是从关联层到干预层的实质性跨越。

**当前 CAR 的根本问题**:

CAR 的 CausalMemory 观察到的是：
```
用户选择了调用 terminal → command_executed
```

但这混淆了两种情况：
1. 用户在危险状态下倾向于调用 terminal → 调用后状态继续危险（观测到的关联）
2. 调用 terminal 本身导致了状态变危险（因果效应）

同理：当 `safe_mode=true` 时，用户可能选择更谨慎的工具，且工具执行结果也更好——`safe_mode` 是一个混杂因子。CAR 当前无法分离 `safe_mode` 的效应和工具本身的效应。

**改进方案**:

```python
class CausalMemoryV2:
    """支持 do-calculus 的因果记忆"""

    def _backdoor_adjustment(self, tool_name, state, confounder_keys):
        """后门调整公式：P(effect | do(tool)) = Σ_z P(effect | tool, z) × P(z)

        confounder_keys: 需要控制的混杂因子列表，如 ["safe_mode", "production"]
        """
        with self._connect() as con:
            # Step 1: 获取所有 confounder 的取值组合及 P(z)
            con.execute("SELECT DISTINCT state_pattern FROM car_transitions")
            all_patterns = [json.loads(r["state_pattern"]) for r in con.fetchall()]

            # Step 2: 对每个 confounder 组合 z
            adjusted_prob = 0.0
            for pattern_z in all_patterns:
                # P(effect | tool, state, z)
                p_effect_given_tool_z = self._query_conditional(
                    tool_name, state, pattern_z
                )
                # P(z) — confounder 的边际分布
                p_z = self._estimate_marginal(confounder_keys, pattern_z)
                adjusted_prob += p_effect_given_tool_z * p_z

            return adjusted_prob

    def predict_do(self, tool_name, state, confounders=None):
        """返回 P(effect | do(tool)) 而非 P(effect | observe tool)"""
        if confounders is None:
            confounders = self._infer_confounders(tool_name, state)

        adjusted_effects = {}
        for effect in self._known_effects:
            prob = self._backdoor_adjustment(tool_name, state, confounders)
            adjusted_effects[effect] = prob

        return adjusted_effects

    def _infer_confounders(self, tool_name, state):
        """利用 LLM 推理可能的混杂因子"""
        # 脉络二的核心教训：LLM 的因果推理需要结构化引导
        # 不让 LLM 端到端推理，只让它回答"哪些变量同时影响工具选择和结果"
        prompt = f"""
        Given a tool call '{tool_name}' in state {state},
        which state variables might affect BOTH:
        (a) whether a user chooses to call this tool, AND
        (b) the outcome of the tool call?

        Only list variable names. These are potential confounders.
        """
        # LLM 回答 → 后门调整的 confounder 集合
```

**为什么这是质的飞跃**:

当前整个竞争文献（SafetyDrift, ProbGuard, GuardAgent）都在计算 P(effect | observe action)，没有一个在做 P(effect | do(action))。如果 CAR 实现了后门调整，它就**在所有竞争工作中第一个进入 Pearl 因果之梯的第二层**。

后门调整公式：
$$P(Y|do(X=x)) = \sum_z P(Y|X=x, Z=z) \cdot P(Z=z)$$

在当前 CAR 的语境中：
- $X$ = 工具调用
- $Y$ = 效果（如 `command_executed`）
- $Z$ = 混杂因子（如 `safe_mode`, `production`, `interactive`）

**实现难度**: 中-高。需要：(a) 在 CausalMemory 中存储足够的边际分布信息，(b) 一个 LLM 调用来推断 confounders，(c) 重构 predict() 接口。

**竞争价值**: 极高。当前没有竞争对手做到了这一点。这可以直接从"关联层的竞争"中跳出来。

---

### 方案 C（高风险，长期目标）：反事实审计

**来源**: 脉络二 §2.5 | Executable Counterfactuals [2510.01539], 脉络一 §0.1 (Pearl 第三层)

**核心思想**: 将 ProofObject 从"预测-实际对比"升级为"反事实对比"。

**当前 CAR**:
```
ProofObject: 预测效果 vs 实际效果 → 记录差异
```

**改进方案**:
```python
class CounterfactualProof(ProofObject):
    """包含反事实推理的审计证明"""

    # 在工具执行前，LLM 推理两个世界：
    # World A (实际): 调用工具，预测效果 E_a
    # World B (反事实): 不调用工具，预测效果 E_b

    counterfactual_world: dict[str, Any]  # "如果不调用会怎样"
    causal_effect_estimate: float         # E_a - E_b 的估计差异
    confounders_controlled: list[str]     # 控制了哪些混杂因子

    def generate_counterfactual(self, tool_name, state, llm):
        """生成反事实预测"""
        # 利用 Executable Counterfactuals 的洞察：
        # 让 LLM 写代码来模拟反事实，而非纯文本推理
        code = llm.generate_code(f"""
        # 模拟以下场景的反事实：
        # 场景 A：调用 {tool_name}，当前状态 {state}
        # 场景 B：不调用 {tool_name}，其他条件不变
        # 输出：两个场景下各状态变量的预期变化
        """)
        result_a, result_b = execute(code)
        return result_a, result_b
```

**为什么这很强**:
- EPO-Safe 的反事实是自然语言规范（模糊）
- CAR 的反事实通过代码执行验证（精确，可复现）
- 这直接进入 Pearl 因果之梯的第三层

**实现难度**: 高。需要代码执行沙箱和大量工程工作。

**竞争价值**: 如果实现，将是所有 agent 安全系统中第一个具备反事实推理能力的。但投入产出比需要权衡——可能作为长期方向更合适。

---

### 方案 D（低风险，快赢）：因果置信度校准

**来源**: 脉络二 §2.1–2.2 | Causal Parrots [2308.13067], CLadder [2312.04350]

**核心思想**: CAR 当前的 confidence 公式过于简单（Laplace 平滑），没有考虑状态空间中观测分布的不均匀性。

**改进方案**: 在 CAR 的 confidence 输出上增加两层校准：

```python
def calibrated_confidence(self, tool_name, state):
    """多维度置信度校准"""
    raw_confidence = self.predict(tool_name, state).confidence

    # 维度 1: 状态相似度加权
    # CLadder 的教训：LLM 在训练分布相似的任务上表现更好
    # 同理，CAR 在与已观测状态更相似的状态上预测更可靠
    state_similarity = self._compute_state_similarity(state, self._observed_states)

    # 维度 2: 观测充分性
    # 不是简单看 support_count，而是看 support_count 相对于
    # 状态空间的复杂度是否足够
    observation_sufficiency = min(
        1.0,
        self._total_observations / (self._state_space_cardinality * 10)
    )

    # 校准后的置信度
    calibrated = raw_confidence * state_similarity * observation_sufficiency
    return calibrated
```

**为什么更好**:
- 当前 confidence 只看单个 (tool, pattern) 有多少观测——忽略了该 pattern 与当前状态的**相似度**（如果当前状态不在任何已知 pattern 中，confidence 应该打折）
- 当前 support_count 不告诉你"还需要多少观测才够"——观测充分性指标回答了这个问题
- SafetyDrift 有收敛性证明，CAR 至少要有数据充分性的基本检验

**实现难度**: 低。主要是计算逻辑的增强。

---

## 综合推荐路径

```
阶段 1 (即刻): 方案 D + 方案 A
  → 贝叶斯先验替换 bootstrap + 置信度校准
  → 产出：预测质量明显提升，冷启动更合理
  → 论文贡献：Provenance-first safety with LLM-informed priors

阶段 2 (核心差异化): 方案 B
  → 实现后门调整，真正进入干预层
  → 产出：第一个在 agent 安全中实现 do-calculus 的系统
  → 论文贡献：From observation to intervention — do-calculus for agent tool safety

阶段 3 (长期): 方案 C
  → 反事实审计 → Pearl 第三层
  → 视阶段 2 的结果和反馈决定是否投入
```

---

## 与竞争文献的理论深度对比（改进后）

| 维度 | SafetyDrift | ProbGuard | GuardAgent | CAR 当前 | CAR 阶段1 | CAR 阶段2 |
|------|:----------:|:---------:|:----------:|:-------:|:--------:|:--------:|
| Pearl 层级 | 1 (关联) | 1 (关联) | 1 (关联) | 1 (关联) | 1 (关联) | **2 (干预)** |
| 数学保证 | 吸收态收敛 | PAC 边界 | 无 | 无 | 贝叶斯收敛(弱) | do-calculus |
| LLM 使用 | 无 | 无 | 推理引擎 | 无 | **先验来源** | **先验+混杂识别** |
| 审计 | 无 | 无 | 无 | 三层对比 | 三层对比 | **反事实对比** |
| 部署 | 离线分析 | 插件 | 代理 | Hook | Hook | Hook |
