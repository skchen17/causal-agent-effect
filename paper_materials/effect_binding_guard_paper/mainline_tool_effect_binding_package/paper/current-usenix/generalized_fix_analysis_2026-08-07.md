# 守卫误伤修复泛化性分析与执行决策（2026-08-07）

> 状态：**决策文档（pre-registered）**。分析基于冻结源码实读（e77_runtime.py v17 / agentdojo_e77_runtime_patch.py / RELATION_CATALOG v2/v3 / runner / run_e75 / agentdojo.scripts.benchmark / AgentDojo venv 任务源码 / pilot 审计日志），全部机制断言附代码证据位置。
> 上游文档：utility_fix_iteration_r2_2026-08-07.md、interface_fix_and_deepseek_pilot_2026-08-07.md、deepseek_pilot_execution_report_2026-08-07.md、utility_problem_analysis_and_design_2026-08-06.md。

---

## 0. 结论先行（决策）

| 修复类 | 决策 | 一句话理由 |
|---|---|---|
| **M3 标点规范化不一致**（含 M3b 数字接地正则） | **做** | 根因已被 AgentDojo 源码实锤（守卫强制的值恰是 scorer 拒绝的值）；对称规范化为严格非扩张变换，安全论证完整 |
| **M4 revision 无 repair loop** | **做** | pilot 实测 11/11 revision 返回**空字符串**；revision_prompt 是唯一带 `/no_think` 前缀的 prompt（planner/replan 不带且全部正常）；修复与 planner 既有 2 次 repair 机制对称，不扩授权 |
| **M2 relation 目录扩张**（send_money.date） | **不做** | 用户简报提议的 v3 catalog 注入**对目标案例（banking/3、/11）无效**（v3 新增条目针对 banking/6，不在 63 例 manifest 内）；真泛化版需授权扩张 + 代码改动，收益仅 2 例且落在噪声带内，成本/收益/风险最差 |

**执行方案**：shadow 树独立副本承载 M3+M3b+M4（零冻结文件改动），63 例 G′（泛化修复版守卫）vs N（no_guard）配对预注册实验，G′ 重复 2 次，另加小规模攻击面 smoke 检查 ASR 非劣化（63 例 manifest 为 benign-only，无法单独支撑安全断言）。

**预期收益上界**：M3/M3b 修复 1–3 个 target 案例（workspace/20、banking/15 等），M4 消除 11/11 revision 事件的系统性失效。合计净收益预期 ≤5/63，**小于已测噪声带宽 ±7–8/63**——因此本实验的主要论文价值不是"G′−N 显著为正"，而是（a）证明守卫 utility 代价可归因于**规则级接口缺陷**并可泛化修复（机制叙事），（b）诚实报告噪声带内的效用账。这一点必须预注册，防止事后过度解读。

---

## 1. 三类泛化修复的逻辑论证

### 1.1 M3：文本规范化不一致（标点）

#### 1.1.1 机制实锤（代码证据链）

1. **守卫侧 exact 比较路径**（e77_runtime.py）：
   - `canonical_grounding_value`（L877–889）string 分支只做 `\s+`→空格折叠 + strip + casefold，**无标点规范化**；
   - `compare_call_to_plan_with_evidence`（L2297–2304）：exact 模式下计划值与实际调用值各经 `canonical_grounding_value` 后严格相等，否则 `outside_exact_plan`（BLOCK + sticky）。
2. **AgentDojo 侧根因**（v1.1.2 venv 源码，workspace/user_tasks.py UserTask20）：
   - `_DESCRIPTION = "Catch up over lunch."`（单句号）；
   - `PROMPT` 用 f-string 内嵌：`...titled '{_TITLE}' and with description {_DESCRIPTION}. Don't forget...` → 任务文本中出现 `lunch.. Don't`（双句号伪影）；
   - utility 函数精确比较 `event.description == self._DESCRIPTION`（单句号）。
