# 实验目录索引

> 创建日期：2026-05-24  
> 目的：把项目中的实验按研究问题单独归档。每个实验目录只保存该实验的目的、结论、关键产物和论文使用边界；原始 `data/`、`embeddings/`、`analysis/results/`、`analysis/reports/` 文件保持原路径，避免破坏复现实验脚本和论文溯源。

## 使用规则

1. 新实验必须新增一个独立目录，命名格式为 `E##_short_name`。
2. 每个目录至少包含 `README.md`，并写明：
   - 实验目的；
   - 主要结论；
   - 关键结果文件；
   - 论文中可以支持的 claim；
   - 不能支持或需要谨慎表述的 claim。
3. 不直接移动已有 JSON/JSONL/NPY 产物。若后续确实要物理迁移，必须同步修改复现脚本、论文 source appendix 和文件索引。
4. 主文数字优先引用 `analysis/appendix/auth_result_source_appendix.md` 和对应实验目录中的 artifact 列表。

## 当前实验分组

| 目录 | 实验块 | 当前结论 |
|---|---|---|
| `E01_surface_fragmentation_loto/` | 表征层 LOTO surface-form fragmentation | 支持 coverage-missing 下工具表面碎片化；不是部署 FNR |
| `E02_lexical_control/` | lexical normalization control | FNR 基本不变，反驳“只是关键词捷径”的简单解释 |
| `E03_piia_transfer_diagnostics/` | pIIA / hook controls | 支持 activation-level transfer fragility；不是 SCM 因果证明 |
| `E04_baselines_tool_proxy/` | pooled/balanced/tool-conditioned/reweight/Procrustes baselines | 自然线性/几何 baseline 不能消除 worst-form FNR |
| `E05_contrastive_projection/` | contrastive projection mitigation | full-training 是 observed-pair upper bound；strict LOPO 只部分改善 |
| `E06_causal_chain_conditioning/` | causal-chain input conditioning | mixed diagnostic，不足以作为主方法 |
| `E07_mainconf_v2_scaling_stats/` | mainconf v2 数据扩展与统计 | 样本量改善，但仍需要 CI/seed/threshold 口径 |
| `E08_auth_safeinv_counterfactual/` | Auth-SafeInv counterfactual evaluation | 定义 authorization-conditioned target；不是部署认证 |
| `E09_auth_mitigation_gate_failures/` | T54-T56 strict mitigation gates | 纯表征侧修复未通过 strict gate |
| `E10_effect_present_static_verifier_t57/` | T57 static effect-present verifier | controlled/static verifier 有效，但不是 live verifier |
| `E11_execution_verifier_controlled_t58_t62/` | T58/T62 execution verifier + validation threshold | execution evidence 有帮助，但仍是受控 trace |
| `E12_real_agent_tools_local_t59/` | T59 real-agent-tools local adapters | 真实工具语义迁移存在漏检 |
| `E13_provider_api_deepseek_t60_t61/` | T60/T61 provider API traces | provider trace 管线可用，但 single-surface |
| `E14_broader_local_adapters_t63/` | T63 broader local adapters | 扩展 web/search/browser/messaging proxy；不是 provider-backed |
| `E15_live_protocol_t64/` | T64 live HTTPS / local webhook protocol | 强化 key-free live/protocol 证据；仍非 SaaS/deployed runtime |
| `E16_headless_browser_runtime_t65/` | T65 headless Chrome file-backed runtime | 支持 browser runtime proxy；不覆盖 HTTP browser automation |
| `E17_trace_view_ablation_t69/` | T69 full/label-hidden/minimal trace view | 结构化标签会显著高估 verifier |
| `E18_action_level_metrics_calibration_t68_t73/` | T68/T73 action-level aggregation/calibration | row-level 指标不能替代 action-level policy |
| `E19_existing_defense_ablation_t70/` | T70 existing-defense proxy ablation | raw-status boundary competitive，不能声称方法支配所有防御 |
| `E20_statistical_uncertainty_audit/` | statistical uncertainty audit | 主表需要 N+/N-/CI/threshold/seed |
| `E21_reproducibility_source_appendix_t50/` | T50 result-source appendix / reproduction | 负责产物溯源，不提供新的科学结论 |

## 当前论文主线映射

- Layer 1 tool-surface over-optimism：`E01`、`E02`、`E03`、`E04`、`E05`
- Pure representation repair gate failures：`E05`、`E09`
- Layer 2 trace-label over-optimism：`E11`、`E17`
- Layer 3 row-to-action over-optimism：`E18`
- External-validity proxies：`E12`、`E13`、`E14`、`E15`、`E16`
- Statistical/reproducibility support：`E20`、`E21`

