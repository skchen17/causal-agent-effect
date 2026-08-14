# Concrete-Atom Authorizer 小规模机制实验

本实验使用已经冻结并执行过的 32 个 ToolSandbox 上下文，检查经验证的 concrete effect atoms 能否真正作为授权接口，而不仅是效果表征。

每个上下文轮流提供一个允许的 concrete-effect 多重集合，再检查同一工具的其他上下文是否属于该权限范围。全量实验共有 232 个有序查询，并比较五种观察方式：工具名、原始参数精确匹配、公共 effect 字段、完整 concrete atoms 和 source-effect oracle。

该实验只验证有限域中的授权关系实现能力。权限集合来自已经执行的效果集合，不是人工编写的真实组织策略，因此结果不能解释为完整授权系统或生产安全证明。

运行入口：

```bash
python scripts/run_toolsandbox_concrete_atom_authorizer.py --mode smoke
python scripts/run_toolsandbox_concrete_atom_authorizer.py --mode full
```
