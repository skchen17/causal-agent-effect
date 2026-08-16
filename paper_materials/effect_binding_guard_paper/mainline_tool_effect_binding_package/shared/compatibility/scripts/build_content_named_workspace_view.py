#!/usr/bin/env python3
"""Build a content-named, read-only-compatible view of the research workspace.

The repository contains long-running jobs and many hard-coded legacy paths.  This
script therefore creates a canonical organization layer with relative symlinks;
it does not move or rename live artifacts.  The generated manifest is the input
for a later physical migration after active jobs have completed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


def discover_root() -> Path:
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir():
            return candidate
        if (candidate / "usenix27_candidate").exists() and (candidate / "evaluation").exists():
            return candidate
    return Path(__file__).resolve().parents[1]


ROOT = discover_root()
OUTPUT = ROOT / "整理后工作区"


@dataclass(frozen=True)
class Experiment:
    folder: str
    title: str
    purpose: str
    flow: str
    claim_boundary: str
    legacy_ids: tuple[str, ...] = ()
    direct_paths: tuple[str, ...] = ()
    include_terms: tuple[str, ...] = ()
    exclude_terms: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ExperimentFamily:
    folder: str
    purpose: str
    flow: str
    claim_boundary: str
    members: tuple[str, ...]


EXPERIMENTS = (
    Experiment(
        "跨方法工具效果绑定压力测试",
        "跨方法工具效果绑定压力测试",
        "检验已有监控方法是否真正绑定 effect、resource、authorization 与 provenance，而非只依赖工具名或表面形式。",
        "构造受控反事实变体，运行不同方法，并分别统计字段轴敏感性、表面不变性和行级不安全预允许。",
        "这是统一的定制压力视图，不等同于复现各方法原论文 benchmark。",
        ("e47",),
        ("code/src/experiments/tool_effect_fragmentation", "runs/tool_effect_fragmentation_phase5"),
        ("tool_effect_fragmentation", "e47_"),
    ),
    Experiment(
        "效果资源元组绑定守卫",
        "效果-资源元组绑定守卫",
        "测试显式 effect-resource tuple 是否改善工具调用级授权。",
        "从配对数据构造元组，运行守卫并计算 UPA、FDeny、Coverage 与配对一致性。",
        "结果说明元组绑定的局部收益，不代表完整授权系统。",
        ("e48",),
        ("code/src/experiments/effect_binding_guard/run_e48.py", "code/src/experiments/effect_binding_guard/dataset.py", "code/src/experiments/effect_binding_guard/guards.py", "code/src/experiments/effect_binding_guard/metrics.py", "code/src/experiments/effect_binding_guard/pairwise.py"),
    ),
    Experiment(
        "学习式绑定校准器",
        "学习式绑定校准器",
        "评估学习式校准能否从压力样本中提高绑定判断。",
        "训练校准器，在隔离测试集上计算字段绑定与安全决策指标。",
        "只支持学习式校准器在当前数据分布上的结论。",
        ("e49",),
        ("code/src/experiments/effect_binding_calibrator",),
    ),
    Experiment(
        "硬守卫鲁棒性与粒度瓶颈",
        "硬守卫鲁棒性与粒度瓶颈",
        "验证规则更强的守卫是否仍会因资源和授权粒度不足而失败。",
        "对资源、授权、操作模式等字段施加压力扰动，比较允许、拒绝与弃权。",
        "主要证据是受控压力集上的 granularity failure。",
        ("e50",),
        ("code/src/experiments/effect_binding_guard/run_e50.py",),
    ),
    Experiment(
        "本地预提交授权原型",
        "本地预提交授权原型",
        "验证显式本地授权上下文能否把高弃权行为转化为受控中介。",
        "构造 atom、展开多资源效果、解析授权上下文，并在提交前执行确定性授权。",
        "主结果使用严格的修正版数据口径；早期版本仅用于版本比较。",
        ("e55",),
        ("code/src/experiments/effect_binding_guard/e55_precommit_authz",),
    ),
    Experiment(
        "决策路径与严格回放审计",
        "决策路径与严格回放审计",
        "检查预提交授权结果能否在隐藏标签条件下严格回放，并审计每条决策路径。",
        "读取固定输入和结果，重放决策、核对路径并生成审计报告。",
        "这是实现与结果一致性证据，不是独立部署验证。",
        ("e56",),
    ),
    Experiment(
        "参考授权器与人工抽查验证",
        "参考授权器与人工抽查验证",
        "用资源扰动、独立参考授权器与人工抽查包验证授权结果。",
        "对固定结果执行扰动、参考实现比对和抽样审核。",
        "参考授权器一致率与人工抽查一致率是不同口径，不能混用。",
        ("e57",),
    ),
    Experiment(
        "独立规格留出授权合约",
        "独立规格留出授权合约",
        "测试 atom 接口能否迁移到不同工具名、字段、别名、资源标识和授权格式。",
        "使用与本地原型不同的 held-out contract，隔离 deployable input 与 sidecar 标签后评测。",
        "现有材料支持 independently specified；独立作者身份需外部人审材料才能升级。",
        ("e60",),
        ("evaluation/e60_heldout_contract",),
        ("e60_heldout", "e60_independent"),
        ("e60_effect_contract", "e60_demo", "e60_reuse", "test_effect_binding_guard_e60"),
    ),
    Experiment(
        "效果合约注册原型",
        "效果合约注册原型",
        "演示工具效果描述从候选合约、反事实验证、修正、冻结到确定性运行时授权的完整链路。",
        "为五类模拟工具生成合约，运行反事实验证，通过门禁后冻结并执行本地授权。",
        "默认 proposer 为确定性 stub；不证明任意 LLM 能自动生成完整合约。",
        ("e60",),
        ("code/src/experiments/effect_binding_guard/e60_effect_contract_prototype",),
        ("e60_effect_contract", "e60_demo", "test_effect_binding_guard_e60"),
        ("e60_heldout", "e60_independent"),
    ),
    Experiment(
        "真实格式代理轨迹回放",
        "真实格式代理轨迹回放",
        "测试 atom extraction 在多步、嵌套参数、别名、部分上下文和不可信工具返回中的可靠性。",
        "规范化保存的 AgentDojo/IPIGuard-style traces，分离运行输入与 sidecar，再执行抽取和授权评测。",
        "这是保存轨迹的 sandbox replay，不是生产部署日志；external atoms 为规则派生 sidecar。",
        ("e61",),
        ("evaluation/e61_realistic_trace_replay",),
    ),
    Experiment(
        "抽取与授权机制分解",
        "抽取与授权机制分解",
        "区分 atom extraction、授权上下文和 checker 逻辑各自造成的错误。",
        "比较 gold atoms、extracted atoms 以及受扰动授权上下文三种模式。",
        "gold 模式只用于分析上限，不是可部署输入。",
        ("e62",),
        ("evaluation/e62_extraction_decomposition",),
        ("e62_extraction",),
        ("local_llm",),
    ),
    Experiment(
        "本地语言模型效果合约生成",
        "本地语言模型效果合约生成",
        "测试本地 LLM 能否为留出工具提出结构化效果合约，并通过严格冻结门禁。",
        "构造无隐藏证据的工具 prompt，解析候选合约，验证一次修正前后结果。",
        "stub 只验证 harness；只有真实 backend 运行才构成 LLM 证据。",
        ("e62",),
        ("code/src/experiments/effect_binding_guard/e62_local_llm_proposer_validation",),
        ("e62_local_llm", "test_effect_binding_guard_e62_local"),
        ("e62_extraction",),
    ),
    Experiment(
        "授权接口负担与上下文退化",
        "授权接口负担与上下文退化",
        "量化新域需要的 schema、rule、alias、provenance 和 policy 成本，以及上下文缺失时的退化行为。",
        "统计接口工件并系统删除、翻转、拆分或陈旧化授权上下文。",
        "负担仅针对已研究域；估时和人工配置字段需按来源解释。",
        ("e63",),
        ("evaluation/e63_interface_burden",),
        ("e63_interface",),
        ("counterfactual_refinement", "gemma", "deepseek", "e63_prompt", "e63_failure", "e63_claim", "e63_round", "e63_feedback", "e63_frozen", "e63_candidate"),
    ),
    Experiment(
        "迭代反事实合约修正",
        "迭代反事实合约修正",
        "测试本地或远程 LLM 候选合约能否通过净化后的反事实失败反馈逐轮改进。",
        "执行原始候选与多轮反馈，记录每轮 prompt、输出、评分和冻结状态。",
        "未过严格门禁的候选必须转人工审查，不能称为安全冻结合约。",
        ("e63",),
        ("code/src/experiments/effect_binding_guard/e63_counterfactual_contract_refinement",),
        ("e63_counterfactual", "e63_gemma", "e63_deepseek", "e63_round", "e63_prompts", "e63_failure", "e63_claim"),
        ("e63_interface",),
    ),
    Experiment(
        "统一粒度基线比较",
        "统一粒度基线比较",
        "在相同 deployable input 上比较工具名、调用级、资源级、元组级、LLM judge 与 capability-style 基线。",
        "统一输入契约和 ALLOW/DENY/ABSTAIN 指标，记录每个基线可见字段。",
        "适配结果不是外部方法原论文协议复现。",
        ("e64",),
        ("reports/baselines_report.md", "reports/e60_e64_final_evidence_report.md"),
        ("e64_", "table_baselines"),
    ),
    Experiment(
        "真实语言模型安全裁决基线",
        "真实语言模型安全裁决基线",
        "用真实本地模型替代启发式 judge，测量直接安全裁决的可靠性。",
        "向本地模型提供无标签工具调用视图，解析决策并统计安全与可用性指标。",
        "模型未执行真实工具；parse failure 计为 ABSTAIN。",
        ("e65",),
        ("evaluation/e65_real_llm_judge",),
    ),
    Experiment(
        "真实语言模型原子抽取",
        "真实语言模型原子抽取",
        "检验 atom extraction 是否能由真实本地 LLM 完成，而非仅靠规则。",
        "LLM 输出严格 atom JSON，再连接确定性 authorizer 并分别评估抽取与决策。",
        "该实验不改变 reference guard 主结果。",
        ("e66",),
        ("evaluation/e66_real_llm_atom_extractor",),
    ),
    Experiment(
        "发布检查点适配基线",
        "发布检查点适配基线",
        "使用公开 TS-Guard、Safiron 或兼容 guardrail checkpoint 进行共同输入比较。",
        "把统一 deployable view 转换为 checkpoint 所需 prompt，运行模型并映射安全决策。",
        "只能称为 released checkpoints on adapted common-input view，不是原 benchmark 复现。",
        ("e67", "b8"),
        ("baselines/b8_official_checkpoints", "baselines/b8_released_guardrail"),
        ("b8_", "official_checkpoint"),
    ),
    Experiment(
        "语言模型字段反事实敏感性",
        "语言模型字段反事实敏感性",
        "直接测试 LLM 在干净与注入上下文中对关键字段变化的 atom 和决策响应。",
        "为保存轨迹生成字段反事实 pair，分别重新调用 Qwen 并核对该变与不该变关系。",
        "它测量 LLM-in-the-loop sensitivity，不直接证明 descriptor 可安全注册。",
        ("e68",),
        ("code/src/experiments/effect_binding_guard/e68_llm_counterfactual_atom_field_stress",),
    ),
    Experiment(
        "反事实筛选原子描述",
        "反事实筛选原子描述",
        "让 LLM 提出候选 atomized descriptors，并按反事实压力结果进行 top-k 选择。",
        "聚合工具视图、生成候选、运行 clean/injected pair、评分并在保存轨迹上比较。",
        "top-k 仅表示实验选择；未过 strict gate 不能称为安全冻结。",
        ("e69",),
        ("code/src/experiments/effect_binding_guard/e69_counterfactually_selected_atomized_contracts",),
    ),
    Experiment(
        "反事实引导原子描述运行时守卫",
        "反事实引导原子描述运行时守卫",
        "离线生成并验证工具 atom descriptor，运行时由确定性 guard 做授权。",
        "LLM 只参与注册；通过门禁的 descriptor 编译为 extractor，每次调用前生成授权检查项。",
        "registered 表示当前 replay 中通过实验门禁，不是生产认证。",
        ("e70",),
        ("code/src/experiments/effect_binding_guard/e70_counterfactual_atom_runtime_guard",),
    ),
    Experiment(
        "原子字段必要性运行时验证",
        "原子字段必要性运行时验证",
        "修正简单字段变化即视为通过的问题，改为验证字段对效果和安全控制是否必要。",
        "为候选字段构造必要性任务，比较保留与删除字段时的运行时决策。",
        "字段通过表示在研究任务中具有控制价值，不表示普遍最小性。",
        ("e71",),
        ("code/src/experiments/effect_binding_guard/e71_atom_field_necessity_runtime_guard",),
    ),
    Experiment(
        "任务权限包络运行时",
        "任务权限包络运行时",
        "让 agent 在任务开始时给出预期效果与权限范围，运行时比较实际调用。",
        "固定工具 atom 描述，生成任务 permission envelope，并对调用差异执行确定性检查。",
        "包络质量依赖初始任务解释，未知字段需显式处理。",
        ("e72",),
        ("code/src/experiments/effect_binding_guard/e72_task_permission_envelope_runtime_guard",),
    ),
    Experiment(
        "意图绑定与动态重规划",
        "意图绑定与动态重规划",
        "当多步调用超出初始权限包络时，把精确差异反馈给 LLM 决定继续、修改或停止。",
        "比较计划与调用，生成 runtime feedback，循环执行 replan/revise，直到获得最终决策。",
        "LLM 全权放行的安全性需以攻击目标是否达成为准单独评估。",
        ("e73",),
        ("code/src/experiments/effect_binding_guard/e73_intent_binding_replan_runtime",),
    ),
    Experiment(
        "无守卫代理回放基线",
        "无守卫代理回放基线",
        "提供相同模型和任务条件下不启用 runtime guard 的基准。",
        "运行 AgentDojo-style 任务并按官方任务效用与攻击目标指标汇总。",
        "无守卫结果必须与同模型、同数据和同协议的方法比较。",
        ("e74",),
        ("code/src/experiments/effect_binding_guard/e74_agentdojo_no_guard_baseline",),
    ),
    Experiment(
        "统一代理安全基线评测",
        "统一代理安全基线评测",
        "在同一 AgentDojo 协议中横向比较本文方法、无守卫和强基线。",
        "统一任务、攻击、模型、官方标签和指标，适配并运行各方法。",
        "外部方法适配必须区分源码运行、checkpoint 运行和近似实现。",
        ("e75",),
        ("code/src/experiments/effect_binding_guard/e75_unified_agentdojo_comparison",),
    ),
    Experiment(
        "语言模型描述符代理运行时",
        "语言模型描述符代理运行时",
        "在完整 AgentDojo 流程中测试由 LLM 识别工具效果并注册 descriptor 的方案。",
        "离线注册描述符，运行多步 agent，并在每次工具调用前执行 atom guard。",
        "运行结果依赖 descriptor 注册完整性和 AgentDojo 适配。",
        ("e76",),
        ("code/src/experiments/effect_binding_guard/e76_llm_descriptor_agentdojo_runtime",),
    ),
    Experiment(
        "效果差异运行时守卫",
        "效果差异运行时守卫",
        "通过计划效果与实际工具调用效果的差异实现更完整的运行时中介。",
        "注册效果描述、计算 effect diff、处理缺省与别名，并在官方 AgentDojo 流程中执行。",
        "当前强模型全量运行仍在进行；目录整理不得移动其源、脚本或运行路径。",
        ("e77",),
        ("code/src/experiments/effect_binding_guard/e77_effect_diff_runtime_guard",),
    ),
    Experiment(
        "强模型横向基线比较",
        "强模型横向基线比较",
        "使用统一强模型比较本文方法、no-guard、提示级与 guardrail 基线。",
        "固定 AgentDojo 版本、任务与攻击，运行 Qwen 32B 并做配对统计。",
        "必须同时报告良性效用与攻击成功率，且保留失败任务。",
        ("e78",),
    ),
    Experiment(
        "长任务跨环境迁移评测",
        "长任务跨环境迁移评测",
        "评估方法在 AgentLab-style 和 ToolSandbox-style 长任务、多步环境中的迁移能力。",
        "构建保存攻击清单和本地 sandbox 子集，运行无守卫与效果守卫并比较。",
        "保存轨迹迁移与完整外部环境复现需要分别标注。",
        ("e79",),
        ("evaluation/e79_long_horizon", "code/src/experiments/effect_binding_guard/e79_agentlab_saved_attack_adapter", "code/src/experiments/effect_binding_guard/e79_toolsandbox_local_runner"),
    ),
    Experiment(
        "条件性效果合约安全模型",
        "条件性效果合约安全模型",
        "形式化在效果抽象、独立权限、完整中介与 check-use 一致性前提下的安全边界。",
        "检查合约义务、复合效果和扩展权限默认行为，并把理论前提映射到实现。",
        "结论是条件性的，不声称无前提 trajectory safety。",
        ("e80",),
        ("code/src/experiments/effect_binding_guard/e80_contract_obligation_hardening", "code/src/experiments/effect_binding_guard/e80_effect_contract_security_model"),
    ),
    Experiment(
        "运行时机制消融",
        "运行时机制消融",
        "量化 atom、别名、来源、权限包络、重规划和 fail-closed 等组件的贡献。",
        "在统一任务协议下逐项移除机制并比较安全、效用与弃权。",
        "消融只解释当前实现组件，不证明所有可能实现。",
        ("e81",),
        ("evaluation/e81_ablation", "code/src/experiments/effect_binding_guard/e81_agentdojo_hardened_runtime", "code/src/experiments/effect_binding_guard/e81_runtime_ablation_kernel"),
    ),
    Experiment(
        "自适应攻击评测",
        "自适应攻击评测",
        "测试了解守卫逻辑的攻击是否能利用别名、默认值、组合调用和重规划接口绕过控制。",
        "生成自适应攻击协议与 materialized cases，在统一运行时下评测。",
        "攻击材料限于受控代理安全研究，不执行真实外部副作用。",
        ("e82",),
        ("evaluation/e82_adaptive_attacks", "code/src/experiments/effect_binding_guard/e82_adaptive_attack_protocol"),
    ),
    Experiment(
        "运行时开销测量",
        "运行时开销测量",
        "量化 atom extraction、diff、授权检查和反馈处理带来的延迟与吞吐开销。",
        "运行微基准并记录各阶段时间、分位数和调用规模。",
        "微基准不能替代完整端到端延迟。",
        ("e83",),
        ("evaluation/e83_overhead", "code/src/experiments/effect_binding_guard/e83_overhead_instrumentation"),
    ),
    Experiment(
        "权限清单人工审查",
        "权限清单人工审查",
        "为 AgentDojo 工具与任务建立可审计的 authority manifest，并收集独立人工确认。",
        "生成 review packet、人工填写、运行验证器并汇总接口负担。",
        "可信状态取决于审查记录完整性；缺失项不能自动视为可信。",
        ("e84",),
        ("evaluation/e84_authority_manifests",),
    ),
    Experiment(
        "因果效果投影验证",
        "因果效果投影验证",
        "验证实际调用到安全相关效果投影的因果对应关系，并对投影清单做人工审查。",
        "运行受控中介检查、生成投影 review packet，并比较人工确认与系统投影。",
        "只支持已覆盖工具与干预轴上的投影有效性。",
        ("e85",),
        ("evaluation/e85_causal_effect_contract_validation", "evaluation/e85_security_effect_projections", "code/src/experiments/effect_binding_guard/e85_causal_effect_contract_validation"),
    ),
    Experiment(
        "增强代理注入攻击数据集",
        "增强代理注入攻击数据集",
        "补充能够有效触发目标模型的受控 AgentDojo 注入样本，避免基线攻击强度过低。",
        "先做小规模有效性门禁，再物化完整数据并在同一协议中运行。",
        "仅用于 sandbox benchmark；不包含真实服务执行或生产攻击。",
        ("e88",),
        ("evaluation/e88_agentdojo_attack_dataset", "code/src/experiments/effect_binding_guard/e88_agentdojo_attack_dataset", "runs/e88_agentdojo_attack_dataset"),
    ),
)


EXPERIMENT_FAMILIES = (
    ExperimentFamily(
        "工具效果绑定失效与粒度瓶颈",
        "建立论文的问题证据：现有方法具有部分绑定能力，但难以同时绑定效果、资源、授权、操作模式和来源。",
        "先运行跨方法反事实压力测试，再依次评估元组守卫、学习式校准器和硬守卫，定位资源与授权粒度瓶颈。",
        "这些结果证明受控压力条件下存在 joint-binding failure，不等同于复现外部方法的原始 benchmark。",
        ("跨方法工具效果绑定压力测试", "效果资源元组绑定守卫", "学习式绑定校准器", "硬守卫鲁棒性与粒度瓶颈"),
    ),
    ExperimentFamily(
        "预提交授权原型与审计",
        "验证显式 atom 与本地授权上下文能否支持提交前中介，并审计结果链。",
        "运行严格修正版预提交原型，随后进行决策路径回放、参考授权器比对和人工抽查。",
        "主性能口径只使用严格修正版；早期版本仅作版本比较，审计一致率不能替代性能结果。",
        ("本地预提交授权原型", "决策路径与严格回放审计", "参考授权器与人工抽查验证"),
    ),
    ExperimentFamily(
        "独立合约真实轨迹与机制分解",
        "回应 synthetic、circularity、机制混淆和接口负担问题。",
        "依次评估独立规格留出合约、真实格式保存轨迹、抽取与授权分解、上下文退化和统一粒度基线。",
        "留出合约当前支持 independently specified；保存轨迹不是生产日志；gold 模式只用于误差分解。",
        ("独立规格留出授权合约", "真实格式代理轨迹回放", "抽取与授权机制分解", "授权接口负担与上下文退化", "统一粒度基线比较"),
    ),
    ExperimentFamily(
        "效果合约生成与反事实注册",
        "研究如何由工具描述产生 atom descriptor，并通过反事实反馈筛选后注册到确定性运行时。",
        "从确定性原型、本地 LLM 生成和迭代修正，发展到字段敏感性、候选筛选和 descriptor runtime guard。",
        "未通过严格门禁的候选只能称为实验描述符，不能称为自动生成的安全合约。",
        ("效果合约注册原型", "本地语言模型效果合约生成", "迭代反事实合约修正", "语言模型字段反事实敏感性", "反事实筛选原子描述", "反事实引导原子描述运行时守卫"),
    ),
    ExperimentFamily(
        "真实模型与发布检查点补强",
        "补充真实 LLM judge、真实 LLM atom extractor 和发布安全检查点的可比证据。",
        "在共同的无标签输入视图上运行本地模型和公开 checkpoint，统一统计安全、效用、弃权和解析失败。",
        "checkpoint 结果是适配后的共同输入比较，不是外部论文原始协议复现。",
        ("真实语言模型安全裁决基线", "真实语言模型原子抽取", "发布检查点适配基线"),
    ),
    ExperimentFamily(
        "任务意图绑定与运行时守卫",
        "验证固定 atom 描述、任务权限包络、动态重规划和 effect-diff guard 在多步代理执行中的作用。",
        "从字段必要性开始，生成任务权限范围，在调用差异出现时重规划，并逐步进入完整 AgentDojo runtime。",
        "运行时结果依赖初始意图解释、descriptor 完整性和工具适配；不声称生产部署安全。",
        ("原子字段必要性运行时验证", "任务权限包络运行时", "意图绑定与动态重规划", "语言模型描述符代理运行时", "效果差异运行时守卫"),
    ),
    ExperimentFamily(
        "统一强基线与代理安全评测",
        "在相同模型、任务、攻击和官方评分协议下比较本文方法与强基线。",
        "先建立 no-guard，再统一运行 AgentDojo 方法适配，最后使用强模型做完整横向比较和配对统计。",
        "必须同时报告良性任务效用和攻击成功率，并区分源码、checkpoint 与近似适配。",
        ("无守卫代理回放基线", "统一代理安全基线评测", "强模型横向基线比较"),
    ),
    ExperimentFamily(
        "长任务跨环境迁移评测",
        "测试方法在更长、多步且具有不同工具接口的代理环境中的迁移能力。",
        "构建 AgentLab-style 保存攻击与 ToolSandbox-style 本地子集，比较无守卫和效果守卫。",
        "保存轨迹迁移和完整环境复现需要分开报告。",
        ("长任务跨环境迁移评测",),
    ),
    ExperimentFamily(
        "安全模型消融自适应攻击与开销",
        "补充条件性安全论证、机制贡献、自适应攻击和系统代价。",
        "映射理论前提到实现，逐项消融关键组件，运行自适应攻击，再测量 runtime 各阶段开销。",
        "安全结论依赖明确前提；微基准不能替代完整端到端部署测量。",
        ("条件性效果合约安全模型", "运行时机制消融", "自适应攻击评测", "运行时开销测量"),
    ),
    ExperimentFamily(
        "人工权限审查与因果验证",
        "通过人工审查权限清单和受控干预验证安全相关效果投影。",
        "生成匿名 review packet，验证填写完整性，并把人工判断与系统投影和中介结果进行比对。",
        "可信状态取决于真实审查材料；只支持已覆盖工具、任务和干预轴。",
        ("权限清单人工审查", "因果效果投影验证"),
    ),
    ExperimentFamily(
        "增强代理注入攻击数据集",
        "构造能够有效测试目标模型、同时保持可控和无真实副作用的代理注入数据。",
        "先做小规模有效性门禁，再生成完整 benchmark cases 并纳入统一横向评测。",
        "数据仅用于 sandbox 安全评测，不对应真实服务攻击。",
        ("增强代理注入攻击数据集",),
    ),
)


SEARCH_ROOTS = (
    "analysis/results",
    "reports",
    "paper_tables",
    "tables",
    "scripts",
    "tests/tests",
    "runs",
    "reproduction",
    "results/analysis/results",
)


PAPER_LINKS = {
    "当前USENIX论文": "usenix27_candidate",
    "紧凑版USENIX论文": "usenix27_candidate_compact",
    "单文件版USENIX论文": "usenix27_candidate_flat",
    "上一版NDSS论文": "ndss_candidate_restructured_v2",
    "早期NDSS论文": "ndss_candidate_restructured",
    "历史论文草稿": "paper_drafts",
    "PaperSpine写作产物": "paper_rewriting_output",
    "论文插图": "paper_figures",
    "共享插图": "figures",
    "论文表格": "paper_tables",
    "共享表格": "tables",
    "方法写作材料": "method_materials",
}


SHARED_LINKS = {
    "公共代码": "code",
    "公共数据": "data",
    "基线实现": "baselines",
    "原始评测材料": "evaluation",
    "原始分析结果": "analysis",
    "原始运行记录": "runs",
    "执行日志": "logs",
    "复现产物": "reproduction",
    "结果归档": "results",
    "通用脚本": "scripts",
    "测试集合": "tests",
    "审计材料": "audit",
    "清单材料": "manifests",
    "报告集合": "reports",
}


def safe_link_name(name: str) -> str:
    name = re.sub(r"^(?:e\d+|b\d+)[_-]*", "", name, flags=re.IGNORECASE)
    return name or "artifact"


def reset_output() -> None:
    if OUTPUT.is_symlink() or OUTPUT.is_file():
        OUTPUT.unlink()
    elif OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    for path in (OUTPUT / "论文内容", OUTPUT / "实验内容", OUTPUT / "公共资源与环境", OUTPUT / "整理清单"):
        path.mkdir(parents=True, exist_ok=True)


def relative_symlink(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidate = destination
    index = 2
    while candidate.exists() or candidate.is_symlink():
        candidate = destination.with_name(f"{destination.stem}-{index}{destination.suffix}")
        index += 1
    candidate.symlink_to(os.path.relpath(source, candidate.parent), target_is_directory=source.is_dir())
    return candidate


def iter_matching(exp: Experiment) -> Iterable[Path]:
    ids = tuple(value.lower() for value in exp.legacy_ids)
    includes = tuple(value.lower() for value in exp.include_terms)
    excludes = tuple(value.lower() for value in exp.exclude_terms)
    seen: set[Path] = set()
    for root_name in SEARCH_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        candidates = root.iterdir() if root.is_dir() else ()
        for path in candidates:
            lowered = path.name.lower()
            id_match = any(lowered.startswith(f"{identifier}_") or lowered == identifier for identifier in ids)
            term_match = any(term in lowered for term in includes)
            if not (id_match or term_match):
                continue
            if excludes and any(term in lowered for term in excludes):
                continue
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield path


def category_for(path: Path) -> str:
    relative = path.relative_to(ROOT)
    head = relative.parts[0]
    if head == "runs":
        return "运行记录"
    if head == "scripts":
        return "脚本"
    if head == "tests":
        return "测试"
    if head in {"paper_tables", "tables"}:
        return "论文表格"
    if head == "reports":
        return "报告"
    if head == "reproduction":
        return "复现产物"
    if head in {"analysis", "results", "evaluation"}:
        return "数据与结果"
    return "源码与实现"


def experiment_readme(exp: Experiment, linked: list[dict[str, str]]) -> str:
    ids = "、".join(exp.legacy_ids) if exp.legacy_ids else "无单一旧编号"
    categories: dict[str, int] = {}
    for item in linked:
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    inventory = "\n".join(f"- `{name}`：{count} 项" for name, count in sorted(categories.items()))
    notes = "\n".join(f"- {note}" for note in exp.notes) or "- 无额外说明。"
    return f"""# {exp.title}