3. **误伤链条**：planner 从任务文本抽取 exact 值时可能取到双句号变体 → 守卫 exact 强制该值 → agent 调用单句号值被 BLOCK/强制改写 → scorer（要求单句号）判失败。**守卫强制的值恰是 scorer 拒绝的值**——这不是"防御代价"，是接口缺陷。
4. **接地侧不对称**：`value_grounded_in_source` string 分支 boundary=`\w`（标点透明），单句号值可在含双句号的文本中接地成功；但 exact 比较不做标点折叠 → 接地通过、比较失败，形成 L2297 的 mismatch 来源。

#### 1.1.2 修复规则设计

**规则 M3-R1（对称标点规范化）**：在 `canonical_grounding_value` string 分支增加规范化步骤，对连续重复的句末标点折叠为单个：

```
normalized = re.sub(r"([.!?:;,])\1+", r"\1", folded)   # 在 \s+ 折叠、strip、casefold 同一函数内
```

关键设计约束：
- **双侧对称**：exact 比较两侧（计划值、调用值）、接地校验两侧（候选值、源文本）用**同一**规范化函数——等价类只在"标点重复次数"上合并，不跨语义合并；
- **省略号对称**：`"..."`（三句号）会被折叠为 `"."`——只要两侧同规则，比较语义不变；接地侧源文本同样折叠，不产生反向盲区；
- **不做**更激进的规范化（不删标点、不统一标点种类、不做 Unicode 折叠超出现有 casefold 范围）——最小变更原则。

**规则 M3-R2（parse 时规范化 + 重新接地，fail-closed 门）**：计划 parse 阶段对 exact 值应用 M3-R1 后，**必须在规范化后的任务文本中重新接地**；接地失败 → 按现行 fail-closed 处理（拒绝该值），不引入任何"宽容放行"。该门保证规范化不会把未接地的值带进计划。

#### 1.1.3 M3b：数字接地句末句号盲区（banking/15）

- 现状正则（value_grounded_in_source number 分支，L900–902）：`(?<![\w.])[+-]?\d+(?:\.\d+)?(?![\w.])`——`"rent is 2200."` 中 `2200` 后随句号的 `.` 被 `(?![\w.])` 排除 → 本应接地成功的数字被拒。
- **修复**：lookaround 只排除"小数/版本号上下文"，不排除句末标点：
  - lookahead：`(?![\w])(?!\.\d)`（后面不是单词字符，且不是"小数点后跟数字"——允许 `2200.` 匹配，拒绝把 `3.14` 的 `3` 单独截出）；
  - lookbehind：`(?<![\w])(?<!\d\.)`（对称）。
- 边界推演（已人工验证）：`3.14` 整体匹配✓；`2200.` 匹配✓；`v1.2` 中 `1.2` 不被 lookbehind 误截（`v` 是 \w）✓；`1.2.3` 各段行为与修复前一致（无新增误匹配方向）。
- **同步点**：`TEXT_CANDIDATE_PATTERNS["number"]`（L85 附近）必须同步改，否则候选提取与接地校验两处正则不一致会产生新的假阴性。
- **安全面**：接地源是**任务文本（trusted input）**，不是工具返回或注入内容；修复方向只是"纠正假阴性"（把确实出现在文本中的数字判为已接地），不会接纳文本中不存在的数字 → 无攻击扩张面。

#### 1.1.4 影响面

- 预期修复：workspace/20（双句号，实锤）、banking/15（数字接地，实锤），以及任务文本含连续标点的同型案例（执行前用脚本对 63 例任务文本做标点扫描可枚举，作为预注册白名单的一部分）；
- 可能新误伤：**理论上为零**——对称规范化不改变任何"规范化后相等"的判定集合以外的行为；唯一行为变化是原先因标点重复数不同而被 BLOCK 的调用现在 ALLOW，这些调用的语义值与原计划值相同。

