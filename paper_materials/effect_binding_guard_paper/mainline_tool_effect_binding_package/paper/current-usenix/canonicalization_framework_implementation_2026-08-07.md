# 效果保持规范化框架：有效实现报告（2026-08-07）

**实验**：`effect-preserving canonicalization framework v1`（三阶段：注册验证 → 冻结 → 运行期变换，含 CEGAR 循环）
**实现位置**：`experiments/security-analysis-ablation-and-overhead/source/canonicalization-registry/`
**设计依据**：`deepseek_utility_experiments_handoff_2026-08-07.md` §5
**运行约束**：CPU-only，stdlib-only，不修改 V0-V3 冻结版（e77_runtime.py/patch），不启动 GPU
**本报告引用**：详细机器报告见 `experiments/security-analysis-ablation-and-overhead/results/canonicalization-registry/`（`control-validation-report.{json,md}`、`cegar-replay-report.{json,md}`、`registry.frozen.json`）

---

## 0. 结论摘要

| 验证项 | 结果 |
|---|---|
| 预注册纪律（先冻结后跑，sha256 校验） | ✅ `5d7a124a…9af5` 通过 |
| 有限域 oracle 校准门（56-call 冻结域） | ✅ 4/5 工具已校准；slack 未校准 → fail-closed |
| 10 条对照规则判定正确性 | ✅ **10/10**（5 通过 + 5 拒绝） |
| CEGAR 回放（M3/M3b 失败案例） | ✅ 3/3 处置完成（2 注册 + 1 拒绝）；期望匹配 3/3 |
| 单元测试 | ✅ **39/39 通过**（含对称性、fail-closed、篡改检测） |
| E2 交叉证据（R07 拒绝的理由佐证） | ✅ visibility/power_set separating_pairs=4, status=necessary |
| 冻结注册表 | ✅ 5 条 ACCEPT 规则落盘，内存/文件哈希校验均无失配 |

---

## 1. 设计回顾（与 handoff §5 对应）

**效果保持等价**（§5.1）：对字段角色 r，v₁≈v₂ 当且仅当将二者填入调用并执行后：
1. 安全相关效果相同（在投影后的效果签名意义下）；
2. 授权结论相同（本框架中授权结论是效果签名的确定性函数，故退化为同一签名比较）。

**三阶段架构**：
- **注册期**（`validation.py` + `domain_oracle.py`）：反事实验证 + 结构论证（rationale）+ 适用范围声明（scope）。
- **冻结期**（`registry.py`）：`frozen_hash = sha256(canonical_json(behavioral_spec(rule)))`，覆盖 `rule_id/field_role/tool/transform/scope`，**排除** validation_record 与时间戳，保证哈希只标识行为；加载/校验时重算比对。
- **运行期**（`runtime.py`）：role → 规则链 → 规范化值；`O(len)` 纯函数；范围外/无工具上下文原样返回（fail-closed 字面比较）。

**CEGAR 循环**（§5.3，`cegar.py`）：失败 → 门禁①分类（false_negative / model_limitation / security_event；后者硬停不归纳）→ 门禁②候选归纳（结构 sanity 检查）→ 门禁③反事实验证 → ACCEPT 注册 / REJECT 拒绝并 fail-closed / UNDETERMINED 不注册。可回放（幂等：重复回放同一失败案例不重复注册）。

**对称性**（`runtime.py`）：`equivalent()`（exact 路径）与 `forbidden_match()`（forbidden 路径）**共享同一私有实现** `_canonical_compare()`；`symmetry_audit()` 记录两路径在探针集上逐对一致的证据。

**模型无关语义层**：`oracle_semantics`（amount=numeric、date=calendar date（MM/DD/YYYY 约定）、recipient_iban/permission=exact_string、subject_label=label（casefold+空白折叠+标点折叠）、email=case_insensitive_string）在预注册文件中固定，规则无关；工具参数→效果绑定（identity/prefix/fanout）由冻结域学习，规则无关。

