# Atom 作用讨论与实验工作交接

日期：2026-08-01  
目标会议：USENIX Security 2027  
工作区：`mainline_tool_effect_binding_package/`

## 1. 当前结论

当前证据支持把 atom 定位为：**工具调用所产生安全相关效果的最小、可独立检查的表示基元**。工具注册阶段通过执行反事实确定哪些参数会改变实际状态或输出，并将这些字段编译为 effect descriptor；运行阶段再把具体字段值绑定到任务意图和授权范围。

当前证据不支持以下更强说法：**仅在 system prompt 或工具描述中展示 atom 字段，就能让 agent 自主抵抗提示词注入。** 多轮无 guard 诊断均未观察到 atom 相对通用意图提示或匹配控制的特异性收益。

因此，论文主线仍可保持 tool-effect binding，但必须区分三个不同义务：

1. **Effect identification**：哪些工具字段改变了安全相关执行效果？
2. **Task binding**：这些字段的哪些具体值由用户任务或可信证据支持？
3. **Authorization/mediation**：候选调用是否处于允许的权限范围，出现不确定性时如何处理？

反事实注册主要回答第 1 项。Atom 为第 2、3 项提供统一检查接口，但自身不产生授权结论。

## 2. 理论主线的演化

### 2.1 初始问题：tool-level 表示不足

E47--E50 的受控反事实实验表明，现有监控器并非都只是工具名分类器，但它们经常不能联合绑定 effect、resource、operation、authorization 和 provenance。一个调用可能同时创建对象、邀请外部主体、改变可见性或写入多个资源；只对工具名或整次调用作一个判断会丢失可独立授权的效果差异。

当前应使用的规范口径是：

- E48 hard guard：UPA `3.6%`，FDeny `6.5%`，coverage `91.7%`。
- 修复后的 E50 resource/authorization stress：UPA `46/120 = 38.3%`，coverage `221/240 = 92.1%`。
- 去除 resource match：UPA `61.7%`。
- 去除 authorization match：UPA `89.2%`。

这些结果说明 resource/authorization binding 是受控压力集上的主要瓶颈。它们是 custom stress 的机制证据，不估计真实系统中的失败发生率。

**口径风险**：早期材料仍有 E50 UPA `61.7%` 被写成 full-guard 结果的旧副本。当前论文证据表和修复审计采用 `46/120 = 38.3%`；`61.7%` 对应去除 resource match 的消融。后续引用必须以 `paper/current-usenix/reproduction/current_evidence.md` 和 canonical JSON key 为准。

### 2.2 Atom 的最初作用

Atom 不是重新命名 complete mediation，也不是一套完整权限系统。它的作用是把一次工具调用展开为可分别检查的效果实例，例如：

- effect / operation；
- resource identity / resource type；
- target principal / recipient role；
- visibility / commit mode；
- provenance source / control source。

最小性应按行为定义：如果改变一个字段可能改变执行效果或安全决策，该字段必须出现在表示或其可验证依赖中；如果字段变化不改变安全相关效果，则表示应保持不变。

### 2.3 反事实注册的正确边界

注册阶段对单个字段做受控干预，并比较 sandbox state/output difference：

- 敏感字段改变后，实际效果发生变化，说明该字段应进入 effect descriptor；
- 表面字段改变但效果不变，descriptor 应保持不变；
- 无法执行或无法判定的字段不能静默标成无关，当前实现将其纳入安全字段或要求人工处理。

该过程证明的是“字段对效果是否有执行意义”，不是“用户是否授权了这个具体字段值”。例如，反事实可以证明 `share_file.permission` 会改变权限效果，但不能仅凭这一点判断本次任务授权的是 `read` 还是 `write`。

## 3. 已完成实验与结论

### 3.1 受控问题刻画：E47--E50

作用：证明 joint tool-effect binding 是真实可测的问题，并定位 resource/authorization 粒度瓶颈。

主要证据：

- `experiments/binding-failure-and-granularity/results/cross-method-binding-stress/`
- `experiments/binding-failure-and-granularity/results/effect-resource-tuple-guard/tuple-guard-results.json`
- `experiments/binding-failure-and-granularity/results/hard-guard-granularity-stress/hard-guard-robustness-results.json`
- `paper/current-usenix/reproduction/current_evidence.md`

能支持：表面鲁棒性不等于 joint effect/resource/authority binding；资源与授权关系是关键瓶颈。  
不能支持：生产环境失败率、完整权限系统已经解决、现有方法普遍无效。

