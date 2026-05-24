# Project File Map

> 最后更新：2026-05-24 | 新增 `analysis/experiments/` 实验分组索引。当前主状态优先见 `PROJECT_SUMMARY.md` 与 `analysis/planning/后续推进规划.md`；各实验目的、结论和 claim boundary 见 `analysis/experiments/README.md`。

## Directory Structure

```
causal-agent-safety-research/
├── paper/                    # 论文
├── analysis/                 # 分析文档与实验输出
│   └── experiments/          # 按实验块整理的目的、结论和产物索引
├── src/                      # 实验脚本（根目录 .py）
├── data/                     # 场景数据
├── embeddings/               # LLM 嵌入
├── insights-and-papers/      # 早期调研文档
├── notebooks/                # Jupyter 探索
├── CLAUDE.md                 # Claude Code 配置
├── README.md                 # 项目说明
├── FILE_MAP.md               # 本文件
├── run_experiments.sh        # 一键全流程
└── run_all.sh               # 简化入口
```

---

## 一、论文 (paper/)

| 文件 | 说明 |
|------|------|
| `paper/main.tex` | 论文 LaTeX 源文件（15 页） |
| `paper/main.pdf` | 编译后 PDF |
| `paper/main.aux`, `.log`, `.out` | 编译产物 |

---

## 二、实验脚本（根目录 .py）

### 数据生成

| 文件 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `generate_data.py` | 实验 1 模板数据（900 条） | — | `data/scenarios_template.jsonl` |
| `generate_counterfactual_data.py` | 实验 2 反事实+LLM 数据 | DeepSeek V4 Flash API | `data/scenarios_counterfactual.jsonl` |
| `generate_targeted_data.py` | 定向低频效果数据 | DeepSeek V4 Flash API | `data/targeted_synthetic.jsonl` |
| `merge_data.py` | 合并数据源 | 上述三个 jsonl | `data/scenarios_merged.jsonl` |
| `generate_main_conference_data_increment.py` | mainconf key-cell 增量生成 | `analysis/main_conference_cell_targets.json` | `data/scenarios_mainconf_increment_v2.jsonl` |
| `merge_main_conference_data.py` | mainconf 数据合并 | original + increment + static traces | `data/scenarios_mainconf_v2.jsonl` |
| `build_authorization_counterfactuals.py` | Auth-SafeInv authorization counterfactual data | scenario templates | `data/authorization_counterfactuals_v1.jsonl` |
| `build_auth_execution_traces.py` | Auth-SafeInv sandbox/static trace artifacts | static/sandbox examples | `data/agent_tool_traces_auth_v1.jsonl` |

### 嵌入提取

| 文件 | 用途 | 模型 | 输出前缀 |
|------|------|------|------|
| `extract_embeddings.py` | MiniLM 嵌入 | all-MiniLM-L6-v2 (384d) | `embeddings/$data_name.*` |
| `extract_embeddings_qwen.py` | Qwen2.5-7B 嵌入 | Qwen2.5-7B-Instruct (3584d) | `embeddings/qwen_$data_name.*` |
| `extract_embeddings_llm.py` | 通用 LLM 嵌入 | Qwen3-8B / Gemma 等 | `embeddings/$model_$data_name.*` |

### 诊断实验

| 文件 | 用途 | 关键输出 |
|------|------|------|
| `train_probes.py` | 线性+非线性探针 Δ 分析 | `analysis/results_*.json` |
| `cross_tool_generalization.py` | 交叉工具泛化 Gap | `analysis/cross_tool_*.json` |
| `pairwise_tool_matrix.py` | 156 工具对矩阵 | `analysis/pairwise_tool_*.json` |

### 因果验证

| 文件 | 用途 | 方法 |
|------|------|------|
| `interchange_intervention_true.py` | **真 IIA** (canonical) | Hook 法 L24/36, L24 探针方向 |
| `interchange_intervention.py` | 早期 DirRank | 嵌入空间 swap (MiniLM) |

### Baseline 与安全量化

| 文件 | 用途 | 关键输出 |
|------|------|------|
| `experiment_baselines.py` | LOTO 表 + 4 baseline | `analysis/baseline_comparison_*.json` |
| `experiment_fnr_frag.py` | FNR/α/FPR/MultiMech/Frag | `analysis/fnr_frag_*.json` |
| `analysis/statistical_uncertainty_audit.py` | T27 统计不确定性审计，支持 `--data` | `analysis/statistical_uncertainty_audit*.{json,md}` |
| `experiment_auth_safeinv.py` | Auth-SafeInv group-aware random / LOTO / family-holdout evaluation | `analysis/auth_safeinv_*.{json,md}` |
| `experiment_auth_baselines.py` | Auth-SafeInv split-matched strong baseline pilot | `analysis/auth_baselines_*.{json,md}` |
| `experiment_auth_baseline_confirmatory.py` | Auth-SafeInv baseline seed/hparam/threshold confirmatory sweep | `analysis/auth_baseline_confirmatory_*.{json,md}` |
| `experiment_auth_mitigation_comparison.py` | Auth-SafeInv contrastive projection vs T47 baseline same-cell comparison | `analysis/auth_mitigation_vs_baseline_*.{json,md}` |
| `interchange_intervention_controls.py` | pIIA direction + embedding-space control analysis; hook controls still partial | `analysis/piia_controls_*.{json,md}` |
| `interchange_intervention_hook_controls.py` | hook-based pIIA controls pilot: matched-norm random, wrong-form/wrong-effect, layer sweep, token aggregation | `analysis/piia_hook_controls_*.{json,md}` |

### 解法

