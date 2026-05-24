# Causal-Chain Conditioning 实验结果

> 2026-05-14 | Qwen3-8B | 5 conditions × 458 base samples = 2290 total

## 核心发现

**显式提供因果链信息（task_causal_chain condition）可大幅降低 LOTO 跨工具 FNR。**

| Effect | raw (max Held-FNR) | task_causal_chain | reduction |
|------|:---:|:---:|:---:|
| content_fetched | 0.78 | **0.00** | 消除 |
| network_egress | 0.69 | **0.00** | 消除 |
| tool_error | 0.27 | **0.00** | 消除 |
| file_written | 0.97 | **0.71** | 部分 (27%) |

## 各 condition 分析

| Condition | 含义 | 效果 |
|------|------|------|
| raw | 原始 scenario_text（基线） | 高 FNR |
| tool_only | 仅工具名和参数，无上下文 | **最差** — FNR=1.0（全失败）。说明工具名本身完全不足以支持效果检测。 |
| effect_chain | 添加"tool → operation → effects"链 | 部分改善 (content_fetched: 0.78→0.69, network_egress: 0.69→0.31) |
| task_causal_chain | 添加"task goal → authorized effects → proposed call → actual effects → consistency" | **最优** — 3/4 效果 held-FNR 归零 |
| wrong_chain | 提供错误/篡改的效果声明 | 诱导错误率 0.12–0.24，探针部分跟随错误链 |

## 结论

1. **Causal-chain conditioning 是 representation-side 有效的缓解方法**，与 contrastive projection（数据侧)互补。
2. **file_written 是所有 effect 中最顽固的**——两种方法都有残余 FNR。原因可能是 write 操作的语义多样性过大。
3. **wrong_chain 条件产生的中等错误率表明**：显式因果链信息的可靠性需要独立验证，不能盲信文本中声称的效果。
