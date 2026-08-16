# Atom 与原始字段语义归因实验

## 目的

该实验不尝试证明反事实注册一定会删除字段。它在原始字段 registry 和 validated descriptor 都保留相同 25 个工具、67 个字段的条件下，比较不同表示能否保留授权所需的区别。

比较对象为工具名、完整原始调用、逐叶原始字段、反事实修正前的 common-effect 表示、反事实验证后的 typed atoms，以及只用于评分的源码效果 oracle。

## 独立变量与固定条件

- 唯一改变的是 monitor 可见的表示。
- 源码执行得到的 committed effects、授权谓词、决策规则和 88 个冻结上下文保持不变。
- source effects 只产生理想决策，不进入任何候选表示。
- 协议不要求 atom 获胜；负面结果同样满足实验完整性门禁。

## 输出

完整运行写入 `results/atom-vs-field-semantic-attribution/`：

- `atom-vs-field-report.json` 与 `.md`；
- `policy-representation-metrics.csv`；
- `ordered-authorizer-metrics.csv`；
- `ordered-authorizer-decisions.jsonl`；
- `ambiguity-witnesses.jsonl`；
- `field-set-control.json`；
- `queue-status.json`。

该实验是确定性机制实验，不调用 LLM、不执行外部服务，也不与当前 GPU 强基线竞争。