## 实验目的

{exp.purpose}

## 主要流程

{exp.flow}

## 目录内容

{inventory or '- 当前未发现可链接材料，需后续补充。'}

目录内文件均为指向原始工作区的相对符号链接。这样可以在不中断运行任务、不破坏已有导入路径和复现命令的情况下，先形成按内容组织的统一入口。

## 结论边界

{exp.claim_boundary}

## 来源追踪

- 历史实验标识：`{ids}`。该标识只用于追溯旧文件，不再用于新目录命名。
- 已链接工件数量：{len(linked)}。
- 物理迁移前必须根据 `整理清单/路径映射.json` 更新代码导入、脚本参数、LaTeX 引用和复现清单。

## 额外说明

{notes}
"""


def family_readme(
    family: ExperimentFamily,
    members: list[Experiment],
    linked: list[dict[str, str]],
) -> str:
    categories: dict[str, int] = {}
    for item in linked:
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    inventory = "\n".join(f"- `{name}`：{count} 项" for name, count in sorted(categories.items()))
    components = "\n".join(
        f"- **{member.title}**（历史标识：`{'、'.join(member.legacy_ids) or '无单一编号'}`）：{member.purpose}"
        for member in members
    )
    return f"""# {family.folder}

## 实验族目的

{family.purpose}

