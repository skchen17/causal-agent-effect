# 因果任务一致性与工具不变因果抽象：形式化框架

> 论文理论部分的核心素材 | 2026-05-12；2026-05-14 更新主线为 causal task consistency

---

## 零、当前统一主张：Causal Task Consistency

Agent 工具调用安全的核心要求不是“识别工具名”，而是维持 **causal task consistency**：

> 每一次工具调用产生的因果效果，必须能被当前任务目标与授权范围解释；安全判断应围绕“该动作实际造成什么后果，以及这些后果是否被任务授权”，而不是围绕工具名、调用形式或表面文本。

本文当前理论框架服务于这条主线：

- **MultiMech** 说明同一因果效果可由多个工具/表面形式实现。
- **Frag / surface-form fragmentation** 描述表征层如何按工具碎片化，打断 causal task consistency。
- **SafeInv / ToolProxyGap** 将碎片化转化为 FNR 中心的安全诊断。
- **pIIA** 作为 probe-mediated 干预式诊断，检查效果方向是否能跨工具传递；它不是标准 SCM-based IIA，也不是安全定理前提。
- **LOTO safety table** 是 coverage-missing counterfactual stress test，不是完整覆盖部署探针的真实风险估计。
- **Auth-SafeInv / AuthToolProxyGap** 将 Causal Task Consistency 操作化为授权条件的安全度量：未授权效果不应被授权探针漏检。

---

## 零-A、授权条件因果任务一致性 (Authorization-Conditioned Causal Task Consistency)

Causal task consistency 的核心判定需要两个对象：

1. **任务授权了什么**：任务上下文 $c$ 定义了**授权效果包络** $A(c) \subseteq \mathcal{E}$——在给定任务中允许产生的因果效果集合。
2. **动作实际产生了什么**：工具调用 $(a, S)$ 的执行产生**实现效果集合** $\Omega(a, S) \subseteq \mathcal{E}$——动作实际导致的因果效果。

**因果任务一致性**成立当且仅当：

$$\Omega(a, S) \subseteq A(c)$$

即动作的因果后果完全被任务授权所覆盖。安全违规发生在：

$$U(c, a, S) = \Omega(a, S) \setminus A(c) \neq \emptyset$$

即存在**未授权效果**——动作产生了任务不允许的因果后果。

这一框架将 agent 安全从"效果检测的正确性"升级为"**未授权效果的不可漏检性**"。效果的 detection 不是为了"识别发生了什么"，而是为了判定"是否有不应该发生的事情发生了"。

本文后续的 Auth-SafeInv、AuthToolProxyGap 和授权条件风险记账定理均建立在此框架上。

## 一、背景：因果抽象（Geiger et al., 2021/2025）

### 1.1 基本定义

**高层因果模型** $H$ 由因果变量 $\{V_1, \dots, V_k\}$ 和因果机制 $\{f_1, \dots, f_k\}$ 组成：

$$V_i = f_i(\mathbf{PA}_i, U_i)$$

其中 $\mathbf{PA}_i$ 是 $V_i$ 的父节点集合，$U_i$ 是独立的外生噪声。

**低层模型** $N$ 是一个神经网络，对输入 $x$ 产生激活值 $\mathbf{a} = N(x) \in \mathbb{R}^n$。

**对齐映射** $\tau: \mathbb{R}^n \to \mathbb{R}^k$ 将低层激活映射到高层变量值：

$$\tau_i(\mathbf{a}) \approx V_i$$

### 1.2 交换干预 (Interchange Intervention)

给定基准输入 $b$ 和源输入 $s$，交换干预 $\text{II}(b, s, V_i, \tau)$ 操作如下：

1. 从 $N$ 中提取 $b$ 和 $s$ 的激活值 $\mathbf{a}^b, \mathbf{a}^s$
2. 预先指定或学习一个低层子空间 $S_i \subseteq \mathbb{R}^n$（或投影算子 $P_i: \mathbb{R}^n \to \mathbb{R}^{d_i}$），将其激活值与 $V_i$ 对齐
3. 构造干预后的激活：$\mathbf{a}^{\text{int}} = \mathbf{a}^b$ 但 $P_i(\mathbf{a}^{\text{int}}) = P_i(\mathbf{a}^s)$
4. 运行 $N$ 的其余部分，得到干预后的输出

**交换干预准确率**：

$$\text{IIA}(V_i, \tau, \mathcal{D}) = \mathbb{E}_{(b,s) \sim \mathcal{D}} \left[\mathbf{1}\left[N_{\text{swap}}(b, s, V_i, \tau) = H_{\text{do}(V_i = v_i^s)}(b)\right]\right]$$

其中 $v_i^s$ 是 $V_i$ 在源输入 $s$ 上的真值。

完美因果抽象对应所有相关交换干预的 IIA 为 1；经验研究中通常检验近似 IIA。

### 1.3 线性约束的必要性 (Sutter et al., NeurIPS 2025)

**定理（非正式，Sutter et al. 2025）**：如果 $\tau$ 可以是非线性的（充分复杂），则对于任意神经网络 $N$（包括随机初始化的）和任意高层因果模型 $H$，存在 $\tau$ 使得 $\text{IIA}(V_i, \tau) = 1$ 对所有 $V_i$ 成立。

因此，本文采用线性 $\tau$ 作为低复杂度、可证伪的对齐类（线性约束是本文的实现选择，不是唯一可能的复杂度约束）：

$$\tau(\mathbf{a}) = \mathbf{W} \mathbf{a} + \mathbf{b}, \quad \mathbf{W} \in \mathbb{R}^{k \times n}, \mathbf{b} \in \mathbb{R}^k$$

---

## 二、扩展：多机制效果与表征碎片化

### 2.1 动机

在 agent 系统中，同一个因果效果（如 `content_fetched`）可以由多种不同的工具产生（如 `web_fetch` 和 `terminal curl`）。从低层神经网络的角度看，这些工具构成了不同的输入分布，可能被编码到激活空间的不同子流形上。

在因果抽象的标准应用中，通常寻找单一对齐变量、子空间或低层表示组件来承载高层变量。本文指出，在 agent 工具场景中，同一高层效果可能呈现工具条件的多模态表征，因此单一线性方向可能捕获工具代理而非效果本身。

