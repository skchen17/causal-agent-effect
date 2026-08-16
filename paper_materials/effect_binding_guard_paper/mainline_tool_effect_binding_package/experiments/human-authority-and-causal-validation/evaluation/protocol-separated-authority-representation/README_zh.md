# 协议隔离的授权表示实验

本实验验证 typed-effect representation 在明确 ACL、capability 和 delegation authority state 下，是否比 tool name、raw arguments 和 common effect fields 更充分地支持授权。

关键隔离：

- copied sandbox 只执行工具并产生状态变化；
- transition oracle 只读取 before/after state，不导入 descriptor；
- descriptor runtime 只解释冻结 JSON，不导入 oracle；
- authority model 以 subject、resource ACL、capability possession 和 delegation scope 判定请求；
- evaluation generator 不读取 descriptor 或结果标签；
- policy-separating mixed cells 在执行和标注后自动发现，不预先人工配成一正一负。

运行：

```bash
python -m shared.compatibility.scripts.independent_authority_benchmark.run_experiment --force-freeze
python -m shared.compatibility.scripts.independent_authority_benchmark.run_experiment --run
```

该实验仍是作者构建的受控 benchmark，不是独立作者数据，也不估计真实部署中的错误发生率。
