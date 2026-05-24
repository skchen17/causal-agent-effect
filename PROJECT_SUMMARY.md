# Causal Agent Safety Research — 项目综述

> 日期：2026-05-22  
> 状态：Path A evaluation/diagnostic paper 路线确认，论文重组完成，规划文档已同步

---

## 一、项目概述

**核心研究问题**：在 LLM agent 安全中，表征是否以工具不变的方式编码了因果效果？如果不是，这对 agent safety monitoring evaluation 意味着什么？

**核心发现**：LLM agent 安全监控评估在三个层面系统性地高估安全性——
1. **工具表面层 (Layer 1)**：线性探针检测因果效果时依赖工具表面形式，覆盖缺失时 FNR 可达 0.80
2. **Trace 标签层 (Layer 2)**：结构化 trace 标签字段让 verifier 表现虚高，隐藏标签后 FNR 退化 3.3×–4.2×
3. **行为级层 (Layer 3)**：row-level FNR/FPR 指标与 action-level allow/deny 决策结构性脱节

**当前定位**：从多组件综合论文收敛为 **evaluation/diagnostic paper**，以 Auth-SafeInv 为评估目标，三层高估为核心诊断，EffectVerif-AuthMonitor 为建设性框架（带诚实边界）。

---

## 二、已完成工作

### 2.1 核心主线实验

| 模块 | 内容 | 关键结果 | 状态 |
|------|------|----------|:--:|
| 数据生成 | 规则模板 + LLM 合成 459 条场景，11 个因果效果，9 个工具 | 打破 tool→effect 确定性映射 | ✓ |
| 嵌入提取 | MiniLM (384d), Qwen2.5-7B (3584d), Qwen3-8B (4096d) | 三种模型嵌入矩阵 | ✓ |
| LOTO 诊断 | Leave-one-tool-out FNR stress test | Held-out FNR 最高 0.97，ToolProxyGap 最高 0.88 | ✓ |
| Lexical control | 替换工具名/[TOOL]、代码/[CMD]、URL/[URL] | 整体 FNR 仅从 0.378→0.382，非词汇捷径 | ✓ |
| pIIA | Probe-mediated interchange intervention，hook L24/36 | pIIA-Drop 0.052 (tool_error) – 0.366 (network_egress) | ✓ |
| pIIA controls | Random direction, matched-norm, wrong-form, layer sweep | 864 raw hook rows, Spearman pIIA-Drop vs FNR=0.53 | ✓ |
| Baselines | Pooled/Balanced/Tool-Cond/Group Reweight/Procrustes | 无方法消除 worst-form FNR | ✓ |
| Contrastive projection | 全训练 + strict LOPO + multiseed (seeds 0-4) | 全训练 post-FNR 0.00 on 5/6 effects; LOPO 40/68 improved | ✓ |

### 2.2 Mainconf v2 扩展

| 模块 | 内容 | 关键结果 | 状态 |
|------|------|----------|:--:|
| 数据扩展 | 408 条增量 + 65 条 static replay traces | 932 rows total, 7 P0 cells 全部 N+≥50 | ✓ |
| LOTO 重跑 | Mainconf v2 上重跑 LOTO/baseline/FNR | 最大 held-out FNR 0.8036 (file_content_read/read_file) | ✓ |
| Strict LOPO | 68 tool-case evaluations | 33 improved, mean ΔFNR=0.1044 | ✓ |
| Multiseed | 5 seeds full-training | max mean post-FNR=0.034 (observed-pair upper bound) | ✓ |
| 统计审计 | N+/N-/Wilson CI/threshold/seed audit | 27/44 cells N+<30 in original data | ✓ |
| Causal-chain v2 | 2290 samples, 5 conditions, typed wrong-chain | Mixed: 部分效果可被因果链文本改善，但不鲁棒 | ✓ |

### 2.3 Auth-SafeInv T38-T73