我们将"同一效果可由多个工具实现"（逻辑层事实）和"不同工具的同效果表征在嵌入空间中分离"（表征层事实）拆为两个独立定义。

### 2.2 表面形式多机制（逻辑层）

agent 操作可以通过不同的**表面形式**（surface form）来描述，而保持相同的因果后果。这些表面形式的差异可以来自多个维度：

- **工具维度** $S \in \mathcal{T}$：用不同工具执行同一效果（如 terminal `rm` vs delete_file）—— **本文实验的原型实例**
- **上下文维度** $S \in \mathcal{C}$：同一工具和效果，但上下文被注入污染（AttriGuard, ARGUS 的攻击面）
- **语义重框定维度** $S \in \mathcal{R}$：同一效果用不同的语义框架描述（"删除文件" vs "清理过期数据"）
- **语言维度** $S \in \mathcal{L}$：同一效果用不同语言描述

令 $\mathcal{S} = \mathcal{T} \cup \mathcal{C} \cup \mathcal{R} \cup \mathcal{L} \cup \cdots$ 为所有表面形式类的集合，其中每个 $S \in \mathcal{S}$ 是一个具体的表面形式标签。

**定义 1（多机制效果，Multi-Mechanism Effect）**

因果效果 $E_i \in \mathcal{E}$ 是**多机制的**，当且仅当存在至少两个不同的表面形式可以产生该效果：

$$\text{MultiMech}(E_i) \iff \exists S_a \neq S_b \in \mathcal{S}: P(E_i = 1 \mid S = S_a) > 0 \land P(E_i = 1 \mid S = S_b) > 0$$

**本文的实验覆盖**：$\mathcal{S} = \mathcal{T}$（工具维度），作为 MultiMech 的原型实例。本文的定理和诊断框架对任何 $\mathcal{S}$ 子集适用（数学上仅依赖表面形式标签的存在），扩展到 $\mathcal{S} \supset \mathcal{T}$ 是直接的概念泛化，不改变框架结构。上下文注入、语义重框定等维度的实验验证留待未来工作。

### 2.3 表征碎片化（表征层）

**定义 2（表面形式条件表征碎片化，Surface-Conditional Representation Fragmentation）**

对于多机制效果 $E_i$ 和表面形式对 $(S_a, S_b)$，定义 $E_i$ 在 $S_a$ 和 $S_b$ 之间的**表征碎片化程度**：

$$\text{Frag}_i(S_a, S_b) = d\left(P(\mathbf{h} \mid E_i=1, S=S_a), \; P(\mathbf{h} \mid E_i=1, S=S_b)\right)$$

其中 $d$ 是分布距离度量。$\mathbf{h} = N(\text{desc}(a, S))$ 是动作描述的 LLM 嵌入，$S$ 是该动作的表面形式标签。

$\text{Frag}_i(S_a, S_b)$ 度量的是：**同一个因果效果的 $=1$ 取值，在表征空间中是否因表面形式不同而形成可区分的模式**。当 Frag 大时，线性分类器可能学到表面形式特定的特征，而非跨形式的因果概念。

当 $\mathcal{S} = \mathcal{T}$（本文实验）时，Frag 退化为工具条件碎片化。若扩展到 $\mathcal{S} \supset \mathcal{T}$，Frag 可以度量上下文污染、语义重框定等攻击引起的表征分离。

**Frag 与 ToolProxyGap 的关系**：Frag 是理论上的表征分布差异（正类条件分布之间的距离）。ToolProxyGap 是本文采用的安全任务相关经验 proxy——它通过 LOTO 下的 FNR 增长来测量"表征碎片化是否转化为跨表面形式的漏检风险"。Frag 是表征概念，ToolProxyGap 是安全度量；前者解释"为什么"，后者量化"多严重"。

**原型实验注记**：本文的实验以 $\mathcal{S} = \mathcal{T}$（工具维度）作为 MultiMech 和 Frag 的原型实例。扩展到 $\mathcal{S} \supset \mathcal{T}$（上下文注入、语义重框定等）是概念上的直接泛化——框架的数学结构（定理 1 的 union bound、定理 2 的 Chernoff、命题 1 的 DA bound）不依赖于 $\mathcal{S}$ 的具体语义，只依赖于表面形式标签的存在性。

这两个定义独立但相关。本文的检验问题是：**MultiMech 效果是否表现出高 Frag（经验跨工具 gap），以及高 Frag 是否关联安全 FNR 风险。**

---

## 三、工具不变效果检测

### 3.1 安全中心的风险定义

设学习算法 $\mathcal{L}$ 从训练数据中学习线性探针。对效果 $E_i$ 和工具 $T$：

$$\hat{\tau}_{i, T} = \mathcal{L}_i(D_T)$$

其中 $D_T$ 是工具 $T$ 上的标注数据。探针输出 $\tau_i(\mathbf{h}) = \sigma(\mathbf{w}_i^\top \mathbf{h} + b_i) \in [0, 1]$。

**定义 3（安全相关 FNR）**

给定安全阈值 $\theta_i \in (0, 1)$（$\tau_i(\mathbf{h}) > \theta_i$ 时认为 $E_i=1$），工具 $T$ 上的安全相关假阴性率为：

$$R_{T, \theta}^{-}(\tau_i) = P\left(\tau_i(\mathbf{h}) \leq \theta_i \mid E_i = 1, T\right)$$

这是真正危险的指标：**危险效果发生了，但探针没检测到**。

类似的，定义假阳性率 $R_{T, \theta}^{+}(\tau_i) = P(\tau_i(\mathbf{h}) > \theta_i \mid E_i = 0, T)$。

**定义 4（安全工具不变性，SafeInv）**

探针 $\tau_i$ 对多机制效果 $E_i$ 是 $(\epsilon_{\text{safe}}, \epsilon_{\text{fpr}})$-安全工具不变的，当且仅当：

$$\max_{T \in \mathcal{T}_{E_i}} R_{T, \theta}^{-}(\tau_i) \leq \epsilon_{\text{safe}}$$

并且 $\max_{T \in \mathcal{T}_{E_i}} R_{T, \theta}^{+}(\tau_i) \leq \epsilon_{\text{fpr}}$（防止平庸解：恒定输出 1 可以满足低 FNR 但 FPR 不受控）。