## 总体流程

{family.flow}

## 包含的实验工作

{components}

这些工作共同支撑一个论文证据问题，因此合并在同一目录中。历史编号只用于追溯原始工件，不再作为目录结构。

## 目录内容

{inventory or '- 当前未发现可链接材料，需后续补充。'}

目录内文件均为指向原始工作区的相对符号链接。这样可以在不中断运行任务、不破坏已有导入路径和复现命令的情况下，先形成按内容组织的统一入口。

## 结论边界

{family.claim_boundary}

## 整理状态

- 已链接工件数量：{len(linked)}。
- 详细新旧路径见 `整理清单/路径映射.json`。
- 物理迁移必须等后台实验结束，并完成 import、脚本、LaTeX 和复现路径更新后执行。
"""


def build_paper_section(mapping: list[dict[str, str]]) -> None:
    paper = OUTPUT / "论文内容"
    for label, old in PAPER_LINKS.items():
        source = ROOT / old
        if source.exists():
            destination = paper / label
            actual_destination = relative_symlink(source, destination)
            mapping.append({"section": "paper", "new_path": str(actual_destination.relative_to(ROOT)), "old_path": old})
    supplements = paper / "根目录论文与审计文档"
    supplements.mkdir(exist_ok=True)
    for path in sorted(ROOT.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".md", ".tex", ".bib", ".pdf"}:
            continue
        actual_destination = relative_symlink(path, supplements / path.name)
        mapping.append({"section": "paper", "new_path": str(actual_destination.relative_to(ROOT)), "old_path": path.name})
    (paper / "README.md").write_text(
        """# 论文内容