| 模块 | 任务 | 关键结果 | 状态 |
|------|------|----------|:--:|
| 形式化 | T38: A(c), Ω(a,S), U(c,a,S), SafeInv, Auth-SafeInv | 授权条件风险记账框架 | ✓ |
| 反事实数据 | T39/T53: authorization counterfactuals v1+v2 | 1464 rows, 7 focus effects unauthorized tools ≥3 | ✓ |
| Execution traces | T40/T49: controlled sandbox/observed traces | 138 traces (70 observed + 56 simulated + 12 static) | ✓ |
| Auth-SafeInv eval | T41/T54: held-out evaluation | Group-aware random/LOTO/family holdout | ✓ |
| Surface graph | T42: graph alignment analysis | 7 focus effects strict-identifiable post v2 expansion | ✓ |
| Strong baselines | T44/T47: 678 pilot + 504 confirmatory + 9408 curve rows | IRM-linear, supervised contrastive, domain-adversarial, abstention | ✓ |
| **Gate 1 (T54)** | Strict contrastive projection | LOTO FNR=0.2804 > best baseline 0.1835 ❌ | ✓ |
| **Gate 2 (T55)** | Pair-free schema-conditioned monitor | LOTO FNR=0.4516, 弱于 baseline ❌ | ✓ |
| **Gate 3 (T56)** | Decomposed frozen verifier | LOTO FNR=0.3547, 弱于 baseline ❌ | ✓ |
| Verifier upper bound | T56 verifier-present | Oracle present label → LOTO FNR=0.0042, family FNR=0.0745 | ✓ |
| Static verifier | T57: trace-calibrated deterministic rules | LOTO FNR=0.0262/FPR=0.073, beats T54 baseline | ✓ |
| Execution verifier | T58: controlled trace candidate-effect data | 1104 rows, schema-to-trace FNR=0.0429/FPR=0.0 | ✓ |
| Real-agent stress | T59: Hermes tool registry audit + local adapters | 74 registered tools, 48 traces, FNR=0.25/FPR=0.0 | ✓ |
| Provider API | T60/T61: DeepSeek API traces, 8→120 traces | 960 rows, exec verifier FNR=0/FPR=0, static FNR=1.0 | ✓ |
| Validation threshold | T62: validation-selected, held-out tested | T58 0/0, T59 0.1765/0, T61 0/0 | ✓ |
| Broader tools | T63: web/search/browser/messaging local adapters | 300 traces, 2400 rows, exec FNR=0.0351, static FNR=0.614 | ✓ |
| Live protocol | T64: real HTTPS + local webhook, full-precision | 300 traces, 2400 rows, exec FNR/FPR=0/0 (N+=197), static=0.629 | ✓ |
| Browser runtime | T65: headless Chrome file-backed DOM/JS | 120 traces, 960 rows, exec FNR/FPR=0/0 (N+=62), static=1.0 | ✓ |
| Action-level | T68: allow/deny aggregation | T61/T65 FDeny=1.0, row≠action metrics | ✓ |
| Trace ablation | T69: full/label-hidden/minimal-evidence | FNR 0.0353→0.1162→0.1465, structured evidence dependent | ✓ |
| Defense proxy | T70: pre-action/provenance/raw-status vs EffectVerif | Raw-status competitive (FNR 0.1113, FDeny 0.0265) | ✓ |
| Calibration | T73: action-level threshold diagnostic | All-allow collapse on T59/T61/T63/T65 (NEGATIVE) | ✓ |
| Reproducibility | T50: reproduction script + source appendix | 53-step reproduce_auth_safeinv.sh, all_outputs_present=True | ✓ |

### 2.4 论文

| 版本 | 内容 | 状态 |
|------|------|:--:|
| v1-v2 | Verifier-assisted controlled study 主线 | ✓ 已编译 |
| Path A v1 | 重组为 "three-layer over-optimism" evaluation paper | ✓ 已编译 |
| Path A v2 | 根据审稿意见修改：两贡献、SafeInv/Auth-SafeInv 区分、两阶段模型、verifier 同源诚实声明、action pipeline 解释、CI 标注 | ✓ 已编译 |

---

## 三、关键结论

### 3.1 可以稳健声称的

1. **SafeInv 失败是真实的**：线性探针对 causal effect 的检测在跨 tool surface 时不稳定。LOTO stress test 下 held-out FNR 可达 0.80 以上，lexical normalization 不消除，pIIA 提供收敛证据，三种模型 (MiniLM/Qwen2.5/Qwen3) 一致。

2. **纯表征修复不够**：三种表征侧方法 (contrastive projection, schema conditioning, decomposed frozen verification) 在 strict held-out 协议下均无法超越强 baseline。这是有统计支撑的诚实负结果。

3. **Trace label 高估是真实的**：full-label trace verifier 的 FNR 在隐藏标签字段后退化 3.3×–4.2×。这意味着依赖结构化 trace 字段的 verifier 评估可能高估真实性能。

