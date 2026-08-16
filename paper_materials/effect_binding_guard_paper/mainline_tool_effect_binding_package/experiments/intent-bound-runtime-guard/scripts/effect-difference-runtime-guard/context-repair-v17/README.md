# context-repair-v17：v17 参数化 context-repair 工具链（P2-b 路径）

本目录提供 v17 全量运行（`effect_diff_runtime_relation_onboarding_v17`）的
参数化 context-repair 工具链，对应已批准的决策树分支 **P2-b**
（`paper/current-usenix/pm_process_review_research_2026-08-05.md` §4）：
400 截断复发 → 分级加窗重跑受影响案例 → 不可变 overlay merge → finalizer → 冻结。

## 选址理由

放在 `experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/`
下（而非 `security-analysis-ablation-and-overhead/.../strict-atom-representation-attribution/`），因为：

1. v2 先例脚本（`run-qwen32-context-repair.py`、`merge-qwen32-context-repairs.py`）、
   v17 runner 与 finalizer 全部位于该目录，repair 运行目录也落在同实验的 `runs/` 下；
2. 本工具直接消费 finalizer（`finalize-recovery-normalization-qwen32-full.py`）
   并产出 `finalizer-passed.json`，与 freeze 链（`build-protocol.py --freeze --run-root <merged>`）
   通过运行目录约定衔接，无需共享代码；
3. 保持 `strict-atom-representation-attribution/` 仅含协议构造/测量脚本的既有边界。

## 脚本

`context-repair-v17.py`，四个子命令（仅 Python 标准库；detect/selftest/merge-dry-run 为 CPU-only）：

| 子命令 | 作用 | GPU |
|---|---|---|
| `detect` | 扫描 base 运行目录，识别 post-tool 空 assistant（400 截断签名）；输出受影响案例清单、分级重跑命令清单、merge 计划 JSON | 否 |
| `repair` | 仅重跑受影响案例到一个独立 repair 运行目录；`--dry-run` 只打印命令与环境契约 | 是（执行模式） |
| `merge` | 不可变 overlay merge：base 只读硬链接 + 修复行替换 + audit 串联 + plan_cache 合并 + 干净 command_status + finalizer 15 门 + freeze 标记 | 否 |
| `selftest` | 合成夹具端到端测试（含 base 不可变性、幂等、篡改拒绝断言） | 否 |

## 标准流程（r2 完成后）

```bash
SCRIPT=experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/context-repair-v17/context-repair-v17.py
R2=experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2
RUNS=experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard

# 0) r2 runner 退出后（pgrep 确认），CPU 探测（也可在运行中做部分快照预览）
python3 $SCRIPT detect --run-root $R2

# 1) 分级重跑（每级一个独立 stage 目录；GPU 独占，禁止与任何主运行并发）
python3 $SCRIPT repair --run-root $R2 \
    --repair-root $RUNS/v17-context-repair-stage1-73728 \
    --window 73728 --dry-run            # 先 dry-run 核对范围与命令
python3 $SCRIPT repair --run-root $R2 \
    --repair-root $RUNS/v17-context-repair-stage1-73728 --window 73728
# 若 repair_report.json 仍有非 repaired_clean 案例：升级窗口再来一级
python3 $SCRIPT repair --run-root $R2 \
    --repair-root $RUNS/v17-context-repair-stage2-81920 --window 81920
python3 $SCRIPT repair --run-root $R2 \
    --repair-root $RUNS/v17-context-repair-stage3-122880 \
    --window 122880 --kv-type q8_0      # 122880 需 Q8_0 KV（v2 先例）

# 2) overlay merge（stage 按窗口升序重复传入；只传实际执行过的 stage）
python3 $SCRIPT merge --run-root $R2 \
    --stage $RUNS/v17-context-repair-stage1-73728 \
    [--stage $RUNS/v17-context-repair-stage2-81920] \
    [--stage $RUNS/v17-context-repair-stage3-122880] \
    --merged-root $RUNS/recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2-context-repaired \
    --dry-run                            # 先看 merge 计划
# 正式 merge：自动跑 15 门 finalizer；全过则写 finalizer-passed.json

# 3) 冻结（R-1 参数化后的 freeze 链）
PYTHONPATH=code:. python3 \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-protocol.py \
  --freeze --run-root $RUNS/recovery-normalization-qwen32-full-allow-with-trail-v17-726-r2-context-repaired
```

