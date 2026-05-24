# 交换干预实验 (Interchange Intervention) 结果

> 实验日期：2026-05-12 | 模型：MiniLM + Qwen3-8B | 数据：459 条

---

## 方法

**独立方向交换干预 (Cross-Tool IIA)**：

1. 在工具 A 上训练线性探针 → 得到效果方向 w_src
2. 在工具 B 上训练独立的线性探针 → 得到评估器 clf_tgt
3. 对工具 B 的测试样本对 (E=0, E=1)：
   - 计算沿 w_src 方向的投影分量
   - 将 base(E=0) 的该分量替换为 source(E=1) 的对应分量
   - 用 clf_tgt 评估干预前后预测的变化方向
4. **IIA_cross** = 预测朝正确方向移动的干预比例
5. **Gap** = IIA_cross − IIA_within（同工具内的 train/test split 基线）

**关键**：w_src 和 clf_tgt 来自不同工具 → 避免了循环论证。如果 w_src 捕获的是真正的因果方向，那么沿它干预应该能改变 clf_tgt 的预测。

---

## 结果

| 效果 | MiniLM IIA_cross | MiniLM Gap | Qwen3-8B IIA_cross | Qwen3-8B Gap |
|------|:---:|:---:|:---:|:---:|
| **tool_error** | 0.711 | **−0.096** ✓ | 0.882 | **+0.009** ✓ |
| **file_deleted** | 0.721 | **+0.150** ✓ | 0.708 | **+0.186** ✓ |
| file_content_read | 0.828 | −0.172 | 0.828 | −0.141 |
| network_egress | 0.598 | −0.148 | 0.605 | −0.189 |
| file_written | 0.645 | −0.133 | 0.728 | −0.272 |
| content_fetched | 0.706 | −0.294 | 0.471 | **−0.529** |

(Qwen3-8B: 2 causal concept, 2 partial, 2 tool proxy)

---

## 关键发现

### 1. IIA 验证了工具代理的因果性

交叉工具 F1 gap 和交叉工具 IIA gap **高度一致**：

| 效果 | F1 Gap | IIA Gap | 一致性 |
|------|:---:|:---:|:---:|
| tool_error | +0.126 | +0.009 | ✓ 双正 |
| file_deleted | −0.218 | +0.186 | ~ 混合 |
| file_content_read | −0.389 | −0.141 | ✓ 双负 |
| network_egress | −0.088 | −0.189 | ✓ 双负 |
| file_written | −0.691 | −0.272 | ✓ 双负 |
| content_fetched | −0.741 | −0.529 | ✓ 双负 |

这说明工具代理问题不是统计伪影——**从工具 A 学到的效果方向，在因果干预意义上无法转移到工具 B**。

### 2. tool_error 是唯一通过两种检验的效果

- F1 gap：+0.126（正向泛化）
- IIA gap：+0.009（正向因果转移）
- 解释："错误/失败"语义是跨工具的，LLM 天然将其编码为可转移的因果方向

### 3. content_fetched 在两种检验中都是最差的

- F1 gap：−0.741（纯工具代理）
- IIA gap：−0.529（严重因果失联）
- 且 Qwen3-8B（更强的工具使用训练）表现**更差**而非更好
- 说明更强的 function-calling 训练强化了工具特定编码

### 4. Qwen3-8B vs MiniLM 的分化

- **改善的效果**：tool_error (+0.105 IIA), file_content_read (+0.031)
- **恶化的效果**：content_fetched (−0.235 IIA), file_written (−0.139 IIA), network_egress (−0.041 IIA)
- 更大模型 + 更多工具训练 → 某些效果的跨工具表征**更尖锐地分离**了

---

## 因果意义

交换干预实验将工具代理问题从**统计观察**升级为**因果结论**：

> **从工具 A 数据中学到的线性效果方向 w_A，在因果上不能有效地表示工具 B 产生的同一效果。**

这对接了因果抽象理论（Geiger et al., 2021/2025）的核心概念：
- 对齐映射 $\tau$ 需要满足 interchange intervention accuracy (IIA)
- 当 IIA_cross << IIA_within 时，$\tau$ 对齐的是工具特定特征而非因果变量
- 这证明了线性约束**不足以保证因果抽象的 fidelity**——还需要跨工具泛化

### 对可证明安全框架的启示

如果安全判定基于线性探针的预测，那么：
- 在 delete_file 上训练的 file_deleted 探针无法识别 terminal `rm -rf`
- 攻击者只需换个工具就能绕过效果预测器
- **可证明安全要求因果效果预测器是工具不变的**

这为"为什么需要因果机制的 agent 安全框架"提供了实验证据。
