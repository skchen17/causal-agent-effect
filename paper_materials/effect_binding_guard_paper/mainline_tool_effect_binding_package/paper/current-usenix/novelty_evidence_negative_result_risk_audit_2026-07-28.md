# 创新点、证据与负面结果审稿风险审计

日期：2026-07-28  
审计对象：`paper/current-usenix/`

范围：核验截至该日期公开且与本文最接近的 2025--2026 年论文，重点覆盖
tool-call authorization、argument provenance、effect contracts、
counterfactual attribution、commit-time enforcement 和 temporal/effect
trace policies；这不是对所有 agent-safety 预印本的穷尽性系统综述。

## 结论

当前工作仍有可区分的论文核心，但必须采用窄口径：

> 一个工具调用可能产生多个需要独立授权的效果实例；监控表示必须保留
> authorization-equivalence classes。源代码执行与反事实干预可以在注册前发现
> 将授权不等价执行合并在一起的效果表示。

如果把创新写成“细粒度工具授权”“参数级 authority binding”“pre-commit
guard”“effect sink”或“用反事实抵御注入”，与 2025--2026 年公开工作高度
重合，原创性风险为高。可保留的差异是：

1. **表示单位是 committed effect occurrence，而不是 tool、call 或 argument。**
   一个参数可参与多个效果，一个效果也可由默认值、前置状态或展开产生。
2. **验证目标是表示充分性。** 反事实用于寻找“具体安全效果已变、授权应变、
   但表示未变”的可执行反例，不用于判断调用为什么被模型提出。
3. **理论对象是 authorization equivalence。** 论文给出表示碰撞的不可避免
   错误下界，以及严格限定在枚举域内的充分性结论。

该区分具有论文价值，但目前不是低风险 USENIX 投稿状态。理论和问题证据基本
成立，主要风险转移到外部有效性、授权接口覆盖、效用和最近邻方法对比。

## 与 2025--2026 年最近工作的重合度

