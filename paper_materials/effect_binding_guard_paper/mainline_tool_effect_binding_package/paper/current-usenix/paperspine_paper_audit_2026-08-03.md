# PaperSpine 论文状态审核报告（2026-08-03）

审核方式：按 PaperSpine skill 流程（resume-first progress_check → latex_guard → 完整性/禁令/数字核验）
审核对象：`paper/current-usenix/main.tex` + `sections/` + `appendix/`（USENIX Security 2027 候选）

---

## 0. PaperSpine 工作流自身状态（Resume-first 检查）

```text
progress_check.py paper_rewriting_output → Next stage: intake
Action: Output directory does not exist. Start from intake.
```

- `paper_rewriting_output/` **不存在**：本项目从未运行过 PaperSpine 写作工作流
  （research/citation/motivation/planning 等阶段产物均无）。
- 含义：本次是"对现有论文做状态审核"，不是启动完整重写流程。
  PaperSpine 各 gate（intake→research→citation→motivation→planning→integrity→latex→final_audit）
  在本项目仍处于**未初始化**状态；若后续要按 PaperSpine 全流程重写论文，需从 intake 开始。

## 1. 论文本体结构审核

| 项 | 结果 | 说明 |
|---|---|---|
| 主文件 | `main.tex`（49 行壳）+ 11 个 `sections/*.tex` + 4 个 `appendix/*.tex` | `\input` 组织，结构清晰 |
| `\title`/`\maketitle` | ✅ 存在 | `Binding Agent Tool Calls to Effects: Counterfactual Contracts for Pre-Commit Mediation` |
| 顶层 section 数 | 10 个（Introduction→Conclusion） | 超过 PaperSpine section_economy 建议的 4-6；安全论文惯例可辩护，但可考虑合并 Experimental Setup/Evaluation Methodology |
| 单文件快照 `main_single.tex` | ⚠️ **已过期** | 07-30 生成（1776 行），与最新 `sections/` 差异 1653 行，缺 `agentlab` 引用；`main_single.pdf`（07-30）亦旧。**提交/共享前勿用 main_single，或重新生成** |
| 最新 PDF | ✅ `main.pdf`（08-03 11:45） | 与 `main.bbl` 同步 |

## 2. 引用安全（latex_guard）

- `latex_guard.py main.tex --bib references.bib`：**Errors 0，Warnings 0** ✅
- bib 覆盖：34 个 bib 条目，34 个被引用 key，**无未引用条目、无缺失条目** ✅
- 引用机制：`\cite{key}` + `\bibliographystyle{plain}` + `\bibliography{references}`，无手写 `[1]` ✅

## 3. 内容卫生（integrity 类检查）

| 检查 | 结果 |
|---|---|
| TODO/FIXME/占位符/lorem | ✅ 无 |
| 元语言泄漏（reviewer/supervisor/"reorganized"等） | ✅ 无 |
| 命令/过程叙述混入正文（A→B→C 转写） | ✅ 未见 |

## 4. 交接文档禁令遵守（项目特有硬约束）

| 禁令（08-02 交接 §7.5 / claim map 08-03） | 结果 |
|---|---|
| Round 1--5 atom specificity 正面差异不得引用 | ✅ 正文零命中（`atom-specificity`/`shuffled`/`specificity` 均无） |
| "atom prompt 自身提升安全推理"不得写 | ✅ 零命中 |
| "低 ASR 主要由 atom 粒度产生"不得写 | ✅ 零命中 |
| 321-case closed-loop 必须带适用性子集边界 | ✅ `results.tex` 明确写 "attribution on an applicability subset, not a full-benchmark estimate"；`experimental_setup.tex` 写 "not benchmark-wide" |
| v17 全量结果未完成前不得用 full 数字 | ✅ Abstract 使用 E78 的 54/627→2/627（已在 claim map 收录），未出现 v17 全量声称 |

## 5. 数字-真源核验（抽查全部通过）

| 论文声称 | 真源文件 | 核验 |
|---|---|---|
| ASR 54/627 → 2/627，benign 63→33/97 | `analysis/results/e78_capacity_matched_statistics.json` | ✅ no_guard 54/627、method 2/627；63→33/97 精确一致 |
| 321-case：whole-call 3/273 vs atom 0/273；attack utility 49/273 vs 57/273；benign 相同 | `representation-closed-loop-attribution/closed-loop-attribution-report.json` | ✅ 3 vs 0；49/273=0.1795 vs 57/273=0.2088 精确一致 |
| 303 saved AgentLAB：95→0，utility 180→87，1,439 匹配 | `agentlab-saved-transfer-{no-guard,e77}-results.json` | ✅ 95→0；180(99+38+11+32)→87(49+7+1+30) 精确一致 |
| 339 calls / 100 effects / 17 compound / 13 cross | `agentdojo-tool-effect-prevalence-report.json` | ✅ n=339；rate 0.295→100/339；0.17→17/100；0.13→13/100 精确一致 |
| 118 pairs / 41→0（finite-domain 与 held-out） | claim map 已收录对应 report | ✅ claim map 行存在，数字与论文一致 |

## 6. 与当前实验进度的时序合规

- v17 726 全量仍在运行（travel 阶段）→ 论文未抢跑 full 数字 ✅（符合协议 §13 "不得先改摘要再等待结果补数"）
- 严格表示归因协议仍为 `protocol-draft`（v17 finalizer 通过后才冻结）→ 论文的 321-case 仅作机制 witness + 适用性子集 ✅
- 论文更新（Phase D）尚未开始——**按协议顺序，现在不动论文正文是正确状态**

## 7. 风险与建议

| # | 级别 | 内容 | 建议 |
|---|---|---|---|
| 1 | 中 | `main_single.tex`/`main_single.pdf` 过期（缺 agentlab cite、1653 行差异） | 提交/共享前删除或重新生成；以 `main.tex` 为唯一真源 |
| 2 | 低 | 10 个顶层 section 超过 PaperSpine economy 预算 | 若目标会议要求紧凑正文，可考虑合并 Evaluation Methodology 与 Experimental Setup；USENIX 下可辩护，不强制 |
| 3 | 信息 | PaperSpine 工作流未初始化（`paper_rewriting_output/` 缺失） | 若用户要启动完整 PaperSpine 流程（intake→research→citation→motivation→rewrite），需先运行 intake wizard 创建配置并确认动机；本次仅为审核 |
| 4 | 信息 | v17 完成后须按协议 §13 顺序更新论文（Evaluation protocol → Results → analysis → Abstract → claim map → reproduction） | 已由 08-03 交接文档 Phase D 承接 |

## 8. 结论

- **论文本体状态：健康**。结构完整、引用安全（latex_guard 0/0）、无禁令违规、
  无内容卫生问题，Abstract/Results 的关键数字与真源 JSON 逐项一致。
- **主要待办**：(1) 清理过期 `main_single.*`；(2) 等 v17 完成 + 严格归因协议冻结后，
  按协议 §13/§14 顺序执行论文更新（Phase D）。
- **PaperSpine 流程**：若后续用 skill 全流程重写，当前为 `next_stage=intake`，需用户确认后启动。