---

## 2. 模块文件清单

| 文件 | 职责 |
|---|---|
| `paths.py` | 共享路径解析（ROOT、冻结域、E2 报告、结果目录） |
| `transforms.py` | 11 个纯变换函数（5 通过用 + 5 拒绝用 + M3b 数字边界）；`TRANSFORMS` 注册表；`apply_transform` |
| `registry.py` | 规则 schema 校验、`behavioral_spec`、`rule_frozen_hash`、`Registry`（add/rules_for/freeze/save/load/verify） |
| `domain_oracle.py` | 有限域效果 oracle：绑定学习（identity/prefix/fanout）、角色语义投影、校准门、`signature_for_role_value`/`value_observed` |
| `validation.py` | `ValidationPipeline.validate_rule`：D1/D2/merge 差分 + probe over-merge 检查；ACCEPT/REJECT/UNDETERMINED（fail-closed） |
| `runtime.py` | `CanonicalizationRuntime`：`canonicalize`/`equivalent`/`forbidden_match`/`symmetry_audit`/`canonicalize_args`（集成接口） |
| `cegar.py` | `CegarReplay`：门禁①→②→③→注册/拒绝，收敛记录，可回放 |
| `preregistered_control_set.json` + `.sha256.txt` | 预注册对照集（10 规则 + oracle 语义 + 工具角色声明），先冻结后跑 |
| `failure_cases_m3.jsonl` | CEGAR 回放输入（F-M3-01 / F-M3b-01 / F-REJ-01） |
| `run_control_validation.py` | 控制集验证 runner（sha 校验→校准→10 规则→冻结→E2 交叉→报告） |
| `run_cegar_replay.py` | CEGAR 回放 runner |
| `tests/` | conftest + 4 个测试文件（39 用例） |

> 注：`failure_cases_m3.jsonl` 在回放前修复了一处 JSON 非法转义（`\w` → `\\w`），属语法修复，不改变失败案例语义内容；已在 CEGAR 报告中如实记录。

---

## 3. 10 条对照规则验证（判定正确性 = 核心机制可行的证据）

**预注册纪律**：`preregistered_control_set.json` 于任何验证运行**之前**冻结，sidecar sha256=`5d7a124a6deec4dcab80f65903bdc0a2aab18fd0c0d0a70e7358c325a1bc9af5`；runner 只读打开并校验，失配即中止。

**判定标准**（fail-closed）：
- **ACCEPT** ⟺ 工具已校准 ∧ samples 非空 ∧ 所有 sample 通过 D1（`sig(v)==sig(r(v))`）/D2（`sig(w)==sig(r(w))`）/merge 一致性（若 `r(v)==r(w)` 则 `sig(v)==sig(w)`）∧ 所有 probe 无 over-merge（规则未合并 oracle-distinct 值）。
- **REJECT** ⟺ 存在 sample 违反上述条件，或 probe over-merge。
- **UNDETERMINED** ⟺ 工具未校准 / 无 samples / 角色未声明（fail-closed）。

| 规则 | 角色 | 变换 | 预期 | 实测判定 | 匹配 | 证据类型 | 违反/过合并 |
|---|---|---|---|---|---|---|---|
| R01 | amount | amount_trailing_zeros | ACCEPT | ACCEPT | ✅ | modeled | — |
| R02 | date | date_iso（MM/DD/YYYY） | ACCEPT | ACCEPT | ✅ | mixed | — |
| R03 | subject_label | fold_repeated_punctuation | ACCEPT | ACCEPT | ✅ | modeled | — |
| R04 | subject_label | fold_whitespace | ACCEPT | ACCEPT | ✅ | modeled | — |
| R05 | subject_label | casefold_value | ACCEPT | ACCEPT | ✅ | mixed | — |
| R06 | recipient_iban | iban_truncate_last | REJECT | REJECT | ✅ | mixed | 违反（差一位合并） |
| R07 | permission | permission_to_read | REJECT | REJECT | ✅ | **observed** | 违反（r vs rw 合并） |
| R08 | amount | amount_round_to_int | REJECT | REJECT | ✅ | modeled | 违反（2200.5≈2200） |
| R09 | date | date_swap_day_month | REJECT | REJECT | ✅ | modeled | 违反（D1 改变日期） |
| R10 | subject_label | negation_flip | REJECT | REJECT | ✅ | modeled | 违反（"不"≈"是"） |