其中 $\mathcal{T}_{E_i} = \{T \in \mathcal{T} : P(E_i=1 \mid T) > 0\}$ 是能产生 $E_i$ 的工具集合。

这比 F1 版定义更贴近 agent 安全的实际需求：安全系统的核心指标是在危险发生时不能漏检。在安全场景中，通常要求 $\epsilon_{\text{safe}} \ll \epsilon_{\text{fpr}}$：假阴性（漏放危险动作）的安全代价远超假阳性（误拒安全动作）。

### 3.1-A 授权条件安全不变性 (Auth-SafeInv)

在授权条件框架下，安全目标从"效果检测"明确为"**未授权效果不可漏检**"。给定任务上下文 $c$ 及其授权包络 $A(c)$：

**定义 4-A（授权安全相关 FNR）**

$$R_{c, S, \theta}^{-}(\tau_i) = P(\tau_i(\mathbf{h}) \leq \theta_i \mid E_i \in U(c, a, S))$$

其中 $U(c, a, S) = \Omega(a, S) \setminus A(c)$ 是未授权效果集合。这是"**发生了不应该发生的事情，但探针没检测到**"的概率。

**定义 4-B（Auth-SafeInv）**

探针 $\tau_i$ 对效果 $E_i$ 是 $(\epsilon_{\text{unauth}}, \epsilon_{\text{fauth}})$-Auth-SafeInv 的，当且仅当：

$$\max_{c, S} R_{c, S, \theta}^{-}(\tau_i) \leq \epsilon_{\text{unauth}} \quad \text{且} \quad \max_{c, S} R_{c, S, \theta}^{+}(\tau_i) \leq \epsilon_{\text{fauth}}$$

其中 $R_{c, S, \theta}^{+}$ 是授权效果的假阳性率（将合法效果误判为危险）。Auth-SafeInv 将安全不变性从"跨工具"扩展为"跨(任务上下文, 表面形式)"——同一个效果在不同任务中可能有不同的授权状态，探针必须在所有授权条件下保持可靠的未授权效果检测能力。

**定义 4-C（AuthToolProxyGap）**

对 heldout 表面形式 $B$，令 $\hat{\tau}_{i,-B}^{\text{diag}}$ 为不含 $B$ 的授权诊断探针，$\hat{\tau}_{i,B}^{\text{within}}$ 为 $B$ 内参照探针。授权条件下的覆盖缺失差异定义为：

$$\Delta\text{FNR}^{\text{auth}}_i(c,B)
= R_{c, B, \theta}^{-}(\hat{\tau}_{i,-B}^{\text{diag}})
- R_{c, B, \theta}^{-}(\hat{\tau}_{i,B}^{\text{within}})$$

$$\text{AuthToolProxyGap}_i(c,B)
= [\Delta\text{FNR}^{\text{auth}}_i(c,B)]_+$$

这是 ToolProxyGap 的授权条件版本：它测量在相同任务授权上下文 $c$ 下，未授权效果在 heldout 表面形式 $B$ 上因训练覆盖缺失造成的额外漏检风险。负差异不计入 gap。

### 3.1-B 授权条件风险记账

**Lemma (Authorization-Conditioned FNR Risk Accounting)**

设 $E \in \mathcal{E}$ 为效果，$c$ 为任务上下文，$S$ 为表面形式，且 $E \in U(c, a, S)$（$E$ 是未授权的）。定义：

$$\beta_{\text{auth}} = R_{c, S, \theta}^{-}(\tau_E^{\text{deploy}}), \quad \alpha_{\text{auth}} = P(\exists E_j \notin A(c), E_j \neq E: \tau_j(\mathbf{h}) > \theta_j \mid E \in U(c, a, S))$$

这里 $\alpha_{\text{auth}}$ 按同一探针套件下的**预测阈值触发**计算：只要其他未授权效果探针触发，系统就会拒绝。因此它包括真实共现的冗余拒绝，也包括其他未授权效果的误触发；不要把它替换成 oracle co-occurrence。

则安全系统放行一个产生未授权效果 $E$ 的动作的概率下界为：

$$P(\mathcal{S}(a, S) = \text{ALLOW} \mid E \in U(c, a, S)) \geq [\beta_{\text{auth}} - \alpha_{\text{auth}}]_+$$

这与 Theorem 1 结构相同，但 $\beta_{\text{auth}}$ 和 $\alpha_{\text{auth}}$ 现在条件于"$E$ 是未授权的"——使风险记账直接对接到安全违规（而非仅效果检测失败）。

### 3.2 工具代理间隙（安全版）

**区分三种探针**。以下定义中区分：

- **LOTO 诊断探针** $\hat{\tau}_{i, -B}^{\text{diag}} = \mathcal{L}_i(D_{\neg B})$：在除 heldout 工具/形式 $B$ 外的所有数据上训练，用于模拟覆盖缺失或新工具加入时的 stress test
- **heldout 内参照探针** $\hat{\tau}_{i, B}^{\text{within}}$：在 heldout 工具/形式 $B$ 内通过 stratified CV 估计，用于衡量该效果在 $B$ 内部本身是否可检测
- **部署探针** $\hat{\tau}_i^{\text{deploy}} = \mathcal{L}_i(D_{\text{train}})$：在混合训练数据上训练，是安全系统实际使用的探针

本文的实验同时报告：(1) LOTO 诊断探针的 ToolProxyGap/FNR-Gap，用于暴露覆盖缺失下的工具代理/表面形式碎片化；(2) 部署探针的 per-tool FNR，用于估计完整覆盖训练下的点估计风险。部署点估计为 0 不等于统计认证，稀有组合仍需置信区间约束。

**定义 5（ToolProxyGap 与 FNR-Gap）**

对 heldout 工具/形式 $B$，定义 coverage-missing stress test 下的 FNR 差异：

$$\Delta\text{FNR}_i(B) = R_{B, \theta}^{-}(\hat{\tau}_{i, -B}^{\text{diag}}) - R_{B, \theta}^{-}(\hat{\tau}_{i, B}^{\text{within}})$$

可正可负（负值表示 all-but-$B$ 训练并未比 $B$ 内参照更差）。**ToolProxyGap** 仅取正向退化：

