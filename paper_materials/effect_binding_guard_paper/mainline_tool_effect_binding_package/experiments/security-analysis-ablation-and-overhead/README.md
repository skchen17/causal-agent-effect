# 安全模型消融自适应攻击与开销

## 目的

补充条件性安全论证、机制贡献、自适应攻击和系统代价。

## 流程

映射理论前提到实现，逐项消融关键组件，运行自适应攻击，再测量 runtime 各阶段开销。

## 包含内容

- **条件性效果合约安全模型**：形式化在效果抽象、独立权限、完整中介与 check-use 一致性前提下的安全边界。
- **运行时机制消融**：量化 atom、别名、来源、权限包络、重规划和 fail-closed 等组件的贡献。
- **自适应攻击评测**：测试了解守卫逻辑的攻击是否能利用别名、默认值、组合调用和重规划接口绕过控制。
- **运行时开销测量**：量化 atom extraction、diff、授权检查和反馈处理带来的延迟与吞吐开销。

## 结论边界

安全结论依赖明确前提；微基准不能替代完整端到端部署测量。

## Reviewed-Authority Qwen3-32B 对比

`scripts/runtime-mechanism-ablation/run-e84-qwen32-reviewed-authority-baselines.py`
负责运行 Qwen3-32B reviewed-authority 子集。先用四个方法各四个良性和四个攻击
case 做接线测试；正式运行只新增 reviewed-authority 方法的 26 个良性 case 和
169 个官方攻击组合。No guard、Prompt Sandwiching 和 PromptArmor-local 从 E78
已完成的同 checkpoint、同 65,536 上下文、同 AgentDojo v1.1.2 日志中按 case key
抽取，避免重复推理。

`scripts/runtime-mechanism-ablation/summarize-e84-qwen32-reviewed-authority-baselines.py`
会核对 checkpoint SHA、上下文、benchmark 版本、每方法 case 数和逐 case 配对，
并检查被拒绝的调用是否仍被执行。Smoke 结果只验证运行链路，不能作为论文性能
证据；只有 195-case 正式结果通过汇总门禁后才能进入主表。

## Qwen3-32B 运行时机制消融

`scripts/runtime-mechanism-ablation/run-e81-qwen32-runtime-ablations.py`
在同一 Qwen3-32B checkpoint、65,536 上下文和 reviewed 26-task AgentDojo
子集上运行 A0/A1/A2/A7/A9/A11/A12/A13/A15。A2、A7、A9、A11、A12、
A13 和 A15 各自只切换一个运行时机制；现有 E84 运行时和结果不会被覆盖。

`scripts/runtime-mechanism-ablation/summarize-e81-qwen32-runtime-ablations.py`
按 26 个良性 key 和 169 个官方攻击 key 做逐行配对，核对 checkpoint、上下文、
case 数和 runtime audit，并对各消融相对 A1 计算 exact McNemar、paired bootstrap
和 Holm 校正。

`scripts/runtime-mechanism-ablation/audit-e81-ablation-applicability.py`
单独审计每个开关在该子集中的适用样本。当前子集只有两个 reviewed effectful
authority rows、一个 typed resolver row，且没有 dynamic security default；
因此 A13 只能作为接线一致性行，不能单独支撑默认值机制的经验结论。

`scripts/audit_agentdojo_effectful_defaults.py` 进一步扫描并执行 AgentDojo
v1.1.2 中已纳入效果投影审查、且带可选参数的 effectful tool。当前共覆盖 7 个
工具实例和 22 个可选字段；所有声明默认值均为空值或 `None`，省略参数与显式传入
默认值在 7/7 次沙箱执行中产生相同效果。该结果说明 AgentDojo 当前版本不提供
可用于检验非空或状态依赖默认值的样本，不能据此宣称该机制已获得基准实证。

## 粗 policy 族 × qualifier-deletion 敏感性（E2）