本目录集中论文源文件、不同版式候选稿、历史稿、图表和写作审计材料。

- `当前USENIX论文`：当前主写作版本。
- `紧凑版USENIX论文`：用于页数压缩与版式比较。
- `单文件版USENIX论文`：便于整体阅读和外部传递的扁平版本。
- `上一版NDSS论文` 与 `早期NDSS论文`：历史版本，只用于追溯，不应混入当前主结果。
- `PaperSpine写作产物`：写作规划、证据映射和审计材料。

当前目录使用相对符号链接，不改变原始 LaTeX 引用和构建路径。完成正在运行的实验后，可依据路径映射执行物理迁移。
""",
        encoding="utf-8",
    )


def build_experiments(mapping: list[dict[str, str]]) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    experiments_by_name = {experiment.folder: experiment for experiment in EXPERIMENTS}
    for family in EXPERIMENT_FAMILIES:
        members = [experiments_by_name[name] for name in family.members]
        destination_root = OUTPUT / "实验内容" / family.folder
        destination_root.mkdir(parents=True, exist_ok=True)
        linked: list[dict[str, str]] = []
        candidates: list[Path] = []
        source_owner: dict[Path, str] = {}
        for exp in members:
            member_candidates: list[Path] = []
            for direct in exp.direct_paths:
                path = ROOT / direct
                if path.exists():
                    member_candidates.append(path)
            member_candidates.extend(iter_matching(exp))
            for path in member_candidates:
                source_owner.setdefault(path.resolve(), exp.folder)
                candidates.append(path)
        seen: set[Path] = set()
        for source in candidates:
            resolved = source.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            category = category_for(source)
            link_name = safe_link_name(source.name)
            destination = destination_root / category / link_name
            actual_destination = relative_symlink(source, destination)
            item = {
                "category": category,
                "new_path": str(actual_destination.relative_to(ROOT)),
                "old_path": str(source.relative_to(ROOT)),
                "component": source_owner.get(resolved, "未指定组成实验"),
            }
            linked.append(item)
            mapping.append({"section": "experiment", "experiment_family": family.folder, **item})
        (destination_root / "README.md").write_text(family_readme(family, members, linked), encoding="utf-8")
        summaries.append({
            "folder": family.folder,
            "title": family.folder,
            "components": [member.title for member in members],
            "legacy_ids": sorted({identifier for member in members for identifier in member.legacy_ids}),
            "linked_artifacts": len(linked),
            "claim_boundary": family.claim_boundary,
        })
    return summaries


def build_shared(mapping: list[dict[str, str]]) -> None:
    shared = OUTPUT / "公共资源与环境"
    for label, old in SHARED_LINKS.items():
        source = ROOT / old
        if source.exists():
            destination = shared / label
            actual_destination = relative_symlink(source, destination)
            mapping.append({"section": "shared", "new_path": str(actual_destination.relative_to(ROOT)), "old_path": old})
    for label, old in {
        "版本控制元数据": ".git",
        "Codex配置": ".codex",
        "代理配置": ".agents",
        "Python测试缓存": ".pytest_cache",
        "代码检查缓存": ".ruff_cache",
    }.items():
        source = ROOT / old
        if source.exists():
            destination = shared / "环境与工具状态" / label
            actual_destination = relative_symlink(source, destination)
            mapping.append({"section": "environment", "new_path": str(actual_destination.relative_to(ROOT)), "old_path": old})
    (shared / "README.md").write_text(
        """# 公共资源与环境