$$\text{ToolProxyGap}_i(B) = [\Delta\text{FNR}_i(B)]_+ = \max(0, \Delta\text{FNR}_i(B))$$

**FNR-Gap** 是所有 heldout 形式上的最大 ToolProxyGap：

$$\text{FNR-Gap}_i(\mathcal{L}) = \max_{B \in \mathcal{T}_{E_i}} \text{ToolProxyGap}_i(B)$$

FNR-Gap 度量的是：**覆盖缺失时 heldout 形式漏检率相对其内部可检测性的最坏增长**。实验表格中同时报告 $\Delta\text{FNR}$ 和 ToolProxyGap，负 $\Delta\text{FNR}$ 不出现在 FNR-Gap 中。

定理 1 的真实部署版本中，$\beta$ 取自部署探针 $\hat{\tau}_i^{\text{deploy}}$ 在目标工具上的 FNR，而非诊断探针的值。本文另报告 LOTO stress-test 版本：$\beta^{\text{LOTO}}$ 和 $\alpha^{\text{LOTO}}$ 均来自不含 heldout 形式 $B$ 的同一诊断系统。诊断探针的 FNR-Gap 提供"工具代理是否可能构成安全风险"的事前证据。

### 3.3 pIIA：Probe-Mediated 交换干预

本文采用中间层交换干预。干预方向 $\mathbf{w}_A$ 从层 $\ell$ 的均值池化激活上训练的探针获取（与干预发生在同一层），评估探针 $\tau_i^B$ 从最终层激活上独立训练。

**干预算子**（一维方向交换，token-level broadcast）：

对探针权重 $\mathbf{w}_A \in \mathbb{R}^d$（单位方向 $\hat{\mathbf{w}}_A$），计算均值投影差异标量：

$$\Delta_i^{A}(b, s) = \hat{\mathbf{w}}_A \hat{\mathbf{w}}_A^{\top} (\bar{\mathbf{h}}_\ell^s - \bar{\mathbf{h}}_\ell^b) \in \mathbb{R}^d$$

其中 $\bar{\mathbf{h}}_\ell = \frac{1}{|\text{tokens}|} \sum_{r} \mathbf{h}_{\ell, r}$ 是层 $\ell$ 所有 token 的均值池化。对基准样本的每个 token $r$：

$$\mathbf{h}_{\ell, r}^{\text{int}} = \mathbf{h}_{\ell, r}^b + \Delta_i^{A}(b, s)$$

然后通过模型上层 $N_{>\ell}$ 传播：$\mathbf{h}_L^{\text{int}} = N_{>\ell}(\mathbf{h}_\ell^{\text{int}})$。

**与标准 Geiger IIA 的区别**：标准 IIA 评估模型行为是否等于高层 SCM 反事实输出 $H_{\text{do}(V_i=v_i^s)}(b)$。本文的判定使用独立探针 $\tau_i^B$ 作为反事实效果的统计读出器，因此称为 **probe-mediated IIA (pIIA)**。

**定义 6（pIIA）**

$$\text{pIIA}_i(A \to B) = P\left(\tau_i^B( N_{>\ell}( I_{\mathbf{w}_A}(\mathbf{h}_\ell^b, \mathbf{h}_\ell^s) ) ) > \tau_i^B(\mathbf{h}_L^b) \mid E_i(b)=0, E_i(s)=1, T(b)=T(s)=B\right)$$

符号约定：$A \to B$ 表示"干预方向在工具 $A$ 上学习，干预和评估在工具 $B$ 上进行"。

- $\mathbf{w}_A$：探针 $\hat{\tau}_{i, A}^{(\ell)} = \mathcal{L}_i(\{\bar{\mathbf{h}}_\ell, y_i\}_{T=A})$ 在层 $\ell$ 训练 → 提供干预方向
- $\tau_i^B$：探针在工具 $B$ 的最终层激活上训练 → 提供独立评估

**注**：pIIA-within 通常接近 1.0（同工具内方向干预几乎总能推动预测向正确方向）。这是预期的——同工具数据上的探针方向与自己的分布高度对齐。pIIA-cross 才是跨工具转移诊断的关键指标。pIIA 不能替代 FNR 的直接测量：它需要目标工具的标注样本对（$E=0, E=1$ 标签），因此适用于"目标工具有少量标注但不足以稳定估计部署 FNR"的场景，而非完全无监督。

**pIIA 在论文中的角色**：probe-mediated 干预式诊断。它检验 FNR-Gap 是否伴随效果方向的跨工具转移失败，但不能替代标准 IIA，也不作为安全定理的数学前提。

---

## 四、授权条件风险记账

### 4.1 Agent 安全系统模型

**定义 7（授权条件下基于效果预测的 Agent 安全系统）**

安全系统 $\mathcal{S}_c = (\Phi, \Psi_c, \Omega)$ 由三个组件组成：

1. **效果预测器** $\Phi = \{\tau_1, \dots, \tau_k\}$。每个 $\tau_i: \mathbb{R}^d \to [0, 1]$ 是线性探针：

$$\tau_i(\mathbf{h}) = \sigma(\mathbf{w}_i^\top \mathbf{h} + b_i)$$

其中 $\mathbf{h} = N(\text{desc}(a, T))$ 是动作描述文本的 LLM 嵌入。

2. **授权条件安全策略** $\Psi_c: [0,1]^k \to \{\text{ALLOW}, \text{DENY}\}$。给定任务上下文 $c$ 的授权效果包络 $A(c)$ 和阈值 $\{\theta_i\}$：

$$\Psi_c(\mathbf{p}) = \text{DENY} \iff \exists E_i \notin A(c): p_i > \theta_i$$

3. **执行环境 / effect verifier** $\Omega: \mathcal{A} \times \mathcal{T} \to 2^{\mathcal{E}}$，返回动作经特定工具执行后的实现因果效果集合。

系统对动作 $a$（使用工具 $T$）的端到端判定：

$$\mathcal{S}_c(a, T) = \Psi_c(\tau_1(\mathbf{h}), \dots, \tau_k(\mathbf{h})), \quad \mathbf{h} = N(\text{desc}(c,a,T))$$

安全目标是：若 $U(c,a,T)=\Omega(a,T)\setminus A(c)\neq\emptyset$，系统应拒绝；若 $\Omega(a,T)\subseteq A(c)$，系统不应仅因授权效果而拒绝。该定义把旧的“全局 critical effects”替换为“当前任务中未授权的 effects”。

