# 工具代理问题 (Tool-Proxy Problem)

> 实验 2b 的核心发现：agent 安全中因果可解释性面临的一个未曾被报道的挑战
>
> 日期：2026-05-12

---

## 一、定义

**工具代理问题**：在 agent 安全系统中，线性探针对因果效果的预测能力来自于学习"工具特定的表面特征"（tool-specific surface features），而非"跨工具的因果概念"（cross-tool causal concept）。当探针在未见过的工具上测试同一因果效果时，预测能力系统性地崩溃。

形式化：

设 $\mathcal{T}$ 为工具集合，$E$ 为因果效果。对两个工具 $A, B \in \mathcal{T}$，若两者都能产生效果 $E$：

$$\text{Gap}(E, A \to B) = \text{F1}\big(\text{probe}_{train=A, test=B}(E)\big) - \text{F1}\big(\text{probe}_{train=A, test=A}(E)\big)$$

当 $\text{Gap} \ll 0$ 时，探针存在工具代理问题。

---

## 二、发现过程

### 2.1 实验 1 和 2 的初步结论

实验 1（模板数据）和实验 2（反事实数据）的 $\Delta$ 分析（线性 vs 非线性探针）显示：对于样本充足的效果，$\Delta \approx 0$——非线性探针无法超越线性探针。

这引导我们暂时得出结论：**因果效果在 LLM 表征中被线性编码**。

### 2.2 交叉工具泛化暴露的问题

实验 2b 引入了交叉工具泛化检验：在工具 A 上训练线性探针，在工具 B 上测试同一因果效果。

结果翻转了之前的结论：5/6 可检验效果存在严重的工具代理问题（Gap < -0.15）。

---

## 三、具体案例

### 3.1 content_fetched（最严重的工具代理）

**场景**：`content_fetched` 效果可以由 `web_fetch`（直接获取 URL 内容）或 `terminal`（curl/wget 等网络命令）产生。

**检验**：在 web_fetch 数据上训练探针，在 terminal 数据上测试。

| 训练数据（web_fetch） | 测试数据（terminal） |
|---|---|
| "agent fetched JSON from https://api.github.com" → content_fetched=1 | "agent ran `curl -s https://api.github.com`" → content_fetched=1 |
| "agent tried https://blocked.internal/ → blocked" → content_fetched=0 | "agent ran `ls -la`" → content_fetched=0 |

**结果**：
- 工具内 F1：0.905（探针在 web_fetch 上表现很好）
- 跨工具 F1：0.058（探针在 terminal 上几乎完全失败）
- **Gap：−0.847**

**机制**：探针在训练时学到的是 "fetch", "api.", "https://", "json" 这些 token 模式。它从未见过 "curl", "wget", "|", "stdout" 这些模式。当测试数据中出现 `curl -s https://api.github.com` 时——这在因果上和 web_fetch 完全等价——探针无法识别。

### 3.2 tool_error（唯一的例外）

**场景**：`tool_error` 可以出现在任何工具中：terminal 的命令错误、write_file 的权限拒绝、web_fetch 的网络拦截、delegate 的递归限制等。

**检验**：跨 8 个工具的留一工具交叉验证。

**结果**：
- 平均工具内 F1：0.699
- 平均跨工具 F1：0.632
- **Gap：−0.067**

**机制**：不同工具的 tool_error 场景共享明显的语言学特征——"尝试...但"、"拒绝"、"拦截"、"限制"、"失败"、"不存在"。LLM 嵌入模型将这些负面语义信号映射到嵌入空间中的邻近区域，形成了跨工具泛化的基础。

---

## 四、根本原因分析

### 4.1 LLM 嵌入的语义聚类机制

all-MiniLM-L6-v2 是句子相似度模型。它将文本映射到嵌入空间中，使得**语义上相似的句子距离近**。

问题在于：对于 agent 工具调用场景，哪些句子是"语义相似"的？

- **按工具聚类**："agent 执行了 `curl ...`" 和 "agent 执行了 `ls -la`" 都是 terminal 命令 → 语法结构相似 → 嵌入接近
- **按效果聚类**："agent 执行了 `curl ...`" 和 "agent 从 https://... 获取了内容" 因果上等价 → 但语法结构不同 → 嵌入距离远