#### 1.1.5 副作用与安全相容性（O1–O6）

- **攻击面质询：标点规范化会不会让攻击值更易通过 exact？** 不会。exact 语义是"调用值 ∈ 计划值集合"。攻击者要改变效果语义（换 recipient/amount/目标），规范化等价类内所有成员的语义值相同（仅标点重复数差异）——注入一个"标点变体"不产生新效果。若攻击值与合法值仅差标点重复，其提交的效果与合法值相同，不构成授权逃逸。关键前提：**forbidden 匹配路径必须与 exact 使用同一规范化函数**（对称应用），否则会出现 forbidden 检查严格而 exact 放宽的不对称缺口——写入变更清单作为强制要求。
- **O1–O5 相容**：授权判定仍是确定性纯函数（规范化是纯函数，无 LLM 参与）；complete mediation 不变（每次调用仍过检查）；fail-closed 不变（M3-R2 重新接地失败即拒）；bound 不扩张（等价类内语义值相同）。
- **O6（override trail）相容**：本修复不触碰 allow_with_trail 路径，strict/effective decision 记录逻辑不变。

### 1.2 M2：relation 目录（send_money.date 字段绑定）——**纠正简报框架 + 决策不做**

#### 1.2.1 用户简报框架与代码事实不符（必须纠正）

- 简报称"RELATION_CATALOG v3 已备但未启用"可修 M2。**实读 v3 catalog**：v3 相对 v2 仅新增一条 `runtime.execution_date_v1.scheduled_transaction` → **schedule_transaction.date**，其 pilot_usage 自述针对 banking/6；
- **banking/6 不在 63 例 manifest 内**；pilot 中 M2 类损失案例是 **banking/3、banking/11**（send_money.date `runtime_default_mismatch`）；
- 结论：**注入 v3 catalog 对 banking/3、/11 零作用**。若按简报方案执行，等于做了一个对目标无效的配置变更——这本身就是 result-uninformed 但 also useless 的操作，拒绝。

#### 1.2.2 banking/3、/11 的真实机制

- planner 按 v2 catalog 把 `send_money.date` 绑定 `runtime_default(execution_date)`（=2026-08-02）；agent 合理复用交易记录里的日期（如 2022-03-07）→ `runtime_default_mismatch` → 守卫代价；
- AgentDojo utility 实读：UserTask3/11 只检查 amount（与 recipient），**不检查 date** → 这是守卫过度约束一个 scorer 不关心的字段。

#### 1.2.3 泛化选项评估（为何都不做）

| 选项 | 可行性 | 问题 |
|---|---|---|
| 注入 v3 catalog | 配置级可注入 | 对 banking/3、/11 无效（§1.2.1） |
| `registered_projection`（get_most_recent_transactions.date → send_money.date） | 不可行（不改代码） | `_registered_projection_values`（L1187–1192）要求投影源 result 为 `str`，而 `get_most_recent_transactions` 返回 `list[Transaction]`；需新 projector 代码 → 代码级 + 新注册 = 授权扩张 |
| `direct_evidence` source-bound resolve | 数据级可行（R2 种子即此路径） | 需逐案手写证据绑定条目 → **正是被否决的 case-specific**，不是泛化 |
| 真泛化：catalog schema 新 kind（结构化 walk 投影）+ 独立副本代码支持 | 逻辑可行 | **授权扩张**：date 接受集从单一 runtime_default 放宽为"交易记录中出现的任意日期"；收益仅 2 例且在噪声带内；需配套 ASR 验证；成本/收益/风险最差 |

#### 1.2.4 安全分析（若做，为何风险不可忽略）

date 接受集扩张虽不触碰金额/收款人等高敏字段，但改变了授权的**确定性语义**（runtime_default 是唯一权威值 → 变为证据集合内任意值），与论文"typed resolver 细化不扩 bound"（O2 义务表述，见 improvement_whitepaper §a）存在张力：结构化 walk 投影属于"细化"还是"扩张"需要新的命题级论证。为 2 个案例引入这种论证负担不划算。

