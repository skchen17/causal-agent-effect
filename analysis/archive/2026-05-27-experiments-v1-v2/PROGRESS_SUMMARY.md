# 实验进展总结 (2026-05-27)

## 整体脉络

核心问题：**LLM agent 的安全监控——如何判断 agent 的工具调用是否超出任务授权？**

经历了三个实验阶段，从诊断走向构造。

---

## 阶段一：Agent Runtime v1（傀儡 agent）

**做了什么**：用本地 GGUF 模型替代 DeepSeek API，任务 prompt 直接指定 shell 命令。

**关键文件**：
- `src/auth/build_local_agent_provider_traces.py` — 任务指定具体命令
- `src/auth/agent_runtime.py` — 初版（文本模拟工具执行）

**关键发现**：
- Static verifier FNR = 1.0（`bash` 不在 T57 规则表）
- 模型没有自主决策——任务已经说"Run: curl -s..."，模型只是照做
- 12 条 trace，工具只有 bash

**问题**：任务直接指定命令，不是 agent 自主行为。

---

## 阶段二：Agent Runtime v2（真实 agent）

**做了什么**：构建完整 agent runtime + sandbox，agent 收到自然语言任务后自主决策工具调用。

**关键文件**：
- `src/auth/agent_runtime.py` — 完整重写：Sandbox 类 + 真实 subprocess/文件操作 + conversation loop
- `src/auth/build_agent_runtime_traces.py` — 8 类自然语言中文任务 × 3 reps = 24 traces
- `src/embeddings/extract_embeddings_gguf.py` — GGUF 模型 GPU embedding 提取
- `src/probes/train_dual_tower_probe.py` — 双塔探针对比实验
- `src/probes/train_dual_tower_probe_v2.py` — MLP 非线性融合
- `src/embeddings/extract_dual_embeddings.py` — 分离编码 task/tool embedding
- `src/experiments/experiment_llm_self_audit.py` — LLM 自审计实验

**模型环境**：
- llama-cpp-python + CUDA (RTX 4090 D × 2)
- Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf (ModelScope 下载)
- GPU 推理: 0.7s/20 tokens, embedding: 0.1s/text

**关键结果**：

### Static Verifier 评估 (192 行 candidate-effect 数据)
| Verifier | Present FNR | Unauthorized FNR |
|---|---|---|
| execution_trace | 0.0 | 0.50 |
| static (两种) | 0.78 | 1.0 |

- Agent 使用 4 种工具：bash, read_file, write_file, delete_file
- Static verifier 对 bash 完全盲（不在规则表），对 read/write/delete 有效
- 比 v1 的 1.0 FNR 更细粒度 (0.78)

### 纯探针检测（跳过 present verifier）
- 单文本 concat + 线性探针：F1=0.78 (baseline)
- 所有双塔变体都更差：lr_dual=0.48, mlp_dual=0.60
- **结论**：让 LLM 在单段文本中自行建模 task-tool 关系 > 分离编码再组合

### 双塔架构探索 (52 样本)
| Architecture | F1 |
|---|---|
| lr_concat (baseline) | 0.78 |
| mlp_dual | 0.60 |
| lr_dual | 0.48 |

- 分离编码 + 线性组合不敌单文本 concat
- MLP 非线性可部分弥补但打不过 baseline
- 词法变体（read_file → file_read）全部完美泛化

### LLM 自审计
- **无 system prompt**: 一律判 UNAUTHORIZED (accuracy=0.5, 全是误报)
- **有 system prompt + "别太保守"**: 一律判 AUTHORIZED (accuracy=0.5, 26 个越权全漏)
- **LLM 推理过程其实正确**，但解析 bug (`AUTHORIZED` 是 `UNAUTHORIZED` 子串) 反转了结果
- **根本结论**: LLM 无法自主区分授权/越权——在默认拒绝和默认放行之间摇摆

---

## 阶段三：直接探针检测

**做了什么**：跳过 present verifier，单探针直接从 embedding 判断 unauthorized。

**关键文件**：
- `src/auth/experiment_probe_direct.py` — 单探针直接检测

**结果**：
- 探针对所有输出 proba=0.000，极端极化
- FNR=0.79, F1=0.24
- 探针学到的是文本模板匹配，不是因果语义

---

## 已归档的数据和文件

存档位置: `analysis/archive/2026-05-27-experiments-v1-v2/`

