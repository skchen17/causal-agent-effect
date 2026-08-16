# 防御性写作草稿（审稿人校准新增优先级：攻击点 1 与 3）

日期：2026-08-04
产出：research-assistant。依据 `reviewer_perspective_improvement_evaluation_2026-08-04.md`
§4（攻击点 1：E2 family 集事后挑选；攻击点 3：V0-V3 正结果与 E78 主表方向一致性）
与该文档 §5"写作资源转向"。草稿正文为英文（论文语言），注释为中文；
均为独立草稿，**不修改 sections/ 任何文件**。

---

## C.1 V0-V3 与 E78 主表一致性段落草稿（攻击点 3）

**用途与位置**：D1 骨架 N2 分支的 R.A.0（Representation Attribution 节的
consistency preamble）。**硬性顺序要求**：本子段必须出现在任何 V0-V3 数字之前
（reviewer_perspective §4.3："把子集选择逻辑放在 V0-V3 结果之前陈述"）。
三个功能：(i) 说明 321-subset 的选择机制（field-level feedback）；
(ii) 预注册 strata 分解方向；(iii) 声明与 E78 主表/Panel(a) 的一致性审查口径。
所有 V0-V3 数字一律 `[PENDING-FINALIZE]` 占位；321-subset 的既有数字
（3/273、0/273 等）来自已完成实验（results.tex §Granularity Attribution），
可引用但此处为保持草稿自洽同样给出出处标注。

### 草稿正文（英文，可直接移植）

