# 三模型对比：MiniLM vs Qwen2.5-7B vs Qwen3-8B

> 实验日期：2026-05-12 | 数据：459 条 | Gemma-4-26B-A4B 待完成

---

## 模型规格

| | MiniLM | Qwen2.5-7B | Qwen3-8B |
|------|------|------|------|
| 参数 | 22M | 7B | 8B |
| 维度 | 384 | 3584 | **4096** |
| 工具使用训练 | 无 | function calling (SFT) | function calling (SFT, 新一代) |
| 发布 | 2021 | 2024 | 2025 |
| VRAM | CPU | 14GB | 16GB |

---

## 一、线性探针能力 (F1_lin)

| 效果 | MiniLM | Qwen2.5-7B | Qwen3-8B | 增量 (MiniLM→Qwen3) |
|------|:---:|:---:|:---:|:---:|
| command_executed | 0.747 | 0.936 | **0.946** | +0.199 |
| file_deleted | 0.785 | 0.911 | **0.933** | +0.148 |
| tool_error | 0.722 | 0.918 | **0.938** | +0.216 |
| subagent_spawned | 0.680 | 0.886 | **0.907** | +0.227 |
| message_sent | 0.769 | 0.880 | **0.886** | +0.117 |
| file_content_read | 0.593 | 0.870 | **0.871** | +0.278 |
| content_fetched | 0.624 | 0.878 | **0.864** | +0.240 |
| network_egress | 0.728 | 0.852 | **0.858** | +0.130 |
| memory_updated | 0.739 | 0.835 | **0.854** | +0.115 |
| file_written | 0.605 | 0.863 | **0.840** | +0.235 |
| search_performed | 0.650 | 0.853 | **0.813** | +0.163 |
| **平均** | **0.695** | **0.880** | **0.883** | **+0.188** |

**结论**：从 384d → 3584d 跳跃巨大 (+0.185)，从 3584d → 4096d 几乎持平 (+0.003)。Qwen3-8B 在 Qwen2.5-7B 基础上没有显著提升线性可读性——天花板可能已接近。

---

## 二、Δ 分析（线性 vs 非线性）

| | MiniLM | Qwen2.5-7B | Qwen3-8B |
|------|:---:|:---:|:---:|
| |Δ|≤0.02 (线性编码) | 0 | 1 | **5** |
| Δ>0 (MLP 更优) | 3 | 1 | **1** |
| NL FAIL | 3 | 0 | 0 |

Qwen3-8B 首次有 5/11 效果通过 |Δ|≤0.02 检验——也就是说，在 4096 维空间中，线性探针的读数接近非线性方法的上限。这支持"因果效果在 LLM 表征中以接近线性方式编码"的假说。

---

## 三、交叉工具泛化 Gap（核心指标）

| 效果 | MiniLM | Qwen2.5-7B | Qwen3-8B | 最佳 |
|------|:---:|:---:|:---:|:---:|
| **tool_error** | −0.067 | +0.112 | **+0.126** | Qwen3 |
| **network_egress** | −0.193 | −0.126 | **−0.088** | Qwen3 |
| file_deleted | −0.412 | −0.346 | **−0.218** | Qwen3 |
| file_content_read | −0.307 | −0.369 | **−0.389** | MiniLM |
| file_written | −0.370 | −0.518 | −0.691 | MiniLM |
| content_fetched | −0.719 | −0.490 | −0.741 | Qwen2.5-7B |

```
tool_error gap 跨模型趋势:
  MiniLM:  −0.067  (PARTIAL)
     ↓
  Qwen2.5: +0.112  (CONCEPT LEARNED)  ← function-calling 训练拐点
     ↓
  Qwen3:   +0.126  (CONCEPT LEARNED)  ← 持续改善

network_egress gap 跨模型趋势:
  MiniLM:  −0.193  (TOOL PROXY)
     ↓
  Qwen2.5: −0.126  (PARTIAL)
     ↓
  Qwen3:   −0.088  (PARTIAL, 接近 CONCEPT 边界)
```

---

## 四、核心发现

**1. 工具使用训练是关键，参数量/代数其次。** 

从 MiniLM（无工具训练）→ Qwen2.5-7B（function calling SFT）→ Qwen3-8B（新一代 function calling），tool_error 的 Gap 从 −0.067 → +0.112 → +0.126，network_egress 从 −0.193 → −0.126 → −0.088。每一代工具使用训练都改善了跨工具泛化。但从 7B 到 8B（Qwen2.5→Qwen3），线性 F1 仅提升 0.003，说明**维度/参数量的边际增益在工具使用训练面前几乎为零**。

**2. 工具代理问题仍然根深蒂固。** 即使在 Qwen3-8B 上，4/6 测试效果仍是 PURE PROXY 或 TOOL PROXY。file_written 和 content_fetched 在 Qwen3 上甚至比 MiniLM 更差——新一代模型可能**强化了工具特定编码**（更强的 function-calling 格式识别 = 更尖锐的工具表面特征分离）。

**3. Δ 分析和跨工具泛化分析测量的是不同的东西。** Qwen3-8B 上 5 个效果通过 |Δ|≤0.02（"线性编码"），但其中只有 tool_error 通过跨工具泛化检验。这说明：**Δ 分析不足以判断因果概念的线性编码——它只能判断"工具内是否有线性可读信号"。跨工具泛化才是因果概念的真正检验。**

---

## 五、等待 Gemma-4-26B-A4B

Gemma 的 MoE 架构（128 专家，3.8B 激活）和原生 agent 训练（多步自主工作流 + 结构化 function calling）是当前最强工具使用模型。关键预测：

- **tool_error 应该继续改善或保持天花板**：已经 +0.126，空间有限
- **network_egress 有望逼近 −0.05**：Gemma 的 agent 训练可能弥合更多跨工具语义
- **file_deleted/content_fetched 是否有质变**：这两个效果从 MiniLM 到 Qwen3 改善最小——MoE + agent 训练是否能突破？

正在下载中。
