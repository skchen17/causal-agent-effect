# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Role

你是科研协作助手。目标：帮助完成具有顶会投稿潜力的人工智能/AI安全/机器学习安全方向研究。工作必须严谨、务实、可验证，优先服务于高质量论文产出。每步关注：问题重要性、假设合理性、理论成立性、方法区分度、实验公平充分可复现、结论被理论和实验共同支撑、论文叙事符合顶会审稿标准。

## Work Principles

1. 严格区分事实、推测、假设和建议。不确定时明确说明。
2. 不夸大贡献，不包装弱结果为强结果。
3. 数学证明逐步检查定义、条件、引理、定理、边界。不跳步。
4. 文献对比需具体到问题设定、假设、方法、理论保证、实验协议、局限。
5. 代码优先保证正确性、可复现性、可扩展性、清晰结构。
6. 主动指出潜在漏洞、反例、已有工作的相似点、审稿人可能质疑处。
7. 不给空泛建议如"需要更多实验"。必须说明具体做什么、为什么、预期验证什么。
8. 涉及最新文献/模型/数据集/工具版本时，提醒查证最新资料；联网环境主动搜索并引用。
9. 以顶会审稿视角评估研究贡献，给出风险等级（Low/Medium/High）和原因。
10. 信息不足时，基于合理假设给出可用版本并标注假设，不简单拒绝回答。

## Project Architecture

```
src/data/*.py     → data/*.jsonl
src/embeddings/*.py → data/*.jsonl → embeddings/{embeddings,effects,meta,texts}_{name}.npy/json
src/probes/*.py     → embeddings/ → analysis/results/*.json
src/intervention/*.py              → analysis/results/iia_true_*.json
src/experiments/*.py               → analysis/results/baseline_comparison_*.json
                                    → analysis/results/fnr_frag_*.json
src/solutions/*.py                 → analysis/results/contrastive_*.json
src/auth/*.py                       → analysis/results/auth_*.json
src/causal_chain/*.py               → data/causal_chain_*.jsonl
```

### Directory Organization

- `src/data/` (6 files) — 数据生成脚本
- `src/embeddings/` (3 files) — 嵌入提取 (MiniLM, Qwen2.5, Qwen3)
- `src/probes/` (3 files) — 探针训练与泛化测试
- `src/intervention/` (4 files) — IIA/pIIA 因果干预
- `src/experiments/` (3 files) — Baseline, FNR, Lexical control
- `src/solutions/` (6 files) — Contrastive, Procrustes, Ablation, LOPO
- `src/auth/` (21 files) — Auth-SafeInv 数据构造与实验
- `src/causal_chain/` (1 file) — Causal-chain conditioning
- `paper/` — 原版论文
- `paper-path-a/` — Path A evaluation/diagnostic paper
- `analysis/results/` — 实验 JSON + MD 结果 (129 files)
- `analysis/reports/` — 研究报告与解读 (23 files)
- `analysis/planning/` — 规划与路线图 (13 files)
- `analysis/manifests/` — 数据 manifest (48 files)
- `analysis/reviews/` — 审稿意见 (7 files)
- `analysis/audits/` — 核验与完成报告 (11 files)
- `analysis/scripts/` — 分析用 Python 脚本 (14 files)
- `analysis/appendix/` — 结果溯源 appendix (4 files)
- `PROJECT_SUMMARY.md` — 项目综述

**Important**: All scripts must be run from the repository root. Scripts use `Path(__file__).resolve().parent.parent` to locate the repo root. Entry shell scripts (`run_*.sh`, `reproduce_*.sh`) remain at root level and reference scripts via `src/<category>/<script>.py`.

**Data naming**: embedding files use suffix `_{data_name}` (e.g., `embeddings_qwen3-8b_scenarios_merged.npy`). Scripts accept data name as CLI argument.

**Two IIA scripts**: `interchange_intervention_true.py` (hook-based L24/36, canonical) and `interchange_intervention.py` (embedding-space, for MiniLM).

## Current Paper Status (2026-05-22)

