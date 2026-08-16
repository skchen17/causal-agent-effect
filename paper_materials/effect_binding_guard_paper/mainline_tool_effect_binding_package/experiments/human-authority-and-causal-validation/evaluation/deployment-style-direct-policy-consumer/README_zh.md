# 直接授权策略消费者扩展

该扩展消除 finite-cell consumer 可能使用完整测试关系进行编译的 oracle-alignment 疑问。授权函数只读取冻结 policy manifest 与当前 representation；ideal decision 仅在预测完成后用于评分。

工具名和 raw arguments 不携带 effect inventory，统一消费者不会导入 typed descriptor 来帮助这些 baseline，而是返回 `ABSTAIN`。Common fields 可以解析 resource/target 规则，但 policy 依赖被移除的 qualifier 时会 `ABSTAIN`。Typed effects 提供完整的受测 policy interface。
