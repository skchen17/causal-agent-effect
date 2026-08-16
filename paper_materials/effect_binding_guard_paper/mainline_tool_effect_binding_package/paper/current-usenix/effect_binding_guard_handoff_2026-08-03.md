# Effect-Binding Guard 交接文档（2026-08-03 v2）

接替：`effect_binding_guard_handoff_2026-08-02.md`（v1 已于 08-03 完成 §7.2 收尾）。
本文档在 v1 基础上补充 **Phase 0 实施成果**（严格表示归因协议的 CPU 侧全部完成）与最新等待状态。

## 1. 本次会话完成的工作（§7.2 收尾）

| §7.2 任务 | 状态 | 交付物 |
|---|---|---|
| 1. finalizer 参数化 | ✅（08-02 完成） | `EXPECTED_RUNTIME` 参数化，v17 验收可直接复用 |
| 2. 隔离无效 atom specificity 结果 | ✅ 本次完成 | 见 §2 |
| 3. E71 artifact 链修复 | ✅（08-02 完成） | 9/9 测试通过，08-03 复验 |
| 4. 严格表示归因协议审阅 | ✅ 本次完成 | `strict_atom_representation_attribution_protocol_review_2026-08-03.md` |

## 2. §7.2.2 隔离交付物清单

1. **修正版 runner**：`experiments/intent-bound-runtime-guard/source/atom-targeted-prompt-guidance/atom_specificity_corrected.py`
   - 显式 `ConditionSpec` frozen dataclass（`uses_intent/uses_atom/uses_grounding_rules/shuffle_roles`），
     `__post_init__` 拒绝不一致组合；位置布尔 tuple 被禁用。
   - 纯函数 prompt 构造，`--prompt-only` 模式无 GPU 可运行（实测输出 30 行
     `results/atom-specificity-corrected/prompt_hashes.jsonl`，correct≠shuffled 全对成立）。
2. **门禁测试**：`shared/compatibility/tests/tests/test_atom_specificity_condition_schema.py`（8 项）
   覆盖交接文档要求的三条不变量：correct 与 shuffled prompt hash 必须不同；
   correct 条件保留 registry 原 roles；neutral control（no_guard）tokenizer-exact。
   另含 label 泄漏检查、hash 稳定性/互异性、shuffle 确定性。
3. **隔离横幅**：`experiments/intent-bound-runtime-guard/results/atom-specificity-summary.md` 顶部
   QUARANTINE 声明——Round 1--6 正面结论已撤销，禁止引用。
4. **claim map 禁令**：`paper/current-usenix/claim_to_source_map.md` 新增
   "Retracted Claims: Citation Prohibited" 节；321-case closed-loop attribution
   仍是唯一可引用的 granularity-transfer 证据（附选择条件边界）。
5. 原始 Round 1--6 脚本与输出未删除，仅作取证保留。

## 3. 当前阻塞状态：v17 726 全量运行

- 仍在运行：runner PID 578021，llama_cpp server PID 578023（端口 18087，双 GPU，
  tensor_split 0.35/0.65），08-03 下午推进到 travel suite（workspace→slack 已完成，
  travel+banking 约剩 320 case）。
- 运行目录：`experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-full-allow-with-trail-v17-726/`。
- **在 v17 结束前：不得启动任何新 GPU server；不得冻结 plan cache；不得改协议状态。**
- **自动等待已部署（2026-08-03 16:55）**：后台脚本 `v17_finalizer_watch.sh`（repo 根目录，
  日志 `v17_finalizer_watch.log`）每 5 分钟轮询 v17 runner、每 1 分钟轮询 llama.cpp server；
  两者退出后自动运行 v17 finalizer，成功则放置 `finalizer-passed.json` 标记并执行
  `build-protocol.py --freeze` 生成 `protocol.json`（状态 `protocol-frozen`）。
  最终 exit code 与产物均写入日志；接替者只需检查 `v17_finalizer_watch.log` 尾部。
  若 finalizer 失败（exit≠0），脚本不会放置标记或冻结，需人工排查后重跑 finalizer。

## 3.5 Phase 0 实施成果（2026-08-03，CPU 侧全部完成）

协议 `strict_atom_representation_attribution_protocol_2026-08-03.md` Phase 0 所列
CPU 工作已全部实施并通过测试：