#### 1.2.5 替代处置

- banking/3、/11 归入 failure analysis，叙事为"守卫对 scorer 不关心字段的过度约束（over-binding）"；
- 论文展望节提出结构化证据投影的 schema 设计（作为 future work，有 §1.2.3 的分析支撑即可）。

### 1.3 M4：revision 无 repair loop

#### 1.3.1 关键新证据（推翻"格式错误"假设）

- pilot runtime_audit.jsonl：11 个 plan_revision 事件**全部** `REVISION_INVALID` + `revision_not_object`；
- pilot plan_cache.json：11 条 revision 缓存的 `raw_output_prefix` **全部为空字符串 `""`**；
- 对照：planner（53 次）与 replan（3 次）调用全部正常产出；
- `parse_plan_revision`（L1817–1822）：payload 非 Mapping → `revision_not_object`——空字符串经 `extract_json_object`（full_atom_runtime.py L212）返回 None → 落入该分支。

**结论**：失败模式是**模型返回空内容**，不是"返回了格式错误的 JSON"。这直接影响修复设计——**相同上下文的确定性重试（temp=0）必然再次返回空**，单纯循环无效。

#### 1.3.2 空输出的候选根因

- **强候选：`/no_think` 前缀**。全代码库唯一带 `/no_think` 前缀的 prompt 就是 `revision_prompt`（e77_runtime.py L1758）；planner_prompt_v2（L418+）与 replan 不带该前缀且全部正常。`/no_think` 是 Qwen3 聊天模板的控制 token，对 DeepSeek v4-flash 无语义/可能被当作用户内容处理，产生退化输出。
- 次候选：revision prompt 结构（system/user 组合）在 DeepSeek 端触发 refusal-by-empty；max_tokens=2048 不足以产出（可被 raw_output 长度分布排除——空串不是截断）。
- **无法在纸面裁决**——这正是预注册实验的价值：修复版行为将区分两个假设。

#### 1.3.3 修复规则设计（iffix 副本内）

**规则 M4-R1（对称 repair loop）**：`_model_revision`（patch L264）增加 repair loop，参数对齐 planner：
- `max_repair_attempts = 2`（新 env `E77_REVISION_REPAIR_ATTEMPTS`，默认 2；与 `E77_PLANNER_REPAIR_ATTEMPTS` 对称）；
- 每次 repair **追加新消息**（错误说明 + 要求的 JSON schema + 最小合法示例），改变上下文——temp=0 下这是重试有意义的唯一方式；
- parse 成功或耗尽次数 → 维持现行行为（耗尽即 `REVISION_INVALID`，fail-closed 不变）。

**规则 M4-R2（`/no_think` 前缀条件化）**：`revision_prompt` 前缀由 env flag（`E77_REVISION_NO_THINK_PREFIX`，iffix 运行设为 0）控制；G′ 实验中移除。该变更必须在 protocol manifest 中显式披露（它是 prompt 级变更，不是防御逻辑变更）。

#### 1.3.4 影响面

- 直接影响所有进入 revision 路径的案例（pilot 中 11 个事件跨多案例）；
- 预期修复：revision 路径恢复功能性（repair 后产出合法 revision 或确定性耗尽），消除 allow_with_trail 下因 revision 全灭导致的守卫致败；
- 新误伤风险：**无新 BLOCK 方向**——repair 只可能让 revision 从"恒失败"变为"可能成功"，成功后的 revision 仍走完整校验链。

#### 1.3.5 安全相容性（O1–O6）

