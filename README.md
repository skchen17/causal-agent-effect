# Causal Agent Safety Research

**研究问题**：在 agent 安全中，LLM 表征是否以工具不变的方式编码了因果效果？

核心发现：**surface-form fragmentation / tool-proxy behavior** —— 线性探针对因果效果的预测会依赖工具表面形式。当训练覆盖不完整时，安全关键效果的假阴性率可高达 0.97。

当前状态（2026-05-22）：mainconf v2 修复链与 Auth-SafeInv T38-T73 已生成可审计 artifacts。项目应表述为 **verifier-assisted controlled/protocol diagnostic study**，不是部署安全认证。核心经验结论是：strict pure representation-side mitigation 仍未过关；contrastive projection 只能作为 observed-pair repair upper bound；更强的当前路线是 EffectVerif-AuthMonitor，即用执行/trace 证据识别 realized effects，再做任务授权检查。T64 已用 full-precision Qwen3-8B 重抽 embeddings 并复跑 downstream；T65 新增 120 条 file-backed headless Chrome DOM/JS runtime traces 和 960 条 candidate-effect rows；T73 说明简单 action-level false-denial-constrained threshold calibration 会在 T59/T61/T63/T65 退化为 all-allow。关键结果包括：T64 execution verifier validation-selected test FNR/FPR=0.0/0.0 (N+=197,N-=1170)，static verifiers FNR/FPR=0.6294/0.0462；T65 execution verifier test FNR/FPR=0.0/0.0 (N+=62,N-=411)，static verifier FNR/FPR=1.0/0.0；T68 action-level execution-verifier unauthorized-action allow / authorized-action false-denial 为 T58 0.0/0.1591、T59 0.2/0.3571、T61 0.0/1.0、T63 0.05/0.21、T65 0.0/1.0、T64 0.0/0.0；T69 after T65 的 full-label / label-hidden / minimal-evidence mean FNR 分别为 0.0353 / 0.1162 / 0.1465；T70 after T65 的 pre-action rule-only / provenance-only / raw-status boundary mean FNR 分别为 0.5700 / 0.2873 / 0.1113。剩余主缺口是 provider-backed search、SaaS messaging、HTTP browser automation、deployed-agent runtime traces，独立 learned/formal effect verifier，以及非退化 action-level policy。

## 项目结构

```
data/              — 场景数据集 (JSONL)
embeddings/        — LLM 嵌入 (npy + meta.json)
analysis/          — 实验结果和分析文档
analysis/experiments/ — 按实验块整理的目的、结论、产物索引
```

## 实验复现

### 一键运行

```bash
bash run_experiments.sh
```

### 分步运行