| 交付物 | 位置 | 状态 |
|---|---|---|
| 协议核心模块（manifest 枚举/校验/hash/leakage） | `experiments/security-analysis-ablation-and-overhead/source/strict-atom-representation-attribution/protocol.py` | ✅ 21 项测试覆盖 |
| 四条件变体语义（V0--V4，显式 enum） | `.../variant_semantics.py` | ✅ 含 V2 registry 生成与 correct-vs-shuffled hash 门禁 |
| CLI：`--build-manifests` / `--freeze` | `experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-protocol.py` | ✅ build 可用；freeze 在 v17 finalizer 通过前正确拒绝（exit 2） |
| 726 官方 case manifest | `evaluation/strict-atom-representation-attribution/all-official-cases.jsonl` | ✅ 97 benign + 629 attack，suite 计数 280/126/160/160，无泄漏 |
| 160-case stability subset | `.../stability-subset.jsonl` | ✅ 每 suite 40（8 benign sha256 最小 + 32 attack 分层 round-robin） |
| 16-case smoke subset | `.../smoke-subset.jsonl` | ✅ 每 suite 1 benign + 3 attack |
| V2 raw-schema registry | `.../raw-schema-field-registry.jsonl` | ✅ 25 tools，全字段 `untyped_argument`，与 V3 同集 |
| 变体契约与产物 hash | `.../variant-contracts.json`、`.../artifact-hashes.json`、`.../manifests-summary.json` | ✅ |
| 门禁测试 | `shared/compatibility/tests/tests/test_strict_atom_representation_attribution.py` | ✅ 21 passed |

**回归基线（08-03）：90 passed**（E77 50 + E71 9 + prompt-guidance 9 + atom schema 8 + strict protocol 21 中
可运行子集；实际共跑 90 项全部通过）。

技术备注：协议目录名含连字符（`strict-atom-representation-attribution`），不能作为 Python 包导入，
且仓库内存在另一 `protocol.py`（adaptive-attack-evaluation），故 `build-protocol.py` 与测试均使用
`importlib.util.spec_from_file_location` 加载并注册 `sys.modules`（dataclass 依赖）；不要改为 sys.path 注入。

## 3.6 论文状态审核（2026-08-03，PaperSpine 流程）

按 PaperSpine skill 流程对 `paper/current-usenix/main.tex`（USENIX Security 2027 候选）做了状态审核，
完整报告：`paper/current-usenix/paperspine_paper_audit_2026-08-03.md`。结论：**论文本体健康**，
引用安全（latex_guard 0 错误 0 警告）、无禁令违规、关键数字与真源 JSON 逐项一致。

### 论文当前对齐的实验版本（重要）

| 论文内容 | 对齐实验 | 状态 |
|---|---|---|
| Headline 主表：ASR 54/627→2/627、benign 63→33/97、attack util 345→207/627、3/629 | **E78 容量匹配对比**（`analysis/results/e78_capacity_matched_statistics.json`，2026-07-29） | ✅ 已入论文 |
| 方法：`ours_e77_effect_diff_runtime` | **E77 runtime 的 v17 之前版本**（`effect_diff_runtime_recovery_normalization_v2` 阶段） | ⚠️ 非 v17 |
| 321-case closed-loop（3/273 vs 0/273） | `representation_closed_loop_attribution`（v1.1.2，适用性子集） | ✅ 已入论文（带边界） |
| 303 AgentLAB transfer（95→0、180→87、1439 匹配） | E79 固定保存攻击迁移 | ✅ 已入论文 |
| 339 calls / 100 effects / 17 compound / 13 cross | agentdojo-tool-effect-prevalence census | ✅ 已入论文 |
| 118 pairs（finite-domain） | 56-call 有限域验证（5 工具） | ✅ 已入论文 |
| 41→0（held-out） | ToolSandbox 32 contexts 预注册 | ✅ 已入论文 |
| 44/97 manifests、26 compile、169 attack keys | E84 reviewed-authority | ✅ 已入论文 |
| 7 个 exact-key ablations | E81 runtime ablations | ✅ 已入论文 |
| 528/822/240/336-row stresses | E48/E50 系 | ✅ 已入论文 |

**关键结论**：论文**尚未对齐 v17**（v17 726 全量仍在运行）；v17 完成后必须按协议 §13 顺序更新
（Evaluation protocol → Results 表 → failure analysis → Abstract/Introduction → claim map →
reproduction），Abstract/Results 的 E78 数字需以 v17 实测替换或并列，不得继续用 63-case 投影。

### 论文已知问题与待办

1. **中风险**：`main_single.tex`/`main_single.pdf`（07-30 单文件快照）已过期——与最新 `sections/`
   差异 1653 行、缺 `agentlab` 引用。提交/共享前删除或重新生成；以 `main.tex` 为唯一真源。
2. **低风险**：10 个顶层 section 超过 PaperSpine economy 预算（4-6）；USENIX 下可辩护，不强制。
3. **PaperSpine 工作流未初始化**：`paper_rewriting_output/` 不存在，`progress_check` 报告
   `next_stage=intake`。若后续要用 PaperSpine 全流程重写论文，需先运行 intake wizard 创建配置
   并确认动机（`references/intake.md`）；本次仅为状态审核，未启动重写。