LLM 嵌入优先按语法/表面形式聚类，而非按因果后果聚类。

### 4.2 线性探针的局限

线性探针 $\hat{E} = \sigma(\mathbf{w}^T \mathbf{h} + b)$ 只能学习一个方向。如果 `content_fetched=1` 的 terminal 样本和 `content_fetched=1` 的 web_fetch 样本在嵌入空间中相距甚远，就没有**单一的线性方向**能同时捕获两者。

### 4.3 与 Sutter et al. 非线性困境的关系

Sutter et al. (2025)：非线性 τ 使因果解释空洞（可以在随机模型上伪造 IIA=100%）。

工具代理问题揭示的是**不同的空洞形式**：线性 τ 给出的解释可能是"工具身份"而非"因果概念"。即使 IIA 高，它验证的可能是工具分类的准确率，而非因果抽象的 fidelity。

---

## 五、6 效果的代理程度

| 效果 | Gap | 探针在学什么 |
|------|:---:|------|
| tool_error | −0.07 | "出错/失败"的通用语义——跨工具泛化尚可 |
| network_egress | −0.19 | 部分工具代理——终端网络命令 vs web API 调用的编码不同 |
| file_content_read | −0.31 | 工具代理——"read_file 调用" vs "terminal cat/grep" 编码分离 |
| file_written | −0.37 | 工具代理——"write_file 调用" vs "echo/tee 重定向" 编码分离 |
| file_deleted | −0.41 | 工具代理——"delete_file 调用" vs "rm 命令" 编码分离 |
| content_fetched | −0.72 | 纯工具代理——web_fetch 和 terminal curl 在两个几乎不连通的嵌入子空间 |

---

## 六、理论意义

### 6.1 现有理论的缺口

因果抽象理论（Geiger et al., 2021/2025）假设高层因果变量 $V_i$ 有明确定义，对齐映射 $\tau$ 将低层激活映射到 $V_i$ 的值。

在 agent 安全中，因果变量是"效果"（如 content_fetched），但同一个变量可以由**不同机制**产生（web_fetch 的 HTTP 客户端 vs terminal 的 curl 进程）。从低层 LLM 的角度看，这些是**不同的输入分布**，可能被编码到嵌入空间的不同子流形上。

### 6.2 工具代理作为一个新的研究问题

工具代理问题将因果抽象的验证增加了一个维度：

$$\text{因果抽象 fidelity} = \text{IIA} \times \text{cross-tool generalization}$$

即：仅仅在一个工具内达到高 IIA 是不够的——对齐映射必须证明它对齐的是"因果变量本身"而非"工具特定特征"。

### 6.3 与已有文献的关系

| 文献 | 与工具代理问题的关系 |
|------|---------------------|
| Sutter et al. (NeurIPS 2025) | 我们发现了线性约束下的另一种空洞形式 |
| Merullo et al. (ICLR 2025) | 频率阈值可能可以解释为何跨工具效果难学（terminal curl 的频率可能低于 web_fetch） |
| Geiger et al. (JMLR 2025) | 因果抽象的定义需要扩展——考虑同一变量多机制产生的情况 |
| Tatsat & Shater (May 2026) | 他们的 SAE 特征也可能面临工具代理问题——但未做跨工具检验 |

---

## 七、后续方向

1. **多机制因果抽象（理论）**：如何形式化"同一因果变量由不同低层机制产生"的情况？这能否整合到现有的因果抽象框架中？

2. **工具不变表征学习（方法）**：能否训练一个编码器，使得跨工具的同一因果效果在嵌入空间中靠近？对比学习可能是一个方向。

3. **更大模型验证**：all-MiniLM-L6-v2（384d）可能太小。Llama-2-7B 或 Qwen-2.5-7B 的 4096 维空间是否有更好的跨工具对齐？

4. **增量数据**：定向生成跨工具对比样本（同效果、不同工具），训练探针在这些样本上，看能否强制学习跨工具不变特征。
