# E30 Same-Attack Evaluation Against FC-Guard

## 目的

用与 E28 完全相同的 AgentDojo Strong+Max attacks 攻击 FC-Guard，避免“baseline 用强攻击、方法用弱攻击”的比较不公平。

## 当前状态

E30 由 `src/auth/agentdojo_fc_guard_t119.py` 的 `--attack-set strong_max` 和 `src/auth/summarize_agentdojo_strongmax_t120.py` 共同支撑。2026-06-01 已完成 DeepSeek API smoke paired summary：T118 smoke 6 shards、T119 smoke 12 shards，T120 产生 12 条 paired comparison rows，并可加载 T114 AuthGraph-style proxy reference。

2026-06-03 已完成 local GGUF minismoke paired summary：T118 local minismoke 1 shard、T119 local minismoke 1 shard，T120 产生 1 条 paired comparison row。该 row 的 baseline A.UR/ASR 与 FC A.UR/ASR 均为 0/1；只能验证 local paired-summary 文件链路，不支持安全性或 utility 结论。

需要完成的全量矩阵：

- 5 attacks × 949 cases × `fc_prod_proxy_v1`
- 必做 ablations：`no_staging_posthoc_checker`、`effect_resource_boundary`、`tool_whitelist_only`、`allow_all`、`deny_all`
- clean-shadow replay upper bound 继续引用 T113 `shadow_replay_commit_v1`
- AuthGraph-style proxy 继续引用 T114 `tool_sequence_proxy_v1` / `tool_arg_alignment_proxy_v1`

## 关键产物

- FC-Guard runner: `src/auth/agentdojo_fc_guard_t119.py`
- Summary/paired comparison: `src/auth/summarize_agentdojo_strongmax_t120.py`
- Summary target: `analysis/results/agentdojo_strongmax_fc_guard_summary_t120.{json,md}`
- Local minismoke summary: `analysis/results/agentdojo_strongmax_fc_guard_summary_t120_local_minismoke.{json,md}`
- Local full summary target: `analysis/results/agentdojo_strongmax_fc_guard_summary_t120_local.{json,md}`

## 汇总命令

```bash
conda run -n causal-safety python src/auth/summarize_agentdojo_strongmax_t120.py \
  --baseline-json analysis/results/agentdojo_strongmax_matrix_t118.json \
  --baseline-shard-dir analysis/results/agentdojo_t118_strongmax_shards \
  --fc-json analysis/results/agentdojo_fc_guard_t119.json \
  --fc-shard-dir analysis/results/agentdojo_t119_fc_guard_shards \
  --authgraph-json analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_full949.json \
  --output analysis/results/agentdojo_strongmax_fc_guard_summary_t120.json \
  --output-md analysis/results/agentdojo_strongmax_fc_guard_summary_t120.md
```

Smoke summary target: `analysis/results/agentdojo_strongmax_fc_guard_summary_t120_api_smoke.{json,md}`。

本地 GGUF 汇总：

```bash
bash scripts/run_agentdojo_strongmax_local_full.sh t120
```

## 论文可支持的 claim

完成后可支持“同一 Strong+Max attack suite 下，FC-Guard 与 no-defense、best official defense、AuthGraph-style proxy、clean-shadow upper bound 的 action-level 对比”。

## 不能支持的 claim

- 如果只完成 smoke 或单一 attack，不能写成完整 AgentDojo strong attack matrix。
- local minismoke 不能和 DeepSeek API smoke/full shards 合并；不同模型后端必须分开报告。
- 如果 abstain 率过高，不能把低 U-Commit 解释为可部署安全。
- 如果 replay errors 高，必须作为方法失败模式而不是忽略。
