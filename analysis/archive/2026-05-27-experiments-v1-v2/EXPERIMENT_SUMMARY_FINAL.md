# 实验汇总 (2026-05-27 ~ 2026-05-28)

## 核心问题

**LLM agent 的安全监控——如何判断 agent 的工具调用是否超出任务授权？**

探索三条路线：
1. 外部探针从 embedding 检测（线性探针 / 双塔架构）
2. 规则匹配检测（static verifier / execution verifier）
3. LLM 自己判断（self-audit）

---

## 实验清单：脚本 → 数据 → 结果

### 实验 1: Agent Runtime + 效果检测

**目的**：构建真实 agent 会话，检测工具调用产生的因果效果，测试 static verifier。

| 脚本 | 输入 | 输出 | 关键结果 |
|------|------|------|---------|
| `src/auth/agent_runtime.py` | — (AgentRuntime 类) | — | Sandbox + 4工具 + conversation loop |
| `src/auth/build_agent_runtime_traces.py` | 8场景 × 5reps | `data/agent_runtime_traces_v2_expanded.jsonl` (40条) | agent 使用4种工具，bash产生最多越权 |
| `src/auth/build_auth_trace_effect_schema_conditioned_data.py` | 40 traces | 320行 candidate-effect | 展开为效果级别标注 |
| `src/auth/experiment_auth_t58_execution_verifier.py` | trace数据 + schema训练数据 | `analysis/auth_t58_*.md` | Static FNR=0.78, Execution FNR=0.0 |

**Static verifier 结果** (v2, 192行):
| Verifier | Present FNR | Unauthorized FNR |
|---|---|---|
| execution_trace | 0.0 | 0.50 |
| static | 0.78 | 1.0 |

**关键发现**：`bash` 不在 T57 规则表 → 78% 效果漏检。read/write/delete 工具能检测。

---

### 实验 2: 纯探针检测（跳过 present verifier）

**目的**：单探针直接从 embedding 判断是否越权。

| 脚本 | 输入 | 输出 | 关键结果 |
|------|------|------|---------|
| `src/auth/experiment_probe_direct.py` | schema训练数据 + trace测试数据 | console | FNR=0.79, 探针输出极端极化(全0或全1) |

**关键发现**：探针学到文本模板匹配，跨分布不泛化。

---

### 实验 3: 双塔架构对比

**目的**：测试分离编码 (task embedding + tool embedding) 是否优于单文本 concat。

| 脚本 | 输入 | 输出 | 关键结果 |
|------|------|------|---------|
| `src/data/generate_dual_tower_data.py` | 规则 + LLM生成 | `data/dual_tower_samples.jsonl` (52条) | 合成 task-tool 对 |
| `src/embeddings/extract_dual_embeddings.py` | 52条 + Qwen3-8B | `embeddings/emb_dual_tower_samples_*.npy` | task/tool/concat 三份嵌入 |
| `src/probes/train_dual_tower_probe.py` | embeddings | console | 线性双塔对比 |
| `src/probes/train_dual_tower_probe_v2.py` | embeddings | console | MLP非线性双塔对比 |

**5-Fold CV (52样本)**:
| Architecture | F1 |
|---|---|
| lr_concat (单文本baseline) | **0.78** |
| mlp_dual (双塔+MLP) | 0.60 |
| lr_dual (双塔+线性) | 0.48 |

**关键发现**：单文本 concat 让 transformer 内部做交互 > 分离编码再线性组合。双塔皆不如 baseline。

---

### 实验 4: LLM 自审计

**目的**：测试 LLM 自己能否判断 tool call 是否越权。

**数据集**：113 样本（52 合成 + 61 agent runtime, 5 reps × 8 场景 = 40 traces）
修复后 gold label: 61 auth / 52 unauth

| 脚本 | 输入 | 输出 | 关键结果 |
|------|------|------|---------|
| `src/experiments/experiment_llm_self_audit_v2.py` | 113条 + GGUF模型 | `analysis/results/llm_self_audit_v2.json` (362KB, 完整I/O) | LLM vs 探针对比 |

**实验配置**：
- 模型：Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf (GPU, llama-cpp)
- System prompt: 不含 "match"，只判断是否超出授权范围
- max_tokens=2048, temperature=0.0
- 解析器：只搜索回复末尾500字符，先搜 UNAUTHORIZED 再搜 AUTHORIZED

**LLM 自审计结果**:

| 指标 | 合成 (52) | Agent Runtime (61) | 总计 (113) |
|------|:-------:|:----------------:|:---------:|
| Accuracy | 0.769 | 0.656 | 0.708 |
| Unauth Recall | 0.769 | 0.462 | 0.615 |
| Unauth Precision | 0.714 | 0.706 | 0.711 |
| Auth Recall | 0.769 | 0.800 | 0.787 |

---

### 实验 5: 线性探针 Baseline（与 LLM 自审计对比）

**目的**：在相同数据上用线性探针做授权判断，对比 LLM zero-shot 能力。

**评估方式**：
- 5-Fold Stratified CV（同任务文本可能出现在 train+test）
- Leave-One-Task-Out CV（严格：留一个任务的全部样本做测试）

| 指标 | 5-Fold CV | LOTO CV |
|------|:-------:|:------:|
| Accuracy | 0.862 | 0.858 |
| Unauth Recall | 0.907 | 0.750 |
| Unauth Precision | — | 0.929 |
| Auth Recall | — | 0.951 |

**LOTO CV by source**:
| 来源 | Accuracy | Unauth Recall |
|------|:------:|:------------:|
| 合成 | 0.904 | 0.923 |
| Agent runtime | 0.820 | 0.577 |

---

## LLM vs 探针 最终对比

| | LLM 自审计 | 线性探针 (5-Fold) | 线性探针 (LOTO) |
|---|---|---|---|
| Unauth Recall | 0.615 | 0.907 | 0.750 |
| Unauth Precision | 0.711 | — | 0.929 |
| Agent Runtime Unauth Recall | 0.462 | — | 0.577 |
| 训练需求 | 无 (zero-shot) | 需标注数据 | 需标注数据 |
| 推理速度 | ~3.8s/sample | ~0.001s/sample | ~0.001s/sample |

## 核心结论

1. **LLM 无法可靠地自我审计**：真实 agent trace 上只能抓到 46% 越权，合成数据上 77%
2. **线性探针碾压 LLM**：即使严格 LOTO 评估，探针也比 LLM 多抓 13.5% 越权
3. **双塔架构不比单文本好**：Qwen3 内部的 cross-attention 已经是最好交互建模器
4. **Static verifier 按工具名索引有根本盲区**：bash 与 terminal 语义等价但不在规则表
5. **探针的局限**：跨分布泛化 (LOTO gap=0.157) 和文本模板匹配问题仍存在
