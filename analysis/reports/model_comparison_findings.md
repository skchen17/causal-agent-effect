# MiniLM vs Qwen2.5-7B 对比：表面形式 vs 因果后果的实证分析

> 实验日期：2026-05-12 | 数据：459 条合并场景 | 论文素材

---

## 一、实验设置

| | MiniLM | Qwen2.5-7B |
|------|------|------|
| 模型 | all-MiniLM-L6-v2 | Qwen/Qwen2.5-7B-Instruct |
| 维度 | 384 | 3584 |
| 参数量 | 22M | 7B |
| 训练数据 | 通用句子相似度 | 通用 + 指令微调 + **函数调用** |
| 推理硬件 | CPU | GPU (RTX 4090D, bfloat16) |
| 样本量 | 459 | 459 |

### 方法

1. **线性探针 F1**：LogisticRegression 对每个因果效果的 5 折 CV → 衡量效果的线性可读性
2. **非线性探针 Δ**：MLP / RBF-kernel vs 线性探针的 F1 差值 → 衡量线性编码的充分性
3. **交叉工具泛化 Gap**：留一工具交叉验证 → 衡量探针学到的是"因果概念"还是"工具代理"

---

## 二、结果一：线性可读性的量级差异

### Qwen 的线性探针全面碾压 MiniLM

| 效果 | MiniLM F1_lin | Qwen F1_lin | 增益 |
|------|:---:|:---:|:---:|
| command_executed | 0.747 | **0.936** | +0.189 |
| content_fetched | 0.624 | **0.878** | +0.254 |
| file_content_read | 0.593 | **0.870** | +0.277 |
| file_deleted | 0.785 | **0.911** | +0.126 |
| file_written | 0.605 | **0.863** | +0.258 |
| memory_updated | 0.739 | **0.835** | +0.096 |
| message_sent | 0.769 | **0.880** | +0.111 |
| network_egress | 0.728 | **0.852** | +0.124 |
| search_performed | 0.650 | **0.853** | +0.203 |
| subagent_spawned | 0.680 | **0.886** | +0.206 |
| tool_error | 0.722 | **0.918** | +0.196 |
| **平均** | **0.695** | **0.880** | **+0.185** |

**解读**：从 384d 到 3584d，线性探针 F1 提升了 18.5 个百分点。这不是简单的维度效应——MiniLM 的 384d 已经足够做工具内分类（F1=0.7），但 Qwen 的 3584d 提供了更丰富的因果语义信号。

### 非线性探针：没有增益

| | MiniLM | Qwen |
|---|---|---|
| |Δ|≤0.02 的效果 | 0 | **1 (tool_error)** |
| NL WORSE / FAIL | 9/11 | **10/11** |
| 正向 Δ (MLP 略优) | 3 | **1** |

两种模型上，非线性探针都无法显著超越线性探针。在 384d 空间这可能是容量不足；在 3584d 空间这更像是支持**线性编码假说**——因果效果以接近线性的方式编码在 LLM 表征中。

---

## 三、结果二：交叉工具泛化的核心对比

这是实验最关键的发现。

| 效果 | 可跨工具数 | MiniLM Gap | Qwen Gap | 变化 | MiniLM 判定 | Qwen 判定 |
|------|:---:|:---:|:---:|:---:|------|------|
| tool_error | 8 | −0.067 | **+0.112** | **+0.179** | ~ PARTIAL | ✓ CONCEPT LEARNED |
| network_egress | 4 | −0.193 | **−0.126** | **+0.067** | ◈ TOOL PROXY | ~ PARTIAL |
| content_fetched | 2 | −0.719 | **−0.490** | **+0.229** | ✗ PURE PROXY | ✗ PURE PROXY |
| file_deleted | 2 | −0.412 | −0.346 | +0.066 | ✗ PURE PROXY | ✗ PURE PROXY |
| file_content_read | 2 | −0.307 | −0.369 | −0.062 | ✗ PURE PROXY | ✗ PURE PROXY |
| file_written | 2 | −0.370 | −0.518 | −0.148 | ✗ PURE PROXY | ✗ PURE PROXY |

### 解读

1. **tool_error 从 partial 反转为 concept learned** (+0.179)：Qwen 的函数调用训练数据中包含"工具调用失败 → 尝试替代方案"的模式，强化了"错误"信号的跨工具语义对齐。

2. **network_egress 从 tool proxy 变为 partial** (+0.067)：高维空间 + 工具使用训练部分弥合了"web 出站"和"shell 网络命令"之间的语义鸿沟。

3. **4/6 效果仍然是 PURE PROXY**：工具使用训练不是万能药。对于语义区隔深的工具对（如 write_file 的 API 风格 vs terminal 的 shell 风格），改进有限甚至倒退（file_written 恶化 0.148）。

