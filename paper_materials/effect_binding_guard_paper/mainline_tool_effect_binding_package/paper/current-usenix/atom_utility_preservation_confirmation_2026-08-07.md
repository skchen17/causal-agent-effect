# Atom 表示效用保持确认报告（2026-08-07）

## 1. 要回答的问题

本轮只回答一个窄问题：把离线反事实注册得到的紧凑 effect-atom 描述加入
side-effectful tool 的描述后，在不启用 runtime guard 的情况下，是否降低 agent
完成官方良性任务的效用。该问题与“当前 authority interface/guard 是否已经无损”
严格分开。

## 2. 两层实验

### 固定成功轨迹

在 Qwen3-32B 已被 AgentDojo 官方评分为成功、且与 reviewed manifest 重叠的轨迹上，
atom 投影后重建原始 effectful call 为 `20/20 = 1.000`。现有 strict authority
interface 只保持 `1/17`，失败主要来自 resolver、canonicalization 和 manifest
语义不匹配。因此，旧 guard 的效用损失不能直接归因于 atom 表示丢失调用信息。

### Agent 行为非劣效

- Benchmark：AgentDojo v1.1.2 全部 97 个官方良性任务。
- Model：DeepSeek v4 Flash，temperature 0。
- Conditions：pristine、字符等长 compact-neutral、compact-atoms。
- Repeats：2；共 `97 x 3 x 2 = 582` 条。
- Guard：关闭；工具执行只发生在 AgentDojo sandbox。
- Descriptor scope：25 个已注册 effectful tools、67 个安全字段。其中 24 个使用
  LLM effect inventory 加单字段 sandbox state/output counterfactual；
  `get_webpage` 使用显式外部网络效果规则。
- 主判定：`compact_atoms - pristine` 的 task-clustered 单侧 95% bootstrap 下界
  高于 `-0.05`。
- 调度：第一轮 pristine→neutral→atoms，第二轮 atoms→neutral→pristine，形成
  crossover；修正发生在完整 atom 主结果可见前，不改变任务、条件或判据。

## 3. 结果

| Condition | Utility | Rate | Model parse failures |
|---|---:|---:|---:|
| pristine | 168/194 | 0.866 | 0 |
| compact-neutral | 177/194 | 0.912 | 1 |
| compact-atoms | 173/194 | 0.892 | 1 |

主比较 `compact_atoms - pristine = +0.0258`。task-clustered bootstrap 95% 区间为
`[-0.0103, 0.0670]`，单侧 95% 下界为 `-0.00515`，高于预注册的 `-0.05`，因此
通过 5 个百分点的非劣效判定。配对观测中有 162 个双成功、15 个双失败、11 个
atom gain 和 6 个 atom loss。

次比较 `compact_atoms - compact-neutral = -0.0206`，95% 区间为
`[-0.0619, 0.0206]`，单侧下界为 `-0.0567`，未通过 5 个百分点非劣效门槛。
neutral 的高点估计说明通用接口文本本身也会改变模型注意力和轨迹。因此，本轮
不能声称 atom 内容提高了效用，只能支持它相对原始工具描述没有造成可检测的
5 点以上效用损失。

两条 malformed tool-argument JSON 均保留为效用失败，分别位于 compact-atoms
和 compact-neutral；没有成功重采样。网络/API 基础设施失败为 0，prompt leakage
violations 为 0。

## 4. 对论文贡献的含义

可以支持的声明：

> On all 97 official benign AgentDojo tasks over two repeats, compact
> counterfactually registered atom descriptions are non-inferior to the
> original tool descriptions at a five-point margin when the runtime guard is
> disabled (173/194 vs. 168/194; clustered one-sided 95% lower bound, -0.005).

该结果降低了“atom 表示本身导致效用下降”的审稿风险，并与固定轨迹 20/20
round-trip 形成互补证据。

不能支持的声明：

- atom 描述在效用上优于通用提示或等长文本；
- 当前完整 guard 已实现无效用损失；
- authority interface、resolver 或 recovery 已经解决；
- atom 描述单独降低攻击成功率；
- 对其他模型、基准或部署环境零损失。

## 5. 后续论文处理

论文应把效用问题拆成两层：

1. 表示兼容性：固定成功调用 20/20 round-trip，加全量良性任务非劣效结果；
2. 完整 guard 效用：仍保留 Qwen3-32B `63/97 -> 33/97` 的负面结果，并将其归因
   边界写为 authority、resolver、plan/recovery interface 的组合问题，而非已经
   证明的单一根因。

这能让论文重心继续放在“最小安全相关工具效果表示及其反事实注册”，而不把
recovery 机制包装成核心创新。下一项安全实验应使用相同 compact-atoms 条件与
匹配 neutral/pristine 对照测攻击任务，验证 atom 内容是否带来安全辨识增益；本轮
良性结果本身不回答该问题。

## 6. 正源文件

- `experiments/security-analysis-ablation-and-overhead/results/atom-utility-preservation-confirmatory/summary.json`
- `experiments/security-analysis-ablation-and-overhead/results/atom-utility-preservation-confirmatory/deepseek_compact_behavior_summary.json`
- `experiments/security-analysis-ablation-and-overhead/results/atom-utility-preservation-confirmatory/deepseek_full_benign_noninferiority_summary.json`
- `experiments/security-analysis-ablation-and-overhead/results/atom-utility-preservation-confirmatory/atom_utility_preservation_evidence.json`
- `experiments/security-analysis-ablation-and-overhead/evaluation/atom-utility-preservation-confirmatory/deepseek_full_benign_noninferiority_protocol.json`
- `experiments/security-analysis-ablation-and-overhead/evaluation/atom-utility-preservation-confirmatory/full_run_scheduler_amendment.json`