| 工作 | 与本文重合 | 可辩护差异 | 风险 |
|---|---|---|---|
| PACT, arXiv:2605.11039 | granularity mismatch、authority binding、argument contract、provenance、确定性运行时检查、AgentDojo | PACT 的单位是参数角色及参数值来源；本文单位是执行后效果实例，并覆盖一参多效、默认值、前置状态、展开和重复效果 | **高**。不得声称首次提出粒度错配、authority binding 或 provenance-aware contract |
| ContractGuard, arXiv:2606.18550 | effect contract、effect integrity、运行时效果验证、contract 是承重假设 | ContractGuard 防止合约被篡改；本文测试一个干净固定合约是否在语义上合并授权不等价执行 | **高**。必须明确 integrity 与 semantic sufficiency 的不同 |
| Commit-time authorization, arXiv:2607.10487 | durable effect、commit boundary、same-effect binding、fail closed | 该工作研究授权 witness 的 freshness/eligibility；本文研究一个调用的效果分解是否充分 | **高**。不得把 commit-time/effect binding 边界本身作为首创 |
| Alignment Contracts, arXiv:2605.00081 | observable effects、effect traces、scope、budgets、formal monitor guarantee | 该工作给定可观察效果字母表后表达时序策略；本文检验 call-to-effect abstraction 是否保留授权区分 | 中高。理论中 effect observability 与本文 O1 明显相邻 |
| AuthGraph, arXiv:2605.26497 | provenance 与 authorization 对齐、参数源偏差、AgentDojo | AuthGraph 检测执行来源图相对用户意图图的偏离；本文比较具体状态变化与效果表示的关系 | 中高。不得声称首次结构化对齐 provenance/authorization |
| SecureClaw, arXiv:2606.09549 | effect sink、PREVIEW--COMMIT、exact canonical request、trusted executor | SecureClaw 的写边界以 canonical request 为授权对象；本文进一步询问该 request 是否隐藏多个独立效果 | 中高。运行时架构不是主要新意 |
| ScopeGate, arXiv:2606.28679 | concrete-value per-call authorization、PDP/PEP、default deny | ScopeGate 审计框架默认缺口并检查调用值；本文检验调用值到效果实例的语义映射 | 中。不得声称首次进行 per-call value authorization |
| Progent, arXiv:2504.11703 | task-scoped privilege、工具名/参数规则、运行时确定性检查、权限扩张 | Progent 关注权限策略生成和单调更新；本文关注效果表示是否足够表达策略需要区分的执行 | 中 |
| MiniScope, arXiv:2512.11147 | least privilege、工具/API 权限映射、非 LLM 仲裁 | MiniScope 重建权限层级；本文验证具体调用的复合状态变化是否需要进一步拆分 | 中 |
| Contract2Tool, arXiv:2606.07904 | tool preconditions/effects、从 schema/docs/traces 学习 contract | Contract2Tool 为规划和过滤学习效果；本文把效果描述视为安全假设并用授权分离执行反例证伪 | 中高，术语重合明显 |
| AttriGuard, arXiv:2603.10749 | counterfactual、tool-call runtime defense、AgentDojo | AttriGuard 干预外部观察并重跑 agent，判断调用是否由用户意图支持；本文干预参数/状态并执行工具，判断效果表示是否保留授权区分 | 中。不要使用未限定的“causal attribution”描述本文 |
| CausalArmor, arXiv:2602.07918 | leave-one-out causal ablation、注入归因 | 其对象是上下文片段对动作选择的影响；本文对象是调用/状态对具体效果关系的影响 | 低中 |
| Agent-C, arXiv:2512.23738 | formal runtime enforcement、轨迹约束 | Agent-C 检查动作顺序和时序策略；本文主要是 per-commit extensional effect bound | 低中。累计配额和历史谓词不要扩张成主要主张 |
| CaMeL/IPIGuard | 控制/数据分离、结构化工具执行与依赖 | 本文不隔离模型推理，而在效果提交前检查独立效果 | 低中 |
| ToolSafe/Safiron | 执行前 step/call guard | 本文不以模型分类输出作为最终授权，并检查复合效果表示 | 低 |