## 护栏与语义（全部 fail-closed）

- **base 只读**：merge 对 base/stage 目录零写入；selftest 对 base 全文件做
  sha256 指纹前后对比断言（曾因硬链接原地写入会污染 base 而发现并修复）。
- **范围守卫**：`repair` 拒绝重跑任何不带截断签名的案例；`--cases` 显式列表
  与探测结果取交集，未确认项直接 exit 2。
- **GPU 排他**：检测到 v17 全量 runner 存活时，`repair` 执行模式 exit 2；
  dry-run 允许但给出"部分快照"警告。
- **runtime 一致性**：base 与每个 stage 的 `runtime_version` 必须匹配
  `--runtime-version`；`E77_UNCERTAINTY_POLICY` / `E77_EXECUTION_DATE` 等
  从 base manifest 继承，禁止凭空构造（协议 §2.2：除上下文窗口外不得改变运行条件）。
- **选择规则**：每个受影响案例取"最后一个验证干净（无 error、原生 bool 指标、
  无 post-tool 空 assistant）的 stage"的行。
- **plan_cache 合并**：repair 审计触碰的 `prompt_hash` 键一律取 repair 条目
  （任一 stage 缓存缺失该键即 exit 2），其余键保留 base 条目；合并结果只写入
  merged 目录，供 freeze 使用（协议 §3.3）。
- **merge 幂等**：相同 `plan_hash` 且已 passed → no-op exit 0；
  相同但停在 ready_for_finalizer → 仅重跑 finalizer；不同 → exit 2 拒绝覆盖。
- **不改判定阈值**：不触碰 finalizer 15 门与协议 §2.3 的任何阈值。

## 与 v2 先例的差异

| 维度 | v2 先例 | v17 参数化（本工具） |
|---|---|---|
| 案例集 | `REPAIR_GROUPS_R1/R2/R3` 硬编码 | `--cases`/`--cases-file` 或 audit 自动探测 |
| 替换表 | `REPLACEMENTS` 12 行字面量 | 由每 stage 逐案例验证推导（对 v2 数据集回测 12/12 一致） |
| 窗口 | 手工三级脚本 | `--window` 序列参数化（默认 73728→81920→122880/q8_0） |
| plan_cache | 未合并 | 显式合并规则 + sha256 记录 |
| 幂等 | merged 已存在即拒绝 | 相同计划 no-op / 仅重跑 finalizer |
| E77 环境 | 缺 `E77_MAX_TOTAL_PLAN_REVISIONS`、`E77_UNCERTAINTY_POLICY`、`E77_EXECUTION_DATE`、`E77_RELATION_CATALOG`；`E77_PLANNER_REPAIR_ATTEMPTS=1` | 与 v17 runner 完全一致（12 / allow_with_trail / 继承 base / 2） |
| 已知保留项 | — | `E77_EFFECT_DIFF_RUNTIME=1` 与 `LOCAL_LLM_PORT` 沿用 v2（前者无消费方，属历史兼容项） |

## 验证记录（2026-08-04，全部 CPU）

- `selftest`：detect/merge dry-run/merge/幂等/篡改拒绝/base 不可变性全部通过。
- `detect` @ r1：恰好 9 案例（user_task_35×6 + user_task_38 inj1/4/5），
  official_rows=726，与既有真值一致。
- `detect` @ 运行中 r2：部分快照 6 案例（user_task_35 全部复发），警告正确。
- `repair --dry-run` @ r2：范围/命令/E77 环境契约正确；执行模式在 runner 存活时被拒。
- 选择语义回测 @ v2 数据集：与 `REPLACEMENTS` 12 行逐条一致（R1×6/R2×4/R3×2）。

## 注意

- r2 的 `E77_EXECUTION_DATE` 继承自 r2 manifest（2026-08-04），与 r1（2026-08-02）
  不同——这是"继承 base 运行日期"的正确行为，merge 后的 claim_boundary 与
  repair_metadata 会完整披露。
- `E77_RUNTIME_VERSION` 环境变量是 vestigial（patch 内硬编码），故不复制。
