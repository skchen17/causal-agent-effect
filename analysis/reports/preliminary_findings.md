# Agent 安全中因果效果的线性可编码性：初步实验报告

> **核心问题**：在 agent 安全场景中，LLM 内部表征是否以线性可解码的方式编码了工具调用的因果效果？
>
> 实验日期：2026-05-12 | 数据：284 条（184 规则模板 + 100 LLM 合成）

---

## 一、理论背景

### 1.1 非线性表征困境 (Sutter et al., NeurIPS 2025 Spotlight)

因果抽象（causal abstraction）旨在验证神经网络的低层计算是否"实现"了人类可理解的高层因果模型。其核心操作是**交换干预（interchange intervention）**：

1. 高层因果模型 $H$ 有变量 $\{V_1, \dots, V_k\}$
2. 低层神经网络 $N$ 有激活值 $\{a_1, \dots, a_n\}$
3. 对齐映射 $\tau: \text{rep}(N) \to \text{var}(H)$ 将激活映射到因果变量

Sutter et al. 的核心定理（非正式表述）：

> **如果对齐映射 $\tau$ 可以是非线性的，那么任何神经网络（包括随机初始化的）都可以被完美对齐到任何高层因果模型。因果抽象变得空洞——不能区分真正的因果理解和伪造的解释。**

形式直觉：

$$\text{IIA}(\tau_{\text{nonlinear}}) \approx 100\% \quad \text{甚至对随机模型}$$

$$\text{IIA}(\tau_{\text{linear}}) = f(\text{线性秩}) \quad \text{——可证伪}$$

因此，**线性约束不是工程偏好，而是因果可解释性的数学必要条件**。

### 1.2 线性表征假说 (LRH)

Park et al. (2023), Merullo et al. (ICLR 2025), Ravfogel et al. (NeurIPS 2025)：

> 神经网络倾向于将概念编码为激活空间中的线性方向。对二元概念 $C$，存在方向向量 $\mathbf{v}_C$ 使得：$P(C=1 | \mathbf{h}) = \sigma(\mathbf{w}^T \mathbf{h} + b)$ 具有高预测精度。

频率依赖性 (Merullo et al., ICLR 2025)：线性表征的形成需要概念在训练数据中有足够共现频率（阈值约 1k-4k 次）。

### 1.3 Agent 安全中的可操作化

将上述理论转化为可检验的实验假设：

$$\Delta_E = \text{F1}_{\text{nonlinear}}(E) - \text{F1}_{\text{linear}}(E)$$

| $\Delta_E$ | 解读 |
|:---:|------|
| $\approx 0$ | 效果 $E$ 被线性编码——因果解释可靠 |
| $\in (0.02, 0.08]$ | 部分非线性信息——混合编码 |
| $\in (0.08, 0.20]$ | 主要非线性编码——线性解释不够 |
| $> 0.20$ | 几乎纯非线性编码——线性因果解释空洞 |

---

## 二、实验架构

### 2.1 整体管道

```
场景文本描述 ──► LLM嵌入 (384维) ──┬──► 线性探针 (LogisticRegression)
                                    └──► 非线性探针 (MLP / RBF-kernel)
                                              │
                                    Δ = F1_nl - F1_lin
```

### 2.2 线性探针

对每个因果效果 $E \in \mathcal{E}$，训练：

$$\hat{P}(E=1 | \mathbf{h}) = \sigma(\mathbf{w}_E^T \mathbf{h} + b_E)$$

其中 $\mathbf{h} \in \mathbb{R}^{384}$ 是 `all-MiniLM-L6-v2` 的归一化嵌入，$\sigma$ 是 sigmoid 函数。通过 L2-正则化逻辑回归 + 5 折分层交叉验证拟合 $\mathbf{w}_E, b_E$。

评估指标：

$$\text{F1} = \frac{2 \cdot \text{TP}}{2 \cdot \text{TP} + \text{FP} + \text{FN}}, \quad \text{AUC} = \int_0^1 \text{TPR}(\text{FPR}^{-1}(t)) \, dt$$

### 2.3 非线性探针

根据正样本量 $N^+$ 自适应选择：