**10/10 判定与预期一致**——这构成"反事实验证管线能正确区分效果保持与非效果保持变换"的机制级证据。

**判定证据示例**：
- R01：`sig("2200.00")==sig("2200")`（amount 语义为数值，effect 叶 `account_funds:*` 投影后均为 `num(2200)`）；probe `("2200","2200.5")` oracle-distinct 且未 over-merge。
- R06：`r("…957")==r("…958")` 但 `sig` 不同（recipient_iban 为 exact_string，target 叶不同）→ merge 一致性违反。
- R07：permission→visibility 绑定使 `sig("r")≠sig("rw")`；E2 交叉证据（visibility/power_set separating_pairs=4, necessary）佐证 permission 为授权相关字段。
- R09：`date_swap_day_month` 不合并但 D1 失败（`sig("2022-03-07")≠sig("2022-07-03")`）——说明管线不止检测"合并"类危险，也检测"值被改写"类危险。

---

## 4. CEGAR 回放（M3/M3b 失败案例）

输入 3 个冻结失败案例；空注册表起跑；输出收敛记录。

| 失败案例 | 门禁① | 候选 | 门禁③ | 动作 | 覆盖 | 期望匹配 |
|---|---|---|---|---|---|---|
| F-M3-01（双句号伪影） | proceed（false_negative） | CEGAR-R01 fold_repeated_punctuation | ACCEPT | registered | ✅ | ✅ |
| F-M3b-01（句末数字盲区） | proceed（false_negative） | CEGAR-R02 number_boundary_punctuation | ACCEPT | registered | ✅ | ✅ |
| F-REJ-01（spurious permission 合并） | proceed（false_negative） | CEGAR-R03 permission_to_read | REJECT | refused（fail-closed） | ❌（设计使然） | ✅ |

**收敛记录**：`n_failures=3, n_registered_rules=2（CEGAR-R01/R02）, n_refused=1, all_failures_disposed=True, all_failures_covered=False（拒绝案例按设计保持字面比较）`；期望匹配 **3/3**。

关键点：第 3 例的**拒绝**本身就是收敛结局——CEGAR 在"假阴性修复冲动"与"效果保持"冲突时选择不注册不安全规则，运行期继续 fail-closed 字面比较。这与设计文档 §5.3 的"注册/拒绝"双出口一致。

---

## 5. 单元测试结果

`python3 -m pytest tests/ -v` → **39 passed**（pytest 8.3.5, Python 3.10.12）。

| 文件 | 覆盖点 | 用例数 |
|---|---|---|
| `test_registry.py` | schema 校验（缺键/未知变换/空 scope）、冻结哈希稳定性、哈希排除证据、重复注册、scope 过滤、freeze/save/load 往返、**篡改检测** | 10 |
| `test_validation.py` | 5 ACCEPT + 5 REJECT 参数化、10/10 期望匹配、**未校准工具 UNDETERMINED（fail-closed）**、无样本 UNDETERMINED、**probe over-merge 检测**、probe 守卫有效 | 12 |
| `test_runtime.py` | 规则链应用、**范围外/无工具上下文 fail-closed**、未注册角色原样、equivalent、**forbidden 路径对称性审计**、canonicalize_args 集成（输入不变性） | 8 |
| `test_cegar.py` | 3 案例回放、期望匹配 3/3、注册规则带验证记录、**security_event 门禁①硬停**、**门禁②结构拒绝**、**幂等去重** | 6 |

---

## 6. 与论文理论的对应说明