**路线**: Path A — evaluation/diagnostic paper. 论文定位为 **Auth-SafeInv evaluation target + three-layer over-optimism diagnosis + constructive framework with honest limits**.

**核心文件**:
- `paper-path-a/main.tex` — Path A 主文 (18 pages, 2 contributions, 3 layers)
- `paper-path-a/appendix.tex` — 附录 (contrastive theory, causal-chain, full tables)
- `PROJECT_SUMMARY.md` — 项目综述
- `analysis/planning/后续推进规划.md` — 主规划文档
- `analysis/planning/path_a_convergence_analysis_2026-05-22.md` — Path A 决策分析

**SafeInv vs Auth-SafeInv 区分**: Layer 1 (LOTO/pIIA) = SafeInv (effect-detection invariance). Layers 2-3 = Auth-SafeInv (authorization-conditioned). 两者不可混用。

**已完成**: T0-T73, T75, Path A v1-v2 论文. **进行中**: T74/T76/T79/T81.

## Key Commands

```bash
conda activate causal-safety  # Python 3.11, PyTorch CUDA 12.4
bash run_experiments.sh qwen3-8b_scenarios_merged     # Full pipeline
bash reproduce_auth_safeinv.sh                         # Auth-SafeInv 53-step reproduction
python src/probes/train_probes.py qwen3-8b_scenarios_merged
python src/intervention/interchange_intervention_true.py  # True IIA (GPU)
python src/experiments/experiment_baselines.py qwen3-8b_scenarios_merged
python src/experiments/experiment_fnr_frag.py qwen3-8b_scenarios_merged
```

## Theory-Experiment Mapping

| Theory Component | Experiment Script | Key Metric |
|------|------|------|
| MultiMech (D1) | `src/experiments/experiment_fnr_frag.py` §0 | P(E=1\|T) per tool |
| Frag (D2) | `src/experiments/experiment_fnr_frag.py` §4 | Cosine dist + tool discriminator |
| SafeInv (D3-4) | `src/experiments/experiment_fnr_frag.py` §1 | Deployed FNR + FPR |
| ToolProxyGap (D5) | `src/experiments/experiment_baselines.py` §1 | ΔFNR + [ΔFNR]₊ |
| pIIA (D6) | `src/intervention/interchange_intervention_true.py` | pIIA-within/cross/Drop |
| Theorem 1 (FNR→safety) | `src/experiments/experiment_fnr_frag.py` α section | [β−α]₊ |
| Theorem 2 (sample complexity) | (theoretical, rare-CI widths) | CI via rule-of-three |
| Proposition 1 (DA bound) | `src/probes/pairwise_tool_matrix.py` | Same/cross-family F1 + ToolProxyGap |

## Critical Naming Conventions

- **pIIA**, not IIA: probe-mediated. Do not claim standard Geiger IIA.
- **IIA-Drop** = IIA_within − IIA_cross (non-negative). Not "IIA-Gap".
- **ToolProxyGap = [ΔFNR]₊**: ΔFNR can be negative; ToolProxyGap is the non-negative clamp.
- **LOTO is counterfactual stress-test**, not deployment risk. Deployed probe FNR≈0 when all tools seen.
- **α is predicted redundancy**: P(other probe predictions exceed threshold | E=1, T=B), from same probe suite as β. Not oracle co-occurrence.
- **β^LOTO ≠ β^deploy**: Theorem 1's β is from deployed probe. LOTO β is counterfactual for coverage-missing scenario.

## Pitfalls

- **FNR ≠ 1−F1**: compute confusion matrices directly.
- **Balanced method**: exclude held-out tool from `tool_train_sizes` dict comprehension, else min_sz=0.
- **RBF in train_probes.py**: must use sklearn Pipeline to prevent CV data leakage.
- **Qwen3-8B layers**: `model.layers[0..35]`, `model.norm`, `model.embed_tokens` (NOT `model.model.layers`).
- **hidden_states indexing**: index 0 = embedding, index k+1 = output of layer k.
- **Gemma-4**: needs `sentencepiece`; config uses `text_config.hidden_size`.
- **459 samples only**: many tool-effect pairs have N+ < 10. Account for small n in statistical claims.
