# 学习文档 1：因果抽象的直觉基础

> 本文档对应学习路线第一层。翻译并解析 Geiger et al. 的两篇奠基性论文：
> - **Geiger et al. (NeurIPS 2021)**: *"Causal Abstractions of Neural Networks"* — 因果抽象的原始定义
> - **Geiger et al. (ICML 2022)**: *"Inducing Causal Structure for Interpretable Neural Networks"* — 交换干预训练 (IIT)

---

## 一、因果抽象要解决什么问题？

### 1.1 动机：黑箱问题

考虑一个场景。你训练了一个神经网络，它在某个任务上表现完美——准确率 99%。但你不知道它**如何**做到的。它是真正理解了任务背后的逻辑，还是利用了数据中的统计捷径？

因果抽象（causal abstraction）提供了一种方法来回答这个问题：**不是看模型输出是否正确，而是看模型内部的计算是否与一个人类可理解的因果模型一致。**

### 1.2 核心直觉：两层模型的对应

想象你有一个高层因果模型 H——这是一个简单、可解释的算法。例如，判断两个等式是否等价的算法：

```
输入: [w,x,y,z]
V₁ = (w == x)    # 第一对是否相等
V₂ = (y == z)     # 第二对是否相等
O  = (V₁ == V₂)   # 两对的结果是否一致
```

这是**人类可以完全理解的**——只有三个变量，因果关系明确。

现在你有一个低层神经网络 N——一个激活值在高维空间中的黑箱。

**因果抽象问的是**：N 的内部计算是否"实现"了 H？具体来说，N 的某些激活模式是否扮演了与 H 中的变量 V₁、V₂ 相同的因果角色？

### 1.3 为什么这个问题重要

因果抽象不只是学术好奇。如果我们可以验证一个神经网络确实"实现了"某个可解释的因果模型：

- **安全性**：我们可以信任模型的内部推理，而不只是其输出
- **可调试性**：如果模型出错，我们可以追踪到具体哪个"因果变量"的计算出了问题
- **可编辑性**：我们可以精准地修改某个因果变量而不影响其他

**在 CAR 的语境中**：如果我们能验证 agent 安全系统的内部表征确实编码了可解释的因果效果（如 `command_executed`），那么安全决策就有了真正的因果基础——而非仅仅统计关联。

---

## 二、因果抽象的形式定义

### 2.1 高层因果模型 H

Geiger et al. 将高层模型定义为**结构化因果模型 (SCM)** 的实例：

$$H = \{\mathcal{V}, \mathcal{U}, \mathcal{F}, P(U)\}$$

其中：
- $\mathcal{V} = \{V_1, V_2, ..., V_k\}$ — 因果变量集合
- $\mathcal{U}$ — 外生噪声变量
- $\mathcal{F}$ — 因果机制集合，$V_i = f_i(PA_i, U_i)$
- $P(U)$ — 噪声分布

每个 $V_i$ 接受其父节点（直接原因）和一个噪声项，产生一个确定性的输出。

**输入-输出对**: 对于给定的输入 I，H 通过其因果机制计算出一组变量值 $\{v_1, ..., v_k\}$ 和输出 O。这定义了 H 的**因果行为**——不仅是"给定输入，输出是什么"，而且是"每个变量是怎么算出来的"。

### 2.2 低层神经网络 N

N 是一个函数 $N: \mathcal{X} \to \mathcal{Y}$，例如一个 transformer 或 MLP。N 的内部计算被分为 $L$ 层，每层产生激活值 $\{a^1, ..., a^L\}$。

N 不需要有任何显式的因果结构。它是一个黑箱函数。

### 2.3 对齐映射 τ

**这是因果抽象最核心的概念。**

对齐映射 $\tau$ 是一个从 N 的内部激活到 H 的变量值的函数：

$$\tau: \mathbb{R}^d \to \text{Domain}(V_i)$$

其中 $\mathbb{R}^d$ 是 N 某层的一个子空间（激活向量的一部分），$\text{Domain}(V_i)$ 是 H 中变量 $V_i$ 的取值范围。

**直觉**: $\tau$ 是一个"翻译器"——它把神经网络内部的数字模式翻译成人类可理解的因果术语。

**关键约束（来自 Sutter et al., 2025）**: $\tau$ 必须被约束为**线性函数**，否则因果抽象变得空洞。我们将在学习文档 3 中详细解释这一点。