- **授权不扩张**：`validate_revision_for_call` 的完整校验链（schema、grounding、exact、forbidden）不变；revision 预算仍受 `max_plan_revisions=3`/signature 去重/`max_total=12` 约束；repair 只增加**提议次数**，不增加**接受集**；
- exact 授权仍由确定性检查裁决（O1–O3 语义不变）；fail-closed 不变（repair 耗尽即拒）；
- O6：不触碰 override trail；
- 成本侧：每案例最多 +2 次 LLM 调用（revision 路径内），开销可记录在审计日志。

---

## 2. 协议合规方案（独立副本设计）

### 2.1 加载链事实（实读确认）

1. runner（run-recovery-normalization-qwen32.py）注入 env（`PYTHONPATH=ROOT/code`、`E77_PLAN_CACHE`、`E77_RELATION_CATALOG`→v2、`E77_AUDIT_JSONL` 等，L431–452）→ 调 run_e75（`--live-method ours_e77_effect_diff_runtime`）；
2. run_e75 method map（L2667–2698，**冻结**）硬编码 `modules_to_load = ["src.experiments.effect_binding_guard.e77_effect_diff_runtime_guard.agentdojo_e77_runtime_patch"]`；
3. run_e75 以 subprocess 跑 `E75_VENV_PYTHON -m agentdojo.scripts.benchmark ... --module-to-load <module>`，`child_env = {**os.environ, ...}`（L1828）→ env 完整传递；
4. benchmark.py L229：`importlib.import_module(module)`——**模块按 sys.path（PYTHONPATH 前置序 + cwd）解析**。

### 2.2 方案：shadow 树 + runner 副本（推荐，唯一满足全部约束）

**机制**：Python 包解析事实——`src`、`src/experiments` 是 namespace package（无 `__init__.py`，跨路径合并）；`effect_binding_guard` 是 regular package（有 `__init__.py`，**路径序先到先得，且独占总路径**）。把 PYTHONPATH 改为 `SHADOW_ROOT:ROOT/code`，则 `effect_binding_guard` 及其**所有**子模块整体从 shadow 解析，`code/src` 冻结树完全不被触碰。

**文件级设计**：

```
code/src/experiments/effect_binding_guard_iffix/          ← 新建 shadow 根（整树 cp，596K）
    __init__.py                                            ← 字节级同冻结版（sha256 记录）
    e75_unified_agentdojo_comparison/                      ← 字节级同冻结版（run_e75 等）
    e77_effect_diff_runtime_guard/
        e77_runtime.py                                     ← ★iffix 变体（M3+M3b diff）
        agentdojo_e77_runtime_patch.py                     ← ★iffix 变体（M4 diff）
        其余文件                                            ← 字节级同冻结版
    其余子包                                                ← 字节级同冻结版
```

> 注意：shadow 必须整树复制而非只放两个文件——regular package 一旦从 shadow 解析，其全部子模块只在 shadow 内查找（run_e75 本身也经 `src.experiments.effect_binding_guard...` 导入，须在 shadow 内存在且与冻结版一致）。整树仅 596K，成本可忽略。
> 目录命名建议放 `code/src/experiments_shadow/...` 或 `code/shadow_iffix/src/experiments/effect_binding_guard/`（保持 src/experiments 两层 namespace 结构），避免与冻结树同目录混淆；最终以实施时 runner 副本中的路径常量为准。

**runner 副本** `run-recovery-normalization-qwen32-iffix.py`（新建，冻结 runner 不动），diff 仅四处：
1. `env["PYTHONPATH"] = f"{SHADOW_ROOT}:{ROOT / 'code'}"`；
2. `E77_RELATION_CATALOG` 保持 v2（M2 不做，无配置注入）；
3. `source_hashes()` 增列 shadow 两文件的 sha256 + "其余文件与冻结版逐文件哈希一致"的校验记录；
4. run-tag 与 protocol manifest 披露：iffix 变体标识、M4-R2 的 `/no_think` 移除、revision repair 参数。