4. **Row-level 指标不能替代 action-level 指标**：候选效果预测的逐行 FNR/FPR 与行为级 allow/deny 正确率之间存在结构性差异。row-FPR=0 可以与 action-FDeny=1.0 共存，simple calibration 可退化为 all-allow。

5. **Execution evidence 有帮助但有限制**：在受控设定下，execution-level evidence 可以显著降低静态规则无法检测的 effect miss。但 verifier 是 handcrafted 且与 trace generator 共享 schema，不应解读为方法性能估计。

### 3.2 不能声称的

- 部署级 agent safety certification
- 纯表征修复已解决问题 (gate failure)
- Verifier-assisted monitoring 优于所有已有防御 (raw-status baseline competitive)
- 三层高估广泛存在于已有 benchmark/defense 中 (只在我们构建的 controlled setting 中验证)
- LOTO degradation 完全归因于 representation-level fragmentation (domain shift 可能混杂)
- pIIA 是 causal proof (它是 probe-mediated diagnostic)
- Provider-backed search/SaaS messaging/HTTP browser automation/deployed-runtime 已覆盖

---

## 四、当前进展与下一阶段

### 4.1 已完成 (T0-T73, T75, Path A v1-v2)

全部实验和规划工作已完成。核心 artifacts 包括：
- 932-row mainconf v2 数据集和全部嵌入
- 1464-row Auth-SafeInv 反事实数据
- 8,988 trace-based candidate-effect rows (6 trace families)
- 三层高估的完整实验证据链
- 三个 gate failure 的统计支撑结果
- EffectVerif-AuthMonitor 框架设计和伪代码
- 53 步可复现脚本
- Path A 论文主文 (18 页) + 附录 (5 页)

### 4.2 进行中 (Path A 后续)

| ID | 任务 | 优先级 | 说明 |
|----|------|--------|------|
| T74 | Path A 论文定稿 | P0 | 在 v2 基础上最终润色，统一口径 |
| T76 | label-hidden/minimal-evidence 主实验代码整理 | P0 | 确保 T69 三种 view 可独立复跑 |
| T79 | 统计审计补全 | P0 | 所有主表补充 N+/N-/CI/threshold/seed |
| T81 | 更新外部文献差异矩阵 | P0 | 同步到 paper/main.tex 和 paper-path-a/main.tex |

### 4.3 待资源允许后启动

| ID | 任务 | 优先级 | 说明 |
|----|------|--------|------|
| T78 | Provider-backed traces | P3 | 需要 search/messaging/browser API key |
| T77 | Action-level calibration 解法 | Future | CEG-Auth 或其他 abstention/utility-aware policy |

### 4.4 投稿目标

- **当前状态**：不投主会
- **Path A 完成后**：NeurIPS 2026 / ICLR 2027 / ICML 2027
- **合适 track**：主会 (evaluation/analysis paper) 或 NeurIPS D&B

---

## 五、项目文件结构

```
causal-agent-safety-research/
├── paper/                         # 原版论文 (保留)
├── paper-path-a/                  # Path A 论文 (main.tex + appendix.tex)
│
├── src/                           # 实验脚本 (按功能分 8 类)
│   ├── data/         (6 files)    #   数据生成
│   ├── embeddings/   (3 files)    #   嵌入提取
│   ├── probes/       (3 files)    #   探针训练与泛化
│   ├── intervention/ (4 files)    #   IIA/pIIA 因果干预
│   ├── experiments/  (3 files)    #   Baseline / FNR / Lexical
│   ├── solutions/    (6 files)    #   Contrastive / Procrustes / Ablation
│   ├── auth/         (21 files)   #   Auth-SafeInv 数据构造与实验
│   └── causal_chain/ (1 file)     #   Causal-chain conditioning
│
├── analysis/                      # 分析与结果 (已重组为 9 个子目录)
│   ├── results/      (129 files)  #   实验 JSON + MD + JSONL + PNG
│   ├── manifests/    (48 files)   #   数据 manifest
│   ├── reports/      (23 files)   #   研究报告与解读
│   ├── planning/     (13 files)   #   规划与路线图文档
│   ├── scripts/      (14 files)   #   分析用 Python 脚本
│   ├── audits/       (11 files)   #   核验与完成报告
│   ├── reviews/      (7 files)    #   审稿意见
│   ├── appendix/     (4 files)    #   结果溯源 appendix
│   └── experiments/  (22 files)   #   按实验块归档的目的、结论和产物索引
│
├── data/                          # 场景数据集 (JSONL)
├── embeddings/                    # LLM 嵌入 (npy + meta.json)
├── probes/                        # 已保存的探针模型
├── notebooks/                     # Jupyter 探索
├── insights-and-papers/           # 早期调研文档
├── real-agent-tools/              # Hermes agent 工具注册参考
│
├── run_experiments.sh             # 主流水线一键入口
├── reproduce_auth_safeinv.sh      # Auth-SafeInv 53 步复现入口
├── run_all.sh                     # 简化入口
├── README.md                      # 项目说明
├── AGENTS.md                      # Agent 指令
├── CLAUDE.md                      # Claude Code 配置
├── PROJECT_SUMMARY.md             # 本文件
└── requirements.txt               # Python 依赖
```