| $N^+$ | 方法 | 容量 |
|:---:|------|------|
| $< 30$ | RBF kernel 近似: $\phi(\mathbf{h}) = [\cos(\boldsymbol{\omega}_1^T\mathbf{h}), \sin(\boldsymbol{\omega}_1^T\mathbf{h}), \dots]$ | 64 维非线性特征 |
| $[30, 100)$ | MLP(64, 32), ReLU, $\alpha=0.01$, early stopping | ~27K 参数 |
| $\geq 100$ | MLP(128, 64), ReLU, $\alpha=0.001$, early stopping | ~52K 参数 |

RBF kernel 近似基于 Bochner 定理 (Rahimi & Recht, 2007)：高斯核 $k(\mathbf{x}, \mathbf{y}) = \exp(-\gamma\|\mathbf{x} - \mathbf{y}\|^2)$ 可以近似为：

$$k(\mathbf{x}, \mathbf{y}) \approx \phi(\mathbf{x})^T \phi(\mathbf{y}), \quad \boldsymbol{\omega}_i \sim \mathcal{N}(0, 2\gamma I)$$

### 2.4 数据生成策略

核心设计目标：**打破"工具名 $\to$ 效果"的确定性捷径**。

实验 1（模板数据）的混淆结构：
$$P(\text{effect} | \text{tool}) = \begin{cases} 1 & \text{若 effect 是该工具的固有效果} \\ 0 & \text{否则} \end{cases}$$

实验 2（反事实数据）：同一工具在不同上下文中产生不同效果：

$$P(\text{effect} | \text{tool}, \text{context}) \neq P(\text{effect} | \text{tool})$$

具体实现：
- **规则模板**（184 条）：每个工具 2-6 种场景变体，上下文嵌入自然语言
- **LLM 合成**（100 条）：DeepSeek V4 Flash 生成，4 个主题批次，每批 15-25 条

### 2.5 代码结构

```
generate_counterfactual_data.py  (665行)  数据生成
  ├── 9 tools × 2-6 variants × weighted sampling
  ├── DeepSeek V4 Flash API (Anthropic 兼容层, 分 batch 调用)
  └── → data/scenarios_counterfactual.jsonl

extract_embeddings.py            (202行)  嵌入提取
  ├── all-MiniLM-L6-v2 (SentenceTransformer, 384d, normalize)
  ├── 命令行参数选择数据源
  └── → embeddings/embeddings_{name}.npy (float32)
        embeddings/effects_{name}.npy      (int32)

train_probes.py                  (490行)  探针对比
  ├── LogisticRegression (线性)
  ├── MLPClassifier / RBFSampler (自适应非线性)
  ├── 5-fold StratifiedKFold → F1, AUC, Δ
  ├── 4-panel 可视化
  └── → analysis/results_{name}.json + delta_comparison_{name}.png

run_all.sh                       (34行)  管道入口
  bash run_all.sh counterfactual | template
```

---

## 三、实验结果

### 3.1 数据概览

| 指标 | 实验 1（模板） | 实验 2（反事实+LLM） |
|------|:---:|:---:|
| 样本数 | 900 | **284** |
| terminal 效果模式 | 1 | **13** |
| 每个效果平均 N+ | 103 | 43 |
| 混淆程度 | 严重（工具=效果） | 低（上下文依赖） |

### 3.2 线性可编码性排名

| 效果 | N+ | F1_lin | F1_nl | Δ | 风险等级 | 判定 |
|------|:---:|:---:|:---:|:---:|:---:|------|
| network_egress | 74 | 0.786 | 0.789 | **+0.003** | HIGH | ✓ LINEAR |
| tool_error | 83 | 0.750 | 0.743 | **−0.007** | BENIGN | ✓ LINEAR |
| file_deleted | 25 | 0.714 | 0.620 | −0.095 | HIGH | ⚠ 数据不足 |
| command_executed | 64 | 0.738 | 0.581 | −0.157 | HIGH | ⚠ 数据不足 |
| search_performed | 15 | 0.800 | 0.346 | −0.454 | LOW | ⚠ 数据不足 |
| memory_updated | 19 | 0.700 | 0.394 | −0.306 | LOW | ⚠ 数据不足 |
| content_fetched | 22 | 0.679 | 0.356 | −0.322 | LOW | ⚠ 数据不足 |
| message_sent | 21 | 0.745 | 0.400 | −0.345 | HIGH | ⚠ 数据不足 |
| subagent_spawned | 17 | 0.560 | 0.351 | −0.209 | HIGH | ⚠ 数据不足 |
| file_content_read | 40 | 0.585 | 0.000 | N/A | LOW | ⚠ NL FAIL |
| file_written | 31 | 0.578 | 0.000 | N/A | MEDIUM | ⚠ NL FAIL |