| 阶段 | 脚本 | 说明 |
|------|------|------|
| 数据生成 | `generate_counterfactual_data.py` | 规则模板 + LLM 合成（DeepSeek V4 Flash） |
| | `generate_targeted_data.py` | 定向生成，针对低频效果 |
| | `merge_data.py` | 合并所有数据源 |
| 嵌入提取 | `extract_embeddings.py` | MiniLM (384d) |
| | `extract_embeddings_qwen.py` | Qwen2.5-7B (3584d) |
| | `extract_embeddings_llm.py` | Qwen3-8B / Gemma 等（支持 4-bit） |
| 探针训练 | `train_probes.py` | 线性+非线性探针，Δ 分析 |
| 泛化测试 | `cross_tool_generalization.py` | 交叉工具泛化 Gap |
| | `pairwise_tool_matrix.py` | 成对工具泛化矩阵 (156 tool pairs) |
| 因果验证 | `interchange_intervention_true.py` | 真 IIA：中间层交换干预（hook/GPU） |
| | `interchange_intervention.py` | 早期 DirRank 版本（已被 true 版替代） |
| Baseline | `experiment_baselines.py` | LOTO 表 + Pooled/Balanced/Tool-Cond 对比 |
| 分析 | `experiment_fnr_frag.py` | 部署 FNR、Spearman 相关、Frag 余弦距离 |
| real-tool proxy | `analysis/validate_real_tool_semantics.py` | 真实工具注册语义的 schema-and-semantic proxy 校验 |
| contrastive strict | `run_contrastive_strict_lopo.py` | pair-level strict LOPO；original 459 数据为 68 cases / 40 improved，mainconf v2 为 68 cases / 33 improved |
| contrastive multiseed | `run_contrastive_multiseed.py` | v2 schema，seeds 0-4 |
| causal-chain v2 | `build_causal_chain_conditioning_data.py`, `analysis/analyze_causal_chain_mechanism.py` | typed wrong-chain 输入、Qwen3-8B embeddings、mechanism 诊断 |
| mainconf v2 data | `generate_main_conference_data_increment.py`, `analysis/build_real_or_semireal_traces.py`, `merge_main_conference_data.py` | 408 条增量 + 65 条 static replay traces + 932 条合并数据 |
| mainconf v2 audit | `analysis/statistical_uncertainty_audit.py --data scenarios_mainconf_v2` | N+/N-/Wilson CI、strict LOPO、multiseed、threshold 风险 |
| Auth-SafeInv | `build_authorization_counterfactuals.py`, `build_authorization_counterfactuals_v2.py`, `build_auth_effect_schema_conditioned_data.py`, `build_auth_trace_effect_schema_conditioned_data.py`, `build_real_agent_tool_execution_traces_t59.py`, `build_broader_agent_tool_traces_t63.py`, `build_live_protocol_tool_traces_t64.py`, `build_headless_browser_runtime_traces_t65.py`, `build_deepseek_api_traces_t60.py`, `build_auth_execution_traces.py`, `build_auth_observed_execution_traces.py`, `experiment_auth_safeinv.py`, `experiment_auth_baselines.py`, `experiment_auth_baseline_confirmatory.py`, `experiment_auth_mitigation_comparison.py`, `experiment_auth_schema_conditioned_mitigation.py`, `experiment_auth_decomposed_verifier_mitigation.py`, `experiment_auth_t57_effect_present_verifier.py`, `experiment_auth_t58_execution_verifier.py`, `experiment_auth_t62_validation_threshold.py`, `analysis/auth_action_level_metrics.py`, `analysis/auth_trace_view_ablation_t69.py`, `analysis/auth_existing_defense_ablation_t70.py`, `analysis/auth_action_level_calibration_t73.py`, `analyze_surface_graph_alignment.py`, `interchange_intervention_controls.py`, `interchange_intervention_hook_controls.py`, `reproduce_auth_safeinv.sh` | T38-T73 已完成可审计 artifacts；T57/T58/T59/T61/T62/T63/T64/T65/T68/T69/T70/T73 支持或约束 verifier-assisted framework，但 T59 是 real-agent-tools local-adapter stress test，T61 是 single-provider API expansion，T63 是 broader local-adapter coverage，T64 是 key-free live HTTPS/local webhook protocol evidence，T65 是 file-backed headless Chrome runtime evidence，T73 是 negative action-level calibration diagnostic，均不是 provider-backed search/SaaS messaging/HTTP browser automation/deployed-agent validation |
| global validation | `analysis/validate_experiment_state.py` | 全局状态 validator |

### 环境

```bash
conda activate causal-safety  # Python 3.11 + PyTorch CUDA 12.4
```

## 论文分析文档