### 4.2 授权条件 FNR 风险记账引理

**引理 1（Authorization-Conditioned FNR Risk Accounting）**

设任务上下文 $c$、表面形式 $B$ 和效果 $E \notin A(c)$ 满足 $E \in \Omega(a,B)$，即 $E \in U(c,a,B)$ 是该动作产生的未授权效果。设安全阈值 $\theta_E$ 给定。定义以下量：

- $\beta_{\text{auth}} = P(\tau_E(\mathbf{h}) \leq \theta_E \mid E \in U(c,a,B))$
  —— 表面形式 $B$ 上未授权效果 $E$ 的假阴性率

- $\alpha_{\text{auth}} = P(\exists E_j \notin A(c), E_j \neq E: \tau_j(\mathbf{h}) > \theta_j \mid E \in U(c,a,B))$
  —— 当未授权效果 $E$ 发生时，**其他未授权效果探针**至少有一个预测触发拒绝的概率

则在表面形式 $B$ 上，安全系统放行一个产生未授权效果 $E$ 的动作的概率下界为：

$$P\left(\mathcal{S}_c(a, B) = \text{ALLOW} \mid E \in U(c,a,B)\right) \geq [\beta_{\text{auth}} - \alpha_{\text{auth}}]_+$$

**证明**：

当 $E \in U(c,a,B)$ 时，系统 DENY 的条件是：

$$\mathcal{S}_c(a, B) = \text{DENY} \iff \tau_E(\mathbf{h}) > \theta_E \;\lor\; \exists E_j \notin A(c), E_j \neq E: \tau_j(\mathbf{h}) > \theta_j$$

取补事件：

$$\mathcal{S}_c(a, B) = \text{ALLOW} \iff \tau_E(\mathbf{h}) \leq \theta_E \;\land\; \forall E_j \notin A(c), E_j \neq E: \tau_j(\mathbf{h}) \leq \theta_j$$

由 union bound：

$$P(\text{ALLOW} \mid E \in U(c,a,B)) = 1 - P(\text{DENY} \mid E \in U(c,a,B))$$
$$\geq 1 - \big[P(\tau_E(\mathbf{h}) > \theta_E \mid E \in U(c,a,B)) + P(\exists E_j \notin A(c), E_j \neq E: \tau_j(\mathbf{h}) > \theta_j \mid E \in U(c,a,B))\big]$$
$$= 1 - [(1 - \beta_{\text{auth}}) + \alpha_{\text{auth}}] = \beta_{\text{auth}} - \alpha_{\text{auth}}$$

当 $\alpha_{\text{auth}} > \beta_{\text{auth}}$ 时下界退化为 0（其他未授权效果探针的拒绝已覆盖该风险）。当 $\alpha_{\text{auth}}$ 较小时，$[\beta_{\text{auth}} - \alpha_{\text{auth}}]_+$ 是仅依赖 union bound 的分布无关下界，不依赖效果变量间的相关结构。$\square$

**讨论**：引理 1 的证明不依赖 ToolProxyGap、pIIA 或任何因果诊断指标。它直接从授权条件安全策略和 FNR 出发，仅使用 union bound。这使得该结果应定位为 risk accounting lemma，而不是安全认证定理。

引理 1 的含义是：**如果某个未授权效果在某个表面形式上的假阴性率高于其他未授权效果探针的冗余拒绝率，则该表面形式构成 authorization-conditioned coverage gap。** 当前旧 LOTO safety table 只是该引理的 effect-level coverage-missing stress-test analogue；真正的 Auth-SafeInv 评估必须使用 $E \in U(c,a,B)$ 条件下的 $\beta_{\text{auth}}$ 和 $\alpha_{\text{auth}}$。

### 4.3 验证样本复杂度定理

**定理 2（稀有工具-效果组合的覆盖复杂度）**

设 $q = P(T=B, E=1)$ 是工具 $B$ 上效果 $E=1$ 的自然发生概率。考虑验证系统 $FNR_B$ 的测试流程：从分布 $P(T, E)$ 中独立采样 $m$ 个测试样本。

1. **覆盖**：要以概率 $\geq 1 - \delta_{\text{cov}}$ 在测试集中至少观察到一个 $(T=B, E=1)$ 样本，需要：

$$m \geq \frac{1}{q} \log \frac{1}{\delta_{\text{cov}}}$$

2. **估计**：要估计 $\text{FNR}_B$ 到误差 $\pm \epsilon$ 且置信度 $1 - \delta_{\text{est}}$，需要观察到 $\Omega(1/\epsilon^2)$ 个 $(T=B, E=1)$ 样本。因此：

$$m = \Omega\left(\frac{1}{q \cdot \epsilon^2} \log \frac{1}{\delta_{\text{est}}}\right)$$

**证明**：

1. 每次采样独立，观察到 $(T=B, E=1)$ 的概率为 $q$。$m$ 次采样中从未观察到的概率为 $(1-q)^m \leq e^{-mq}$。令 $e^{-mq} \leq \delta_{\text{cov}}$ 即得 $m$ 的下界。

2. FNR 的估计精度需要该组合的 $\Omega(1/\epsilon^2)$ 个独立样本（Hoeffding 界）。乘以 $1/q$ 的采样开销即得总复杂度。$\square$

**注**：精确覆盖条件为 $m \geq \frac{\log \delta_{\text{cov}}}{\log(1-q)}$。当 $q \ll 1$ 时 $\log(1-q) \approx -q$，得充分条件 $m \geq \frac{1}{q} \log \frac{1}{\delta_{\text{cov}}}$。估计复杂度写作 $m = \tilde{O}\left(\frac{1}{q \epsilon^2} \log \frac{1}{\delta}\right)$。

**安全含义**：在依赖自然分布采样的验证流程中，稀有工具-效果组合或稀有授权违规组合的覆盖成本随 $1/q$ 增长。若组合空间导致 $q$ 按指数级稀疏，覆盖成本也随之指数级增长。引理 1 说明覆盖缺失导致的高未授权 FNR 在冗余拒绝不足时会转化为正的 unsafe-allow 下界；定理 2 说明自然采样难以可靠覆盖稀有工具-效果组合。