公共元数据来源：  
[PACT](https://arxiv.org/abs/2605.11039)；
[ContractGuard](https://arxiv.org/abs/2606.18550)；
[commit-time authorization](https://arxiv.org/abs/2607.10487)；
[Alignment Contracts](https://arxiv.org/abs/2605.00081)；
[AuthGraph](https://arxiv.org/abs/2605.26497)；
[SecureClaw](https://arxiv.org/abs/2606.09549)；
[ScopeGate](https://arxiv.org/abs/2606.28679)；
[AttriGuard](https://arxiv.org/abs/2603.10749)；
[Contract2Tool](https://arxiv.org/abs/2606.07904)。

## 创新声明与实验支持

| 创新声明 | 现有主要证据 | 支持程度 | 不能推出的结论 |
|---|---|---|---|
| 一个调用会包含多个独立授权效果，常见表示会发生授权碰撞 | E85 common projection 65/80；56-call common contract 有 118 separating pairs；ToolSandbox common fields 有 41 pairs | **强但有限域** | 不能证明所有现实工具普遍如此，也不能给出部署流行率 |
| 表示碰撞使仅依赖该表示的确定性监控器无法同时安全且允许合法调用 | `sections/security_analysis.tex`、`appendix/formal_proofs.tex`；E48/E50 collision audit | **理论强，经验实例化强** | 定理本身是条件性不可区分论证，不证明 effect oracle 或 authority 正确 |
| 反事实执行可在注册前发现不充分的 effect contract | E85 在 payload/time/recurrence/interaction/default 上发现 15 个 gap；E50 暴露 resource/auth failure | **强 falsification 证据** | 找不到反例不等于开放域证明；当前干预覆盖仍有限 |
| typed effect occurrence 可消除已观察碰撞 | 56-call typed contract 0 pairs；预注册 ToolSandbox 32 contexts/5 tools 上 common fields 41→0 | **中强的 bounded evidence** | AgentDojo typed 修正 80/80 是同数据 post-hoc；ToolSandbox 规模小，不能称任意工具迁移 |
| 运行时 complete mediation/check-use 路径有效 | 3,173/3,173 executed signatures 匹配；blocked call 未到 sandbox executor | **强的 sandbox-local 实现证据** | 不证明远端并发服务、恶意工具、TOCTTOU 或 host compromise |
| effect-level guard 能降低注入攻击成功 | Qwen3-32B AgentDojo ASR 53/629→3/629；cluster-aware 区间不跨 0 | **强的单模型安全效果** | 不证明跨模型、生产环境或 Pareto 优势 |
| 资源/授权绑定是关键瓶颈 | E50 UPA 46/120；去 resource 为 .617，去 authorization 为 .892 | **中强机制证据** | custom stress 不能估计真实发生率；新 PACT-compatible 对照只检验表示粒度，不比较完整授权系统 |
| 当前系统在安全与效用之间具有有竞争力的总体优势 | BU 64/97→33/97，UA 342/629→207/629；Prompt Sandwiching BU .619/ASR .013 | **不支持** | 只能说显著降低攻击并付出较大效用成本，不能说全面优于强基线 |
| authorization infrastructure 已经可扩展 | 44/97 manifest 通过审查，只有 26/97 可编译；full-benign 26/97 | **反向证据** | 当前结果表明 O2 接口尚未解决 |

主要证据索引见 `claim_to_source_map.md`；机器可读数字见
`reproduction/current_evidence.json`（341 rows，full-benign utility gate
保留为 failed）。

## 负面结果与审稿风险

### 高风险

1. **良性效用从 66.0% 降到 34.0%。**  
   Prompt Sandwiching 为 BU 61.9%、ASR 1.3%，而本文为 BU 34.0%、ASR
   0.5%。本文并非被严格支配，但审稿人很容易认为安全收益不足以补偿效用损失。
   正确口径是“security gain with a severe utility cost”，不能写
   “better security--utility tradeoff”。

2. **授权接口只覆盖 26/97。**  
   full-benign 中 152/426 checks abstain，107 次因为缺 manifest，43 次因为
   resolver 未证明；预注册 50-task utility gate 失败。这直接攻击核心前提 O2：
   系统不是只差工程优化，而是尚未展示 authority source 可规模化构建。

3. **最近邻 PACT 的系统结果更强且范围更广。**  
   PACT 报告五个模型并在最强三个模型达到 100% security、38.1--46.4%
   utility。本文只有一个 32B 主模型。现已加入 literal
   PACT-L2-compatible representation baseline：最大参数视图在 56 条
   fresh-state AgentDojo 调用上无碰撞，但在 32 条 ToolSandbox contexts
   上仍有 4 个混合单元和 13 个 separating pairs；typed effect
   occurrence 为 0。该结果支持 state-dependent effect granularity 的窄
   区分，但不是 PACT 代码、自动推断、policy 或 benchmark reproduction，
   因而不能替代完整系统横向比较。

4. **主结果存在 12 条 context-capacity repair。**  
   714-key sensitivity 保留主方向，但剔除规则由本文方法的失败决定，不能替代
   相同上下文的 726-case 主结果。该问题会被质疑为 protocol asymmetry。

5. **长任务 E79 仍不可评估。**  
   当前 `agentlab-saved-transfer-e77-results.json` 为
   `incomplete_or_failed`，ASR/utility 为 null。任何 long-horizon、
   trajectory safety 或跨环境效用声明都必须继续从 PDF 排除。

### 中高风险

6. **typed correction 的 AgentDojo 80/80 是 post-hoc。**  
   ToolSandbox 预注册 32-context 结果缓解了 circularity，但规模不足以支持
   自动合约生成或开放域 soundness。

7. **bounded adaptive 结果不显著。**  
   4/40→1/40 的 McNemar `p=.375`，terminal utility 18/40→12/40。
   只能作为 sensitivity，不能写 adaptive robustness。

8. **消融大部分开关适用样本太少。**  
   A2/A7 只有 17/7 个 checks，A13 为 0；只有 registry validation 对效用的
   影响有较清晰证据。当前实验不能证明全部设计组件必要。

9. **E47/E48/E50 主要是 custom stress。**  
   它们适合给出反例和机制诊断，不适合声称现有方法在原始 benchmark 上失败，
   也不能估计现实系统中的 prevalence。

10. **有限域 oracle 和 review 仍可能漏效应。**  
    constant、async、callback、remote 和 malicious-tool effects 未覆盖；
    当前 ToolSandbox review 也不是独立人类认证。

### 中风险

11. **端到端耗时只具描述性。**  
    53.27s→85.54s、paired ratio 1.36 来自顺序运行且混入 12 条修复；只能报告
    observed trajectory duration。22.1--352.0 微秒只代表 deterministic kernel。

12. **默认值机制几乎没有 benchmark applicability。**  
    AgentDojo 的 22 个 optional fields 只有 empty/`None` defaults。论文可以
    把 dynamic defaults 作为设计必要性，但不能说实验已经验证。

13. **baseline 多为 local adapters。**  
    当前表格已正确声明不是原论文复现，但这降低了横向性能结论的力度。

14. **artifact 尚不具备投稿可用性。**  
    Open Science appendix 缺匿名稳定 URL，release manifest 过期。这是投稿
    完整性问题，不是方法正确性问题。

## 投稿口径建议

### 可保留

- “We identify authorization-separating representation collisions.”
- “One call can realize multiple independently authorizable effect
  occurrences.”
- “Source-executed interventions falsify candidate call-to-effect
  abstractions.”
- “The typed contract is sufficient on the enumerated finite domain.”
- “The runtime sharply reduces AgentDojo attack success, with substantial
  utility and authority-coverage costs.”

### 必须避免

- first fine-grained/argument-level/tool-call authorization；
- first authority binding or effect-sink enforcement；
- first causal/counterfactual agent defense；
- open-domain contract soundness；
- production/deployed safety；
- Pareto-superior security--utility；
- adaptive robustness；
- complete trajectory confinement without residual authority and long-horizon
  evidence。

## 投稿前优先级

1. **已完成的最近邻表示对照：**56-call 与 ToolSandbox finite domains 已加入
   reviewed PACT-L2-compatible `argument role + value + provenance` 表示。
   fresh-state AgentDojo 域不能区分两种表示；ToolSandbox 中同参数、不同
   pre-state 的 9 个 witness 使最大参数视图保留 13 个 separating pairs，
   typed effect occurrence 为 0。后续不得将其升级为完整 PACT 系统比较。
2. **修复主协议：**完成相同上下文/预算的 726-case 结果，或把当前 12-repair
   行明确降为 sensitivity。
3. **提高 O2 覆盖或降级定位：**若 manifest/runtime-ready coverage 不能明显
   提升，就把 runtime 定位为 feasibility prototype，把 representation
   validation 作为论文主贡献。
4. **第二模型：**在完全相同协议上复现主要安全/效用结果。
5. **只在严格 finalizer 通过后加入 E79。**
6. **保持负面结果：**不要删除 26/97、152 abstentions、非显著 adaptive 和
   post-hoc correction；这些结果应统一解释为 representation 与 authority
   infrastructure 的边界。

## 最终判断

- **原创性：**窄口径下为中高；宽口径下为低，且会与 PACT、ContractGuard、
  commit-time authorization 发生直接碰撞。
- **理论支持：**足以支撑有限域 representation-sufficiency 论文主张；不能独立
  支撑开放域安全。
- **问题证据：**足以证明问题存在并能构造真实代码路径反例。
- **系统证据：**足以证明 sandbox-local feasibility 和显著 ASR 降低。
- **综合 USENIX 风险：**当前为高。主要原因不是核心定理错误，而是 utility、
  authority coverage、单模型、protocol repair 和直接最近邻比较不足。