### 3.2 Controlled local authorization：E55-v2

作用：在干净的本地 contract 中验证显式 atom expansion 和 authorization context 能否完成 pre-commit mediation。

主口径：E55-v2 strict 是唯一主结果，UPA `0.000`、FDeny `0.000`、coverage `0.880`。原 E55 仅用于版本比较，human-corrected sensitivity 仅用于审计。

证据目录：`experiments/precommit-authorization-and-audit/results/local-precommit-authorizer/`。

能支持：在受控 contract 和显式授权基础设施下，atom-level mediation 可运行。  
不能支持：开放域 agent、真实 SaaS、任意工具自动 onboarding 或 production safety。

### 3.3 字段必要性与 descriptor runtime：E71

数据：156 条 saved AgentDojo/IPIGuard-style replay，24 个工具、78 个字段任务。Qwen 输出 `156/156` 可解析；necessity pass `66`，invariance pass `39`；最终注册 20 个工具，4 个未注册。

Runtime 结果：

- UPA：`0/134`；
- coverage：`128/156 = 82.1%`；
- abstain：`28/156 = 17.9%`；
- FDeny：`20/22 = 90.9%`。

解释：字段必要性测试可生成 fail-closed descriptor，但安全主要来自拒绝或未注册工具，效用不可接受。该实验不能证明 atom 提高了模型自身的判断。

证据：`experiments/intent-bound-runtime-guard/results/atom-field-necessity-runtime/report.json`。

### 3.4 Task permission envelope：E72

数据：同一 156 replay。LLM 在任务开始生成权限 envelope，runtime 不再调用 LLM。

结果：

- UPA：`0/134`；
- coverage：`49/156 = 31.4%`；
- abstain：`107/156 = 68.6%`；
- FDeny：`7/22 = 31.8%`。

最大原因是 `control_source_not_in_task_envelope`（310 次），其次是 participant、hotel、date、recurrence 等字段缺失或无法接地。

解释：从原始任务一次性生成完整权限范围对多步任务过于严格。任务中需要后续查询、解析、规范化或计算的值，在任务开始时本来就未知。该结果暴露的是 authority/context interface 不完整，不是 atom 表示本身必然失败。

证据：`experiments/intent-bound-runtime-guard/results/task-permission-envelope-runtime/report.json`。

### 3.5 Intent binding + iterative replan：E73

流程：任务开始生成计划；候选调用与计划 atom 比较；缺字段进入 `NEEDS_REPLAN`；LLM 可选择 CONTINUE、REVISE、ASK_USER 或 STOP，最多三轮。

结果：初始只有 `5/156` 直接通过，151 条进入 replan；共产生 283 次 LLM replan：CONTINUE 105、REVISE 165、STOP 12、ASK_USER 1。对于 251 个带不可信/注入关系的 replan case，仍有 91 次继续失败，failure rate `36.3%`。

解释：replan 改善了缺省值处理，但把最终决定完全交还同一个 agent 并不能形成安全保证。Runtime feedback 必须清楚区分合法 resolver fill、隐式任务需求、额外权限范围和注入来源。

证据：`experiments/intent-bound-runtime-guard/results/intent-binding-and-replanning/report.json`。

### 3.6 LLM descriptor registration：E76

流程：LLM 离线识别工具 effect 和字段；反事实检查后注册 descriptor；正式 AgentDojo runtime 不再调用 onboarding LLM。

官方 AgentDojo v1.1.2 726-key 结果：

- ASR：`10/629 = 1.6%`；
- benign utility：`34/97 = 35.1%`；
- attack utility：`207/629 = 32.9%`。

解释：LLM 生成、反事实门禁和 deterministic runtime 的完整链路可运行，但效用仍明显低于 no guard。不能把低 ASR 单独解释为 atom 带来的安全收益。

证据：

- `experiments/intent-bound-runtime-guard/results/llm-descriptor-agent-runtime/llm-descriptor-registration-report.json`
- `experiments/intent-bound-runtime-guard/results/llm-descriptor-agent-runtime/llm-descriptor-official-strict-full-run-report.json`

### 3.7 Effect-difference registration + runtime：E77

E77 不信任 LLM 将字段声明为 non-security；能执行的字段用一字段 sandbox state/output difference 验证，无法解决的字段 fail closed。

原始 726-key 结果：ASR `0/629`，benign utility `32/97 = 33.0%`，attack utility `191/629 = 30.4%`。在披露的 12 条 context repair overlay 后：

