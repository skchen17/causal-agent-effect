# Causal Agent Safety Research — 项目综述

> 日期：2026-06-02
> 状态：主线已切换为 Future-Constrained CEG-Auth / AuthTrace-Guard 新方法；旧 Path A / Auth-SafeInv / 表征诊断内容暂时搁置为背景、负结果、附录或 fallback

---

## 一、项目概述

**当前核心研究问题**：如何构建一个面向 LLM agent 工具调用的越权检测方法，使其不依赖工具名、LLM 自审计或 oracle trace 标签，而是在任务授权包络 `A(c)` 下，从 label-hidden 执行证据中推断实际发生的 realized effects，并在真实副作用 commit 前做选择性授权决策？

**已有核心发现**：LLM agent 安全监控评估在三个层面系统性地高估安全性，这些结果现在作为方法论文的动机和约束——
1. **工具表面层 (Layer 1)**：线性探针检测因果效果时依赖工具表面形式，覆盖缺失时 FNR 可达 0.80
2. **Trace 标签层 (Layer 2)**：结构化 trace 标签字段让 verifier 表现虚高，隐藏标签后 FNR 退化 3.3×–4.2×
3. **行为级层 (Layer 3)**：row-level FNR/FPR 指标与 action-level allow/deny 决策结构性脱节

**当前定位**：主线从 Path A evaluation/diagnostic paper 切换为 **CEG-Auth / AuthTrace-Guard 方法论文**。Path A 的 surface-form fragmentation、label-hidden degradation、row-to-action breakdown 和 gate failures 作为方法论文的动机、负结果和评估要求；方法主线聚焦 label-hidden realized-effect inference、evidence localization、uncertainty 和 action-level selective policy。2026-05-31 新增 prevention-layer 方案：**future-constrained shadow execution / trajectory-locked authorization**，即 `c/A(c)/intent -> F_c -> shadow trace -> evidence graph -> locked replay -> guarded real commit`。

**当前执行原则**：只主动推进新方法，但论文重写暂停到真实场景评测之后。`T102`-`T111` 已完成 local prototype / mechanism evidence。`T112`-`T114` 已从 5x3 pilot 推进到 installed AgentDojo `v1.2.2` full949 direct gate：DeepSeek `direct/no-defense` A.UR=830/949、ASR=40/949；AuthGraph-style proxy ASR=0/949 但 A.UR 仅 317/949 或 234/949，明显 over-deny；T113 `shadow_replay_commit_v1` A.UR=800/949、ASR=0/949，但仍是 clean-shadow oracle upper-bound，且 workspace/slack/travel 存在 replay fidelity errors。2026-06-01 已新增并完善 `T118` Strong+Max baseline matrix runner、`T119` 非 oracle FC-Guard production-proxy runner 和 `T120` paired summary scaffold；DeepSeek API smoke 已通过。2026-06-03 当前 T118 full Strong+Max 长跑因 DeepSeek API `402 Insufficient Balance` 停在 13/100 full shards，T119/T120 full 尚未启动；同日新增 local GGUF backend（Qwen3.5-9B-DeepSeek-V4-Flash GGUF via llama.cpp）并完成 T118/T119/T120 1-case local minismoke，完整 raw prompt/output audit 已落盘；随后 T119 补充 theory-audit proxy v2，将 `F_c` resource envelope、CEG evidence/probability/uncertainty、replay equivalence、mediation status 和条件安全界误差项写入 artifact。local theory-v2 smoke 暴露 replay_error=1/1，因此当前只能说明实现会显式暴露理论条件失败，不能作为方法成功证据。旧 SafeInv、Path A、Auth-SafeInv、contrastive、pIIA、causal-chain 和旧论文重写不再主动扩展，只在新方法论文中作为动机、限制、负结果、baseline 约束或附录材料使用。

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

### 4.2 已完成（2026-05-27 ~ 2026-05-28 新实验）

| ID | 任务 | 说明 | 状态 |
|----|------|------|:--:|
| T82 | 本地 Agent Runtime 搭建 | llama-cpp + CUDA, Qwen3.5-9B-DeepSeek-V4-Flash-GGUF, Sandbox + conversation loop | ✓ |
| T83 | Agent Runtime v2 trace 生成 | 8场景 × 5reps = 40条真实agent会话, 4工具(bash/read/write/delete) | ✓ |
| T84 | Static Verifier 评估 (v2) | T58跨分布评估, Static FNR=0.78 (bash盲区), Execution FNR=0.0 | ✓ |
| T85 | 双塔架构探索 | 52样本, lr_concat(0.78) > mlp_dual(0.60) > lr_dual(0.48) | ✓ |
| T86 | 纯探针直接检测 | 跳过present verifier, FNR=0.79, 文本模板匹配不泛化 | ✓ |
| T87 | LLM 自审计实验 | 113样本, LLM vs 探针对比, 完整I/O记录 | ✓ |
| T88 | 线性探针 LOTO 评估 | Leave-One-Task-Out: Unauth Recall 0.750 (vs 5-Fold 0.907) | ✓ |

