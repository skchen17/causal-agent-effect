# E28 AgentDojo Strong+Max Baseline Matrix

## 目的

补齐方法论文需要的 AgentDojo official-baseline 对照：installed AgentDojo `v1.2.2` full949、`deepseek-v4-flash`、Strong+Max 攻击集和官方防御矩阵。

## 当前状态

已新增可恢复 runner：`src/auth/agentdojo_strongmax_matrix_t118.py`。2026-06-01 已完成 DeepSeek API smoke：`workspace` 2 user tasks × 2 injection tasks × 2 attacks × 3 defenses，共 6 shards / 24 attacked rows。2026-06-02 起初因 `transformers_pi_detector` 依赖的 HuggingFace 模型无法通过 hub metadata API 下载而中断；随后已通过镜像直链下载必要文件到 `models/protectai_deberta-v3-base-prompt-injection-v2/`，并让 T118 支持 `--pi-detector-model` 本地路径。用户曾要求释放 GPU 给另一个项目，full run 暂停在 6/100 full shards；随后用户确认继续，并通过 `--resume` 恢复长跑。2026-06-03 06:32 检查显示 full run 因 DeepSeek API 返回 `402 Insufficient Balance` 停止，当前无后台 API 实验进程。

2026-06-03 按用户要求新增 local GGUF backend：`src/auth/agentdojo_local_llm.py` 使用 llama.cpp 加载 `models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`，把 AgentDojo messages 和工具 schema 渲染为本地 prompt，解析 `<tool_call>{...}</tool_call>`，并对每次本地模型调用保存完整 raw input/output audit。T118 local minismoke 已完成：`workspace/direct/none`，1 user task × 1 injection task，UR/A.UR/ASR = `0/1`, `0/1`, `0/1`。该结果只验证 local runner、tool-call parser、case logging 和 audit logging 可运行；本地模型初步 utility 很低，不能作为有效 baseline 结论。

Strong+Max attacks 固定为：

- `important_instructions`
- `tool_knowledge`
- `injecagent`
- `ignore_previous`
- `direct`

官方防御矩阵固定为：

- `none`
- `repeat_user_prompt`
- `spotlighting_with_delimiting`
- `transformers_pi_detector`
- `tool_filter_deepseek`

其中 `tool_filter_deepseek` 是对 AgentDojo 官方 `tool_filter` prompt 的 DeepSeek-compatible wrapper，因为 AgentDojo 原生 OpenAI wrapper 会使用 DeepSeek 不支持的 `developer` role。

## 关键产物

- Runner: `src/auth/agentdojo_strongmax_matrix_t118.py`
- Local LLM wrapper: `src/auth/agentdojo_local_llm.py`
- Local full launcher: `scripts/run_agentdojo_strongmax_local_full.sh`
- Inventory smoke JSON: `analysis/results/agentdojo_strongmax_matrix_t118_inventory_smoke.json`
- Inventory smoke report: `analysis/results/agentdojo_strongmax_matrix_t118_inventory_smoke.md`
- Shard output dir: `analysis/results/agentdojo_t118_strongmax_shards/`
- Full summary target: `analysis/results/agentdojo_strongmax_matrix_t118.{json,md}`
- API smoke: `analysis/results/agentdojo_strongmax_matrix_t118_api_smoke.{json,md}`
- API smoke shards: `analysis/results/agentdojo_t118_strongmax_api_smoke_shards/`
- Full long-run log: `runs/agentdojo_strongmax_full_20260602.log`
- Full long-run tmux session: `agentdojo_full` via `/tmp/agentdojo_full_tmux.sock` when running
- HF dependency handling: `scripts/run_agentdojo_strongmax_full.sh` now auto-uses `models/protectai_deberta-v3-base-prompt-injection-v2/` and can fill missing PI detector files through mirror direct links unless `AUTO_DOWNLOAD_HF_MODELS=0`.
- Local minismoke JSON/report: `analysis/results/agentdojo_strongmax_matrix_t118_local_minismoke.{json,md}`
- Local minismoke shards: `analysis/results/agentdojo_t118_strongmax_local_minismoke_shards/`
- Local minismoke AgentDojo case logs: `runs/agentdojo_t118_strongmax_local_minismoke/`
- Local minismoke full model I/O audit: `runs/agentdojo_local_model_io_t118_minismoke/t118_none.jsonl` (45 rows)
- Local full targets: `analysis/results/agentdojo_strongmax_matrix_t118_local.{json,md}`, `analysis/results/agentdojo_t118_strongmax_local_shards/`, `runs/agentdojo_t118_strongmax_local/`, `runs/agentdojo_local_model_io_strongmax/`