本目录保存跨实验复用的数据、公共代码、测试、脚本、基线、运行记录和审计材料。实验目录提供按内容筛选后的入口；这里保留完整原始集合，保证任何尚未精确归类的文件仍可访问。

`环境与工具状态` 中的缓存和版本控制目录不是论文证据，不应打包进匿名投稿 artifact。
""",
        encoding="utf-8",
    )


def audit_top_level(mapping: list[dict[str, str]]) -> list[str]:
    covered = {entry["old_path"].split("/", 1)[0] for entry in mapping}
    ignored = {OUTPUT.name}
    return sorted(path.name for path in ROOT.iterdir() if path.name not in covered | ignored)


def write_manifests(mapping: list[dict[str, str]], experiments: list[dict[str, object]], unclassified: list[str]) -> None:
    inventory = OUTPUT / "整理清单"
    (inventory / "路径映射.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (inventory / "实验索引.json").write_text(json.dumps(experiments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (inventory / "未归类顶层条目.json").write_text(json.dumps(unclassified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = "\n".join(
        f"| {item['title']} | {', '.join(item['legacy_ids']) or '无'} | {item['linked_artifacts']} | {item['claim_boundary']} |"
        for item in experiments
    )
    status = "全部顶层条目已纳入论文、实验或共享入口。" if not unclassified else f"仍有 {len(unclassified)} 个顶层条目待人工归类：{', '.join(unclassified)}。"
    (inventory / "整理覆盖报告.md").write_text(
        f"""# 工作区整理覆盖报告

