# Path A 收敛分析：外部文献格局与项目定位

> 日期：2026-05-22
> 目的：搜索最新文献后，确认 Path A（evaluation/diagnostic paper）的具体定位、与外部工作的边界、以及规划文档需修改的方向。

## 1. 外部文献格局

### 1.1 直接竞争方向：provenance/effect-trace monitoring（最拥挤）

2026年4-5月密集出现的核心工作：

| 工作 | 时间 | 核心机制 | 与我们的关系 |
|------|------|----------|-------------|
| **PACT** (2605.11039) | May 2026 | argument-level provenance + capability contracts | 比我们更细粒度，做authority binding |
| **Alignment Contracts** (2605.00081) | Apr 2026 | formal effect-trace semantics + monitor enforcement + Lean 4 proofs | 直接定义了与我们A(c)类似的allowed/forbidden effects |
| **ARM** (2604.04035) | Apr 2026 | provenance graph + counterfactual edges for causality laundering | 比我们更关注causal provenance |
| **Parallax** (2604.12986) | Apr 2026 | cognitive-executive separation + adversarial validator | 架构分离，98.9% attack block |
| **AgentTrust** (2605.04785) | May 2026 | runtime interception + allow/warn/block/review | 300+630 scenarios, 95-96.7% accuracy |
| **ECA** (2605.19192) | May 2026 | evidence-carrying certificates, hallucination→action gate | typed certificates from verifiers |

**关键判断**：Effect-trace monitoring / runtime interception 正在成为红海。如果我们以"又一个 verifier-assisted monitor"投稿，novelty 会被这些工作严重稀释。Alignment Contracts 的 formal effect-trace semantics 和我们的A(c)/Omega(a,t)框架在概念层面重叠度很高。

### 1.2 相邻但不重叠的方向

| 方向 | 代表工作 | 我们与之的差异 |
|------|---------|-------------|
| Agent safety benchmarks | AgentDojo, ToolEmu, AgentHarm, ASB, ST-WebAgentBench, TraceSafe, AgentHazard | 我们不做benchmark，不靠规模竞争 |
| Causal attribution (why a call happened) | AttriGuard, CausalArmor, ARGUS | 我们关注"实际发生了什么effect"，不是"为什么产生call" |
| Runtime defense | ClawGuard, AgentTrust, Parallax | 我们不做deployment system |
| Representation-level safety | AIR (ICML 2026), OPCT, FARS, S2C | 这些关注refusal/safety alignment的表面形式脆碎性，不关注tool-call effect representation |

### 1.3 我们最独特的资产（外部文献中找不到对应物）

1. **Linear-probe-based surface-form fragmentation diagnosis for tool-call effects**：
   - "Beyond the Black Box" (May 2026) 用probes做pre-action tool monitoring，但是做tool-need/tool-risk二分类，不做cross-tool effect generalization。
   - "Necessity Check for Linear Safety Probes" (LessWrong 2026) 强调projective ablation作为causal test，但没有cross-tool split概念。
   - **没有其他工作**在做"同一个causal effect在read_file/write_file/browser/terminal等不同tool surface下的表征是否一致"这个问题。

2. **Authorization-conditioned realized-effect monitoring (Auth-SafeInv)**：
   - Alignment Contracts 定义了类似的allowed/forbidden effects但没有operationalize成可评估的探针指标体系(FNR/ToolProxyGap/pIIA)。
   - PACT做authority binding但不做effect-level probe evaluation。

3. **Pure representation repair gate failure (三个gate failure的负结果链)**：
   - T54: strict contrastive coverage 21/21但FNR=0.2804 > best baseline 0.1835
   - T55: pair-free schema-conditioned monitor FNR=0.4516
   - T56: pure decomposed frozen verifier FNR=0.3547
   - 大多数方法论文不会报告这种方法gate failure，这是很强的诚实信号。

4. **三层高估证据（tool-surface → trace-label → row-to-action）**：
   - Layer 1: LOTO tool-surface fragmentation（max FNR=0.8036）
   - Layer 2: T69 label-hidden/minimal-evidence 退化（FNR 0.0353→0.1162→0.1465）
   - Layer 3: T68/T73 row-level→action-level 断裂（FDeny=1.0, all-allow collapse）
   - **没有任何其他工作系统展示了这三层高估**。

## 2. Path A 的具体定位

### 2.1 推荐论文类型

**Evaluation/diagnostic paper with a positive framework contribution** — 不是纯benchmark paper，也不是纯方法paper，而是：

> We introduce Auth-SafeInv as an action-level evaluation target, diagnose three layers of over-optimism that make current monitoring evaluation overstate safety, and provide a verifier-assisted monitoring framework as constructive evidence of what rigorous evaluation requires.

### 2.2 核心贡献（四个）

1. **Auth-SafeInv evaluation target**：定义authorization-conditioned realized-effect monitoring为可操作的评估对象，包含A(c)、Omega(a,t)、U(c,a,t)的形式化定义。

2. **Surface-form fragmentation diagnosis**：用线性探针+LOTO split系统展示同一causal effect在不同tool surface下的FNR退化。这是前面外部文献中没有的representation-level发现。

3. **Three-layer over-optimism evidence**：
   - Tool-surface layer: LOTO FNR up to 0.80
   - Trace-label layer: label-hidden degrades from full-label
   - Action-level layer: row-level 0/0 FNR/FPR ≠ action-level safety