### 2.4 交换干预：验证因果抽象

交换干预（interchange intervention）是验证对齐映射是否正确的实验。

**步骤**:

1. **选择两个输入**: 基准输入 $b$ 和源输入 $s$。在 H 中，这两个输入在变量 $V_i$ 上有不同的值。例如：
   - $b$: "AABB" → $V_1 = \text{True}$（前两个相等）
   - $s$: "ABCC" → $V_1 = \text{False}$（前两个不相等）

2. **定位内部表征**: 选择 N 中假设"编码"了 $V_i$ 的激活区域——即 $\tau$ 映射到的区域。记这个区域为 $[V_i]^N$。

3. **执行交换**: 将 $[V_i]^N$ 在基准输入 $b$ 上的激活值**替换**为它在源输入 $s$ 上的激活值。N 的其余部分保持不变。

4. **观察输出**: 如果 $\tau$ 是正确的，N 的输出应该与 H 在"$V_i$ 被干预为源输入的值"时的输出一致。

**形式化**: 记 $\text{II}_{b,s,V_i}(N)$ 为在基准输入 $b$ 和源输入 $s$ 上对变量 $V_i$ 做交换干预后 N 的输出。如果：

$$\text{II}_{b,s,V_i}(N) = H(b \text{ with } V_i \leftarrow H_V(s))$$

则对齐映射 $\tau$ 在变量 $V_i$ 上是**忠实**的。

**本质**: 交换干预是在 N 内部做因果实验——不改变输入，只改变内部表征，然后检查行为是否符合因果模型的预测。这与 Pearl 的 do-操作符（在外部队列上做随机干预）有相同的因果逻辑——但操作对象是内部激活而非外部变量。

### 2.5 交换干预准确率 (IIA)

**定义**: IIA 是在所有可能的基准-源输入对和所有变量上，交换干预产生正确输出的比例：

$$\text{IIA} = \frac{1}{|D|} \sum_{(b,s,V_i) \in D} \mathbf{1}[\text{II}_{b,s,V_i}(N) = H(b \text{ with } V_i \leftarrow H_V(s))]$$

当 $\text{IIA} = 100\%$ 时，N 的计算严格符合 H 的因果结构。

---

## 三、IIT：从被动分析到主动训练

### 3.1 IIT 的核心创新

Geiger et al. (ICML 2022) 提出的**交换干预训练 (IIT)** 将因果抽象从"分析已有模型"的工具升级为"训练模型使其符合因果模型"的方法。

**传统因果抽象**: 分析一个已经训练好的模型 N，寻找对齐映射 τ，使其 IIA 最高。

**IIT**: 在训练过程中同时优化任务损失和 IIA 损失，使得训练出的模型天然符合因果模型。

### 3.2 IIT 的损失函数

IIT 的总损失是两个项的组合：

$$\mathcal{L}_{\text{IIT}} = \mathcal{L}_{\text{task}} + \lambda \cdot \mathcal{L}_{\text{interchange}}$$

其中：
- $\mathcal{L}_{\text{task}}$ 是标准的任务损失（如交叉熵），确保模型能够正确完成任务
- $\mathcal{L}_{\text{interchange}}$ 是交换干预损失，衡量 N 在交换干预下的行为与 H 在对应干预下的行为之间的差异

**交换干预损失**的具体形式（对于变量 $V_i$）：

$$\mathcal{L}_{\text{II}}(V_i) = \mathbb{E}_{b,s \sim D}\left[\text{dist}\left(\text{II}_{b,s,V_i}(N), H(b \text{ with } V_i \leftarrow H_V(s))\right)\right]$$

其中 dist 是距离度量（如交叉熵或 L2）。

### 3.3 核心定理：零损失 = 因果抽象

IIT 的理论保证由其核心定理给出：

> **定理（非正式）**: 当 $\mathcal{L}_{\text{II}}(V_i) = 0$ 对所有 $V_i \in \mathcal{V}$ 成立时，N 是 H 的因果抽象——即 H 的因果结构被忠实地实现在 N 的内部计算中。

**为什么这个定理成立**:

