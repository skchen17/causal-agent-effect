# 实验 1: 因果效果的线性可编码性扫描

## 研究问题

在 agent 安全场景中，LLM 的内部表征是否以**线性可编码**的方式编码了工具调用的因果效果？

## 实验逻辑

```
工具调用场景 (文本描述) → LLM 嵌入 → 线性探针 → 预测因果效果
                                              ↓
                                   R² (每个效果的线性可编码性)
```

## 因果效果定义

基于 CAR 的效果分类体系，定义以下二元因果效果：

| 效果 | 定义 | 风险等级 |
|------|------|---------|
| command_executed | 在系统上执行了命令 | HIGH |
| file_written | 向文件系统写入了数据 | MEDIUM |
| file_deleted | 从文件系统删除了文件 | HIGH |
| file_content_read | 读取了文件内容 | LOW |
| message_sent | 向外部发送了消息 | HIGH |
| network_egress | 网络数据出站 | HIGH |
| subagent_spawned | 创建了子代理 | HIGH |
| content_fetched | 从 URL 获取了内容 | LOW |
| search_performed | 执行了搜索 | LOW |
| memory_updated | 更新了持久化记忆 | LOW |
| tool_error | 工具执行出错 | BENIGN |

## 工具定义

| 工具 | 典型固有效果 |
|------|------------|
| terminal | command_executed, network_egress |
| write_file | file_written |
| read_file | file_content_read |
| delete_file | file_deleted |
| send_message | message_sent, network_egress |
| web_fetch | content_fetched, network_egress |
| web_search | search_performed, network_egress |
| delegate | subagent_spawned |
| memory | memory_updated |

## 实验步骤

### Phase 1: 数据生成

生成三种数据源：

1. **规则模板数据** (N=1000): 从工具 × 状态 × 参数的模板生成场景文本
2. **LLM 合成数据** (N=500): 用 LLM 生成多样化的 agent 工具调用场景  
3. **真实执行数据** (N=待定): 从 Hermes 或其他 agent 的实际执行中收集

### Phase 2: 嵌入提取

从 LLM 的隐藏状态中提取嵌入：
- 每个场景文本 → LLM → 最后一层隐藏状态 → $h \in \mathbb{R}^d$
- 也提取中间层 (−4, −8 层) 以对比不同抽象级别的线性可编码性

### Phase 3: 线性探针训练

对每个效果 E，训练：
- 逻辑回归: $P(E=1|h) = \sigma(w^T h + b)$
- 5 折交叉验证
- 记录 F1, AUC, R²

### Phase 4: 分析

按效果排名线性可编码性，检验以下假设：
- H1: 高频效果具有更高的线性可编码性
- H2: 不同模型层的线性可编码性不同
- H3: 效果复杂度影响线性可编码性

## 独立于 CAR

- 不依赖 CAR 代码
- 不依赖 Hermes
- 只依赖: Python, transformers/sentence-transformers, scikit-learn
