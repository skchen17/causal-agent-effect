# CAR Policy Engine — 核心主线提炼

## 定位

CAR (Causal Agent Runtime) Policy Engine 是一个**基于因果效应预测的智能体安全引擎**。
它替换了传统"工具 X 是危险的"静态黑名单模式，转而使用从执行历史中**学到的因果转移统计**来做出安全决策。

## 动机：为什么要颠覆静态规则？

传统 agent 安全方案（包括 Hermes 自身的 approval 系统）的核心假设是：
> 某个工具本身就是危险的（如 terminal、send_message），因此无论上下文如何，都需要拦截。

这个假设存在根本性问题：
- 同一个 `terminal` 调用 `echo hello` 和 `rm -rf /` 风险完全不同
- 同一个 `write_file` 在只有 3 个文件的工作区和有 5000 个文件的工作区意义不同
- 静态规则无法随经验改进——被拦截 100 次也不会变聪明

## 核心创新：从"工具是什么"转向"这个动作会产生什么效果"

```
传统范式:  Decision = f(tool_name, static_danger_list)
CAR 范式:  Decision = f(predicted_effects, confidence, state_context)
```

这是从**基于身份的安全**到**基于行为预测的安全**的范式转换。

---

## 架构主线（5 个模块，5 个职责）

### 1. CausalMemory — 因果记忆（`causal_memory.py`）

**职责**: 从每次工具执行中学习转移统计 P(s' | do(a), s)

核心机制：
- **状态模式提取** (`_state_pattern`): 将连续状态离散化为 bucket 特征（如 file_count: "0-1", "2-5"）和布尔标志（如 safe_mode, production）
- **效果检测** (`_diff_state`): 比较 before/after 快照，自动检测 file_created, file_deleted, message_sent 等效果
- **Laplace 平滑**: `confidence = support_count / (support_count + failure_count + 1)` — 避免小样本过拟合
- **SQLite 持久化**: 跨会话积累证据，confidence 随观测增加而提高

关键洞察：**记忆不是存储对话，而是存储因果转移统计**。这是"学习"和"记录"的本质区别。

### 2. Effect Risk Tiers — 效果风险分层（`rules.py`）

**职责**: 将可观测效果映射到风险等级

| Tier | 语义 | 示例效果 | 策略 |
|------|------|----------|------|
| CRITICAL (0) | 不可容忍 | credential_leak, privilege_escalation | 硬阻断 |
| HIGH (1) | 需确认 | command_executed, file_deleted | 需用户确认 |
| MEDIUM (2) | 需关注 | file_written, state_changed | 允许但记录 |
| LOW (3) | 例行操作 | file_content_read, search_performed | 直接允许 |
| BENIGN (4) | 纯信息 | tool_error, noop | 始终允许 |

关键洞察：**这是系统中唯一的静态知识**。其他一切（什么工具产生什么效果）都从因果记忆中学习。

### 3. PolicyEngine — 决策引擎（`engine.py`）

**职责**: 将因果预测转化为可审计的安全决策

决策流水线：
```
1. CausalMemory.predict(tool_name, state) → 预测效果 + 置信度
2. ConstraintChecker.check(predicted_effects, confidence) → 风险评估
3. 构建 PolicyDecision（含因果证据链）
```

每个决策都包含完整的因果证据：
- 预测的效果列表
- 置信度（基于观测次数）
- 风险等级
- 证据来源（causal_memory / bootstrap / user_prohibition）

### 4. ConstraintChecker — 约束检查器（`rules.py`）

**职责**: 基于预测效果（而非工具名）做安全判断

三层防护：
1. **用户显式禁止**: `prohibited_tools` 集合（用户主动关闭的工具）
2. **不可信数据流检测**: 标记为 untrusted 的数据流入特权操作 → 硬阻断（结构性检查，不可学习）
3. **因果效应推理**（核心）:
   - CRITICAL 效果 + 置信度 > 30% → 硬阻断
   - CRITICAL 效果 + 低置信度 → 升级为需确认
   - HIGH 效果 → 需用户确认
   - MEDIUM/LOW/BENIGN → 放行

冷启动策略 (`_bootstrap_check`): 当因果记忆为空时，使用保守的固有风险启发式，**但随着证据积累自动被因果预测覆盖**。

### 5. ProofObject — 审计证明（`proof.py`）

**职责**: 为每次工具执行生成不可变的审计记录

每条记录包含三层对比：
- **预测层**: policy 预期的效果/风险/状态
- **决策层**: 最终允许/阻断/需确认 + 理由
- **实际层**: 执行是否成功 + 实际观察结果

这实现了**事后可审计性**——任何安全决策都可以追溯到具体的因果证据。

---

## 集成方式（`integration.py`）

两个 hook 嵌入 Hermes 的工具执行管线：

```
pre_tool_check()  → PolicyEngine.evaluate() → 允许/阻断/需确认
post_tool_learn() → CausalMemory.update()   → 学习新证据
                  → ProofObject 写入审计日志
```

---

## 自改进闭环

```
工具执行 → 记录观察 (before_state, action, after_state, success)
    ↓
CausalMemory 更新转移统计 (support↑ / failure↑)
    ↓
下次同样 (state, action) → predict() 返回更高置信度的预测
    ↓
PolicyEngine 做出更精准的决策
```

这个闭环意味着：**系统越用越安全，且不需要人工更新规则**。

---

## 可发表的核心论点

1. **从静态黑名单到因果预测**: agent 安全可以被建模为因果推理问题，而非规则工程问题。这是方法论的跨越。

2. **决策 = f(效果, 置信度, 上下文)**: 核心公式简洁且有理论支撑（因果推断中的 do-calculus + Laplace 平滑），具备学术可辩护性。

3. **自改进安全**: 系统随使用变得更安全而不需要人工干预——这是一个可以量化的主张（对比 confidence 曲线随观测次数增长）。

4. **可审计的 AI 安全**: ProofObject 提供了安全决策的完整证据链——每一个 block 都可以追溯到"哪条经验告诉我要阻止这个动作"。

5. **冷启动与热运行的一致性**: bootstrap 保守策略 + Laplace 平滑保证了冷启动安全和热运行的渐进改进之间没有断裂。

---

## 论文定位建议

- **安全/AI Safety 方向**: 强调"可审计的自改进安全系统"，对标 RLHF 安全训练的高成本和不可解释性
- **Agent 系统方向**: 强调"因果感知的工具安全策略"，对标 LangChain/OpenAI 的静态 permission 系统
- **因果推断方向**: 强调 do-calculus 在真实 agent 系统中的工程落地