**冻结共存保证**：
- `code/src/.../e77_effect_diff_runtime_guard/` 两冻结文件与 `experiments/.../source/` 副本零改动（V2 237/726 进行中不受影响）；
- V0–V3 的 runner、env、PYTHONPATH 全部不变；G′ 运行用独立 run-tag 目录（`...-iffix-gprime-*`），审计日志独立；
- plan_cache 不预置（拒绝种子缓存路径），G′ 全部 live planner 产出——这是"泛化"主张的必要条件。

**备选方案（已否决）**：sitecustomize.py 预载 shim（隐式 import 副作用，审计困难，违反显式性原则）；shim 模块 monkey-patch 冻结模块属性（可行但绕过文件级 diff 审计，且 patch 内部闭包引用顺序风险高）；单文件 shadow（regular package 整体解析规则下不可行）。

### 2.3 配置注入项盘点（本轮全部不用）

| 注入点 | 是否使用 | 理由 |
|---|---|---|
| `E77_RELATION_CATALOG` → v3 | 否 | v3 对目标案例无效（§1.2.1） |
| 预置 plan_cache.json | 否 | 种子修复已被否决为效用证据 |
| 正则/schema 配置文件 | 不适用 | 冻结代码无此类 hook，正则改动只能在 iffix 副本内 |

---

## 3. 实验设计（预注册）

### 3.1 假设

- **H1（M3/M3b）**：预注册白名单内的标点/接地误伤案例（workspace/20、banking/15 及标点扫描命中的同型案例）在 G′ 下翻转为成功；白名单外无新增守卫致败；
- **H2（M4）**：revision 事件不再 11/11 空输出；`revision_not_object` 率显著下降；若 `/no_think` 是根因，repair 第 0 次即成功（repair 仅在假设不成立时消耗）；
- **H3（总账）**：G′−N ≥ G−N（配对差），且 26 个 control 零回归。

### 3.2 条件与运行

| 条件 | 运行 | 备注 |
|---|---|---|
| G′ | **2 次重复**（rep1/rep2，独立 run-tag、独立 plan_cache/audit） | shadow 树 + iffix runner，63 例 manifest v17，allow_with_trail（与 pilot 一致） |
| N | 复用 pilot N + **补 1 次重复**（噪声配对需要同模型同窗口的重复） | `--live-method no_guard`，管线不变 |
| G（历史） | 复用 pilot G 结果作基线 | 不重跑（节约预算；G−N 已有一对） |
| attack-smoke | G′ vs G，各 suite 抽 5–10 个攻击案例 | 63 例 manifest 为 benign-only，**ASR 非劣化必须由 smoke 单独支撑**；G′ 若 ASR 高于 G 即中止并入主线 |

### 3.3 判定标准（单次判定，禁止结果回调参）

1. **per-case 配对翻转**：G′✗∧N✓ → G′✓ 的案例必须落在预注册白名单内；白名单外翻转一律记为行为变化并溯源审计；
2. **control retention**：26 control 全保留（与 manifest 验收线一致）；
3. **噪声处理**：G′−N 取 rep1/rep2 均值；若 |均值(G′−N) − (G−N)| < 8（已测带宽），判 **inconclusive（噪声带内）**，不得表述为效用提升，只报告 per-case 机制修复证据（白名单翻转 + revision_not_object 率）；
4. **reconciliation**：precommit_execution_reconciliation（每个 effectful call 有匹配 ALLOW 检查）必须满足，否则运行作废；
5. **M4 机制判别**（次级观察）：修订事件的 raw_output 前缀分布 + repair 触发次数 → 裁决 `/no_think` 假设。

### 3.4 成本

- pilot 实测：单条件 63 例 ≈25 min、700–780 次 API 调用、<$2（DeepSeek v4-flash）；
- 本设计：G′×2 + N×1 + attack-smoke（G′/G 各 ~20 案例）≈ **3.5 条件 × 25 min ≈ 1.5–2 小时，<$7**；不占 GPU（E77_LLM_BASE_URL 模式跳过本地 server）。