1. $\mathcal{L}_{\text{II}}(V_i) = 0$ 意味着对**所有**可能的基准-源输入对，交换干预产生正确的输出
2. 这意味着 $\tau$ 对齐的激活区域 $[V_i]^N$ 在**所有可能的反事实场景**中都与 $V_i$ 有相同的因果行为
3. 如果每个 $V_i$ 都被忠实地对齐，那么这些变量之间的因果关系也必然被 N 的计算图所忠实实现

**关键直觉**: 零损失不是"平均正确"，而是"在所有反事实场景中正确"。这是一个非常强的条件——它排除了"模型碰巧在大多数输入上正确但因果结构错误"的可能性。

---

## 四、理解交换干预的深度

### 4.1 为什么交换干预比简单的激活分析更强？

考虑三种分析方法：

**(a) 激活观察**: "当输入包含'相等'时，神经元 42 的激活值很高"
- 问题：这只能建立**关联**，不能建立**因果**

**(b) 激活消融**: "当我将神经元 42 清零时，模型在相等判断任务上的表现下降"
- 问题：这告诉你神经元 42 是任务相关的，但不告诉你它编码了**什么信息**

**(c) 交换干预**: "当我把神经元 42 的激活替换为'不相等'输入上的激活时，模型的输出像看到了'不相等'一样变化"
- **这建立了因果关系**: 神经元 42 的特定激活值**导致**了模型对相等性判断的特定输出

交换干预的强大之处在于：它不只是说"这个神经元参与了计算"，而是说"这个神经元的激活值以**这种特定的方式**因果地影响输出"。

### 4.2 一个具体例子

用 CS224u 教程中的 Hierarchical Equality 任务：

**高层模型**:
```
V₁ = (w == x)  # 第一对是否相等
V₂ = (y == z)   # 第二对是否相等
O  = (V₁ == V₂) # 是否"两对的结果一致"
```

**交换干预实验**:
1. 基准输入 b: "AB AB"（第一对不相等，第二对不相等）→ V₁ = False, V₂ = False, O = True
2. 源输入 s: "AA BB"（第一对相等，第二对相等）→ V₁ = True, V₂ = True, O = True

在这两个输入中，O 的值碰巧相同（都是 True），所以单纯看输入-输出对无法区分它们。

**交换干预**: 将基准输入中"编码 V₁ 的激活"替换为源输入中的激活。

- 交换后：V₁ 的激活来自 s → V₁ = True（第一对相等）
- V₂ 的激活保持在 b → V₂ = False（第二对不相等）
- 如果对齐正确：N 的输出应该变为 O = False（因为 True ≠ False）

**如果 N 的输出确实变成了 False**，那就证明了 V₁ 的激活确实在因果地控制"第一对是否相等"的判断——它不只是碰巧与 V₁ 相关，而是以 V₁ 的因果角色在运作。

### 4.3 为什么需要多个基准-源对

一次成功的交换干预可能是巧合。IIT 要求**对所有可能的基准-源对**都正确——这意味着：

- 对于每种可能的 $V_i$ 取值组合
- 对于每种可能的其他变量的取值
- 交换 $V_i$ 总是产生正确的反事实结果

这相当于在 N 内部运行了一个**完整的因果实验空间**——覆盖了高层因果模型中所有可能的干预场景。

---

## 五、从理论到实践

### 5.1 CS224u 教程的核心代码逻辑

Stanford CS224u 的 `iit_equality.ipynb` 教程实现了 IIT 的完整流程：

```python
# 1. 定义高层因果模型
class EqualityModel:
    def compute_v1(self, input_pair1):
        return input_pair1[0] == input_pair1[1]

    def compute_v2(self, input_pair2):
        return input_pair2[0] == input_pair2[1]

    def compute_output(self, input):
        v1 = self.compute_v1(input[:2])
        v2 = self.compute_v2(input[2:])
        return v1 == v2

# 2. 训练神经网络（标准方式）
model = MLP(hidden_dim=10)
loss_task = CrossEntropyLoss(model(input), target)

# 3. 添加 IIT 损失
# 选择模型中"对齐"到 V₁ 的激活区域（如隐藏层的前 5 个维度）
v1_subspace = model.hidden[:, :5]
# 交换这些维度上的激活值
v1_subspace_intervened = intervene(
    base_activation=v1_subspace_on_base_input,
    source_activation=v1_subspace_on_source_input
)
# IIT 损失：交换后的输出应该匹配高层模型的干预结果
loss_iit = CrossEntropyLoss(
    model.forward_from_intervened(v1_subspace_intervened),
    high_level_model_output_with_intervention
)
# 总损失
loss_total = loss_task + lambda_iit * loss_iit
```

