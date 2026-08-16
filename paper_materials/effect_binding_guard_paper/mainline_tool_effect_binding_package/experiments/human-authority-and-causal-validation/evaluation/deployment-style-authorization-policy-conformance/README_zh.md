# 部署式授权策略接口合规实验

## 目的

这是正式冻结版本。它使用四个带状态的复制 sandbox 工具以及 ACL、capability、delegation 风格策略，比较工具名、canonical raw arguments、既有定义的 common effect fields 和 validated typed effects。

`common_effect_fields` 保留 effect、operation、resource type、resource ID、target principal 和 commit mode，仅去除 tool-specific qualifiers。该定义与论文现有 coarse-view 比较一致。

四种表示使用同一个有限域 policy consumer。主模式对 mixed cells 返回 `ABSTAIN`；统一 fail-open/fail-closed 诊断分别报告 unsafe allow 和 false denial。source post-state 只用于离线 descriptor 检查和 ideal policy decision，不进入 pre-commit representation。