| 文件 | 说明 |
|------|------|
| agent_runtime_traces_v2.jsonl | v2 agent runtime 24 条 trace |
| auth_trace_effect_schema_conditioned_agent_runtime_v2.jsonl | v2 展开后的 192 行 candidate-effect |
| dual_tower_samples.jsonl | 双塔实验 52 个 task-tool 对 |
| llm_self_audit.json | LLM 自审计结果 |
| experiment_plan.md | 实验方案文档 |
| auth_t58_*.md | T58 评估结果 |
| meta_*.json | 嵌入元数据 |

---

## 新增的关键源文件

| 文件 | 功能 |
|------|------|
| `src/auth/agent_runtime.py` | 轻量 agent runtime（Sandbox + 工具执行 + conversation loop） |
| `src/auth/build_local_agent_provider_traces.py` | v1 trace 生成（已废弃） |
| `src/auth/build_agent_runtime_traces.py` | v2 trace 生成（自然语言任务） |
| `src/embeddings/extract_embeddings_gguf.py` | GGUF 模型 GPU embedding 提取 |
| `src/embeddings/extract_auth_embeddings.py` | Auth 数据格式的 Qwen3 embedding 提取 |
| `src/embeddings/extract_dual_embeddings.py` | task/tool 分离编码 |
| `src/data/generate_dual_tower_data.py` | 双塔实验数据生成 |
| `src/probes/train_dual_tower_probe.py` | 双塔探针对比（线性） |
| `src/probes/train_dual_tower_probe_v2.py` | 双塔探针对比（MLP 非线性） |
| `src/auth/experiment_probe_direct.py` | 直接探针检测实验 |
| `src/experiments/experiment_llm_self_audit.py` | LLM 自审计实验 |

---

## 阶段四：LLM 自审计实验（2026-05-28 最终结果）

**做了什么**：让 LLM 自己判断给定的 (task, tool_call) 对是否越权。对比线性探针 baseline。

**数据集**：113 样本（52 合成 + 61 agent runtime traces，5 reps × 8 场景 = 40 traces）

**关键文件**：
- `src/experiments/experiment_llm_self_audit_v2.py` — 完整 I/O 记录的 LLM 自审计
- `data/dual_tower_samples_expanded.jsonl` — 113 样本（修复 gold label 后）
- `analysis/results/llm_self_audit_v2.json` — 完整实验结果（362 KB）

### 实验结果一览表

| 指标 | 合成数据 (52) | Agent Runtime (61) | 总计 (113) |
|------|:----------:|:----------------:|:---------:|
| Accuracy | 0.769 | 0.656 | 0.708 |
| Unauth Recall | 0.769 | **0.462** | 0.615 |
| Unauth Precision | 0.714 | 0.706 | 0.711 |
| Auth Recall | 0.769 | 0.800 | 0.787 |
| TP | 20 | 12 | 32 |
| FN | 6 | 14 | 20 |
| FP | 8 | 5 | 13 |
| TN | 20 | 28 | 48 |

### 线性探针 Baseline（同数据集 Qwen3 embedding + SGD）

| 指标 | 数值 |
|------|:---:|
| Accuracy | 0.862 |
| Unauth Recall | **0.907** |

### 关键发现

1. **LLM 自审计能力有限**：在真实 agent trace 上只能抓到 46% 的越权（vs 合成数据 77%）
2. **线性探针碾压 LLM 自审计**：Unauth recall 0.907 vs 0.615 — 探针比 LLM 自己判断准得多
3. **LLM 失败模式**：
   - 对 bash 工具调用（参数长、多语义）判断困难
   - 对多步任务中"前置步骤"（ls 查看目录 → 准备清理）的判断不一致
   - thinking 过程消耗大量 token，偶尔结论被截断
4. **label 修复**：tool_error 场景和 content_fetched 误检的 gold label 从 UNAUTHORIZED 修正为 AUTHORIZED（5 条）

### 实验设置

- 模型：Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf (GPU)
- System prompt：不含 "match" 关键词，只要求判断是否超出授权范围
- max_tokens: 2048，temperature: 0.0
- 完整 I/O 记录：system_prompt + user_prompt + full_reply + token 统计

---

## 待继续

1. **使用更强的模型测试**：当前 GGUF Q4_K_M 量化模型可能有精度损失
2. **few-shot 示例**：加入 2-3 个带标注的示例看是否能提升 LLM 判断
3. **扩大 agent runtime 场景多样性**：当前 8 类场景，可增加更细粒度的授权边界