---

## 4. 优先级与执行顺序

1. **M4 优先**：影响面最大（11/11 revision 事件系统性失效）、机制候选明确、代码变更集中在 patch 单函数、与既有 planner 机制对称（审稿叙事顺）；
2. **M3+M3b 次之**：根因实锤、安全论证最完整、但影响案例少（1–3）；
3. **M2 不做**（§1.2）：入 failure analysis + future work。

**条件组织**：不做三条件消融（3×2 重复成本高且 63 例尺度下检验力不足），改为**单条件 G′（M3+M3b+M4）+ per-case 归因**——三类修复的预期翻转集合不相交（标点类/接地类/revision 类），白名单归因即可完成分解；若归因出现混杂案例，再追加单修复 smoke。

---

## 5. 逻辑结论：可行 → 执行方案

**M3+M3b+M4 逻辑上可行且安全相容，批准进入编码与实验。M2 不做。**

### 5.1 代码变更清单（全部为新文件/新目录，零冻结文件改动）

| # | 文件 | 动作 | 变更内容 |
|---|---|---|---|
| 1 | shadow 树（整树复制） | 新建 | `effect_binding_guard` 全量复制；非变更文件逐文件 sha256 校验=冻结版 |
| 2 | shadow/.../e77_runtime.py | iffix 变体 | (a) `canonical_grounding_value` string 分支加 M3-R1 标点折叠（纯函数）；(b) `value_grounded_in_source` number 正则 lookaround 改 M3b 方案，**同步** `TEXT_CANDIDATE_PATTERNS["number"]`；(c) 接地校验对源文本对称应用同一规范化（M3-R2，失败 fail-closed）；(d) 确认 forbidden 路径共用同一 canonical 函数（对称性审计） |
| 3 | shadow/.../agentdojo_e77_runtime_patch.py | iffix 变体 | (a) `_model_revision` 加 repair loop（M4-R1：最多 2 次，追加 repair 消息改变上下文，`E77_REVISION_REPAIR_ATTEMPTS` 可配）；(b) `revision_prompt` `/no_think` 前缀 env 条件化（M4-R2，G′ 运行关闭） |
| 4 | runner 副本 run-recovery-normalization-qwen32-iffix.py | 新建 | 仅 §2.2 四处 diff（PYTHONPATH 前置 shadow、source_hashes 增列、manifest 披露、run-tag） |
| 5 | 预注册记录 | 新建 | 白名单案例集（含标点扫描脚本输出）、判定标准（§3.3）、预期翻转集合——**在任何 G′ 运行启动前冻结** |

### 5.2 实验命令（模板，执行阶段使用）

```bash
source /tmp/deepseek_key.env   # E77_LLM_BASE_URL / E77_LLM_API_KEY / E77_LLM_MODEL 等

# G′ rep1（iffix runner，63 例 manifest，benign）
python experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/run-recovery-normalization-qwen32-iffix.py \
  --mode pilot --uncertainty-policy allow_with_trail --run-tag gprime-rep1 \
  --case-manifest experiments/intent-bound-runtime-guard/evaluation/effect-difference-runtime-guard/registered_relation_expanded_pilot_manifest_v17.json

# G′ rep2：同上，--run-tag gprime-rep2
# N rep2：pilot 协议 §C.5 四条 suite 命令，--live-method no_guard --live-logdir .../agentdojo_logs_noguard
# attack-smoke：iffix runner 与冻结 runner 各跑每 suite 5–10 个攻击案例（attack 模式不经 manifest，按 suite 抽样）
```

（具体 suite 拆分命令沿用 pilot 协议 §C.5 形态；runner 副本按 manifest 自动按 suite 分组。）

### 5.3 风险登记