## 当前状态

{status}

- 论文实验族目录数：{len(experiments)}
- 路径映射项数：{len(mapping)}
- 整理方式：相对符号链接兼容视图
- 物理迁移状态：暂缓，等待当前全量模型实验结束

## 实验索引

| 实验内容 | 旧标识 | 已链接工件 | 结论边界 |
|---|---|---:|---|
{rows}

## 后续物理迁移门禁

1. 确认所有后台实验进程结束。
2. 冻结原始工作区并校验哈希。
3. 根据 `路径映射.json` 移动物理文件。
4. 批量更新 Python import、脚本路径、LaTeX 输入、复现清单和测试。
5. 运行完整测试、复现脚本和论文编译。
6. 验证不存在断链后，再移除旧兼容路径。
""",
        encoding="utf-8",
    )
    (inventory / "README.md").write_text(
        """# 整理清单

- `路径映射.json`：新入口到旧路径的机器可读映射。
- `实验索引.json`：按论文证据问题合并后的实验族及其结论边界。
- `未归类顶层条目.json`：尚未纳入任何入口的顶层文件或目录。
- `整理覆盖报告.md`：覆盖统计与后续物理迁移门禁。
""",
        encoding="utf-8",
    )


def write_root_readme() -> None:
    (OUTPUT / "README.md").write_text(
        """# 按内容整理的工作区