- **效果保持等价的判定实现**：`validation.py` 的 D1/D2/merge 差分即 §5.1 定义在冻结有限域上的操作化；"授权结论相同"由"授权是效果签名确定性函数"承接（与 E2 的 separating-pairs 判定同构）。
- **三阶段架构**：注册期=`validation.py`（反事实证据 + `rationale` 结构论证 + `scope` 适用范围）；冻结期=`registry.py`（行为哈希，加载校验）；运行期=`runtime.py`（`O(len)` 纯函数，fail-closed）。
- **CEGAR 循环**：`cegar.py` 三门禁实现 §5.3；`failure_cases_m3.jsonl` 直接取材 M3/M3b 修复先例（双句号、句末数字），归纳出的 CEGAR-R01/R02 与 `shadow_iffix` 的 G′ 修复（标点折叠、数字边界）一致。
- **对称性主张**：`runtime.py` 中 exact/forbidden 共用 `_canonical_compare`，`symmetry_audit` 提供证据——论文可主张"同一规范化函数贯穿两条判定路径"。
- **模型无关 vs 模型感知校准**：oracle 语义层（授权语义）模型无关且在预注册文件中固定；工具级校准门（slack 未校准→fail-closed）即"策略参数层模型感知校准"的体现。
- **与 E2 的关系**：E2 报告 `policy-family-sensitivity-report.json` 提供 visibility 的 separating pairs（4, necessary），作为 R07 拒绝的独立佐证；本实验不修改 E2 结果。
- **与 T1 的关系**：T1（refinement-monotonicity）检查轨迹单调性；本框架的注册期验证与 CEGAR 收敛记录提供了"规则集演化可追溯"的配套证据（`registry.frozen.json` 冻结哈希保证规则集行为可审计）。

---

## 7. 局限性与边界（如实声明）

1. **oracle 覆盖**：4/5 工具可校准（52/56 contexts）；slack 的 payload digest 在 stdlib 哈希族（sha256/md5/sha1/blake2/b3/crc32/adler32 等 8 种候选）下均不可复现 → 标记未校准，其上的规则一律 UNDETERMINED（fail-closed）。这是**保守设计**而非失败：未校准工具保持字面比较。
2. **证据类型**：10 条规则中多数样本为 modeled（反事实）而非 frozen 域中直接观察到（observed）。这是 E2 式反事实验证的正常形态——判定依赖已校准的效果模型外推，而非仅依赖观测；R07 是唯一的 fully-observed 案例。
3. **日期语义依赖声明**：R02 的通过依赖预注册的 `slash_convention=MM/DD/YYYY`（§5 明确日期格式化"视语义"）。若切换为 DD/MM/YYYY，`08/01/2026` 的判定将不同——语义声明必须随规则一起冻结（本实现已满足）。
4. **CEGAR 门禁②为脚本化归纳**：当前候选规则由失败案例文件直接携带（`induced_rule`），live 系统中由分析者/LLM 在环生成；结构 sanity 检查已实现，但归纳本身不在本模块范围内。
5. **运行期集成未落地**：`CanonicalizationRuntime.canonicalize_args` 提供集成接口，但未修改 V0-V3 冻结版（e77_runtime.py/patch），按约束留待后续。
6. **无 GPU、无网络、无外部依赖**：全部验证在 CPU 上、stdlib 内完成；随机种子不适用（全部为确定性纯函数，无采样）。

---

## 8. 复现命令

```bash
cd experiments/security-analysis-ablation-and-overhead/source/canonicalization-registry
python3 run_control_validation.py   # 10/10 控制集 + 冻结注册表
python3 run_cegar_replay.py         # CEGAR 回放
python3 -m pytest tests/ -v         # 39 个单元测试
```

**输出**：`results/canonicalization-registry/` 下 `control-validation-report.{json,md}`、`cegar-replay-report.{json,md}`、`registry.frozen.json`（5 条 ACCEPT 规则，哈希校验通过）。