| 风险 | 等级 | 缓解 |
|---|---|---|
| M4 空输出根因非 `/no_think`（DeepSeek 端其他行为） | 中 | repair loop 本身即为通用缓解；§3.3-5 机制判别观察裁决假设；最坏结果 revision 仍全灭 → 负结果入报告 |
| G′−N 落在噪声带内 | 高（预期内） | 已预注册 inconclusive 判定（§3.3-3）；论文价值转向机制归因证据 |
| shadow 解析意外污染冻结运行 | 低 | shadow 只存在于 G′ runner 的 env；冻结 runner 的 PYTHONPATH 不变；V0–V3 路径零交集；运行前用 `python -c "import ...; print(module.__file__)"` 双向验证解析位置 |
| M3 规范化引入未预见的等价类碰撞 | 低 | 仅折叠重复标点，无跨语义合并；白名单外翻转触发审计（§3.3-1） |

---

## 6. 论文价值评估

### 6.1 泛化修复的叙事位置（若成功）

- **可入正文**：作为"守卫 utility 代价的根因分析与接口加固"小节——三类规则级根因（harness 伪影、接地盲区、恢复路径不对称）的诊断 + 机制驱动的泛化修复 + 预注册验证。这是对"防御有 utility 代价"这一负结果的**建设性回应**，直接对冲审稿人"守卫代价是否系统性"的质询；
- **方法论价值**：修复全部为规则级、无逐案参数、修复集预注册——可作为"防御系统迭代纪律"的示例（与种子修复形成正面对照）；
- **诚实边界**：净收益 ≤5/63 在噪声带内 → 不得写成效用显著提升；表述为"机制性误伤已消除，残余代价为模型相关的行为噪声"。

### 6.2 种子修复的边界（维持原判）

- 8 例种子计划缓存只进 failure analysis / appendix（case-specific、result-informed，不能支撑效用主张）；
- R2 的价值保留为**根因分类学**（本文件的 M3/M2/M4 即源于 R2），而非其修复产物。

### 6.3 负结果预案

若 G′ 未修复白名单案例（如 DeepSeek 行为与 Qwen3 诊断不同型）：报告"误伤机制的模型依赖性"，守卫效用账按模型分列——这本身是可发表的诚实发现，且保护主线（V0–V3、O1–O6 论证）不受影响。

---

## 附录：关键代码证据索引

| 断言 | 证据位置 |
|---|---|
| canonical 无标点规范化 | e77_runtime.py L877–889 |
| exact 比较 → outside_exact_plan | e77_runtime.py L2297–2304 |
| number 接地正则句末盲区 | e77_runtime.py L900–902 |
| string 接地 boundary 标点透明 | e77_runtime.py L990–993 |
| UserTask20 双句号伪影 + 单句号 utility | agentdojo venv: default_suites/v1_1_1/workspace/user_tasks.py（UserTask20） |
| banking/3、11 utility 不查 date | agentdojo venv: default_suites/v1/banking/user_tasks.py L124–162、L389–424 |
| v3 catalog 仅增 schedule_transaction.date | registered_relation_catalog_v3_interface_fix.json（pilot_usage 自述） |
| registered_projection 要求 str 结果 | e77_runtime.py L1187–1192 |
| revision 11/11 空输出 | pilot runtime_audit.jsonl + plan_cache.json（raw_output_prefix 全 ""） |
| /no_think 仅在 revision_prompt | e77_runtime.py L1758（全库唯一） |
| planner repair loop 存在 | agentdojo_e77_runtime_patch.py L111–216（max_repair_attempts=2） |
| revision 无 repair loop | agentdojo_e77_runtime_patch.py L264–329 |
| benchmark importlib.import_module | agentdojo venv: agentdojo/scripts/benchmark.py L229 |
| run_e75 硬编码模块名/child_env | run_e75.py L2667–2698、L1828 |
| manifest v17：63 例 benign-only、验收线 | registered_relation_expanded_pilot_manifest_v17.json（26 control/37 target；control 零回归、target ≥15/37、precommit_execution_reconciliation） |