4. **v17 结果落地后**：论文更新顺序与停止规则见 08-02 交接 §7.5（可保留 vs 暂不可写主张、
   收缩规则、旧数据保留）。

## 4. 后续执行顺序（给接替者）

### Phase A：v17 收尾（已自动化，等 GPU）

1. ~~等 v17 进程自然退出~~ 已由 `v17_finalizer_watch.sh` 自动完成（含 finalizer + 标记 + freeze）。
2. 仅需检查 `v17_finalizer_watch.log`：确认 `finalizer exit=0`、`freeze exit=0`，
   并核对 `evaluation/strict-atom-representation-attribution/protocol.json` 状态为 `protocol-frozen`。
3. 通过后记录 v17 实测 median seconds/case（协议 §12 时间估算要以此替换）。
4. 若日志显示 finalizer 失败：在 v17 目录保留证据，重跑 08-02 交接文档 §6.4 的命令排查。

### Phase B：协议冻结（v17 finalizer 通过后）

```bash
runs/e75_agentdojo_env/bin/python3 \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-protocol.py \
  --freeze
```

- 该命令校验 v17 目录 `finalizer-passed.json` 与 `plan_cache.json` 存在，生成
  `evaluation/strict-atom-representation-attribution/protocol.json`（状态 `protocol-frozen`，含全部 hash）。
- 冻结后协议状态改为 `protocol-frozen`；此后任何协议改动须产生新 protocol ID。
- 注意：`--freeze` 目前把 plan cache 复制为 `frozen-common-plan-cache.json` 的 hash 记录——
  实现已写为对 v17 `plan_cache.json` 直接 hash；如需物理副本，在 freeze 中补充复制逻辑。

### Phase C：GPU 实验（v17 释放后）

按协议 §9：16-case smoke → 4×726 主实验（V0→V3 顺序）→ 160-case stability
repeat 1/2 → finalize。预计 4,184 case executions（约 70--110 GPU 小时，以 v17
实测 median 为准）。判定规则与结果解释矩阵见协议 §2.3，不得中途改阈值。

### Phase D：论文更新

按协议 §13/§14 的顺序：Evaluation protocol → Results 表 → failure analysis →
Abstract/Introduction → claim map → reproduction。主对照若为负，收缩主张。
Round 1--5 正面结果在任何阶段不得复活引用。

## 5. 测试与验证命令

```bash
# 全量回归（08-03 实测 90 passed；含 strict protocol 21 项门禁）
cd shared/compatibility && PYTHONPATH=code:tests timeout 300 python3 -m pytest \
  tests/tests/test_strict_atom_representation_attribution.py \
  tests/tests/test_atom_specificity_condition_schema.py \
  tests/tests/test_effect_binding_guard_e77_effect_diff_runtime.py \
  tests/tests/test_atom_targeted_prompt_guidance.py \
  tests/tests/test_effect_binding_guard_e71_atom_field_necessity_runtime_guard.py -q

# 重建协议 manifests（幂等；不依赖 v17，仅需 e75 env）
cd <repo root> && runs/e75_agentdojo_env/bin/python3 \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-protocol.py \
  --build-manifests

# 修正版 runner 无 GPU 验证
python3 experiments/intent-bound-runtime-guard/source/atom-targeted-prompt-guidance/atom_specificity_corrected.py --prompt-only
```

已知环境问题：Python 3.10 下部分旧测试文件因 `StrEnum`（3.11+）收集失败，
为预存问题；请显式指定目标测试文件运行。

## 6. 关键文件索引

| 文件 | 作用 |
|---|---|
| `paper/current-usenix/effect_binding_guard_handoff_2026-08-02.md` | 上一份交接（任务清单真源、v17 命令） |
| `paper/current-usenix/strict_atom_representation_attribution_protocol_2026-08-03.md` | 严格归因协议（protocol-draft） |
| `paper/current-usenix/strict_atom_representation_attribution_protocol_review_2026-08-03.md` | 本次审阅结论 |
| `paper/current-usenix/atom_effect_experiment_evidence_audit_2026-08-03.md` | Round 1--5 接线缺陷取证 |
| `paper/current-usenix/claim_to_source_map.md` | claim 真源表 + 禁令节 |
| `experiments/intent-bound-runtime-guard/results/atom-specificity-summary.md` | 已隔离旧总结（顶部横幅） |
| `paper/current-usenix/paperspine_paper_audit_2026-08-03.md` | 论文状态审核报告（PaperSpine 流程，08-03） |