4. **Constructive framework (EffectVerif-AuthMonitor) with honest limits**：
   - Verifier-assisted monitoring在controlled setting下可行（T64 FNR/FPR=0/0）
   - 但action-level calibration未解决（T73 all-allow）且raw-status boundary competitive（T70）
   - Pure representation repair gate failed

### 2.3 论文叙事结构

```
1. Problem: Agent safety monitors need to check realized effects against authorization
2. Diagnostic method: Linear probes + LOTO/pIIA for surface-form fragmentation
3. Finding 1 (Layer 1): Tool-surface fragmentation causes coverage-missing FNR
4. Finding 2 (Negative): Pure representation repair fails (3 gate failures)
5. Finding 3 (Layer 2): Full-label traces overstate safety vs. label-hidden traces
6. Finding 4 (Layer 3): Row-level metrics overstate safety vs. action-level metrics
7. Constructive: EffectVerif-AuthMonitor framework with T64/T65 evidence
8. Limits: Static verifiers fail on provider/browser effects; action-level calibration unsolved
```

### 2.4 与外部文献的差异表述（一句话）

> Unlike provenance-trackers (PACT, ARM) that trace argument/data origin, runtime interceptors (AgentTrust, Parallax) that block calls pre-execution, or benchmarks (AgentDojo, TraceSafe) that measure attack success, we ask: *given a tool call has been made, can a low-complexity representation readout detect what causal effects it actually realized, and is this detection invariant to the tool surface form used?*

## 3. 各规划文档需要修改的关键点

### 3.1 `后续推进规划.md`

- **Section 0.1-0.2**：主线从"causal task consistency强主张"改为"Auth-SafeInv evaluation target + three-layer over-optimism diagnosis + constructive framework"
- **Section 0.3**：贡献组织从层级式改为四贡献结构
- **P9**：从"CEG-Auth方法论文"改为"Path A evaluation paper"，明确T74-T80的Path A版本
- **T74**：论文重写为evaluation paper主线
- **T75**：删除CEG-Auth设计文档作为独立任务（已有设计文档保留为参考）
- **T76**：label-hidden/minimal-evidence上升为主结果（保留）
- **T77**：action-level calibration从"必须解决"改为"作为limitation + future work"
- **T78**：provider-backed traces从"必须做"改为"如果资源允许做，否则写成明确limitation"
- **T79**：统计审计（保留）
- **T80**：理论/pIIA/contrastive降权（保留）
- **新增T81**：与外部的差异矩阵更新（包含PACT/Alignment Contracts/ARM/AgentTrust等新发现工作）

### 3.2 `AuthSafeInv理论补强后续规划.md`

主要更新：
- 开头加入Path A决策说明
- T45状态从"BLOCKED for strong pure-method claim"改为"converging to evaluation/diagnostic paper"
- 不再把CEG-Auth写入本文档（或只在末尾作为future work提及）

### 3.3 `外部审稿意见v1采纳与后续规划.md`

主要更新：
- P6更新：外部有效性不再追求provider-backed traces作为必须项，而是作为明确的limitation写入
- 新增P7：将最新文献(PACT, Alignment Contracts, ARM, AgentTrust等)纳入difference matrix

## 4. 不做的事

1. **CEG-Auth不进入主文**：作为方法contribution的时机未到。graph novelty不够，action-level policy未解决，外部validity不足。可保留设计文档在analysis/作为future work。
2. **CEG-Auth不重写为"只是graph representation"**：已有设计文档已明确graph不是novelty。
3. **不追求provider-backed traces作为必须项**：如果资源允许就做(T78)，但不block投稿。
4. **不把action-level calibration写成已解决**：T73是负结果，论文中作为limitation。
5. **不声称verifier-assisted monitoring优于所有已有defenses**：T70 raw-status boundary competitive，方法边界应诚实写。

## 5. 修订后的任务优先级

| ID | 任务 | Path A优先级 | 说明 |
|----|------|------------|------|
| T74 | 论文重写为evaluation paper | P0 | 最大工作量，改变整篇论文叙事 |
| T79 | 统计审计升级 | P0 | 所有主表补N+/N-/CI/threshold/seed |
| T76 | label-hidden/minimal-evidence变主表 | P0 | 当前最重要的实验升级 |
| T81 | 更新外部文献差异矩阵 | P0 | 加入PACT/Alignment Contracts/ARM等 |
| T80 | 理论/pIIA/contrastive降权 | P1 | 理论改framing，pIIA改diagnostic |
| T70-refine | raw-status boundary honest comparison | P1 | 把competitive baseline写成优势而非弱点 |
| T77 | action-level calibration limitation | P2 | 从"必须解决"降为"写进limitation" |
| T78 | provider-backed traces | P3/resource | 如果有资源做，否则写成limitation |
| CEG-Auth | 不进入本轮 | — | 保留设计文档，未来工作 |

## 6. 投稿策略

- **当前版本**：不投主会。
- **Path A完成后**：可投 NeurIPS 2026 / ICLR 2027 / ICML 2027。
- **适合的venue类型**：接受evaluation/analysis/diagnostic贡献的顶会。NeurIPS D&B track也合适（Auth-SafeInv作为新的evaluation target）。
- **竞争风险**：PACT和Alignment Contracts的工作如果也定义了类似的effect authorization概念，需要在related work中明确区分（他们做formal enforcement/contracts，我们做representation-level diagnosis + evaluation framework）。
