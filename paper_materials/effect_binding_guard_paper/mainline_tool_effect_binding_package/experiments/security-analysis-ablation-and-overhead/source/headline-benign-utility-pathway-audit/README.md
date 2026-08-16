# E78 主结果良性效用路径审计

本实验对冻结的 E78 capacity-matched 结果做零模型调用、零工具执行的逐任务审计。
它回答两个问题：

1. `63/97 -> 33/97` 的效用差距主要出现在哪类轨迹中；
2. 失败前是否真实出现 runtime replan/deny 反馈，以及反馈涉及初始权限计划、
   字段绑定、可信证据接口还是恢复状态。

审计不修改 AgentDojo 官方效用标签。`literal_grounding_probe` 只检查被拒值是否
字面出现在原任务或此前的良性工具结果中，不能替代语义关系、可信度或授权判断。
由于 no-guard 与 guarded 轨迹是两次独立模型运行，输出使用“observed pathway”
口径，不把分层差异写成随机化因果效应。

运行：

```bash
python experiments/security-analysis-ablation-and-overhead/source/\
headline-benign-utility-pathway-audit/run_audit.py
```

输出位于：

`experiments/security-analysis-ablation-and-overhead/results/headline-benign-utility-pathway-audit/`

同目录的 `run_source_relation_probe.py` 运行四个确定性对照：正确 resolver
source、正确 source 加语义字段约束、错误 source 名称、以及含两个候选标识符的
歧义结果。该探针用于区分 projector 故障与 source-relation 构造故障，不估计
端到端效用恢复。

`run_planner_source_catalog_pilot.py` 是三任务本地模型检查。它验证修复后的
planner prompt 是否真实显示 resolver source 名称与工具返回字段，以及生成的
计划能否通过来源 schema 校验。该脚本不执行工具，也不估计端到端效用或攻击率。

`analyze_source_catalog_smoke.py` 汇总修复后的两行 Qwen3-32B AgentDojo
端到端 smoke。它检查 amount/recipient 是否已从账单读取结果绑定，并保留
date/subject 关系仍未证明导致的拒绝。该结果仅定位下一接口缺口，不作为主结果。

`analyze_call_revision_routing_smoke.py` 检查 v5 是否把单次调用修正与权限范围
扩展分开。`run_registered_relation_planner_pilot.py` 检查模型能否选择账单主题
projection 和执行日期 default。`analyze_bounded_relation_smoke.py` 检查 v8
中第一次失败调用能否通过确定性反馈修正，并确认注入文档不会产生注册
projection。

`build_registered_relation_benign_pilot_manifest.py` 从冻结的旧 E78 审计中选择
全部 12 条“良性 1->0 且可信上游结果含待解析值”的历史损失，并加入每个 suite
一条稳定成功控制。生成的 16 条 manifest 在 v8 运行前冻结，明确标记为
outcome-conditioned mechanism pilot，而非 AgentDojo 总体效用估计。运行命令：

```bash
python experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/\
run-recovery-normalization-qwen32.py \
  --mode pilot \
  --case-manifest experiments/intent-bound-runtime-guard/evaluation/\
effect-difference-runtime-guard/registered_relation_benign_pilot_manifest.json \
  --run-tag registered-relation-benign-pilot-v8-suite-scope-fix \
  --execution-date 2026-07-30
```

完成后由 `analyze_registered_relation_benign_pilot.py` 在固定分母上汇总目标恢复、
控制保留、错误和执行前检查一致性；任何失败案例都保留。首次
`registered-relation-benign-pilot-v8` 运行也被保留，但只完成 banking 的 4 条；
其他 suite 因全局账单 relation 被错误强制注册而退出，不能作为实验结果。修复仅
在目标工具整个不属于当前 suite 时跳过 relation；目标工具存在而字段缺失仍会
失败。