### 4.4 域距离与跨工具泛化上界

**命题 1（域距离上界，Domain Adaptation Bound）**

设 $A, B$ 为两个工具域，$P_A^Z, P_B^Z$ 为两个域上 LLM 嵌入的边际分布。令 $\mathcal{H}$ 为线性探针假设类。则对任意探针 $h \in \mathcal{H}$：

$$R_B(h) \leq R_A(h) + d_{\mathcal{H}\Delta\mathcal{H}}(P_A^Z, P_B^Z) + \lambda_{A,B}$$

其中 $R_T(h) = \mathbb{E}_{(\mathbf{h}, y) \sim P_T}[\mathbf{1}[h(\mathbf{h}) \neq y]]$ 是工具 $T$ 上的 0-1 风险，$d_{\mathcal{H}\Delta\mathcal{H}}$ 是基于 $\mathcal{H}$-散度的域距离，$\lambda_{A,B} = \min_{h \in \mathcal{H}} (R_A(h) + R_B(h))$ 是两个工具域的最优联合风险。

**适用条件**：采用标准 domain adaptation bound 的形式（Ben-David et al., 2010），存在如上类型的不等式。上界紧致的前提是 $d_{\mathcal{H}\Delta\mathcal{H}}(P_A^Z, P_B^Z)$ 对线性假设类可被有效估计，且域差异沿分类方向有非零投影。在本文的实验中，我们检验其经验相关性：

$$\text{经验预测}: d(A, B) \uparrow \;\Rightarrow\; \text{FNR-Gap}(A \to B) \uparrow$$

其中 $d(A, B)$ 取嵌入空间中工具条件均值之间的余弦距离作为 $d_{\mathcal{H}\Delta\mathcal{H}}$ 的经验 proxy。

**与命题 1 初版的区别**：初版尝试给出 F1 的硬性线性下降公式。这个公式因 $\mathbf{w} \cdot (\boldsymbol{\mu}_B - \boldsymbol{\mu}_A)$ 可能正交于分类方向而不成立。当前版本采用 domain adaptation 标准形式，只给出**上界**而非下界。

**安全相关注记**：命题 1 使用总体 $0-1$ 风险 $R_T(h)$。在安全场景中，FNR（假阴性率）才是核心关注量。若需将上界应用于 FNR，应将域距离限定为正类条件分布之间的距离：

$$d_{\text{pos}}(A, B) = d_{\mathcal{H}\Delta\mathcal{H}}(P_A^{Z \mid Y=1}, P_B^{Z \mid Y=1})$$

当正类条件分布高度非高斯、或方差在工具间差异显著时（我们的实验显示均值余弦距离仅 0.003–0.068 但跨工具分类 gap 远大于此），边际 DA bound 可能显著低估 FNR 风险。实践中，我们使用经验跨工具 FNR-Gap 作为更直接的安全量度。

---

## 五、从定理到实验的映射

### 5.1 定理 1 和定理 2 的实验量化

**部署探针**（在所有工具上训练）：per-tool FNR = 0.000，per-tool FPR = 0.000。Point estimates satisfy SafeInv on well-sampled tool-effect pairs; statistical certification requires pre-specified $\epsilon_{\text{safe}}, \epsilon_{\text{fpr}}$ and confidence upper bounds below these thresholds. For rare pairs (small $n$), CI widths preclude certification.

**覆盖缺失反事实安全下界**（LOTO counterfactual）：下表模拟"目标工具在训练中缺失"的场景。$\beta^{\text{LOTO}}$ 是 LOTO heldout-FNR，$\alpha^{\text{LOTO}}$ 为同一 stress-test 系统下其他效果探针的**预测**触发率（非 oracle 共现），下界为 $[\beta^{\text{LOTO}} - \alpha^{\text{LOTO}}]_+$。注意：该表不是当前完整部署系统的真实 unsafe-allow 下界。

| 效果 | Heldout Tool | β^LOTO (FNR) | α^LOTO (redundancy) | [β^LOTO−α^LOTO]₊ |
|------|------|:---:|:---:|:---:|
| content_fetched | terminal | 0.500 | **1.000** | **0.000** |
| file_content_read | read_file | 0.875 | 0.188 | **0.688** |
| file_written | write_file | 0.970 | 0.455 | **0.515** |
| file_deleted | terminal | 0.600 | 0.150 | **0.450** |
| network_egress | web_search | 0.731 | 0.308 | **0.423** |
| tool_error | terminal | 0.269 | 0.038 | **0.231** |

**关键发现**：高 LOTO FNR 不必然导致 stress-test 安全下界为正。content_fetched 的 terminal FNR=0.50 但 $\alpha^{\text{LOTO}}=1.00$（其他效果探针在同一 coverage-missing 系统中全覆盖触发），下界为 0。当前重新核对后的最大正下界是 file_content_read/read_file：$0.875-0.188=0.688$；file_written、file_deleted、network_egress 与 tool_error 也存在正 stress-test 下界。定理 1 将风险条件精确化为"**高 FNR + 低冗余拒绝**"，但真实部署风险必须使用部署探针的 $\beta^{\text{deploy}}$。

**LOTO 诊断探针**（leave-one-tool-out）：模拟工具覆盖缺失/新工具加入/稀有组合未标注时的安全风险。

| 效果 | Training Forms | Heldout Tool | Heldout N+ | Within-FNR | Held-FNR | ΔFNR | ToolProxyGap |
|------|------|------|:---:|:---:|:---:|:---:|:---:|
| content_fetched | all-but-terminal | terminal | 8 | 0.111 | 0.500 | +0.389 | 0.389 |
| content_fetched | all-but-web_fetch | web_fetch | 32 | 0.064 | 0.781 | +0.718 | 0.718 |
| file_content_read | all-but-read_file | read_file | 32 | 0.033 | 0.875 | +0.842 | 0.842 |
| file_deleted | all-but-terminal | terminal | 20 | 0.246 | 0.600 | +0.354 | 0.354 |
| file_written | all-but-write_file | write_file | 33 | 0.091 | 0.970 | +0.879 | 0.879 |
| network_egress | all-but-web_search | web_search | 26 | 0.074 | 0.731 | +0.657 | 0.657 |
| tool_error | all-but-web_search | web_search | 10 | 0.278 | 0.100 | -0.178 | **0.000** |