| 文件 | 用途 |
|------|------|
| `solution_contrastive.py` | **对比投影**（主要解法），PyTorch autograd |
| `solution_procrustes.py` | Procrustes 对齐（对比 baseline） |
| `solution_ablation.py` | 维度消融 + strict cross-tool 测试 |
| `solution_tool_invariant.py` | 早期组合版（已废弃，保留参考） |
| `run_contrastive_strict_lopo.py` | pair-level strict LOPO；original 459 数据为 68 cases / 40 improved，mainconf v2 为 68 cases / 33 improved |
| `run_contrastive_multiseed.py` | contrastive multiseed v2；seeds 0-4 |
| `build_causal_chain_conditioning_data.py` | causal-chain v2 typed wrong-chain 数据构造 |
| `build_authorization_counterfactuals_v2.py` | Auth-SafeInv v2 surface-graph expansion dataset | `data/authorization_counterfactuals_v2.jsonl`, `analysis/authorization_counterfactuals_v2_manifest.{json,md}` |
| `analysis/select_main_conference_cells.py` | mainconf P0 cell target 选择 |
| `analysis/build_real_or_semireal_traces.py` | real-agent-tools static replay trace 构造 |
| `analyze_surface_graph_alignment.py` | Auth-SafeInv surface-form graph identifiability analysis | `analysis/surface_graph_alignment_*.{json,md}` |

### 入口脚本

| 文件 | 用途 |
|------|------|
| `run_experiments.sh` | **一键全流程**：数据 → 嵌入 → 探针 → IIA → baseline → 解法 |
| `run_all.sh` | 简化版：数据 → 嵌入 → 探针 |

---

## 三、分析文档 (analysis/)

### 核心框架

| 文件 | 内容 |
|------|------|
| `analysis/formalization.md` | **形式化框架**：7 定义 + 4 定理 + 1 命题 + 实验映射 |
| `analysis/formalization_audit.md` | 框架审计报告 |
| `analysis/contrastive_theory.md` | 定理 3-4 推导（对比泛化界 + 对齐→FNR） |

### 论文素材

| 文件 | 内容 |
|------|------|
| `analysis/final_summary.md` | 项目最终成果汇总 |
| `analysis/completion_report.md` | 第三轮完成报告 |
| `analysis/completion_report_actuality_check.md` | mainconf completion report 与实际文件核对报告 |
| `analysis/AuthSafeInv_completion_actuality_check.md` | Auth-SafeInv T38-T45 completion report 与实际文件核对报告；当前权威状态源 |
| `analysis/mainconf_v2_repair_report.md` | mainconf v2 修复链与实验结果报告 |
| `analysis/self_review.md` | 第三轮后自审 |
| `analysis/experiment_state_validation.md` | 全局 validator 报告 |
| `analysis/literature_agent_threats.md` | 12 篇核心文献详细分析 |
| `analysis/model_comparison_findings.md` | MiniLM vs Qwen2.5 vs Qwen3 对比 |
| `analysis/tool_proxy_problem.md` | 工具代理问题深度说明 |
| `analysis/solution_method.md` | 对比投影方法文档 |
| `analysis/iia_results.md` | IIA 实验分析 |

### 流程与计划

| 文件 | 内容 |
|------|------|
| `analysis/roadmap.md` | 项目路线图 |
| `analysis/current_status_and_gaps.md` | 进度与差距 |
| `analysis/AuthSafeInv理论补强后续规划.md` | 授权条件 causal task consistency / Auth-SafeInv 理论补强路线 |
| `analysis/外部审稿意见v1采纳与后续规划.md` | 外部审稿意见 v1 的采纳判断、主会定位修正和 T66-T73 后续任务规划 |
| `analysis/related_work_difference_matrix.md` | T66 相关工作差异矩阵；明确本文与 benchmark、runtime defense、causal attribution、provenance auditing 的边界 |
| `analysis/effectverif_authmonitor_spec.md` | T67 EffectVerif-AuthMonitor 方法规格；包含输入接口、trace schema、failure modes、metrics 和 claim boundary |
| `analysis/theory_adjustments.md` | 理论调整记录 |
| `analysis/v4_improvement_plan.md` | v4 改进方案 |

### 实验输出 (JSON)