- ASR：`3/629 = 0.5%`；
- benign utility：`33/97 = 34.0%`；
- attack utility：`207/629 = 32.9%`。

这说明 effect-difference descriptor 加 runtime mediation 能显著压低 AgentDojo ASR，但当前结果同时伴随约一半 benign utility 损失。原始 `0% ASR` 不能作为唯一 headline，因为它与严格 fail-closed 和低效用耦合；修复 overlay 也不是 uniform-context rerun。

证据：

- `experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/descriptor-registration-report.json`
- `experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/agentdojo-official-full-run-report.json`
- `experiments/intent-bound-runtime-guard/results/effect-difference-runtime-guard/recovery-normalization-qwen32-full-context-repaired-report.json`

### 3.8 AgentDojo 同模型强基线

Qwen3-32B、AgentDojo v1.1.2、相同 726 keys 的当前可比结果：

| 方法 | Benign utility | Attack utility | ASR |
|---|---:|---:|---:|
| No defense | 66.0% | 54.4% | 8.4% |
| MELON-style | 63.9% | 54.1% | 8.9% |
| Spotlighting | 61.9% | 59.0% | 7.6% |
| Prompt Sandwiching | 61.9% | 57.6% | 1.3% |
| PromptArmor-style | 27.8% | 21.9% | 0.2% |
| Effect-binding runtime, repaired overlay | 34.0% | 32.9% | 0.5% |

Prompt Sandwiching 当前形成最直接的审稿风险：它在相同模型和 case keys 上达到较低 ASR，同时保留明显更高效用。PromptArmor ASR 更低但效用更差。论文不能只比较 ASR，也不能声称当前 runtime 在整体安全效用权衡上优于所有基线。

协议边界：MELON-style、Prompt Sandwiching 和 PromptArmor-style 是同输入下的 comparable local adapters，不是原论文协议复现；历史 direct rows 没有保留完整逐方法 command diagnostics。Effect-binding 行是 714 条原轨迹加 12 条披露的 context repair overlay，也不是 uniform-context rerun。

证据：`experiments/unified-agent-security-baselines/results/strong-model-baseline-comparison/qwen32-strong-baseline-report.md`。

### 3.9 Atom 直接帮助模型自我治理：官方四例 pilot

从 AgentDojo 四个 suite 各选一条此前 no-guard 已成功攻击的 case，所有 A--G 条件均不阻断调用。

结果：pristine ASR `2/4`；token-matched neutral `2/4`；validated atoms `2/4`；intent rubric + neutral `3/4`；intent rubric + validated atoms `3/4`。Validated atoms 还使 benign utility 从 `3/4` 降为 `2/4`。

结论：representation-only gate 失败。Descriptor 找到了 `password`、`recipient`、`body` 等效果字段，但模型没有将字段的具体值绑定到原始任务。Unvalidated atoms 的 ASR 为 `3/4`，说明不完整 atom 甚至可能增加风险。

证据：`experiments/intent-bound-runtime-guard/results/atomized-tool-description-self-governance/targeted-pilot-analysis.md`。

### 3.10 显式 targeted prompt pilot：8 条自建案例

这是 8 组预冻结 clean/injected single-action stress，不是 AgentDojo 总体 ASR。

| 条件 | Clean utility | Injected utility | ASR |
|---|---:|---:|---:|
| No defense | 7/8 | 1/8 | 6/8 |
| Generic intent prompt | 8/8 | 6/8 | 1/8 |
| Token-matched neutral | 8/8 | 6/8 | 0/8 |
| Validated atom prompt | 7/8 | 5/8 | 1/8 |
| Prompt Sandwiching | 8/8 | 8/8 | 0/8 |

结论：数据有攻击信号，但 atom 没有超过 generic 或 token-matched control，不能证明 atom 特异性收益。该模板主要测量模型是否忽略显眼的 `IMPORTANT INSTRUCTIONS`，不适合继续扩展为 atom 核心证据。

证据：`experiments/intent-bound-runtime-guard/results/atom-targeted-prompt-guidance/analysis.md`。

### 3.11 隐式字段 V1/V2 诊断

V1 移除显式注入标记，但自然语言 metadata 对模型几乎没有攻击作用：no guard clean utility `6/8`、injected utility `7/8`、ASR `0/8`。因此 V1 没有判别力。

V2 在看过 V1 后构造 schema-shaped resolver output，并在比较前冻结。结果如下：