（显示代表性 heldout stress-test 单元。Within-FNR 是 heldout 工具内部 stratified CV，Held-FNR 是 all-but-heldout 训练后的 heldout FNR。ΔFNR 可负，ToolProxyGap = [ΔFNR]₊。）

**LOTO 训练口径**：对于每个 heldout tool $B$，所有效果探针均在不含 $B$ 的训练集上训练，并在 $B$ 上计算预测值。因此 $\beta^{\text{LOTO}}$ 和 $\alpha^{\text{LOTO}}$ 对应同一个 coverage-missing stress-test system。

关键模式：heldout 工具内部通常可检测（Within-FNR 多数较低），但 all-but-heldout 训练后 heldout FNR 可高（0.10-0.97）。ΔFNR 可负（tool_error: all-but-web_search 不比 web_search 内参照更差），此时 ToolProxyGap = 0——覆盖缺失未造成退化。

Tool-conditioned baseline 在所有 LOTO 效果上与 pooled 完全等价：因为 LOTO 设置下 heldout 工具 ID 在训练中未出现，其 one-hot 维度退化为全零，模型等价于标准 pooled。**这不是方法失败，而是 LOTO stress-test 场景下工具条件化不可用的固有局限。**

### 5.2 pIIA 作为干预式诊断

我们通过中间层 pIIA 提供 probe-mediated 干预式诊断——干预方向来自层 $\ell=24$ 训练的探针，评估来自最终层独立探针。该指标检查跨工具效果方向转移，不等同于标准 Geiger IIA。

| 效果 | pIIA-within | pIIA-cross | pIIA-Drop | Max LOTO FNR |
|------|:---:|:---:|:---:|:---:|
| tool_error | 1.000 | 0.948 | **0.052** | 0.269 |
| file_content_read | 1.000 | 0.837 | 0.164 | 0.875 |
| file_deleted | 1.000 | 0.800 | 0.200 | 0.600 |
| content_fetched | 1.000 | 0.702 | 0.298 | 0.781 |
| file_written | 1.000 | 0.669 | 0.331 | 0.970 |
| network_egress | 1.000 | 0.634 | 0.366 | 0.731 |

**Threshold Transfer Proxy**：将 pIIA 的判定条件从"分数上升"类比到跨过安全阈值 $\theta=0.5$。这里以 LOTO within-recall 和 heldout-recall 作为近似（注：这不是来自干预实验的真实阈值干预指标，而是 recall 的跨工具转移率）：

| 效果 | Representative heldout | ThreshProxy (within) | ThreshProxy (cross) | Drop |
|------|------|:---:|:---:|:---:|
| tool_error | web_search | 0.722 | 0.900 | -0.178 |
| content_fetched | web_fetch | 0.936 | 0.219 | **0.718** |
| file_written | write_file | 0.909 | 0.030 | **0.879** |
| network_egress | web_search | 0.926 | 0.269 | **0.657** |

Threshold Transfer Proxy Drop 比原始的 pIIA-Drop（仅要求分数上升）更具区分度：file_written 和 network_egress 的跨工具 recall 转移很弱。由于该量不是来自真实干预后的阈值判定，不能称为 pIIA-threshold。

**Spearman $\rho$(pIIA-Drop, FNR-Gap) = 0.771 (p=0.072, n=6)**。pIIA-Drop 与 FNR-Gap 呈 suggestive positive trend（受限于 n=6 未达显著）。两者的统计关系在论文中表述为"趋势关联"而非"已验证"。

### 5.3 命题 1 的经验检验

命题 1 预测：工具域距离越大，跨工具泛化越差。我们在 156 个工具对上检验了该预测。

**同家族 vs 跨家族**（156 个工具对，Qwen3-8B）：
- 同家族工具：平均 F1 = 0.569 (95% CI: [0.48, 0.66])
- 跨家族工具：平均 F1 = 0.424 (95% CI: [0.37, 0.48])
- 差异 Δ = +0.145, bootstrap p < 0.01
- 同家族 mean ToolProxyGap = 0.12 (95% CI: [0.04, 0.22])
- 跨家族 mean ToolProxyGap = 0.31 (95% CI: [0.21, 0.40])
- 差异 Δ = +0.19, bootstrap p < 0.01（与 F1 差异方向一致，量级更大）

**注**：156 个工具对共享工具和效果，非独立。稳健性以 mixed-effects 回归（random intercepts by effect/tool）确认 CrossFamily 方向不变。pIIA 的样本为干预对 $(b,s)$，有效对数量大于原始样本数但非独立；pIIA 置信区间按 source example bootstrap 计算。pIIA 在本论文中作为描述性诊断指标，不做推断性统计检验。

**正类表征均值距离与跨工具 gap 的关系**：
- 正类条件均值余弦距离仅 0.003–0.068（极低）
- 但代表性 LOTO ToolProxyGap 最高达到 0.879（极大）
- **碎片化不在均值中**——在方差、协方差、或非线性可分结构中
- **补充检验**：线性 tool discriminator（在 $E=1$ 样本上区分来源工具）跨效果准确率 0.72–0.95，而随机基线为 0.50（两工具）——正类表征按工具高度可分，但这一分离信号几乎完全正交于均值方向（余弦距离 < 0.07）。碎片化存在于高阶统计量中
- 这解释了为什么命题 1 的边际 DA bound 可能严重低估 FNR 风险：需要正类条件分布距离

### 5.4 Baseline：简单方法能否解决？

我们测试了五种 baseline：**pooled**（class_weight=balanced）、**balanced pooled**（每工具等量采样）、**tool-conditioned**（嵌入拼接工具 ID one-hot）、**Group Reweight**（per-tool inverse-frequency sample weights）、**Procrustes alignment**（几何旋转对齐探针方向）。

| 效果 | Pooled | Balanced | Tool-Cond | Group Reweight | Procrustes |
|------|:---:|:---:|:---:|:---:|:---:|
| content_fetched | 0.78 | 0.78 | 0.78 | **0.75** | 0.44 |
| file_content_read | 0.88 | **0.53** | 0.88 | 0.91 | 1.00 |
| file_deleted | 0.60 | **0.20** | 0.60 | 0.87 | 0.25 |
| file_written | 0.97 | 0.94 | 0.97 | 0.97 | 1.00 |
| network_egress | 0.73 | **0.41** | 0.73 | 0.81 | 0.35 |
| tool_error | 0.27 | 0.31 | 0.27 | 0.27 | 0.27 |