### 3.3 实验 1 → 实验 2 的关键变化

| | 实验 1 | 实验 2 | 说明 |
|---|:---:|:---:|---|
| HIGH tier avg F1_lin | 0.978 | 0.709 | 虚高 → 真实 |
| tool_error F1 | 0.043 | 0.750 | 从不可探测变可探测 |
| 有意义 Δ 的效果 | 0 | **2** | 实验 1 全是捷径 |
| 结论可靠性 | 低 | 中 | 需更多数据 |

### 3.4 初步结论

**C1 — 确认的（2 效果）**：对于样本充足的高频效果（$N^+ \geq 74$），$\Delta \approx 0$。`network_egress` 和 `tool_error` 在 LLM 表征中被线性编码——非线性探针无法超越线性探针。

**C2 — 待验证的（7 效果）**：其余效果的 $N^+$ 在 15-64 之间，非线性探针表现显著**低于**线性探针（$\Delta < -0.02$）。这最可能是小样本欠拟合，而非真正的"线性优于非线性"。

**C3 — 理论一致**：当前发现与 Sutter et al. (2025) 的核心论点在方向上一致——如果效果被线性编码，则因果解释可验证。但需要更大规模实验来确认这一模式对低频效果是否同样成立。

---

## 四、与已有文献的关系

| 文献 | 与我们工作的关系 |
|------|-----------------|
| Sutter et al. (NeurIPS 2025) | **理论基础**：我们将其非线性困境从纯语言任务推广到 agent 安全 |
| Merullo et al. (ICLR 2025) | **预测方向**：我们的频率依赖性假设直接来自 LRH 频率阈值 |
| Geiger et al. (JMLR 2025) | **方法论源**：因果抽象的交换干预框架是我们的终极验证目标 |
| Tatsat & Shater (May 2026) | **差异化**：他们用 SAE 提取 agent 特征，但不涉及安全决策中的因果线性性验证 |
| SafetyDrift (Mar 2026) | **竞争方法**：吸收马尔可夫链做安全预测，但忽略了可审计性问题 |

**我们的独特贡献空间**：将线性约束（来自 Sutter et al. 的数学必要性）应用于 agent 安全的因果效果可解释性验证——这是所有竞争工作都忽略的维度。

---

## 五、后续实验规划

### 实验 2b：扩大数据 + 交叉工具泛化（优先级：最高）

**目标**：为 N+ < 50 的效果获取充足样本，并验证探针是否学到了"因果概念"而非"工具代理"。

**方法**：
1. 用 DeepSeek V4 Flash 生成额外 500-700 条数据，确保每个效果 N+ ≥ 50
2. **交叉工具泛化检验**：在工具 A 上训练探针，在工具 B 上测试同效果

$$\text{Generalization Gap} = \text{F1}_{\text{test on tool B}} - \text{F1}_{\text{train on tool A}}$$

若探针真正学到了因果概念（如 `network_egress` 的语义），它应能跨工具泛化。若不能，则说明它仍在学"工具代理特征"。

### 实验 3：交换干预验证（优先级：高）

**目标**：从统计相关性（探针 F1）升级到因果验证（interchange intervention accuracy）。

**方法**：
1. 使用 pyvene 库实现交换干预
2. 对线性探针最高的子空间维度做干预
3. 测量 $\text{IIA}_L$（线性对齐的交换干预准确率）

$$\text{IIA}_L = \frac{1}{N} \sum_{i=1}^{N} \mathbf{1}[\text{swap}_\tau(\text{base}_i, \text{source}_i) = \text{expected}_i]$$

### 实验 4：模型容量对比（优先级：中）

**目标**：测试嵌入维度是否影响线性编码结论。

**方法**：对比三种模型：
- all-MiniLM-L6-v2（384d，当前）
- BERT-base-uncased（768d，中层）
- Llama-2-7B / Qwen-2.5-7B（4096d，高层）

### 实验 5：频率梯度严格检验（优先级：中）

**目标**：验证 Merullo et al. 的频率阈值在 agent 安全效果中是否成立。

