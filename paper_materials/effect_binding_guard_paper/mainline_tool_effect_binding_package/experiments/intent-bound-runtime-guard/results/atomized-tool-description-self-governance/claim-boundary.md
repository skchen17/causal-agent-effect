# Claim Boundary

本实验把两个问题分开：经过反事实验证的 atom 表示能否直接帮助 LLM 自身决策，以及确定性 runtime guard 在相同表示之上增加多少安全性和代价。

当前 smoke 只支持实现级结论：A--D 不执行 atom/forecast，E 才执行 `fail_closed` mediation；各条件使用 label-hidden 工具描述；AgentDojo 工具仅在 sandbox 中执行；缺失或格式错误的 forecast 均被保留。

当前 smoke 不支持以下声明：atom 表示已普遍降低攻击成功率、已保持完整 benchmark 效用、已满足 production safety、LLM 可独立替代 complete mediation，或 E 的收益全部来自表示而不是 guard。

在多套件、token-matched、同模型同任务的 A0/A/B/C/D/E 协议完成前，论文只能把该实验写成 mechanism-isolation pilot。D 相对 A/B 才衡量经过验证的表示本身；E 相对 D 才衡量 deterministic guard 的增量。

四套件 targeted pilot 已完成，但 representation-only gate 未通过。当前结果不支持“把 validated atoms 加入工具描述即可提升 LLM 自身安全决策”的声明。它支持更窄的结论：反事实验证的 atoms 表示 effect-bearing fields，但可靠授权仍需把这些实例化 effects 显式绑定到原始任务和 provenance-separated evidence。该结论必须保留为负面机制结果，不能用后续 guard 的低 ASR 覆盖。

同模型显式 pre-commit reviewer 的 smoke 也未通过效用门禁。即使要求逐字段检查，reviewer 仍把错误 recipient 判为 supported、把正确派生 amount 判为 conflict。论文不得声称 LLM reviewer 已解决 authority binding；该结果只支持“atoms 指明检查对象，但精确 canonicalization/equality/arithmetic 仍需结构化接口和确定性检查”的设计结论。
