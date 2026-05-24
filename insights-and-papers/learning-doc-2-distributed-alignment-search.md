# 学习文档 2：分布式对齐搜索 (DAS)

> 本文档对应学习路线第二层。翻译并解析分布式对齐搜索的方法论。
> - **Geiger et al. (JMLR 2025)**: *"Causal Abstraction: A Theoretical Foundation for Mechanistic Interpretability"* — 统一框架
> - **Boundless DAS (2023)**: 将 DAS 扩展到 7B+ 参数模型
> - **Pyvene 库**: 斯坦福官方的交换干预实现

---

## 一、为什么需要 DAS？

### 1.1 局部对齐的局限

在学习文档 1 中，IIT 的对齐方式是"局部"的——假设每个高层变量对应一组**不相交的神经元**。例如：

```
V₁ → 隐藏层的前 5 个神经元
V₂ → 隐藏层的后 5 个神经元
```

但真实的神经网络表征是**分布式的**：
- 一个概念可能散布在激活向量的多个维度上
- 同一个维度可能参与编码多个不同的概念（polysemanticity）
- 概念之间可能有重叠、嵌套、层级关系

**局部对齐在分布式表征上必然失败**——你无法通过简单分组来捕捉散布在激活空间中的因果信息。

### 1.2 DAS 的核心思想

DAS 放弃"每个变量 → 一组神经元"的局部假设，改为"每个变量 → 激活空间中的一个线性子空间"。

**几何直觉**:
- 激活空间是一个高维向量空间（如 768 维的 BERT 隐藏状态）
- 一个因果概念可能对应这个空间中的**一个方向**或**一个子空间**（而不是一组坐标轴）
- DAS 通过学习一个**旋转矩阵**，找到正确的"观察角度"——在旋转后的空间中，因果概念对应的维度变得明确

**类比**: 想象你在一个房间里看一个物体。从某个角度看，物体的形状难以辨认。但如果你旋转到正确的角度，它的轮廓变得清晰。DAS 的学习过程就是寻找这个"正确的观察角度"。

---

## 二、DAS 的核心方法

### 2.1 正交旋转矩阵 R

DAS 的核心是一个**可学习的正交旋转矩阵** $R \in \mathbb{R}^{d \times d}$。

**正交矩阵的性质**:
- $R^T R = I$ — 旋转后各维度仍然相互正交（不丢失信息、不引入冗余）
- $R^{-1} = R^T$ — 逆旋转计算代价极低
- $\|Rh\| = \|h\|$ — 旋转不改变向量的模长（不放大也不缩小信息）

**为什么是正交而不是任意线性**:
- 正交保证旋转是**保距的**——不会扭曲激活空间的几何结构
- 如果允许任意线性变换，你可能会"拉伸"某些维度的信息或"压缩"其他维度的信息——这会破坏激活中编码的信息量分布
- 正交旋转相当于"换一个坐标系"——不改变激活向量本身携带的信息，只改变你观察它的角度

### 2.2 分布式交换干预 (DII)

DAS 的交换干预被称为**分布式交换干预 (DII)**，因为它操作的是子空间而非单个神经元：

**步骤**:
1. **旋转**: 将激活向量 $h \in \mathbb{R}^d$ 乘以旋转矩阵 $R$，得到旋转后的表示 $y = Rh$
2. **在子空间中干预**: 在 $y$ 中，选择特定的维度区间（如第 1-10 维）作为变量 $V_i$ 的"领地"，将这些维度上的值替换为源输入的对应值
3. **逆旋转**: 将干预后的 $y'$ 乘以 $R^T$，回到原始激活空间
4. **前向传播**: 从干预层继续网络的前向传播，观察输出

**形式化**:

记 $[V_i]_R$ 为在旋转后的空间中被分配给 $V_i$ 的维度索引集合，$y[V_i]$ 为这些维度上的值。分布式交换干预定义为：

$$\text{DII}_{b,s,V_i}(N) = N_{\text{from layer } \ell}(R^T \cdot \text{replace}(R \cdot h_b, [V_i], R \cdot h_s))$$

其中 $\text{replace}(y_{\text{base}}, [V_i], y_{\text{source}})$ 将 $y_{\text{base}}$ 中 $[V_i]$ 维度替换为 $y_{\text{source}}$ 中对应维度的值。