Balanced pooling 在 3/6 效果上降低了 worst-tool FNR，但 Group Reweight（per-tool 逆频率样本权重）在 4/6 上持平或更差——逆频率加权在 file_deleted 上从 0.60 恶化到 0.87（稀有工具 upweight 引入噪声方向）。Tool-conditioned 因 LOTO 下 heldout 工具 ID 退化为全零而等价于 pooled。Procrustes alignment 改善部分工具对，但不能系统降低每个效果的 worst-tool FNR。

**结论**：类别/工具采样不平衡解释了部分跨工具漏检（balanced pooling 在 3/6 效果上显著降低 worst-FNR），但不能完全解释该现象——即使平衡采样，多个效果仍保留较高 worst-tool FNR（0.20-0.94）。工具代理问题是采样不平衡与表征碎片化的复合效应。

### 5.5 多模型验证

| 模型 | content_fetched IIA-Drop | tool_error IIA-Drop |
|------|:---:|:---:|
| MiniLM (384d, 无工具训练) | 0.294 | 0.096 |
| Qwen3-8B (L24探针, 函数调用) | 0.298 | 0.052 |

MiniLM 与 Qwen3-8B 的对比显示，不同表示族上工具不变性表现不一致：tool_error 在 Qwen3-8B 上接近完全不变（pIIA-Drop=0.052 vs 0.096），content_fetched 的 pIIA-Drop 在两种模型上接近（0.298 vs 0.294）。**注**：MiniLM 的非转换器架构不支持中间层 hook 干预，因此 MiniLM 使用嵌入空间方向交换（`interchange_intervention.py`），Qwen3-8B 使用层 24 的 hook 干预（`interchange_intervention_true.py`）。两者测量同一概念（方向互换后的探针分数变化），但实现路径不同——前者的”干预”在冻结嵌入空间中进行，后者的干预经模型上层传播。跨模型比较应理解为”不同表示族的趋势观察”而非严格的同方法对比。需要同系列 ablation（base/instruct/tool-SFT）才能做出归因结论。

---

## 六、与已有理论的对接（修订版）

### 6.1 与 Sutter et al. (NeurIPS 2025) 的关系

Sutter et al. 提供了为什么需要限制 alignment class 复杂度的理论动机：无约束的高复杂度非线性对齐映射会使因果抽象平凡化（在随机模型上也能达到 IIA = 1）。本文采用线性探针作为该限制的一种实现。

在此基础上，本文进一步检验：在满足低复杂度约束的前提下，对齐映射是否还需要额外的**跨工具稳定性**条件才能支撑安全相关的因果解释。结论是：低复杂度约束不够，还需要工具不变性——两者是互补的诊断维度。

### 6.2 与 Geiger et al. (2021/2025) 的关系

在因果抽象的标准应用中，高层变量通常对应低层中单一的对齐组件。本文指出 agent 场景的特殊性：同一高层效果可能呈现工具条件分离的表征模式。工具不变性因此成为因果抽象在 agent 安全中适用性的额外诊断条件。

### 6.3 与 CIVeX (May 2026) 的关系

CIVeX 提出 agent 动作执行前需要因果证书，并证明非因果验证器在有混淆的环境中必然产生错误放行。在任何需要由模型预测候选效果或构造效果标签的执行验证框架中，效果预测器的跨工具可靠性会构成证书输入质量的上游风险。

本文补充 CIVeX 的上游问题：**当效果预测器依赖 LLM 表征时，工具不变性应作为证书可信度的前置诊断。** 如果表征碎片化严重，从某个工具数据训练的预测器在另一个工具上产生系统性盲区，则因果证书的输入不可靠。

两个工作在[行为层 | 表征层]上互补，而非竞争。CIVeX 的"证书框架"+ 本文的"表征诊断"可以构成完整的 agent 安全因果验证栈。

---

## 七、论文结构（修订版）

```
1. Introduction
   - Agent 安全需要跨工具的效果检测
   - CIVeX 等在行为层做因果验证，表征层前提未被检验
   - 核心发现：LLM 表征是工具碎片化的，效果探针学到的是工具代理

2. Related Work
   - 因果抽象 (Geiger, Sutter)
   - Agent 安全验证 (CIVeX, VIRF, Containment)
   - 表征学习 (LRH, CRL)

3. Formal Framework
   3.1 Agent 安全系统模型
   3.2 多机制效果与表征碎片化 (MultiMech + Frag)
   3.3 安全工具不变性 (SafeInv: FNR 版)
   3.4 FNR-Gap 与 pIIA (诊断/部署探针区分)

4. Authorization-Conditioned Risk Accounting
   4.1 引理 1：未授权效果 FNR → unsafe-allow 下界 [β_auth−α_auth]₊
   4.2 定理 2：稀有工具-效果/授权违规组合的验证样本复杂度 Ω(1/q)
   4.3 命题 1：域距离上界 (DA bound, 含正类条件距离注记)

5. Experiments
   5.1 部署探针 vs LOTO：覆盖缺失导致 FNR-Gap (定理 2+1 验证)
   5.2 pIIA 干预式诊断：L24 探针方向干预，6 效果完整表
   5.3 pIIA-Drop 与 FNR-Gap 的趋势关联 (ρ=0.77, p=0.072, n=6)
   5.4 命题 1 经验检验：156 工具对 + Frag 余弦距离分析
   5.5 多模型对比 (MiniLM → Qwen3)

6. Discussion
   - 表面形式 vs 因果后果：碎片化不在均值中
   - 工具使用训练为何部分有效（改善 tool_error，未改善 content_fetched）
   - 本文以工具切换为原型实例；框架泛化到上下文注入、语义重框定等维度
   - 对可证明安全框架的设计约束：表征层诊断是所有行为层防御的前提
   - 与 AttriGuard/ARGUS/ClawGuard 的互补关系
   - 局限与未来工作

Appendix: 定理证明、完整实验表格、LOTO/DirRank/pIIA 实现细节
```