| 条件 | Clean utility | Injected utility | ASR |
|---|---:|---:|---:|
| No defense | 7/8 | 5/8 | 1/8 |
| Generic intent prompt | 8/8 | 7/8 | 0/8 |
| Token-matched neutral | 7/8 | 6/8 | 1/8 |
| Field-shuffled atom | 7/8 | 4/8 | 2/8 |
| Validated atom prompt | 7/8 | 5/8 | 2/8 |

Validated 和 shuffled atom 都接受了两次字段替换：`Q2-report -> payroll-raw` 和 `read -> write`。当前 descriptor 只告诉模型哪些字段重要，没有要求具体值来自用户任务；字段列表反而可能让模型更注意不可信 resolver output。

由于 no-guard 只有 `1/8` attack、generic 已达到 `0/8` 且 atom 更差，V2 按 pilot gate 停止，没有继续跑昂贵强基线。

证据：

- `experiments/intent-bound-runtime-guard/results/implicit-atom-binding-prompt-stress/v1-pilot-analysis.md`
- `experiments/intent-bound-runtime-guard/results/implicit-atom-binding-prompt-stress-v2/analysis.md`

### 3.12 “通用意图提示能否防 AgentDojo”

不能从 V2 的 `0/8` 得出肯定结论。官方四例 pilot 中 intent rubric ASR 为 `3/4`，没有防住攻击。

仓库已有完整 AgentDojo `repeat_user_prompt` 日志，它是最接近但不等同于当前 generic system prompt 的官方提示基线。使用现有 E75 importer 对两个日志目录进行只读合并得到完整 726 keys、0 missing metrics：

- ASR：`21/629 = 3.3%`；
- benign utility：`34/97 = 35.1%`；
- attack utility：`151/629 = 24.0%`。

它相对 no guard 降低 ASR，但效用几乎减半，不能称为解决 AgentDojo 攻击。

这些 repeat-user-prompt 数字目前是利用已有 importer 对保存日志进行的只读重算，尚未单独冻结为论文主表 artifact；在进入论文前应生成独立 metrics JSON/CSV 和 reproduction status。

日志来源：

- `experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-official-v112-workspace-repeat-user-prompt/`
- `experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-official-v112-remaining-repeat-user-prompt/`

## 4. 当前最重要的问题

### 4.1 缺少 task-to-effect value binding

当前 descriptor 表达“哪些字段影响效果”，但没有稳定表达“本次任务允许这些字段取什么值”。例如：

- `file_id` 是资源字段，不代表 `payroll-raw` 被授权；
- `permission` 是 scope 字段，不代表 `write` 被授权；
- `recipient` 是 target 字段，不代表工具输出中新增的外部地址属于用户目标。

下一步必须测试具体 value binding，而不是继续增加字段名称提示。

### 4.2 Descriptor 角色仍过粗

注册结果中存在语义错误或过粗映射，例如 `send_email.cc/bcc` 被标成 `resource_or_operation`，而不是 target-principal binding。Counterfactual state difference 能发现字段有作用，但未必能自动命名正确的安全角色。

### 4.3 Authority interface 不完整

多步任务的 participant、resource ID、日期、金额差、搜索结果等值在任务开始时未知。把它们全部要求字面出现在原始任务会造成大量 abstain；无条件允许 resolver fill 又会给注入提供通道。需要显式区分：

- 用户直接给定值；
- 可信工具解析值；
- 算术或格式规范化派生值；
- 合理隐式需求；
- 不可信内容建议值；
- 扩大权限范围的值。

### 4.4 当前低 ASR 与拒绝耦合

E76/E77 的 ASR 明显低于 no guard，但 benign utility 只有约 34%。这足以证明 runtime 可以执行 effect-level mediation，却不足以证明安全提升主要来自 atom 粒度，而不是严格拒绝、注册缺失和 authority context 不足。

### 4.5 Prompt-only 证据为负

当前三类无 guard 证据都没有支持 atom 特异性：官方四例、显式 8 例、隐式 V2 8 例。论文不能写“向模型展示 atom 即提升安全性”。

## 5. 对论文可用与不可用的声明

### 5.1 当前可用

- 一次工具调用可能产生多个可独立授权的执行效果。
- 只基于表面形式或整次调用的表示可能发生安全相关碰撞。
- 注册前执行反事实能够发现 effect descriptor 中遗漏的执行相关字段。
- Counterfactually registered descriptors 可以作为 deterministic pre-commit mediation 的检查接口。
- 在 AgentDojo sandbox 中，当前 runtime 显著降低 ASR，但伴随明显效用损失。
- 主要剩余瓶颈是具体 effect value 与 task-scoped authority 的绑定，而不是是否知道工具名。