- `analysis/formalization.md` — 完整的形式化框架（定义 + 定理 + 实验映射）
- `analysis/theory_adjustments.md` — 实验发现后的理论调整记录
- `analysis/roadmap.md` — 后续路线图
- `analysis/model_comparison_findings.md` — MiniLM vs Qwen2.5-7B 详细对比
- `analysis/iia_results.md` — IIA 实验分析
- `analysis/tool_proxy_problem.md` — 工具代理问题深度说明
- `analysis/current_status_and_gaps.md` — 进度与差距
- `analysis/preliminary_findings.md` — 初步实验报告
- `analysis/completion_report.md` — 第三轮完成状态
- `analysis/completion_report_actuality_check.md` — v1 completion report 实际核对
- `analysis/mainconf_v2_repair_report.md` — mainconf v2 修复链与实验结果
- `analysis/AuthSafeInv理论补强后续规划.md` — 保留原理论主张的授权条件补强路线
- `analysis/外部审稿意见v1采纳与后续规划.md` — 外部审稿意见 v1 后的论文定位、方法化补强和 T66-T73 规划
- `analysis/related_work_difference_matrix.md` — T66 相关工作差异矩阵和 novelty boundary
- `analysis/effectverif_authmonitor_spec.md` — T67 EffectVerif-AuthMonitor 方法接口、trace schema 和 claim boundary
- `analysis/auth_action_level_metrics_t68.md` — T68 action-level Auth-SafeInv allow/deny 指标；暴露 T61 provider split 过度拒绝风险
- `analysis/auth_trace_view_ablation_t69.md` — T69 full / label-hidden / minimal-evidence trace-view verifier ablation
- `analysis/auth_existing_defense_ablation_t70.md` — T70 pre-action rule-only、provenance-only、raw-status boundary 与 EffectVerif proxy 对照
- `analysis/agent_tool_traces_headless_browser_t65_v1_manifest.md` — T65 file-backed headless Chrome runtime trace manifest
- `analysis/auth_action_level_calibration_t73.md` — T73 action-level threshold calibration negative diagnostic
- `analysis/AuthSafeInv_completion_actuality_check.md` — Auth-SafeInv T38-T45 自报完成情况的实际核验；当前权威状态源
- `analysis/auth_threshold_policy.md` — Auth-SafeInv fixed / validation-calibrated / ex-post FPR-constrained 阈值口径
- `analysis/self_review.md` — 第三轮后自审
- `analysis/experiment_state_validation.md` — 全局 validator 报告
- `analysis/experiments/README.md` — 按实验块归档的目的、结论、关键产物和 claim boundary 索引

## 当前关键结果

- Original 459 strict LOPO：68 tool-case evaluations，40 improved，mean DeltaFNR=0.1567。
- Original 459 multiseed contrastive v2：6 effects，seeds `[0,1,2,3,4]`，最大 mean post-FNR=0.1625。
- Causal-chain v2：2290 samples；wrong-chain typed subsets 为 153 effect omissions、153 authorization flips、152 effect flips。
- Real-tool calibration：459 proxy scenarios，schema/flow/semantic conflicts 均为 0。
- Mainconf v2：932 rows；7 个 tracked P0 cells 全部达到 N+ >= 50。
- Mainconf v2 LOTO：最大 held-out FNR 为 0.8036 (`file_content_read/read_file`) 和 0.7679 (`file_written/write_file`)。
- Mainconf v2 strict LOPO：68 tool-case evaluations，33 improved，mean DeltaFNR=0.1044。
- Mainconf v2 full-training multiseed：最大 mean post-FNR=0.034；只能作为 observed-pair repair upper bound。
- Auth-SafeInv：v2 有 1464 authorization counterfactual rows，T55 effect-schema conditioned data 有 35136 rows；T54/T55/T56 共同说明 strict pure-method gate 失败。T57/T58/T59/T61/T63/T64/T65 构成 verifier-assisted evidence stack：T58 controlled traces test FNR/FPR=0.0/0.0 under validation-selected thresholds，T59 real-agent local-adapter test FNR/FPR=0.1765/0.0，T61 DeepSeek provider API test FNR/FPR=0.0/0.0，T63 broader local-adapter test FNR/FPR=0.0351/0.0，T64 full-precision key-free live/protocol test FNR/FPR=0.0/0.0，T65 file-backed headless Chrome runtime test FNR/FPR=0.0/0.0。Static verifiers 在 T61/T63/T64/T65 上明显弱化，分别暴露 provider、broader-tool、live/protocol 和 browser-runtime effect gaps。T68/T73 也暴露 action-level policy 尚未解决：T61/T65 false denial 可达 1.0，且 T73 的简单校准会在多个 trace family 上退化为 all-allow。所有这些结果仍不是 provider-backed search、SaaS messaging、HTTP browser automation 或 deployed-agent runtime validation。