### 5.2 关键实现细节

**激活区域的选择**: 这是 IIT 的核心设计决策。两种策略：

1. **局部对齐**: 假设每个高层变量映射到一个**不相交的神经元集合**——如 V₁ → 隐藏层的前 5 个神经元
2. **分布式对齐**: 假设每个高层变量映射到激活空间中的一个**线性子空间**——如 V₁ → 激活向量的一个特定方向。这是 DAS（学习文档 2）处理的情况

**干预操作**: 对于局部对齐：
```python
# 将隐藏层的指定神经元替换为源输入的值
hidden_intervened = hidden_base.clone()
hidden_intervened[v1_indices] = hidden_source[v1_indices]
```

---

## 六、论文核心内容翻译摘要

### 6.1 Geiger et al. (NeurIPS 2021) 的主要贡献

> **原文核心 claim**: "We propose a structural analysis method grounded in a formal theory of causal abstraction."

**翻译与解析**: 作者提出了一种基于因果抽象形式理论的结构分析方法。这里的"结构分析"指的不仅仅是看模型输出，而是分析模型**内部**的计算结构。"因果抽象"意味着我们用一个更简单、更抽象的因果模型来描述复杂神经网络内部正在发生的事情。

> **实验发现**: "A BERT-based model with state-of-the-art performance successfully realizes parts of the natural logic model's causal structure."

**翻译与解析**: 在 MQNLI（多重量化自然语言推理）任务上，表现最好的 BERT 模型在其内部激活中**部分地**实现了自然逻辑模型的因果结构。关键修饰词是"部分地"——即使是最好的模型也没有完美地实现完整的因果结构。这意味着模型可能在用混合策略——部分因果推理，部分统计捷径。

### 6.2 Geiger et al. (ICML 2022) 的主要贡献

> **核心 claim**: "IIT is fully differentiable, flexibly combines with other objectives, and guarantees that the target causal model is a causal abstraction of the neural model when its loss is zero."

**翻译与解析**: IIT 的三个关键性质：
1. **完全可微**：可以通过标准反向传播训练——不需要强化学习或黑箱优化
2. **灵活组合**：IIT 损失可以与其他训练目标（如任务准确率、正则化）同时优化
3. **理论保证**：零 IIT 损失**保证**了因果抽象关系——这不是"可能"，而是数学上被证明的

> **实验结论**: "In every experiment, IIT achieves the best results."

**翻译与解析**: 在 MNIST-PVR（结构化视觉）、ReaSCAN（导航语言）和 MQNLI（自然语言推理）三个任务上，IIT 训练出的模型都比标准训练、多任务训练和数据增强更忠实地实现了目标因果模型。

---

## 七、关键概念自查清单

确保完全理解以下概念后再进入学习文档 2：

- [ ] **因果抽象的定义**：高层模型 H → 低层模型 N，通过对齐映射 τ 建立对应关系
- [ ] **对齐映射 τ**：从 N 的激活子空间到 H 的变量值的映射函数
- [ ] **交换干预**：不改变输入，只改变 N 内部的特定激活值，观察输出是否与 H 的干预预测一致
- [ ] **IIA（交换干预准确率）**：在所有可能的输入对和变量上，交换干预产生正确输出的比例
- [ ] **IIT（交换干预训练）**：在训练中同时优化任务损失和交换干预损失，使模型天然符合因果模型
- [ ] **零损失定理**：当 IIT 损失为 0 时，N 被保证是 H 的因果抽象
- [ ] **局部对齐 vs 分布式对齐**：局部对齐假设每个变量对应不相交的神经元集合；分布式对齐假设对应线性子空间
- [ ] **为什么交换干预比激活观察和消融更强**：它建立了因果关系而非关联关系

---

## 参考资料

1. Geiger et al. (2021). "Causal Abstractions of Neural Networks." NeurIPS 2021. arXiv: 2106.02997.
2. Geiger et al. (2022). "Inducing Causal Structure for Interpretable Neural Networks." ICML 2022. arXiv: 2112.00826.
3. Stanford CS224u. "Interchange Intervention Training: Equality Learning Tasks." Spring 2022. github.com/cgpotts/cs224u