**核心发现**：
- **LLM 自审计不可靠**：真实agent trace上只抓46%越权，合成数据77%
- **线性探针 > LLM**：LOTO下探针抓75%，LLM抓62%
- **单文本concat > 双塔**：LLM内部cross-attention已是最好交互建模
- **Static verifier**：bash不在规则表→78%漏检

### 4.3 当前主线（方法论文）

| ID | 任务 | 优先级 | 说明 |
|----|------|--------|------|
| T100 | Future-constrained shadow execution 方案 | DONE | 已写入规划/方案；明确 `F_c`, shadow trace, trace-locked replay, guarded commit 和条件性保证 |
| T101 | 四节论文写作材料与引用清单 | DONE | 已新增 Introduction / Related Work / Threat Model / Method 材料文档 |
| T102 | Future constraint compiler 标注与评估 | DONE for local v1 / LLM compiler deferred | 已生成 200 tasks × 3 intents、rule baseline outputs、manifest 和 evaluation；rule_v1_gold_auth schema_valid=1.0000、sound_viol=0.0000、decision_acc=1.0000，仅验证本地 schema/validator 自洽 |
| T103 | Shadow execution + trace-locked replay 原型 | DONE for deterministic staged prototype | 600 T102 rows：unauth_block=1.0000、unauth_commit=0.0000、authorized_FDeny=0.0000；200 个授权 deviation challenge 全部 commit 前阻断；仍非真实工具 commit 实验 |
| T104 | Pre-commit blocking benchmark | DONE for local instrumented v1 | 1000 cases：unauth_block=1.0000、unauth_commit=0.0000、authorized_FDeny=0.0000、authorized_commit=1.0000；使用 staged local effects/dry-run counters/local outbox/simulated browser submit，仍非 provider-backed 外部有效性 |
| T92-T98 | 旧 monitor-route 遗留任务 | LEGACY / MIGRATED | 不再独立推进；T98→T107，T97→T108/T110，T95→T110，T96→T111 |
| T105 | Shadow-real divergence 与 safe substitution | DONE for local substitution v1 | 400 rows：faithful_allow=1.0000、unsafe_nonallow=1.0000；unsafe effect/host/path/tool divergence=0.5250/0.2750/0.5750/0.4000；仍非 provider-backed fidelity |
| T106 | 方法效率实验 | DONE for local prototype | 本地 deterministic stages：T102 compile/validate mean=0.0878ms，T103 shadow/plan/replay=0.0164ms，T105 faithful/unsafe divergence=0.0684/0.1504ms；排除 LLM/provider/browser/human-review latency |
| T107 | 本地结果统计审计与 claim boundary | DONE | 已生成 T102-T106 count/n、Wilson CI、timing、artifact source 和 claim register；当前只支持 controlled local prototype evidence |
| T108 | LLM / independent future-constraint compiler stress test | DONE for text-rule v1 / GGUF LLM permitted but pending | 不读 gold envelope 的 deterministic task-text compiler：decision_acc=0.9583、over_perm=0.0000、over_restrict=0.0417；API dry-run 资源缺失暴露 task context 缺口；用户已允许后续使用 Qwen3.5-9B-DeepSeek-V4-Flash-GGUF 做 LLM compiler |
| T109 | 更真实本地 side-effect boundary | DONE for local observable boundary v1 | 1000 cases：unauth_block=1.0000、unauth_commit=0.0000、authorized_FDeny=0.0000；授权路径产生 55 次本地 HTTP dry-run 请求；仍非 provider/SaaS/browser 外部有效性 |
| T110 | Future-constrained ablation/baseline | DONE | 1000 cases × 10 policies：full U-Commit=0/800、FDeny=0/200；no replay lock/prefix guard U-Commit=400/800；no staging U-Commit=800/800；tool-only U-Commit=750/800；effect-only U-Commit=120/800；但 no-shadow 与 resource-aware boundary 和 full 持平 |
| T111 | 外部有效性资源实验 | DONE for complex local runtime proxy / provider-backed unresolved | 600 cases × 8 policies：full trace-lock U-Commit=0/300、FDeny=0/300；effect-resource/effect-only/tool-only 均 U-Commit=300/300；exact lock without safesub FDeny=300/300；post-hoc no-staging unsafe-before-block=300/300。仍非 provider-backed/SaaS/真实浏览器/deployed validation |
| T112 | AgentDojo/AuthGraph-aligned 真实场景评测门槛 | DONE for full949 direct / 5x3 stronger | installed AgentDojo `v1.2.2` full949 `direct/no-defense`：A.UR=830/949、ASR=40/949；5x3 stronger attack 保留为 pilot；summary 见 `analysis/results/agentdojo_full949_direct_summary_2026-06-01.md` |
| T113 | 方法接入 AgentDojo action boundary | DONE for full949 replay-commit / ORACLE LIMIT | `shadow_replay_commit_v1` full949 direct：A.UR=800/949、ASR=0/949；仍是 clean-shadow oracle upper-bound，replay errors 主要在 workspace/slack/travel |
| T114 | AuthGraph-style proxy baseline | DONE for full949 log-based proxy | full949 direct `tool_sequence` proxy A.UR=317/949、ASR=0/949；`tool_arg` proxy A.UR=234/949、ASR=0/949；说明 simple clean-plan alignment 严重 over-denies |
| T115 | 方法论文主文重建 | BLOCKED / WAITING STRONGER FULL RUN | direct full949 ASR 只有 40/949，建议先补 `important_instructions_no_model_name` full949 或等价 stronger-attack full run，再恢复主文重建 |
| T118 | AgentDojo Strong+Max official baseline matrix | IMPLEMENTED / API BLOCKED / LOCAL MINISMOKE DONE | 新增 `src/auth/agentdojo_strongmax_matrix_t118.py`：5 attacks × 5 paper defenses × full949，支持 OpenAI-compatible 与 local GGUF backend、resume、per-setting shards、Wilson CI、Max-ASR。DeepSeek API smoke 已完成 6 shards / 24 attacked rows；API full 因 `402 Insufficient Balance` 停在 13/100 shards。2026-06-03 新增 local llama.cpp backend 和 full I/O audit；local minismoke `workspace/direct/none` 1×1 完成，输出 `analysis/results/agentdojo_strongmax_matrix_t118_local_minismoke.{json,md}`，UR/A.UR/ASR=0/1、0/1、0/1，raw I/O 45 rows |
| T119 | FC-Guard production-proxy AgentDojo implementation | IMPLEMENTED V5 THEORY-AUDIT PROXY / LOCAL MINISMOKE DONE / FULL NOT STARTED | `src/auth/agentdojo_fc_guard_t119.py` 已升级为审稿级 production-proxy + theory audit：决策前 staged capture 不计算 labels；policy 只读 `F_c` + typed CEG graph；DENY/ABSTAIN 不复放且不复用 staged answer；新增 staged/eval cache，支持多 policy 复用同一 injected staged trace；`F_c` 写入 resource envelope；CEG 写入 evidence/probability/uncertainty/severity；每行写入 replay equivalence、mediation status 和 `compiler_error + verifier_miss + replay_divergence + mediation_bypass` 条件界审计。API smoke：12 shards / 48 rows。local minismoke完成；theory-v2 smoke 输出 replay_error=1/1、Conditional_Theory_Audit_Pass=0/1，说明 replay fidelity 风险被显式记录；full T119 尚未启动 |
| T120 | Same-attack paired comparison summary | IMPLEMENTED V4 / LOCAL MINISMOKE DONE / WAITING FULL SHARDS | `src/auth/summarize_agentdojo_strongmax_t120.py` 已支持多个 FC shard dir、action-level paired metrics、AuthGraph-style proxy reference；API smoke 产生 12 条 paired rows。local minismoke summary 输出 `analysis/results/agentdojo_strongmax_fc_guard_summary_t120_local_minismoke.{json,md}`，1 paired row；full T120 需等待 T118/T119 matching full shards |