### 2.3 训练目标

DAS 的训练目标是学习旋转矩阵 $R$（以及可能需要学习的子空间划分）以最大化交换干预准确率：

$$\max_R \ \mathbb{E}_{b,s,V_i}\left[\mathbf{1}[\text{DII}_{b,s,V_i,R}(N) = H(b \text{ with } V_i \leftarrow H_V(s))]\right]$$

因为 DII 操作是完全可微的（矩阵乘法 + 值替换），这个目标可以通过标准梯度下降优化。

**损失函数**（交叉熵形式）:

$$\mathcal{L}_{\text{DAS}} = \mathbb{E}_{b,s,V_i}\left[\text{CrossEntropy}\left(\text{DII}_{b,s,V_i,R}(N), \ H(b \text{ with } V_i \leftarrow H_V(s))\right)\right]$$

### 2.4 旋转矩阵的维护

在训练过程中，$R$ 可能失去正交性（由于梯度更新的累积误差）。因此需要周期性地**重新正交化**：

```python
# Gram-Schmidt 正交化
def reorthogonalize(R):
    Q, _ = torch.linalg.qr(R)  # QR 分解 → 正交矩阵
    return Q
```

---

## 三、边界 DAS：扩展到大规模模型

### 3.1 标准 DAS 的限制

标准 DAS 有两个需要手动指定的参数：
- **子空间维度**: 每个高层变量分配多少维度的激活空间？
- **子空间位置**: 哪些维度对应哪个变量？

在小型 MLP（如 10 维隐藏层）上，这可以通过尝试不同组合来解决。但在 7B 参数模型的 4096 维隐藏状态中，组合空间爆炸使手动搜索不可行。

### 3.2 边界 DAS 的核心创新

**边界 DAS (Boundless DAS)** 将子空间的维度划分也变成**可学习的**。

**方法**:
- 使用**可微掩码 (differentiable soft masks)** 而不是硬边界
- 对每个高层变量 $V_i$，学习一个软掩码 $m_i \in [0,1]^d$（通过 sigmoid 或 Gumbel-softmax）
- 训练目标同时优化旋转矩阵 $R$ 和软掩码 $\{m_i\}$

**软掩码的直观**:
- 硬边界: "维度 1-10 属于 V₁，维度 11-20 属于 V₂"
- 软掩码: "维度 3 有 70% 的概率属于 V₁，维度 7 有 30% 的概率属于 V₁..."

训练过程中，模型不仅学习"从哪个角度看"，还学习"哪些维度是重要的"。

### 3.3 关键发现

边界 DAS 在 Alpaca-7B 模型上发现了解释布尔变量的因果子空间仅占用 **5-10% 的表征空间**。这意味着：大多数维度可能与当前分析的特定因果变量无关——它们编码了其他信息（其他概念、噪声、冗余编码）。

---

## 四、JMLR 2025 统一框架：十大方法的共同语言

### 4.1 框架的贡献

Geiger et al. (JMLR 2025) 的长期版本将因果抽象理论扩展为一个统一框架，把十种不同的机械可解释性方法纳入同一个形式语言中：

| 类别 | 方法 | 在统一框架中的角色 |
|------|------|-------------------|
| 修补/追踪 | Activation patching, Path patching, Causal tracing | 硬干预：完全替换机制 |
| 中介/消洗 | Causal mediation analysis, Causal scrubbing | 软干预：部分替换 + 噪声注入 |
| 电路分析 | Circuit analysis | 寻找因果图的子图 |
| 表征控制 | Concept erasure, Steering | 干预表征的方向（消去或增强概念） |
| 稀疏分解 | Sparse autoencoders (SAEs) | 从分布式表征中分解出可解释的特征方向 |
| 搜索方法 | Differential binary masking (DBM), DAS | 用梯度下降搜索对齐而非暴力搜索 |

### 4.2 统一的数学语言

框架的核心贡献是**将"机制替换"（hard/soft intervention）推广为"机制变换"（arbitrary mechanism transformation）**：

**机制替换**: $f_i^{\text{new}} = f_j$（用另一个变量的机制完全替换这个变量的机制）  
**机制变换**: $f_i^{\text{new}} = T(f_i)$（对机制施加任意函数变换）