> **Selection mechanism, stated before any result.** The earlier 321-case
> closed-loop attribution is an applicability subset, not a random or
> stratified sample of the benchmark: a case enters it only if the deployed
> atom monitor produced field-level replan feedback on that case
> [claim map: closed-loop-attribution row; boundary: "Selection is conditioned
> on atom-field feedback; direct closed-loop attribution on an applicability
> subset, not a full-benchmark estimate"]. Selection therefore conditions on a
> mechanism property (feedback availability), and the subset's three safety
> differences concentrate in a single Slack injection goal, which is why that
> result was reported as a mechanism witness. We state this rule here, before
> any number from the strict protocol, because the strict 726-key design was
> constructed precisely to remove this selection: all 726 official case keys
> are pre-enumerated by benchmark API under a fixed sort order, with
> `selection_reason` fixed to `all_official_keys_pre_registered`
> (protocol §3.1), and the manifest excludes any prior-method decision,
> mismatch, attack outcome, or utility outcome (protocol §3.1 last paragraph).
> Nothing in the subset-selection logic depends on, or is adjusted after,
> the V0-V3 outcomes.
>
> **Stratification direction, pre-registered.** The decomposition dimensions
> are fixed before results: suite (workspace/slack/travel/banking), attack
> type, and injection goal, matching hypothesis H5 (protocol §2.1): a positive
> security claim requires the effect to appear in at least three suites and
> three static attack strata, and a difference confined to a single injection
> goal is demoted to a mechanism witness (protocol §2.3 row 5). This direction
> test is applied to the V0-V3 table below; it was not available for the
> 321-case subset, which is one reason the subset cannot serve as the main
> attribution evidence.
>
> **Consistency check against the main comparison.** The 321-case panel and
> the V0-V3 table share the model checkpoint, scorer, and representation
> lineage, so their directions must be reconcilable even though their
> denominators differ. On the 321-case subset, holding all other components
> fixed, the whole-call view permitted 3/273 attack goals while atom fields
> permitted none (Table granularity-transfer, Panel (a)). The V0-V3 table
> extends the same comparison from the applicability subset to all official
> cases under a frozen common plan cache. We therefore pre-commit the
> following consistency audit, reported in the same subsection: (i) paired
> ASR direction of V3 versus V0 and V3 versus V1 on the 726-key set
> [PENDING-FINALIZE]; (ii) the same two contrasts restricted to the 321-case
> subset keys, which must not contradict the subset panel's direction
> [PENDING-FINALIZE]; (iii) a discordance inventory for any key on which the
> full-set and subset-restricted contrasts disagree in direction
> [PENDING-FINALIZE]. If (ii) contradicts the already-reported panel, we
> report the contradiction and re-scope the attribution claim rather than
> harmonize denominators post hoc. If (i) is null while the subset panel was
> positive, the reading is coverage-driven: the subset measured cases where
> field-level feedback was available, and the full set dilutes that stratum
> [PENDING-FINALIZE: stratum sizes]. No re-weighting of the full set is
> permitted to recover the subset direction.

### 中文注释

1. 第一段把"选择机制先于结果"做成显式声明，直接回应"子集是事后挑选"的读法；
   关键锚点是协议 §3.1 的 `selection_reason=all_official_keys_pre_registered`
   与 manifest 泄漏禁令——移植时保留这两个引用。
2. 第二段把 H5 的方向检验说成**对 V0-V3 表施加的测试**而非对结果的描述，
   防止审稿人把 strata 分解读作事后切片。
3. 第三段是本草稿的核心防御：预先承诺一个三步一致性审计（全量方向、
   子集限定方向、不一致清单），并写死两条裁决规则（矛盾时收缩主张、
   零结果时按 coverage 解释且禁止事后重加权）。V0-V3 落地后只需回填
   三处 `[PENDING-FINALIZE]`，裁决规则不可再改（否则触发 R1/R8）。
4. 与 E78 主表的关系：E78 是全系统（含 planner/recovery/scorer 全链）对照，
   V0-V3 是表示层隔离；草稿不声称两者数字可比，只声称方向可审计——
   这是 accept_path §4 正分支"E78 降为全系统对照"的措辞落地。

---

## C.2 E2 表注 claim boundary 文案草稿（攻击点 1）

**状态**：E2 已完成（`experiments/security-analysis-ablation-and-overhead/results/policy-family-sensitivity/policy-family-sensitivity-report.md`，
下称 E2 报告），本草稿为**可直接用于论文**的表注/claim boundary 文案。
防御目标：反驳"family 集是看到冗余率后挑的"（事后挑选）与
"只报告对己有利的方向"（单向报告）。

### 草稿 1：表注（随 E2 敏感性表发布，英文）

> **Family enumeration (table note).** The four authority families are not
> selected from the data. They are the images of the paper's submultiset
> authority construction under a pre-enumerated lattice of occurrence
> projections: identity (the power-set baseline used throughout the paper),
> the effect-name quotient, the resource quotient, and the {0, 1, ≥2} count
> truncation of the effect-name quotient. Every family contains every
> submultiset of every observed projected effect multiset, so each family is
> an authority genealogy closed under submultisets by construction. The family
> set was fixed before any metric was computed and was not adjusted after
> observing redundancy rates. Both directions of the sensitivity grid are
> reported for every domain–family–qualifier cell: retained separating pairs
> (authorization-separating collisions that survive the deletion, i.e., the
> qualifier is still doing work) and redundant pairs (distinctions the family's
> projection cannot see, i.e., the qualifier is policy-invisible under that
> family), together with overpartition cells and false-rejection pairs.
> Necessity claims are scoped to cells marked *necessary*; cells marked
> *redundant* delimit where the coarser family cannot express the distinction,
> and cells marked *vacuous* indicate qualifiers not instantiated in that
> domain.

### 草稿 2：正文 claim boundary 句（Results §R.8 段 3 用，英文）

> The sensitivity grid is a deterministic recomputation over two frozen finite
> domains (the 56-call AgentDojo finite domain and the ToolSandbox held-out
> domain) with source-hash-bound effect oracles; separability is defined
> relative to each declared family's projection of source-effect multisets.
> Observed direction: mixed. Under the power-set family, [E2: 7 of 10]
> non-baseline deletion rows create authorization-separating collisions, so
> the typed qualifiers remain necessary there; under the three coarser
> families, [E2: 20 of 24] non-vacuous deletion rows have redundancy rate
> 1.000, meaning those distinctions are policy-invisible for those families,
> with one partial exception (resource family, payload qualifier: redundancy
> [E2: 0.75], residual separating pairs [E2: 2]). We read the two directions
> jointly: qualifier necessity is representation-relative—scoped to the
> declared power-set authority family—while the coarser families quantify
> exactly which effect details those policies cannot express. This is evidence
> that the representation is policy-relative rather than a fixed serialization
> of state differences. The result does not extend to unenumerated calls, open
> tool domains, deployment policy languages, or families outside the
> enumerated lattice.

### 中文注释

1. 表注第一句直接否认事后挑选，随后用**构造性定义**（submultiset 封闭的
   权威族谱系 = 投影格上的像）支撑——这是 reviewer_perspective §4.1 要求的
   两个要素（枚举原则 + 双向冗余率）的落点。
2. "Both directions … reported for every cell" 把 MC5 的双向报告要求写进表注
   本身，审稿人无需翻附录即可核验；对应 E2 报告的列定义
   （Separating/Redundant/Overpartition/False rejections 同表并列）。
3. 草稿 2 的数字均取自已完成的 E2 报告（7/10、20/24、resource×payload
   redundancy 0.75、residual separating pairs 2），**允许入稿**（E2 已完成，
   不受"V0-V3/v17 未落地禁填数字"约束）；方括号标注处移植时替换为表内
   精确引用。若 PM 要求更保守，可把三个数字改为"见 Table X 行标记"式引用。
4. 双向解读句（"We read the two directions jointly"）预写了高冗余方向的
   正面解释（policy-relative 的正面证据）与低冗余方向的必要性解释，与 E2 报告
   §Claim boundary 的三模板一致；实际观测为 mixed，故草稿按 mixed 模板写，
   两个反事实模板保留在 E2 报告内备查。
5. 与论文既有主张的衔接：results.tex §Authorization Collisions Panel (b) 的
   118 separating pairs 基线被 E2 复现检查覆盖（E2 报告 Baseline reproduction
   checks：power-set 无删除零碰撞基线 + 全 qualifier 删除复现 118/41 基线），
   移植时建议在该段加一句交叉引用，强化"非事后"叙事链。

---

## 两份草稿的共同纪律

- 攻击点 4（E4 恢复不入 headline）与攻击点 5（E1 绝对退化）不在本任务包范围，
  但其措辞戒律（禁"utility 问题已解决"、禁跨规模泛化）已并入 D1 骨架
  R.6 段 4 主题句与 N1 不变式清单；
- 两份草稿在 V0-V3 finalize 前**不得**移植入 sections/（C.1 依赖结果回填；
  C.2 技术上可先行移植，但按 B 线顺序统一在 Phase D 执行，避免中途改稿）；
- 移植时均触发 claim map diff 审查（决策书 §2f 第 1 条）。