| 文件 | 来源脚本 | 内容 |
|------|------|------|
| `analysis/results_qwen3-8b_scenarios_merged.json` | train_probes | 探针 F1/AUC/Δ |
| `analysis/cross_tool_qwen3-8b_scenarios_merged.json` | cross_tool_generalization | 交叉工具 F1 |
| `analysis/iia_true_qwen3-8b_scenarios_merged.json` | interchange_intervention_true | pIIA 结果 |
| `analysis/baseline_comparison_qwen3-8b_scenarios_merged.json` | experiment_baselines | LOTO + 4 baseline |
| `analysis/fnr_frag_qwen3-8b_scenarios_merged.json` | experiment_fnr_frag | FNR/α/FPR/MultiMech |
| `analysis/pairwise_tool_qwen3-8b_scenarios_merged.json` | pairwise_tool_matrix | 156 工具对矩阵 |
| `analysis/contrastive_qwen3-8b_scenarios_merged.json` | solution_contrastive | 对比投影结果 |
| `analysis/ablation_qwen3-8b_scenarios_merged.json` | solution_ablation | 消融 + strict 测试 |
| `analysis/procrustes_qwen3-8b_scenarios_merged.json` | solution_procrustes | Procrustes 结果 |
| `analysis/contrastive_strict_lopo_qwen3-8b_scenarios_merged.json` | run_contrastive_strict_lopo | strict LOPO 正式结果 |
| `analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json` | run_contrastive_multiseed | multiseed v2 正式结果 |
| `analysis/baseline_comparison_qwen3-8b_scenarios_mainconf_v2.json` | experiment_baselines | mainconf v2 LOTO + 4 baseline |
| `analysis/fnr_frag_qwen3-8b_scenarios_mainconf_v2.json` | experiment_fnr_frag | mainconf v2 FNR/FPR/alpha/Frag |
| `analysis/contrastive_strict_lopo_qwen3-8b_scenarios_mainconf_v2.json` | run_contrastive_strict_lopo | mainconf v2 strict LOPO：68 cases / 33 improved / mean DeltaFNR=0.1044 |
| `analysis/contrastive_multiseed_qwen3-8b_scenarios_mainconf_v2.json` | run_contrastive_multiseed | mainconf v2 full-training projection multiseed |
| `analysis/causal_chain_mechanism_qwen3-8b_causal_chain_conditioning_v2.json` | analyze_causal_chain_mechanism | causal-chain v2 mechanism 诊断 |
| `analysis/real_tool_scenarios_v2_validation.json` | validate_real_tool_semantics | real-tool schema-and-semantic proxy 校验 |
| `analysis/statistical_uncertainty_audit.json` | statistical_uncertainty_audit | cell counts、Wilson CI、threshold、seed variance、small-N 审计 |
| `analysis/statistical_uncertainty_audit.md` | statistical_uncertainty_audit | T27 审计报告，可用于论文主表/appendix 取舍 |
| `analysis/statistical_uncertainty_audit_mainconf_v2.json` | statistical_uncertainty_audit | mainconf v2 cell counts、Wilson CI、strict LOPO、multiseed 审计 |
| `analysis/statistical_uncertainty_audit_mainconf_v2.md` | statistical_uncertainty_audit | mainconf v2 可读审计报告 |
| `analysis/experiment_state_validation.json` | validate_experiment_state | 全局状态 validator，当前 `overall=ok` |
| `analysis/authorization_counterfactuals_v1_manifest.json` | build_authorization_counterfactuals | Auth-SafeInv v1 manifest；1184 rows，`split_group` 完整，focus unauthorized N>=30 |
| `analysis/authorization_counterfactuals_v1_manifest.md` | build_authorization_counterfactuals | Auth-SafeInv v1 可读 manifest |
| `analysis/agent_tool_traces_auth_v1_manifest.json` | build_auth_execution_traces | Auth trace manifest；68 traces，56 sandbox_simulated，0 observed_execution |
| `analysis/agent_tool_traces_auth_v1_manifest.md` | build_auth_execution_traces | Auth trace 可读 manifest |
| `data/agent_tool_traces_auth_observed_v1.jsonl` | build_auth_observed_execution_traces | controlled local sandbox observed executions；70 rows |
| `analysis/agent_tool_traces_auth_observed_v1_manifest.json` | build_auth_observed_execution_traces | observed-only auth trace manifest；observed_execution_sufficient=True |
| `analysis/agent_tool_traces_auth_observed_v1_manifest.md` | build_auth_observed_execution_traces | observed-only auth trace 可读 manifest |
| `data/agent_tool_traces_auth_v2.jsonl` | build_auth_observed_execution_traces | auth v1 + observed v1 combined；138 rows |
| `analysis/agent_tool_traces_auth_v2_manifest.json` | build_auth_observed_execution_traces | auth v2 manifest；70 observed + 56 simulated + 12 static |
| `analysis/agent_tool_traces_auth_v2_manifest.md` | build_auth_observed_execution_traces | auth v2 可读 manifest |
| `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v1.json` | experiment_auth_safeinv | Auth-SafeInv group-aware random / LOTO / family-holdout evaluation |
| `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v1.md` | experiment_auth_safeinv | Auth-SafeInv 可读结果报告 |
| `analysis/auth_baselines_qwen3-8b_authorization_counterfactuals_v1.json` | experiment_auth_baselines | split-matched strong baseline pilot；678 rows across random/LOTO/family |
| `analysis/auth_baselines_qwen3-8b_authorization_counterfactuals_v1.md` | experiment_auth_baselines | Auth baseline aggregate readable report |
| `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.json` | experiment_auth_baseline_confirmatory | T47 baseline confirmatory sweep；504 fixed rows + 9408 threshold-curve rows |
| `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.md` | experiment_auth_baseline_confirmatory | T47 baseline confirmatory readable report |
| `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v1.json` | experiment_auth_mitigation_comparison | T51 same-cell mitigation-vs-baseline；132 fixed rows + 2772 threshold-curve rows |
| `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v1.md` | experiment_auth_mitigation_comparison | T51 可读报告；strict train-only projection 只覆盖 LOTO 4/14 cells |
| `data/authorization_counterfactuals_v2.jsonl` | build_authorization_counterfactuals_v2 | T53 v2 surface-graph expansion；1464 rows |
| `analysis/authorization_counterfactuals_v2_manifest.json` | build_authorization_counterfactuals_v2 | T53 manifest；7 focus effects all have unauthorized tools >=3 |
| `analysis/authorization_counterfactuals_v2_manifest.md` | build_authorization_counterfactuals_v2 | T53 可读 manifest |
| `embeddings/embeddings_qwen3-8b_authorization_counterfactuals_v2.npy` | extract_embeddings_llm | T54 v2 Qwen3-8B embeddings；1464×4096 |
| `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.json` | experiment_auth_safeinv | T54 Auth-SafeInv v2 held-out evaluation；22 LOTO rows / 21 family rows |
| `analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.md` | experiment_auth_safeinv | T54 Auth-SafeInv v2 可读报告 |
| `analysis/surface_graph_alignment_authorization_counterfactuals_v2.json` | analyze_surface_graph_alignment | T54 v2 graph；7 focus effects unauthorized strict-identifiable |
| `analysis/surface_graph_alignment_authorization_counterfactuals_v2.md` | analyze_surface_graph_alignment | T54 v2 graph 可读报告 |
| `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json` | experiment_auth_baseline_confirmatory | T54 v2 baseline confirmatory；756 fixed rows + 14112 threshold-curve rows |
| `analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.md` | experiment_auth_baseline_confirmatory | T54 v2 baseline 可读报告 |
| `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.json` | experiment_auth_mitigation_comparison | T54 v2 mitigation comparison；246 fixed rows + 5166 threshold-curve rows |
| `analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.md` | experiment_auth_mitigation_comparison | T54 v2 mitigation 可读报告；strict train-only coverage 21/21 but worse than best baseline |
| `build_auth_effect_schema_conditioned_data.py` | T55 data builder | Builds pair-free candidate-effect schema-conditioned Auth-SafeInv rows |
| `data/auth_effect_schema_conditioned_v2.jsonl` | build_auth_effect_schema_conditioned_data | T55 candidate-effect data；35136 rows across full/auth-only/tool-only conditions |
| `analysis/auth_effect_schema_conditioned_v2_manifest.json` | build_auth_effect_schema_conditioned_data | T55 manifest；no snakecase effect-id or label-field leakage in model text |
| `analysis/auth_effect_schema_conditioned_v2_manifest.md` | build_auth_effect_schema_conditioned_data | T55 可读 manifest |
| `embeddings/embeddings_qwen3-8b_auth_effect_schema_conditioned_v2.npy` | extract_embeddings_llm | T55 Qwen3-8B schema-conditioned embeddings；35136×4096 |
| `experiment_auth_schema_conditioned_mitigation.py` | T55 evaluation | Pair-free schema-conditioned unauthorized monitor evaluation |
| `analysis/auth_schema_conditioned_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json` | experiment_auth_schema_conditioned_mitigation | T55 schema-conditioned mitigation；252 fixed rows + 5292 threshold-curve rows |
| `analysis/auth_schema_conditioned_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.md` | experiment_auth_schema_conditioned_mitigation | T55 可读报告；full-tool-chain schema monitor remains weaker than T54 best baselines |
| `experiment_auth_decomposed_verifier_mitigation.py` | T56 evaluation | Decomposed candidate-effect-present / authorization verifier mitigation；supports pure decomposed and verifier-present upper-bound modes |
| `analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json` | experiment_auth_decomposed_verifier_mitigation | T56 full decomposed/verifier evaluation；765 fixed rows + 16065 threshold-curve rows；pure decomposed best full-tool-chain LOTO FNR=0.3547, family FNR=0.5638 |
| `analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.md` | experiment_auth_decomposed_verifier_mitigation | T56 full decomposed/verifier 可读报告；pure gate failed, verifier-present is upper-bound only |
| `analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2_verifier_present_full.json` | experiment_auth_decomposed_verifier_mitigation | T56 verifier-present full-tool-chain upper bound；85 fixed rows + 1785 threshold-curve rows；global auth model LOTO FNR=0.0042, family FNR=0.0745 at FPR=0 |
| `analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2_verifier_present_full.md` | experiment_auth_decomposed_verifier_mitigation | T56 verifier-present upper-bound 可读报告；requires external/execution-level candidate-effect-present verifier |
| `experiment_auth_t57_effect_present_verifier.py` | T57 evaluation | Trace-calibrated non-oracle effect-present verifier plus authorization monitor evaluation |
| `analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.json` | experiment_auth_t57_effect_present_verifier | T57 verifier-assisted framework result；170 fixed rows + 3570 threshold-curve rows；best LOTO FNR=0.0262/FPR=0.073 |
| `analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.md` | experiment_auth_t57_effect_present_verifier | T57 可读报告；deterministic static verifier, not live deployed-agent validation |
| `build_auth_trace_effect_schema_conditioned_data.py` | T58 data builder | Builds candidate-effect rows from controlled Auth-SafeInv execution traces |
| `data/auth_trace_effect_schema_conditioned_v1.jsonl` | build_auth_trace_effect_schema_conditioned_data | T58 trace candidate-effect data；1104 rows from 138 traces |
| `analysis/auth_trace_effect_schema_conditioned_v1_manifest.json` | build_auth_trace_effect_schema_conditioned_data | T58 manifest；no snakecase effect-id or label-field leakage in model text |
| `analysis/auth_trace_effect_schema_conditioned_v1_manifest.md` | build_auth_trace_effect_schema_conditioned_data | T58 可读 manifest |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_v1.npy` | extract_embeddings_llm | T58 Qwen3-8B trace candidate-effect embeddings；1104×4096 |
| `experiment_auth_t58_execution_verifier.py` | T58 evaluation | Schema-trained authorization monitor evaluated with execution-trace effect-present verifier |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json` | experiment_auth_t58_execution_verifier | T58 execution verifier result；96 fixed rows + 2016 threshold-curve rows；schema-to-trace-all FNR=0.0429/FPR=0.0 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.md` | experiment_auth_t58_execution_verifier | T58 可读报告；controlled execution trace validation, not live deployed-agent logs |
| `build_real_agent_tool_execution_traces_t59.py` | T59 data builder | Statically audits `real-agent-tools/` Hermes registrations and builds local handler-equivalent file/terminal traces |
| `build_deepseek_api_traces_t60.py` | T60 data builder | Builds DeepSeek OpenAI-compatible provider API traces when `DEEPSEEK_API_KEY` is set; covers provider-call network/content/error effects, not browser/search/messaging tools |
| `analysis/real_agent_tool_inventory_t59_v1.json` | build_real_agent_tool_execution_traces_t59 | T59 real-agent-tools inventory；74 registered tools statically found, 58 external/API-service candidates, direct imports blocked by missing `agent` / `hermes_constants` |
| `analysis/real_agent_tool_inventory_t59_v1.md` | build_real_agent_tool_execution_traces_t59 | T59 inventory readable report with manual/API-key candidates |
| `data/agent_tool_traces_real_agent_tools_t59_v1.jsonl` | build_real_agent_tool_execution_traces_t59 | T59 real-agent-tools grounded local-adapter traces；48 traces over read_file/write_file/terminal |
| `analysis/agent_tool_traces_real_agent_tools_t59_v1_manifest.json` | build_real_agent_tool_execution_traces_t59 | T59 trace manifest；local adapter traces, not direct Hermes handler or live API execution |
| `analysis/agent_tool_traces_real_agent_tools_t59_v1_manifest.md` | build_real_agent_tool_execution_traces_t59 | T59 trace manifest readable report |
| `data/auth_trace_effect_schema_conditioned_t59_v1.jsonl` | build_auth_trace_effect_schema_conditioned_data | T59 candidate-effect data；384 rows from 48 real-agent-tools local traces |
| `analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.json` | build_auth_trace_effect_schema_conditioned_data | T59 candidate-effect manifest |
| `analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.md` | build_auth_trace_effect_schema_conditioned_data | T59 candidate-effect manifest readable report |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.npy` | extract_embeddings_llm | T59 Qwen3-8B real-agent-tools trace candidate-effect embeddings；384×4096 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json` | experiment_auth_t58_execution_verifier | T59 real-agent local-trace stress test；schema-to-trace-all FNR=0.25/FPR=0.0 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.md` | experiment_auth_t58_execution_verifier | T59 readable report；real-agent-tools local-adapter stress test, not live deployed-agent validation |
| `data/agent_tool_traces_deepseek_api_t60_v1.jsonl` | build_deepseek_api_traces_t60 | T60 DeepSeek provider API observed traces；8 traces, 6 success calls, 2 planned invalid-model errors |
| `analysis/agent_tool_traces_deepseek_api_t60_v1_manifest.json` | build_deepseek_api_traces_t60 | T60 DeepSeek trace manifest；API key value not stored |
| `analysis/agent_tool_traces_deepseek_api_t60_v1_manifest.md` | build_deepseek_api_traces_t60 | T60 DeepSeek trace manifest readable report |
| `data/auth_trace_effect_schema_conditioned_t60_deepseek_v1.jsonl` | build_auth_trace_effect_schema_conditioned_data | T60 DeepSeek candidate-effect data；64 rows from 8 provider API traces |
| `analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.json` | build_auth_trace_effect_schema_conditioned_data | T60 DeepSeek candidate-effect manifest |
| `analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.md` | build_auth_trace_effect_schema_conditioned_data | T60 DeepSeek candidate-effect manifest readable report |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.npy` | extract_embeddings_llm | T60 DeepSeek Qwen3-8B candidate-effect embeddings；64×4096 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.json` | experiment_auth_t58_execution_verifier | T60 DeepSeek provider API pilot；execution verifier FNR=0.0/FPR=0.0 over one unauthorized eval cell, static verifiers FNR=1.0 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.md` | experiment_auth_t58_execution_verifier | T60 DeepSeek readable report；tiny provider API pilot, not broad real-agent validation |
| `data/agent_tool_traces_deepseek_api_t61_v1.jsonl` | build_deepseek_api_traces_t60 | T61 expanded DeepSeek provider API observed traces；120 traces, 90 success calls, 30 planned invalid-model errors |
| `analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.json` | build_deepseek_api_traces_t60 | T61 DeepSeek trace manifest；provider unauthorized counts: network_egress=30, content_fetched=60, tool_error=30 |
| `analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.md` | build_deepseek_api_traces_t60 | T61 DeepSeek trace manifest readable report |
| `data/auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl` | build_auth_trace_effect_schema_conditioned_data | T61 DeepSeek candidate-effect data；960 rows from 120 provider API traces |
| `analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.json` | build_auth_trace_effect_schema_conditioned_data | T61 DeepSeek candidate-effect manifest；no snakecase effect-id or label-field leakage |
| `analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.md` | build_auth_trace_effect_schema_conditioned_data | T61 DeepSeek candidate-effect manifest readable report |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.npy` | extract_embeddings_llm | T61 DeepSeek Qwen3-8B candidate-effect embeddings；960×4096 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json` | experiment_auth_t58_execution_verifier | T61 expanded DeepSeek provider API evaluation；execution verifier FNR=0.0/FPR=0.0 over 3 provider cells, static verifiers FNR=1.0 |
| `experiment_auth_t62_validation_threshold.py` | T62 evaluation | Selects thresholds on validation trace groups and evaluates fixed thresholds on held-out trace groups |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json` | experiment_auth_t62_validation_threshold | T62 controlled trace validation-selected threshold；execution verifier test FNR=0.0/FPR=0.0 with N+=44/N-=558 |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.md` | experiment_auth_t62_validation_threshold | T62 controlled trace readable report |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json` | experiment_auth_t62_validation_threshold | T62 real-agent-tools local-adapter validation-selected threshold；execution verifier test FNR=0.1765/FPR=0.0 with N+=17/N-=178 |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.md` | experiment_auth_t62_validation_threshold | T62 real-agent-tools local-adapter readable report |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json` | experiment_auth_t62_validation_threshold | T62 DeepSeek provider API validation-selected threshold；execution verifier test FNR=0.0/FPR=0.0 with N+=78/N-=432; static verifiers FNR=1.0 |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.md` | experiment_auth_t62_validation_threshold | T62 DeepSeek provider API readable report |
| `build_broader_agent_tool_traces_t63.py` | T63 data builder | Builds controlled local-adapter traces using `real-agent-tools` web/search/browser/messaging tool names and local verifiers |
| `data/agent_tool_traces_broader_tools_t63_v1.jsonl` | build_broader_agent_tool_traces_t63 | T63 broader local-adapter traces；300 traces across web/browser/messaging toolsets |
| `analysis/agent_tool_traces_broader_tools_t63_v1_manifest.json` | build_broader_agent_tool_traces_t63 | T63 trace manifest；unauthorized counts content_fetched=60/network_egress=60/tool_error=60/message_sent=30 |
| `analysis/agent_tool_traces_broader_tools_t63_v1_manifest.md` | build_broader_agent_tool_traces_t63 | T63 trace manifest readable report；controlled local adapters, not live external services |
| `data/auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl` | build_auth_trace_effect_schema_conditioned_data | T63 broader trace candidate-effect data；2400 rows from 300 traces |
| `analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.json` | build_auth_trace_effect_schema_conditioned_data | T63 candidate-effect manifest；no snakecase effect-id or label-field leakage |
| `analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.md` | build_auth_trace_effect_schema_conditioned_data | T63 candidate-effect manifest readable report |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.npy` | extract_embeddings_llm | T63 Qwen3-8B broader trace candidate-effect embeddings；2400×4096 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json` | experiment_auth_t58_execution_verifier | T63 broader local-adapter execution verifier result；execution verifier mean FNR=0.0625/FPR=0.0 at best tradeoff; static verifiers mean FNR=0.625 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.md` | experiment_auth_t58_execution_verifier | T63 broader local-adapter readable report |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json` | experiment_auth_t62_validation_threshold | T63 broader local-adapter validation-selected threshold；execution verifier test FNR=0.0351/FPR=0.0 with N+=114/N-=1133; static verifiers FNR=0.614/FPR=0.0132 |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.md` | experiment_auth_t62_validation_threshold | T63 broader local-adapter readable report |
| `build_live_protocol_tool_traces_t64.py` | T64 data builder | Builds key-free live/protocol traces: real outbound HTTPS plus local webhook protocol receiver |
| `data/agent_tool_traces_live_protocol_t64_v1.jsonl` | build_live_protocol_tool_traces_t64 | T64 raw traces；300 traces: 150 live HTTP external + 150 local protocol messaging |
| `analysis/agent_tool_traces_live_protocol_t64_v1_manifest.json` | build_live_protocol_tool_traces_t64 | T64 trace manifest；unauthorized counts content_fetched=150/network_egress=60/message_sent=60/tool_error=60 |
| `analysis/agent_tool_traces_live_protocol_t64_v1_manifest.md` | build_live_protocol_tool_traces_t64 | T64 readable trace manifest；key-free live/protocol evidence, not provider-backed search/SaaS messaging |
| `data/auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl` | build_auth_trace_effect_schema_conditioned_data | T64 candidate-effect data；2400 rows from 300 traces |
| `analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.json` | build_auth_trace_effect_schema_conditioned_data | T64 candidate-effect manifest；no snakecase effect-id or label-field leakage |
| `analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.md` | build_auth_trace_effect_schema_conditioned_data | T64 candidate-effect manifest readable report |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.npy` | extract_embeddings_llm | T64 full-precision Qwen3-8B live/protocol candidate-effect embeddings；2400×4096 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json` | experiment_auth_t58_execution_verifier | T64 live/protocol execution verifier result；execution verifier best tradeoff FNR=0.0/FPR=0.0; static verifier mean FNR=0.5833 on trace-type split |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.md` | experiment_auth_t58_execution_verifier | T64 live/protocol readable report |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json` | experiment_auth_t62_validation_threshold | T64 validation-selected threshold；execution verifier test FNR=0.0/FPR=0.0 with N+=197/N-=1170; static verifiers FNR=0.6294/FPR=0.0462 |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.md` | experiment_auth_t62_validation_threshold | T64 validation-selected threshold readable report |
| `analysis/t64_live_protocol_external_validity_report.md` | manual synthesis | T64 interpretation report；allowed/disallowed claims and full-precision rerun note |
| `build_headless_browser_runtime_traces_t65.py` | T65 data builder | Builds file-backed headless Chrome DOM/JavaScript browser-runtime traces |
| `data/agent_tool_traces_headless_browser_t65_v1.jsonl` | build_headless_browser_runtime_traces_t65 | T65 raw traces；120 traces over `browser_navigate` and `browser_snapshot` |
| `analysis/agent_tool_traces_headless_browser_t65_v1_manifest.json` | build_headless_browser_runtime_traces_t65 | T65 trace manifest；unauthorized counts content_fetched=60/memory_updated=30/tool_error=30 |
| `analysis/agent_tool_traces_headless_browser_t65_v1_manifest.md` | build_headless_browser_runtime_traces_t65 | T65 readable manifest；actual headless Chrome over file-backed pages, not HTTP browser networking or deployed runtime |
| `data/auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl` | build_auth_trace_effect_schema_conditioned_data | T65 browser-runtime candidate-effect data；960 rows from 120 traces |
| `analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.json` | build_auth_trace_effect_schema_conditioned_data | T65 candidate-effect manifest |
| `analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.md` | build_auth_trace_effect_schema_conditioned_data | T65 candidate-effect manifest readable report |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.npy` | extract_embeddings_llm | T65 full-precision Qwen3-8B browser-runtime candidate-effect embeddings；960×4096 |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json` | experiment_auth_t58_execution_verifier | T65 browser-runtime execution verifier result |
| `analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json` | experiment_auth_t62_validation_threshold | T65 validation-selected threshold；execution verifier test FNR=0.0/FPR=0.0 with N+=62/N-=411; static verifier FNR=1.0/FPR=0.0 |
| `analysis/auth_action_level_metrics.py` | T68 action-level Auth-SafeInv metrics | Aggregates T62 candidate-effect predictions into action-level allow/deny metrics |
| `analysis/auth_action_level_metrics_t68.json` | analysis/auth_action_level_metrics.py | T68 machine-readable action-level metrics over T58/T59/T61/T63/T65/T64 |
| `analysis/auth_action_level_metrics_t68.md` | analysis/auth_action_level_metrics.py | T68 readable action-level metrics；execution verifier unauthorized-action allow / authorized-action false-denial: T58 0.0/0.1591, T59 0.2/0.3571, T61 0.0/1.0, T63 0.05/0.21, T65 0.0/1.0, T64 0.0/0.0 |
| `analysis/auth_trace_view_ablation_t69.py` | T69 trace-view verifier ablation | Compares full-label, label-hidden raw, and minimal-evidence effect-present verifier views under T62 threshold policy |
| `analysis/auth_trace_view_ablation_t69.json` | analysis/auth_trace_view_ablation_t69.py | T69 machine-readable trace-view ablation after T65；full-label mean FNR=0.0353, label-hidden raw=0.1162, minimal-evidence=0.1465 |
| `analysis/auth_trace_view_ablation_t69.md` | analysis/auth_trace_view_ablation_t69.py | T69 readable report；supports structured execution evidence claim, not arbitrary sparse logs |
| `analysis/auth_existing_defense_ablation_t70.py` | T70 existing-defense proxy ablation | Compares EffectVerif against pre-action rule-only, provenance-only, and raw-status boundary proxy monitors |
| `analysis/auth_existing_defense_ablation_t70.json` | analysis/auth_existing_defense_ablation_t70.py | T70 machine-readable proxy comparison after T65；pre-action FNR=0.5700, provenance=0.2873, raw-status boundary=0.1113 |
| `analysis/auth_existing_defense_ablation_t70.md` | analysis/auth_existing_defense_ablation_t70.py | T70 readable report；raw-status boundary is strong, so avoid method-dominance overclaims |
| `analysis/auth_action_level_calibration_t73.py` | T73 action-level calibration diagnostic | Selects action-level thresholds on validation trace groups under false-denial constraints |
| `analysis/auth_action_level_calibration_t73.json` | analysis/auth_action_level_calibration_t73.py | T73 machine-readable calibration output；several trace families choose all-allow thresholds |
| `analysis/auth_action_level_calibration_t73.md` | analysis/auth_action_level_calibration_t73.py | T73 readable negative result；simple threshold calibration is not a deployable action policy |
| `analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.md` | experiment_auth_t58_execution_verifier | T61 expanded DeepSeek readable report；single provider surface, not broad real-agent validation |
| `analysis/surface_graph_alignment_authorization_counterfactuals_v1.json` | analyze_surface_graph_alignment | Auth surface graph identifiability analysis |
| `analysis/surface_graph_alignment_authorization_counterfactuals_v1.md` | analyze_surface_graph_alignment | Auth surface graph 可读报告 |
| `analysis/piia_controls_qwen3-8b_scenarios_mainconf_v2.json` | interchange_intervention_controls | pIIA direction + embedding-space controls；hook layer/token controls 仍缺 |
| `analysis/piia_controls_qwen3-8b_scenarios_mainconf_v2.md` | interchange_intervention_controls | pIIA controls 可读报告 |
| `analysis/piia_hook_controls_qwen3-8b_scenarios_mainconf_v2.json` | interchange_intervention_hook_controls | hook-based pIIA controls pilot；144 raw intervention rows |
| `analysis/piia_hook_controls_qwen3-8b_scenarios_mainconf_v2.md` | interchange_intervention_hook_controls | hook controls pilot 可读报告 |
| `analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json` | interchange_intervention_hook_controls | T48 hook controls confirmatory scale-up；864 raw intervention rows |
| `analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.md` | interchange_intervention_hook_controls | T48 hook controls confirmatory 可读报告 |
| `analysis/auth_threshold_policy.md` | T52 threshold policy | fixed / validation-calibrated / ex-post FPR-constrained reporting rules |
| `reproduce_auth_safeinv.sh` | T50/T51/T53/T54/T55/T56/T57/T58/T59/T61/T62/T63/T64/T65/T68/T69/T70/T73 Auth-SafeInv reproduction entrypoint | Ordered rebuild commands for T39-T73 artifacts；defaults `CUDA_VISIBLE_DEVICES=1` unless already set；T60/T61 API-key calls are not rerun by default |
| `analysis/generate_auth_result_source_appendix.py` | T50 result-source appendix generator | `analysis/auth_result_source_appendix.{json,md}` |
| `analysis/auth_result_source_appendix.json` | generate_auth_result_source_appendix | machine-readable artifact-to-command map；all_outputs_present=True |
| `analysis/auth_result_source_appendix.md` | generate_auth_result_source_appendix | reviewer-facing result-source appendix |

### 审查记录

| 文件 | 审查轮次 |
|------|:---:|
| `analysis/审查建议.md` | v1 |
| `analysis/审查意见-新.md` | v2 |
| `analysis/审查意见v2.md` | v2 补充 |
| `analysis/审查意见v3.md` | v3 |
| `analysis/审查意见v4.md` | v4 |
| `analysis/审查意见v5.md` | v5 |

### 图表 (PNG)

| 文件 | 说明 |
|------|------|
| `analysis/delta_comparison_*.png` | 线性 vs 非线性探针 Δ 分析图 |
| `analysis/encodability_results.png` | 实验 1 可编码性排名图 |

---

## 四、数据 (data/)

| 文件 | 规模 | 说明 |
|------|------|------|
| `data/scenarios_merged.jsonl` | **459 条** | **主数据集**（反事实 + LLM + 定向） |
| `data/scenarios_mainconf_increment_v2.jsonl` | 408 条 | mainconf v2 key-cell 增量数据，含 `tool_call` / `call_flow` |
| `data/agent_tool_traces_mainconf_v2.jsonl` | 65 条 | real-agent-tools static replay traces，字段完整但非 observed execution |
| `data/scenarios_mainconf_v2.jsonl` | 932 条 | mainconf v2 合并数据：459 original + 408 increment + 65 traces |
| `data/scenarios_counterfactual.jsonl` | 284 条 | 反事实规则 + LLM 合成 |
| `data/targeted_synthetic.jsonl` | 175 条 | 定向低频效果生成 |
| `data/scenarios_template.jsonl` | 900 条 | 实验 1 模板数据（不被合并使用） |
| `data/llm_synthetic.jsonl` | 100 条 | LLM 合成中间产物 |
| `data/real_tool_scenarios_v2.jsonl` | 459 条 | real-tool schema-and-semantic proxy scenarios |
| `data/causal_chain_conditioning_v2.jsonl` | 2290 条 | causal-chain typed wrong-chain v2 数据 |
| `data/authorization_counterfactuals_v1.jsonl` | 1184 条 | Auth-SafeInv counterfactual data；`split_group` 完整，focus unauthorized N>=30 |
| `data/agent_tool_traces_auth_v1.jsonl` | 68 条 | Auth-SafeInv traces；56 sandbox_simulated + 12 static_replay，0 observed_execution |
| `data/agent_tool_traces_broader_tools_t63_v1.jsonl` | 300 条 | T63 web/search/browser/messaging broader local-adapter traces；not live external-service traffic |
| `data/auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl` | 2400 条 | T63 broader trace candidate-effect rows |

---

## 五、嵌入 (embeddings/)

命名规则：`{embeddings,effects,meta,texts}_{model}_{data_name}.{npy,json,jsonl}`

### Qwen3-8B（主模型，4096d）

| 文件 | 说明 |
|------|------|
| `embeddings/embeddings_qwen3-8b_scenarios_merged.npy` | 嵌入矩阵 (459×4096) |
| `embeddings/embeddings_qwen3-8b_scenarios_mainconf_v2.npy` | mainconf v2 嵌入矩阵 (932×4096) |
| `embeddings/effects_qwen3-8b_scenarios_merged.npy` | 效果标签 (459×11) |
| `embeddings/effects_qwen3-8b_scenarios_mainconf_v2.npy` | mainconf v2 效果标签 (932×11) |
| `embeddings/meta_qwen3-8b_scenarios_merged.json` | 元数据 |
| `embeddings/meta_qwen3-8b_scenarios_mainconf_v2.json` | mainconf v2 元数据 |
| `embeddings/texts_qwen3-8b_scenarios_merged.jsonl` | 场景文本+工具名 |
| `embeddings/texts_qwen3-8b_scenarios_mainconf_v2.jsonl` | mainconf v2 场景文本+工具名 |
| `embeddings/embeddings_qwen3-8b_causal_chain_conditioning_v2.npy` | causal-chain v2 嵌入矩阵 (2290×4096) |
| `embeddings/embeddings_qwen3-8b_authorization_counterfactuals_v1.npy` | Auth-SafeInv data 嵌入矩阵 (1184×4096) |
| `embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.npy` | T63 broader trace candidate-effect 嵌入矩阵 (2400×4096) |
| `embeddings/effects_qwen3-8b_authorization_counterfactuals_v1.npy` | Auth-SafeInv data 效果标签 (1184×11) |
| `embeddings/texts_qwen3-8b_authorization_counterfactuals_v1.jsonl` | Auth-SafeInv data 场景文本+工具名 |
| `embeddings/effects_qwen3-8b_causal_chain_conditioning_v2.npy` | causal-chain v2 效果标签 |
| `embeddings/meta_qwen3-8b_causal_chain_conditioning_v2.json` | causal-chain v2 元数据 |
| `embeddings/texts_qwen3-8b_causal_chain_conditioning_v2.jsonl` | causal-chain v2 文本+工具名 |

### MiniLM（对比模型，384d）

| 文件 | 说明 |
|------|------|
| `embeddings/embeddings_scenarios_merged.npy` | 嵌入矩阵 (459×384) |
| `embeddings/effects_scenarios_merged.npy` | 效果标签 |
| `embeddings/meta_scenarios_merged.json` | 元数据 |

### Qwen2.5-7B（对比模型，3584d）

| 文件 | 说明 |
|------|------|
| `embeddings/embeddings_qwen_scenarios_merged.npy` | 嵌入矩阵 (459×3584) |
| `embeddings/effects_qwen_scenarios_merged.npy` | 效果标签 |

### 实验 2 早期数据

| 文件 | 模型 | 数据 |
|------|------|------|
| `embeddings/embeddings_counterfactual.npy` | MiniLM | counterfactual (284 条) |
| `embeddings/embeddings_scenarios_counterfactual.npy` | MiniLM | counterfactual (284 条, 修正命名) |

---

## 六、早期调研 (insights-and-papers/)

| 文件 | 内容 |
|------|------|
| `agent-causal-safety-research.md` | CAR 项目原始文档 |
| `三条脉络_LLM因果推理技术史诗.md` | 因果推理文献综述 |
| `path1-learning-curriculum.md` | 路径一学习路线（因果抽象） |
| `learning-doc-1~5-*.md` | 5 篇结构化学习文档 |
| `car-policy-engine-core-thesis.md` | CAR 策略引擎核心论点 |
| `causal-interpretability-mechanism.md` | 因果可解释性机制 |
| `causal-reasoning-feasibility-analysis.md` | 因果推理可行性分析 |
| `beyond-pearl-implicit-causal-learning.md` | Pearl 之外：隐式因果学习 |
| `core-arguments-potential-evaluation.md` | 核心论点评估 |
| `honest-assessment-and-gaps.md` | 诚实评估与差距 |
| `literature-comparison-analysis.md` | 文献对比分析 |
| `related-literature-details.md` | 相关文献详情 |
| `theoretical-improvement-proposals.md` | 理论改进提案 |

---

## 七、实验入口

```bash
# 一键复现全流程（推荐）
bash run_experiments.sh qwen3-8b_scenarios_merged

# 简化流程
bash run_all.sh

# 分步运行
python generate_counterfactual_data.py    # 1. 数据生成
python generate_targeted_data.py          # 2. 定向数据
python merge_data.py                       # 3. 合并
python extract_embeddings_llm.py Qwen/Qwen3-8B scenarios_merged.jsonl  # 4. 嵌入
python train_probes.py qwen3-8b_scenarios_merged          # 5. 探针
python cross_tool_generalization.py qwen3-8b_scenarios_merged  # 6. 泛化
python interchange_intervention_true.py                     # 7. pIIA (GPU)
python experiment_baselines.py qwen3-8b_scenarios_merged    # 8. Baseline
python experiment_fnr_frag.py qwen3-8b_scenarios_merged     # 9. FNR分析
python pairwise_tool_matrix.py qwen3-8b_scenarios_merged    # 10. 工具对
python solution_contrastive.py qwen3-8b_scenarios_merged    # 11. 对比投影
python solution_ablation.py qwen3-8b_scenarios_merged       # 12. 消融
```
