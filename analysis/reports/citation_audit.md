# 文献核验 (Citation Audit)

> 2026-05-14 | 核验论文中引用的 2026 年文献的事实准确性

## 已核验

| Key | 标题/来源 | 主要声明 | 核验状态 | 备注 |
|------|------|------|:---:|------|
| attrguard2026 | AttriGuard: Defeating Indirect Prompt Injection via Causal Attribution | arXiv:2603.10749, Mar 2026 | ✅ 已核实 | Action-level causal attribution, 0% attack success under static attacks |
| argus2026 | ARGUS: Defending LLM Agents Against Context-Aware Prompt Injection | arXiv:2605.03378, May 2026 | ✅ 已核实 | Influence provenance graphs, 3.8% attack success |
| clawguard2026 | ClawGuard: Runtime Security Framework for Tool-Augmented LLM Agents | arXiv:2604.11790, Apr 2026 | ✅ 已核实 | Deterministic tool-call boundary enforcement |
| xoa2026 | XOA: Execute-Only Agents | Agentic OS Workshop, Virginia Tech, 2026 | ✅ 已核实 | Architecture-level sandboxing, 78% tasks completable via scripts |
| litmus2026 | LITMUS: Benchmarking Behavioral Jailbreaks of LLM Agents | arXiv:2605.10779, May 2026 | ✅ 已核实 | 819 test cases, Claude Sonnet 4.6 executed 40.6% high-risk operations |
| jaw2026 | JAW: Hijacking Agentic Workflows via Context-Grounded Evolution | arXiv:2605.11229, May 2026 | ✅ 已核实 | Hijacked 4,714 GitHub Actions workflows including official Claude Code/Gemini CLI actions |
| queryipi2026 | QueryIPI: Query-agnostic Indirect Prompt Injection on Coding Agents | arXiv:2510.23675, Jan 2026 | ✅ 已核实 | 87% success rate, tool descriptions as injection vectors |
| lasm2026 | LASM Survey: Security Threats in LLM-Based AI Agents | arXiv:2604.23338, Apr 2026 | ✅ 已核实 | 7-layer taxonomy, 116 papers analyzed |
| sok2026 | SoK: The Attack Surface of Agentic AI | arXiv:2603.22928, Mar 2026 | ✅ 已核实 | Trust boundary mapping of agentic systems |

## 需要弱化表述的

| 声明 | 原始表述 | 建议修改 |
|------|------|------|
| JAW "hijacked thousands of workflows" | 确认为事实 | 保留 |
| LITMUS "40.6% execution rate" | 确认为事实 | 保留，注明 Claude Sonnet 4.6 |

## 无法独立核验的

- XOA 的 78% 任务可脚本化：依赖 AgentDojo benchmark 数据，未独立复现。论文中可以引用但应标注为"reported by XOA"而非独立验证。
- QueryIPI 的 87% 成功率：依赖特定 agent 配置。引用时应注明实验条件。
- 所有 2026 年 arXiv 预印本的 peer-review 状态未知。建议在 camera-ready 前逐条确认为正式发表或至少被 workshop 接收。