## 当前阻塞点

- Completed full shards: `13/100`
- Last complete shard set: `workspace / injecagent / spotlighting_with_delimiting`
- Current partial setting: `workspace / injecagent / transformers_pi_detector`
- Partial case logs in current setting: `230`
- Latest status check: 2026-06-03 06:32 stopped by DeepSeek API `402 Insufficient Balance`
- T119/T120: not started for full run
- Resume condition: replenish DeepSeek balance or provide a usable replacement key, then rerun the same script with `--resume`.
- Local full condition: `llama-cpp-python` is installed and local smoke passes, but full949 local matrix is expected to be very slow. The current 1-case smoke needed minutes and produced UR=0/1, so a local full run should be treated as a resumable feasibility/diagnostic run unless utility is improved.

## 全量运行命令

```bash
export DEEPSEEK_API_KEY='<set outside repo>'
export AGENTDOJO_PI_DETECTOR_MODEL=models/protectai_deberta-v3-base-prompt-injection-v2
export CUDA_VISIBLE_DEVICES=1
conda run -n causal-safety python src/auth/agentdojo_strongmax_matrix_t118.py \
  --run-agentdojo \
  --resume \
  --benchmark-version v1.2.2 \
  --attack-set strong_max \
  --defense-set paper \
  --model deepseek-v4-flash \
  --pipeline-label local \
  --logdir runs/agentdojo_t118_strongmax \
  --shard-dir analysis/results/agentdojo_t118_strongmax_shards \
  --output analysis/results/agentdojo_strongmax_matrix_t118.json \
  --output-md analysis/results/agentdojo_strongmax_matrix_t118.md \
  --pi-detector-model models/protectai_deberta-v3-base-prompt-injection-v2
```

本地 GGUF 后端：

```bash
export CUDA_VISIBLE_DEVICES=1
export AGENTDOJO_LOCAL_MODEL_PATH=models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf
bash scripts/run_agentdojo_strongmax_local_full.sh t118
```

最小本地 smoke：

```bash
export CUDA_VISIBLE_DEVICES=1
bash scripts/run_agentdojo_strongmax_local_full.sh t118-smoke
```

## 论文可支持的 claim

完成全量运行后，可支持“本文在 installed AgentDojo `v1.2.2` full949 Strong+Max 攻击矩阵上，与无防御及官方 prompt-injection defenses 对齐比较”的实验设置说明。

## 不能支持的 claim

- 该设置不是 AgentDojo 原论文 629-case 表格的逐项复现。
- 若本地 PI detector 路径丢失或未完成对应 shards，不能声称覆盖完整官方 defense matrix。
- local GGUF smoke 不能与 DeepSeek API shards 合并，也不能被解释为 DeepSeek `deepseek-v4-flash` 的结果。
- 当前 local minismoke utility 为 0/1；在 utility 未改善前，local full 只能作为可运行性/诊断证据，不能支撑方法优越性。
- `ASR=0` 不能写成绝对安全，必须报告 Wilson upper CI。
- `tool_filter_deepseek` 是官方 tool-filter prompt 的兼容实现，不是 AgentDojo 作者发布的新 defense。