### 4.4 待资源允许后启动

| ID | 任务 | 优先级 | 说明 |
|----|------|--------|------|
| T96 | Provider-backed / deployed-runtime 外部有效性 | MIGRATED TO T111 | provider-backed search、SaaS messaging/email、HTTP browser automation、deployed-agent runtime logs 或 direct handler traces |
| T89 | 更强模型复现 | P1 | Qwen3.5-9B GGUF → 更大模型 |
| T99 | LLM self-audit baseline 修复 | P2 | 修复 parser；区分 `scope_authorized/effect_authorized/task_success/tool_error`；只作为 baseline |

### 4.5 投稿目标

- CEG-Auth / AuthTrace-Guard 方法论文
- 目标：NeurIPS 2026 / ICLR 2027
- **当前判断**：AgentDojo full949 direct gate 已给出第一组真实 benchmark 主结果，但 direct ASR 只有 40/949，攻击强度仍不足以单独支撑主会方法论文。下一步应补 full949 stronger-attack 或更强 prompt-injection setting，再决定是否恢复主文重建。Path A 保留为 fallback

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
│   ├── planning/     (14 files)   #   规划与路线图文档
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
| 方法论文写作材料 | `analysis/planning/method_paper_writing_materials_2026-05-31.md` | 当前方法论文 threat model、证据清单和缺口 |
| CEG-Auth 方法设计 | `analysis/planning/ceg_auth_method_plan.md` | 当前方法论文设计基础 |
| 成果汇总 | `analysis/planning/final_summary.md` | 项目成果与 claim limits |
| 实验分组索引 | `analysis/experiments/README.md` | 各实验块的目的、结论、关键产物和论文 claim boundary |
| Paper v1 (原版) | `paper/main.tex` | 15 页，verifier-assisted controlled study |
| Paper v2 (Path A) | `paper-path-a/main.tex` | 18 页，three-layer evaluation paper |
| Paper appendix | `paper-path-a/appendix.tex` | 5 页，contrastive theory + causal-chain + full tables |