---

## 六、核心实验数据速查

| 指标 | 数值 | 来源 |
|------|------|------|
| 原始数据集 | 459 scenarios, 11 effects, 9 tools | `data/scenarios_merged.jsonl` |
| Mainconf v2 | 932 rows, 7 P0 cells N+≥50 | `data/scenarios_mainconf_v2.jsonl` |
| Auth-SafeInv v2 | 1464 authorization counterfactual rows | `data/authorization_counterfactuals_v2.jsonl` |
| Trace candidate-effect rows | 8,988 rows (6 families) | `data/auth_trace_effect_schema_conditioned_*.jsonl` |
| 最大 LOTO FNR | 0.97 (file_written/write_file) | LOTO stress test |
| 最大 ToolProxyGap | 0.88 (file_content_read/read_file) | LOTO stress test |
| pIIA-Drop range | 0.052 (tool_error) – 0.366 (network_egress) | pIIA Qwen3-8B |
| Lexical control Δ | +0.004 mean FNR | Lexical normalization |
| Full-training contrastive | post-FNR 0.00 on 5/6 effects | Full-training upper bound |
| Strict LOPO contrastive | 40/68 improved, mean ΔFNR +0.157 | Strict LOPO protocol |
| Gate 1 (contrastive strict) | FNR 0.2804 vs best baseline 0.1835 | ❌ |
| Gate 2 (schema-conditioned) | FNR 0.4516 vs best baseline 0.1835 | ❌ |
| Gate 3 (decomposed frozen) | FNR 0.3547 vs best baseline 0.1835 | ❌ |
| T64 live protocol exec verifier | Test FNR/FPR=0.0/0.0 (N+=197, N-=1170) | Validation-selected |
| T65 browser exec verifier | Test FNR/FPR=0.0/0.0 (N+=62, N-=411) | Validation-selected |
| T69 label-hidden degradation | FNR 0.0353→0.1162 (3.3×) | Trace-view ablation |
| T69 minimal-evidence degradation | FNR 0.0353→0.1465 (4.2×) | Trace-view ablation |
| T68 action FDeny (T61/T65) | 1.0 | Action-level aggregation |
| T73 calibration collapse | All-allow on 4/6 trace families | NEGATIVE |
| T70 raw-status boundary | row FNR 0.1113, FDeny 0.0265 | Competitive baseline |

---

## 七、关键文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| Path A 收敛分析 | `analysis/planning/path_a_convergence_analysis_2026-05-22.md` | 外部文献分析 + Path A 决策 |
| 后续推进规划 | `analysis/planning/后续推进规划.md` | 主规划文档，含完整任务清单 |
| 当前状态与差距 | `analysis/planning/current_status_and_gaps.md` | 三阶段进展 + 剩余缺口 |
| 路线图 | `analysis/planning/roadmap.md` | 里程碑与投稿判断 |
| Auth-SafeInv 理论规划 | `analysis/planning/AuthSafeInv理论补强后续规划.md` | 理论补强路线详细设计 |
| 外部审稿意见 | `analysis/planning/外部审稿意见v1采纳与后续规划.md` | 审稿意见采纳 + P7 新文献 |
| CEG-Auth 方法设计 | `analysis/planning/ceg_auth_method_plan.md` | Future work 参考 |
| 成果汇总 | `analysis/planning/final_summary.md` | 项目成果与 claim limits |
| 实验分组索引 | `analysis/experiments/README.md` | 各实验块的目的、结论、关键产物和论文 claim boundary |
| Paper v1 (原版) | `paper/main.tex` | 15 页，verifier-assisted controlled study |
| Paper v2 (Path A) | `paper-path-a/main.tex` | 18 页，three-layer evaluation paper |
| Paper appendix | `paper-path-a/appendix.tex` | 5 页，contrastive theory + causal-chain + full tables |
