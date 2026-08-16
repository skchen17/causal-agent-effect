# 第五章安全分析审计

审计日期：2026-08-13

## 总体结论

第五章的定义、定理和证明在修订后是自洽且成立的。它证明的是三个有边界的结论：表示碰撞带来的不可避免取舍、有限干预域上的反例驱动细化、以及满足显式前提时的单次提交安全性。它不证明开放域 descriptor 完备、provenance/grounding 天然可靠、完整 ACL 授权、轨迹级累计权限或生产系统安全。

## 逐项判定

| 内容 | 判定 | 依据与边界 |
|---|---|---|
| Authorization sufficiency | 正确 | 使用理想语义视图 `omega(u)=(mu(u), gamma(u))`，同时覆盖提交效果和策略相关 provenance；定义相对于域 `D` 和策略族 `P`。 |
| Representation collision theorem | 正确 | 对同一策略上下文，若两个调用的 monitor view 相同而理想判定不同，确定性 monitor 必须在 unsafe allow 与拒绝/搁置合法工作之间至少承担一种错误。 |
| Counterfactual witness | 正确 | 反事实对是证伪工具；只有理想策略判定被区分但表示未区分时，才构成 sufficiency 反例。输出字符串变化本身不是证据。 |
| Finite refinement termination | 正确且有界 | 不合并 partition、每步进行非空 split 时最多 `|D|-1` 次；只有以“无 policy-mixed cell”为停止条件时，才能推出该有限域和策略族上的 sufficiency。 |
| Conditional atom-level mediation | 正确但条件性强 | descriptor fidelity、authorizer soundness、complete mediation、call 与 policy-snapshot check-use consistency 共同推出允许提交满足理想策略。实验只能有限验证这些前提，不能由定理反向证明前提成立。 |
| Provenance-origin confinement | 正确但仅适用于当前 profile | 需要 descriptor 覆盖、value/effect-request provenance 完整、task grounding 无误报、complete mediation 和 exact-call execution。结论不等价于 ACL entitlement，也不是一般因果归因。 |

## 本轮修正

1. 明确 monitor 可以看到策略上下文 `P`，但关于调用本身只能看到 `rho(u)`。
2. 将理想语义从仅有 `mu(u)` 扩展为 `omega(u)=(mu(u), gamma(u))`，修复 provenance 策略无法由状态变化单独表达的问题。
3. 将 policy snapshot integrity 纳入 atom mediation 定理的 check-use 前提。
4. 为 provenance-origin 定理补充 untrusted effect-request 提取和 authenticated grounding soundness 前提。
5. 把 finite refinement 的停止条件写成显式条件，避免把有限 partition 必然终止误写成算法必然找到充分表示。
6. 明确 `introduced solely` 是当前集合 profile 的定义，不是一般 causal attribution 声明。

## 可执行核对

- 有限模型穷举 27 种三上下文表示、54 个 authorization-separating collisions 和每个 collision 的三种 monitor decision。
- 多策略表检查通过。
- 条件性 mediation 的 allow implication 检查通过，并构造 policy snapshot 改变时的反例。
- provenance inclusion profile 穷举 256 种组合，并构造漏提取 effect request 和错误 grounding 时的反例。
- 加入相同 effect multiset、不同 provenance、相反策略判定的表示碰撞检查。
- 理论及 AgentDojo 复合效果相关测试共 6 项通过。

## 投稿前仍需保持的边界

- 不能把有限域 sufficiency 写成开放域或全局最小性。
- 不能把 counterfactual testing 写成对未测试效果的证明。
- 不能把 conditional mediation theorem 写成当前 AgentDojo 实现已满足全部前提。
- 不能把 provenance-origin confinement 写成完整授权、委托、配额或组织 ACL。
- concrete-atom authorizer 完整实验完成前，只能把 ToolSandbox 称为有限机制实例。