4. **content_fetched 改善显著但仍为 PURE PROXY** (+0.229，但从 -0.719 到 -0.490)：改善幅度第二大，但绝对值仍然很差——"web_fetch 获取内容"和"terminal curl 获取内容"在 Qwen 的嵌入空间中仍然相距甚远。

---

## 四、根本机制：LLM 表征天然按表面形式组织

### 4.1 分布假说的后果

LLM 的预训练目标是最小化下一个 token 的预测误差，这等价于学习 token 的条件概率分布：

$$P(w_t | w_{<t})$$

根据分布假说（Harris, 1954; Firth, 1957），两个 token 的嵌入接近当且仅当它们频繁出现在相似的上下文中。

这在 agent 场景中产生了一个直接后果：同一工具的不同调用共享语法结构（"agent 执行了 X"→"agent 执行了 Y"），在同一工具的数据中密集共现。但由不同工具产生的同一因果效果，它们的文本描述在预训练语料中几乎不共现。

### 4.2 具体案例：content_fetched

两个因果上等价的场景：

> **场景 W**："The agent fetched JSON data from `https://api.github.com/repos/torch` using the web_fetch tool."
>
> **场景 T**："agent 在终端执行了 `curl -s https://api.github.com/repos/torch`"

**表面形式分析**：

| 维度 | 场景 W (web_fetch) | 场景 T (terminal) |
|------|------|------|
| 核心动词 | "fetched" (API 语义) | "curl" (shell 语义) |
| 工具名 | "web_fetch" | "终端/terminal" |
| 语法结构 | 英文被动/完成 | 中文主动 |
| 伴随词汇 | JSON, data, resource | -s, 执行, 命令 |
| 预训练语域 | API docs, web dev | Shell manuals, DevOps |

在预训练语料中，"fetched" 的共现上下文是 API 文档、网页抓取教程、JSON 解析指南。"curl" 的共现上下文是 shell 手册、命令行教程、系统管理指南。两者几乎不在同一上下文中出现。

因此，场景 W 和场景 T 在嵌入空间中被拉向不同的方向。不存在单一的线性方向能同时穿过这两种嵌入——这就是工具代理问题的数学根源。

### 4.3 形式化表述

设 $h = f_\theta(x)$ 为 LLM 对输入文本 $x$ 的嵌入表示。对于因果效果 $E$，存在两种不同的嵌入子流形：

$$\mathcal{M}_{E, A} = \{f_\theta(x) : \text{tool}(x) = A \land \text{effect}(x, E) = 1\}$$

$$\mathcal{M}_{E, B} = \{f_\theta(x) : \text{tool}(x) = B \land \text{effect}(x, E) = 1\}$$

当 $A$ 和 $B$ 的语言学特征差异足够大时，$\mathcal{M}_{E, A}$ 和 $\mathcal{M}_{E, B}$ 在嵌入空间中相距甚远。不存在单一线性分类器能同时在两个子流形上达到高精度，除非它训练的样本覆盖了两个子流形。

**工具代理问题**的本质：线性探针 $\sigma(\mathbf{w}^T \mathbf{h} + b)$ 在 $\mathcal{M}_{E, A}$ 上训练时，学到的 $\mathbf{w}$ 指向的是"$\mathcal{M}_{E, A}$ 区域 vs 其他区域"的分界面——而非"因果效果 $E$ 发生 vs 不发生"的分界面。

### 4.4 为什么 tool_error 是例外

`tool_error` 的不同工具表达共享丰富的跨工具语言学信号：

| 工具 | tool_error 的典型表达 |
|------|------|
| terminal | "命令不存在或参数错误" |
| write_file | "被权限系统拒绝" |
| web_fetch | "被网络安全策略拦截" |
| web_search | "遭遇了 API 速率限制" |
| delegate | "已达到最大递归深度" |
| send_message | "无法连接" |

这些表达的共享语义核心是"**否定/失败/阻挡**"——"不"、"拒绝"、"拦截"、"限制"、"无法"——在预训练语料中高频共现。LLM 天然将它们编码到嵌入空间的邻近区域。

### 4.5 Gap 大小反映语言学距离

| 效果 | Gap (Qwen) | 语言学距离 |
|------|:---:|------|
| tool_error | +0.11 | 极近：所有工具的错误表达共享"否定/失败"语义场 |
| network_egress | −0.13 | 中等：web API 和 shell 网络命令有部分共享词汇 (URL, port, connect) |
| file_deleted | −0.35 | 远：delete_file API 和 terminal rm 属于不同语域 |
| file_content_read | −0.37 | 远：read_file API 和 terminal cat/grep 属于不同语域 |
| content_fetched | −0.49 | 极远：web_fetch API 和 terminal curl 几乎没有共现 |
| file_written | −0.52 | 极远：write_file API 和 terminal echo/tee 几乎没有共现 |