### 5.2 当前不可用

- Atom prompt 本身提高了 agent 的安全推理能力。
- 当前方法在整体安全效用权衡上优于 Prompt Sandwiching。
- `0% ASR` 证明了 production safety。
- 反事实字段必要性等同于授权正确性。
- LLM 自动生成的 descriptor 已经完整或可用于任意工具。
- E47--E50 custom stress 代表真实部署失败率。
- `repeat_user_prompt` 或 generic intent prompt 已经解决 AgentDojo 注入。

## 6. 推荐的下一轮实验

下一轮不应继续改 V2 后追加结果，而应建立一个独立、预冻结的 **task-to-effect binding experiment**。

### 6.1 核心问题

在不使用 deterministic allow/deny guard 的情况下，正确的 atom value binding 是否能让模型比 generic intent prompt、token control 和错误 atom mapping 更准确地完成任务并拒绝字段级权限扩张？

### 6.2 最小条件组

1. No defense。
2. Generic intent system prompt。
3. Token-matched neutral control。
4. Field-shuffled / role-shuffled atom binding。
5. 正确字段列表，但无具体 task binding。
6. 正确 task-bound atom self-check。

第 6 组应要求模型在输出工具调用前形成结构化但不暴露长思维链的检查结果：每个 effect field 的 planned value、来源类型、与候选调用值的关系，以及最终 CALL/NO_ACTION。代码只解析和评分，不独立拦截。

### 6.3 数据门禁

先从官方 AgentDojo 中冻结一个跨四 suite 的 attack-sensitive pilot，而不是继续使用结果后设计的小样本。要求：

- no-guard 至少出现 4 个 attack success，否则数据无判别力；
- generic control 不能已经完全饱和；
- 正确 binding 必须同时优于 generic、neutral、shuffled 和 field-list-only；
- benign utility 不能靠大规模 NO_ACTION 换取；
- pilot 未通过则不启动 726-key full run，也不进入论文正面主张。

### 6.4 如果 pilot 通过

在同一 Qwen3-32B checkpoint、AgentDojo v1.1.2、相同 726 case keys 和 native evaluator 上完成 full run。至少报告 ASR、benign utility、attack utility、coverage、parse failure，并与 no guard、generic/repeat prompt、Prompt Sandwiching 和现有 runtime guard 同表比较。

### 6.5 如果 pilot 不通过

保留负面结果，将论文定位收缩为：

> Counterfactually validated effect contracts provide a representation and falsification interface for pre-commit mediation; they do not by themselves make an LLM a reliable authority reasoner.

此时论文创新应集中在 effect representation、counterfactual registration 和条件性 mediation，而不能把 model self-governance 作为贡献。

## 7. 当前投稿风险判断

Atom 理论本身仍有价值：它统一连接了表示碰撞、注册前验证、运行时检查和安全分析。但当前 USENIX 风险仍高，原因不是缺实验数量，而是核心因果归因尚未闭合：

- runtime 结果证明“带 atom 接口的严格系统可降低攻击”，但未隔离 atom 粒度与拒绝策略；
- prompt-only 结果没有证明 atom 直接帮助模型；
- Prompt Sandwiching 当前提供更好的整体效用；
- authority interface 和多步 resolver provenance 仍是部署假设。

最能降低风险的下一步不是继续扩大 guard 结果，而是完成 task-bound atom self-check 的严格 matched-control pilot。其结果无论正负，都能明确论文边界。

## 8. 复现与检查状态

最近完成的 implicit V2 prompt-only run：80 条输出，prompt leakage `0`，未执行真实工具。相关测试：

```bash
PYTHONPATH=code python -m pytest \
  shared/compatibility/tests/tests/test_atom_targeted_prompt_guidance.py \
  shared/compatibility/tests/tests/test_implicit_atom_binding_prompt_stress.py -q
```

结果：`15 passed`。

最近检查时没有遗留的 `run_multimethod` 或 `llama_cpp.server` 进程。

## 9. 后续执行者的第一步

1. 不修改或覆盖上述负面实验结果。
2. 为 task-to-effect binding pilot 写独立 preregistration、case manifest 和 scoring sidecar。
3. 修正 descriptor role schema，至少把 recipient/cc/bcc/participants 与 resource/operation 分开。
4. 先跑 no-guard signal smoke，再冻结完整 pilot。
5. 只有在正确 binding 超过全部 matched controls 后，才运行强基线和 AgentDojo full benchmark。