`source/policy-family-sensitivity/run_policy_family_sensitivity.py`
只读使用两个冻结有限域（56-call AgentDojo 有限域、32-context ToolSandbox
held-out 域），对四个预先枚举的授权族（power-set 基线、effect-kind 聚合、
resource 聚合、计数截断 {0,1,≥2}）与五个 qualifier 角色删除（none/date/
subject/recurrence/payload/visibility）逐一重算 separating pairs、冗余对、
overpartition 与假拒绝对，输出 family×qualifier 敏感性表、逐 qualifier 判定、
双向 claim boundary 预案与 family 枚举原则表注。族集定义为 submultiset 权威
构造在固定出现投影格下的像，先于任何指标计算声明；所有删除操作只作用于
typed-contract 表示，族投影作用于未修改的 source-effect 多重集。脚本为纯
CPU、纯标准库、确定性输出；基线复现校验（power-set×none 精确划分、全
qualifier 删除复现 118/41）内置为验收门禁。结果位于
`results/policy-family-sensitivity/`（JSON + Markdown 报告 + 网格 CSV），
测试位于 `tests/tests/test_policy_family_sensitivity.py`。该实验只回答
"qualifier 必要性相对于哪个授权族成立"，不外推到开放工具域或部署策略语言。

## 效果表示与权限接口四格诊断

`source/joint-effect-authority-diagnostic/` 在 reviewed-authority 的 26 个任务、
26 条良性轨迹和 169 条攻击轨迹上做确定性固定轨迹分析。四格分别替换当前或
source-reviewed 效果表示，以及 reviewed authority 或 AgentDojo 官方
`ground_truth()` evaluation oracle。模型轨迹、攻击目标和攻击标签均不参与
oracle 构造；诊断不调用 LLM、不执行工具。

在 180 条共同支持轨迹上，四格均接纳 170 条。当前与 source-reviewed 字段在
16 个已审工具上一致，reviewed authority 与官方 oracle 对 195 条轨迹的接纳
判定一致。20 条 no-guard utility 成功良性轨迹中，19 条符合官方调用链且全部被
reviewed authority 接纳；剩余一条包含未被用户任务要求的额外转账。五条
no-guard 成功攻击中，四条包含受中介副作用调用且均被拦截，另一条没有此类调用，
位于该 pre-commit 诊断的作用域外。

这些数字是固定轨迹可接纳性，不是重新运行后的 ASR 或 utility；官方调用链也可能
排除其他合法计划，因此不能作为可部署权限。当前 runtime 已经使用 reviewed
projection 区分 observation-only 工具，所以 effect 侧的零差异是集成一致性检查，
不是独立验证。

## 良性效用路径与有界关系修复

`source/headline-benign-utility-pathway-audit/` 审计冻结的 E78 日志，并将效用
损失定位到初始权限计划、typed evidence 和恢复路径。修复后的运行时把权限范围
扩展与单次调用修正分开，并只允许目录中显式注册的 source projection 和 runtime
default。

代表性账单任务的 v8 端到端机制烟测中，Qwen3-32B 首次提出的日期和主题不匹配，
runtime 返回逐字段修正信息；第二次调用使用已配置执行日期和已注册账单主题关系，
良性任务成功执行。配对注入文档没有产生注册 projection，也没有执行注入转账。
对应结果为：

- `results/headline-benign-utility-pathway-audit/call-revision-routing-v5-smoke.json`
- `results/headline-benign-utility-pathway-audit/registered-relation-planner-model-pilot.json`
- `results/headline-benign-utility-pathway-audit/bounded-relation-v8-end-to-end-smoke.json`

这些结果只证明一个固定账单 schema 上的机制可行性，不估计 AgentDojo 全基准的
效用或攻击成功率。冻结后的 16 条良性机制 pilot 进一步得到：12 条历史
trusted-source resolver 损失中只恢复 1 条，4/4 稳定控制保留成功，零运行错误，
零非 `ALLOW` 检查到达执行。11 条剩余失败中，7 条仍缺运行时关系，4 条在权限
计划构造阶段失败。该负面结果说明单个账单 relation 不足以泛化；下一步需要
预声明、验证并冻结系统化 relation onboarding，而不是默认放行未解析值。对应
gap inventory 含 14 个精确 `source_tool -> target_tool.field` 组和 17 条
relation-case 行；只有两个账单绑定出现在恢复案例中，12 个组出现在失败案例中。
这些组是待验证接口需求，不是可直接注册的授权。

目录名按实验内容命名。历史实验编号只保留在原始 artifact 内容和兼容路径中，不再作为目录名。