Gap 的大小不是随机的——它精确反映了"同一因果效果由不同工具描述时的语言学距离"。距离越大，共现频率越低，嵌入越分离，泛化越差。

---

## 五、理论贡献定位

### 5.1 与 Sutter et al. 非线性困境的关系

Sutter et al. (NeurIPS 2025) 证明：如果不约束 $\tau$ 为线性，因果抽象空洞。

我们的发现揭示了一个**互补的空洞形式**：即使在 $\tau$ 被约束为线性时，因果解释仍然可能被表面形式混淆。线性约束是必要的，但不足以保证因果抽象的 fidelity——还需要考虑**同一因果变量的多机制表征**问题。

### 5.2 与 Geiger et al. 因果抽象框架的关系

Geiger et al. (2021/2025) 的因果抽象框架假设高层因果变量 $V_i$ 与低层激活之间存在对齐映射 $\tau$。这个框架默认假设 $V_i$ 的每个取值在低层激活空间中对应一个**单独的子空间**。

在 agent 安全中，这假设不成立：$V_i = \text{content\_fetched}$ 的 $=1$ 取值对应的低层激活分布在**多个分离的子流形**上（web_fetch 子流形、terminal curl 子流形等）。现有的因果抽象理论没有处理"同一变量取值由多种异质低层机制产生"的情况。

### 5.3 提出的新概念：工具代理问题 (Tool-Proxy Problem)

**定义**：在 agent 系统中，因果效果的线性探针学到"工具特定表面特征"而非"跨工具的因果概念"时产生系统性泛化失败的现象。

**度量**：

$$\text{Tool-Proxy Gap}(E) = \text{F1}_{\text{cross-tool}}(E) - \text{F1}_{\text{within-tool}}(E)$$

**理论意义**：因果抽象 fidelity 需要扩展为：

$$\text{Fidelity}(\tau) = \text{IIA}(\tau) \times \text{Cross-Tool Generalization}(\tau)$$

即：仅在一个工具内达到高 IIA 不够——对齐映射必须证明它对齐的是"因果变量本身"而非"工具特定特征"。

---

## 六、与已有文献的关系

| 文献 | 与本文发现的关系 |
|------|-----------------|
| Sutter et al. (NeurIPS 2025) | 本文发现了线性约束下的互补空洞形式 |
| Merullo et al. (ICLR 2025) | 本文的跨工具泛化 gap 大小可能由预训练中的跨工具对比对频率决定——这是 LRH 频率阈值在 agent 安全中的新表现 |
| Geiger et al. (JMLR 2025) | 本文发现了因果抽象框架在 agent 安全中需要扩展的新维度：多机制表征 |
| Tatsat & Shater (May 2026) | 他们的 SAE 特征提取可能也面临工具代理问题，但未做跨工具检验 |
| Engels et al. (ICLR 2025) | "Not all features are linear"——工具代理可能是多维非线性的另一种表现 |

---

## 七、论文可用论点

**C1 — 工具代理问题是一个新发现**：在 agent 安全中，因果效果可以被线性探针高精度读出（F1 > 0.85），但这种高精度掩盖了探针对工具表面特征的依赖。交叉工具泛化检验暴露了线性可读性与因果忠实性之间的系统性格差距。

**C2 — 工具使用训练部分但不足以解决问题**：Qwen2.5-7B-Instruct 的 function-calling 训练在某些效果上显著改善了跨工具泛化（tool_error +0.179，content_fetched +0.229），但对大多数效果改进有限。4/6 效果仍然是 PURE PROXY。

**C3 — Gap 的大小不是随机的**：它反映了同一因果效果的不同工具描述在预训练语料中的语言学共现频率。这是一个可检验的预测——可以通过分析预训练语料中的跨工具对比对频率来验证。

**C4 — 现有因果抽象理论需要扩展**：同一因果变量由多种异质低层机制产生的情况下，因果抽象的 fidelity 度量需要同时考虑 IIA 和跨工具泛化。

---

## 八、未解决问题

1. **因果方向 vs 代理方向**：如何形式化"嵌入空间中的因果方向"与"工具代理方向"的差异？能否通过干预实验分离两者？

2. **对比学习能否解决**：如果用跨工具的同效果对比对做对比微调，能将不同工具的同效果嵌入拉近吗？

3. **更大模型的极限**：70B+ 模型是否比 7B 在跨工具泛化上有质变？

4. **预训练语料验证**：能否直接分析预训练语料中的"同一因果效果，不同工具"共现频率，检验它与 Gap 的相关性？

5. **与 IIA 的整合**：结合 pyvene 的交换干预来验证：在跨工具 IIA 条件下，工具代理 gap 是否缩小？