这个推广使得框架可以同时容纳：
- **干预型方法**（patching, mediation）：改变机制为一个特定的替代机制
- **相关型方法**（SAE, concept erasure）：在原始机制的基础上做线性变换（投影、消去）

### 4.3 对 CAR 的影响

这个统一框架意味着 CAR 不需要选择"用哪种方法"——因果抽象的语言足够通用，可以容纳 CAR 可能需要的各种表征分析操作。无论是用 SAE 分解效果表征、用 DAS 搜索线性对齐、还是用 steering 编辑不安全行为的表征——它们都是同一形式语言中的不同操作。

---

## 五、Pyvene 库：实操

### 5.1 库的核心 API

Pyvene (`stanfordnlp/pyvene`) 是斯坦福 NLP 组开发的交换干预官方库。其核心 API 围绕几个概念：

```python
import pyvene as pv

# 1. 定义高层因果模型
# 变量: V1, V2 → 输出 O
# 机制: O = V1 == V2
causal_model = pv.CausalModel(
    variables=["V1", "V2", "O"],
    edges=[("V1", "O"), ("V2", "O")],
    mechanisms={
        "O": lambda v1, v2: v1 == v2
    }
)

# 2. 定义对齐
# 将 V1 对齐到网络第 2 层激活的前 5 维
# 将 V2 对齐到网络第 2 层激活的后 5 维
alignment = pv.Alignment(
    {"V1": {"layer": 2, "start": 0, "end": 5},
     "V2": {"layer": 2, "start": 5, "end": 10}}
)

# 3. 创建可干预模型
intervenable_model = pv.IntervenableModel(
    model=my_neural_network,
    alignment=alignment
)

# 4. 执行交换干预
# 基准输入: "AABB" → V1=True, V2=True
# 源输入: "ABCC" → V1=False, V2=False
# 干预: 交换 V1
output = intervenable_model(
    base_input="AABB",
    source_inputs={"V1": "ABCC"},
    intervention_type="interchange"
)
# output 应该反映 V1=False, V2=True → O=False

# 5. 训练循环
optimizer = torch.optim.Adam(alignment.parameters())
for epoch in range(num_epochs):
    loss = 0
    for base, source_pairs in dataloader:
        for var, source in source_pairs.items():
            output = intervenable_model(base, {var: source})
            target = causal_model.intervene(base, var, source)
            loss += F.cross_entropy(output, target)
    loss.backward()
    optimizer.step()
```

### 5.2 DAS 在 Pyvene 中的实现

```python
# DAS: 可学习的正交旋转矩阵
das_config = pv.DASConfig(
    hidden_dim=768,          # 激活维度
    num_variables=2,         # V1, V2
    subspace_dim=10,         # 每个变量的子空间大小
    intervention_layer=9     # 在第 9 层做干预
)

# 创建带旋转矩阵的可干预模型
intervenable = pv.DASIntervenable(
    model=bert_model,
    config=das_config
)

# R 和子空间划分都是可学习参数
# 训练时同时优化任务损失和 IIA
```

---

## 六、关键概念自查清单

- [ ] **为什么需要 DAS**：局部对齐在分布式表征上失败
- [ ] **正交旋转矩阵 R 的几何意义**：换坐标系观察同样的激活向量
- [ ] **分布式交换干预 (DII) 的步骤**：旋转 → 子空间干预 → 逆旋转 → 前向传播
- [ ] **DAS 的训练目标**：最大化 IIA 通过梯度下降学习 R
- [ ] **边界 DAS**: 用可微掩码自动学习子空间大小和位置
- [ ] **JMLR 2025 统一框架**: 将 10 种方法纳入因果抽象的共同语言
- [ ] **机制替换 vs 机制变换**: 框架推广的关键
- [ ] **Pyvene 的基本用法**: CausalModel → Alignment → IntervenableModel → 训练

---

## 参考资料

1. Geiger et al. (2025). "Causal Abstraction: A Theoretical Foundation for Mechanistic Interpretability." JMLR 2025. arXiv: 2301.04709.
2. Wu et al. (2023). "Boundless DAS" / "Interpretability at Scale: Identifying Causal Mechanisms in Alpaca."
3. Pyvene library: github.com/stanfordnlp/pyvene