**方法**：
1. 按 N+ 将效果分为高/中/低三组
2. 检验 $\text{F1}_{\text{linear}}$ 与 $\log(\text{frequency})$ 的相关性
3. 估计线性可编码的临界频率阈值

### 论文时间线（暂定）

| 阶段 | 内容 | 预计 |
|------|------|:---:|
| 已完成 | 实验 1 + 2（概念验证 + 初步 Δ 测量） | 5/12 |
| 进行中 | 实验 2b（扩大数据 + 交叉工具泛化） | 5/13-15 |
| 计划 | 实验 3（交换干预验证） | 5/16-20 |
| 计划 | 撰写初稿 | 5/20-25 |

**目标投稿**：NeurIPS 2026（截止日约 5 月底）或 AAAI 2027（截止日约 8 月）。

---

## 附录 A：关键公式汇总

### A.1 线性探针

$$\hat{P}(E=1 | \mathbf{h}) = \sigma(\mathbf{w}_E^T \mathbf{h} + b_E), \quad \sigma(x) = \frac{1}{1 + e^{-x}}$$

$$\mathcal{L}(\mathbf{w}_E, b_E) = -\sum_i \left[y_i \log \hat{p}_i + (1-y_i) \log(1-\hat{p}_i)\right] + \lambda \|\mathbf{w}_E\|_2^2$$

### A.2 非线性探针 (MLP)

$$\mathbf{z}^{(1)} = \text{ReLU}(\mathbf{W}^{(1)} \mathbf{h} + \mathbf{b}^{(1)}), \quad \mathbf{z}^{(2)} = \text{ReLU}(\mathbf{W}^{(2)} \mathbf{z}^{(1)} + \mathbf{b}^{(2)})$$

$$\hat{P}(E=1 | \mathbf{h}) = \sigma(\mathbf{w}^{(3)T} \mathbf{z}^{(2)} + b^{(3)})$$

### A.3 RBF Kernel 近似 (Bochner 定理)

$$k_{\text{RBF}}(\mathbf{x}, \mathbf{y}) = \exp(-\gamma \|\mathbf{x} - \mathbf{y}\|^2) = \mathbb{E}_{\boldsymbol{\omega} \sim \mathcal{N}(0, 2\gamma I)}[\cos(\boldsymbol{\omega}^T(\mathbf{x} - \mathbf{y}))]$$

$$\phi(\mathbf{x}) = \frac{1}{\sqrt{D}} [\cos(\boldsymbol{\omega}_1^T \mathbf{x}), \sin(\boldsymbol{\omega}_1^T \mathbf{x}), \dots, \cos(\boldsymbol{\omega}_{D/2}^T \mathbf{x}), \sin(\boldsymbol{\omega}_{D/2}^T \mathbf{x})]^T$$

### A.4 线性编码度量

$$\Delta_E = \text{F1}_{\text{nonlinear}}(E) - \text{F1}_{\text{linear}}(E)$$

$$\text{F1} = \frac{2 \sum_i \mathbb{1}[y_i = \hat{y}_i = 1]}{2 \sum_i \mathbb{1}[y_i = \hat{y}_i = 1] + \sum_i \mathbb{1}[y_i = 1, \hat{y}_i = 0] + \sum_i \mathbb{1}[y_i = 0, \hat{y}_i = 1]}$$

### A.5 因果抽象的形式框架 (Geiger et al., 2021/2025)

高层因果模型 $H$ 与低层神经网络 $N$ 之间的对齐映射 $\tau$ 满足因果抽象，当且仅当：

$$\forall \text{base}, \text{source}, \text{variable } V: \quad N_{\text{swap}_\tau(\text{base}, \text{source}, V)} = H_{\text{do}(V=v_{\text{source}})}(\text{base})$$

Sutter et al. (2025) 的线性约束要求：$\tau(\mathbf{h}) = \mathbf{W} \mathbf{h} + \mathbf{b}$（线性），否则因果抽象不可证伪。

---

## 附录 B：复现命令

```bash
# 实验 1（模板数据）
conda activate causal-safety
bash run_all.sh template

# 实验 2（反事实 + LLM 合成数据）
bash run_all.sh counterfactual

# 仅数据生成
python generate_counterfactual_data.py

# 仅嵌入提取
python extract_embeddings.py scenarios_counterfactual.jsonl

# 仅探针分析
python train_probes.py scenarios_counterfactual
```