本目录是当前研究工作区的统一入口，分为：

- `论文内容`：当前 USENIX 稿、历史稿、图表与写作材料。
- `实验内容`：按论文证据问题合并的实验族目录，每个目录包含中文说明和相关源码、数据、结果、运行记录、脚本与测试入口。
- `公共资源与环境`：不能归属单个实验的跨实验数据、公共代码、基线、复现、日志、审计与环境状态。
- `整理清单`：路径映射、覆盖报告和后续迁移步骤。

## 为什么当前使用符号链接

工作区仍有全量模型实验在运行，且现有 Python import、LaTeX、复现脚本和运行命令包含旧路径。此时直接移动文件会破坏正在运行的任务和结果链。因此本轮先建立完整的内容命名视图；旧编号只用于来源追踪，不作为新目录名。

待后台实验完成后，再按照整理清单执行物理迁移和全量回归验证。
""",
        encoding="utf-8",
    )


def main() -> None:
    reset_output()
    mapping: list[dict[str, str]] = []
    build_paper_section(mapping)
    experiments = build_experiments(mapping)
    build_shared(mapping)
    unclassified = audit_top_level(mapping)
    write_manifests(mapping, experiments, unclassified)
    write_root_readme()
    print(json.dumps({
        "status": "passed" if not unclassified else "passed_with_unclassified_top_level_entries",
        "output": str(OUTPUT),
        "experiments": len(experiments),
        "mapped_entries": len(mapping),
        "unclassified_top_level_entries": unclassified,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
