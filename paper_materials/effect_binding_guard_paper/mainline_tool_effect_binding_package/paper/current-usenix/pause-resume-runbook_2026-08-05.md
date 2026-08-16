# Protocol v2 暂停/重启操作手册（D2）

- 日期：2026-08-05
- 依据：`strict_atom_representation_attribution_protocol_v2_2026-08-05.md`、`recommendations_analysis_2026-08-05.md` §2/§4.3（D1–D4/D7，已获用户确认）
- 运行基线：V0（`tool_identity_only`）正在 v1 驱动（PID 1448380）下跑 726-case 全量，预计 08-06 凌晨完成

所有路径相对 repo 根目录
`/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package`。

---

## 0. 现状快照（2026-08-05 签发时）

| 项 | 状态 |
|---|---|
| V0 全量 | 运行中（`experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32/tool_identity_only/repeat-0/`） |
| v1 驱动 | `run-v0v3-full-serial-driver.sh`，PID 1448380，manifest `_v0v3_full_driver_manifest_2026-08-05.log` |
| protocol v2 | 已签发（protocol_id `e830b9b24138f8ad`；v1 归档 `protocol-v1.json`） |
| V1 重构 | 已完成（真 whole-call；51 项测试全过） |
| envelope registry | 已固化（sha256 `702331d4...`；`--check` PASS） |

## 1. 暂停步骤（V0 完成后立即执行）

**首选：一键暂停门**（fail-closed：V0 不足 726 行或完整性检查不过会拒绝执行）：

```bash
bash experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/pause-after-v0.sh
# 若驱动 PID 已变化：pause-after-v0.sh <新PID>
```

脚本执行内容：
1. 验证 V0 `paired-case-results.jsonl` == 726 行；
2. 运行 read-only 完整性检查（`check-variant-completeness.py --variant tool_identity_only --scope full`），rc 必须为 0；
3. 核对 v1 驱动 manifest 的 `CHECK variant=tool_identity_only rc=0` 行（信息性）；
4. **先** SIGTERM 驱动（防止其继续启动 V1），再处理 V1 runner：
   - 若 V1 runner 已在跑（v1 语义，结果无效）：SIGTERM → 等待 → 归档部分结果到
     `runs/strict-atom-representation-attribution/_archive_v1_partial_protocol_v1_interrupted_2026-08-05/`；
   - 若未启动：无需处理；
5. 写暂停记录 `qwen32/_pause_record_protocol_v2_2026-08-05.json`。

**手动备选**（仅当脚本不可用时，逐步执行并记录）：

```bash
# 1) V0 完成判定
wc -l experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32/tool_identity_only/repeat-0/paired-case-results.jsonl   # 必须 = 726
# 2) 完整性检查（rc=0 才继续）
PYTHONPATH=code:. runs/e75_agentdojo_env/bin/python \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/check-variant-completeness.py \
  --variant tool_identity_only --scope full --repeat-index 0
# 3) 核对驱动 manifest
tail -5 experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32/_v0v3_full_driver_manifest_2026-08-05.log
# 4) 终止驱动（先于一切）
kill -TERM 1448380
# 5) 若 V1 runner 已启动：找到并终止，然后归档
pgrep -af "run-strict-attribution.py --scope full --variant opaque_whole_call"
#    kill -TERM <pid>，等待 30s，确认 llama_cpp.server 已退出
#    mv .../qwen32/opaque_whole_call .../  _archive_v1_partial_protocol_v1_interrupted_2026-08-05/
```

**边界情况**：
- V0 完成但完整性检查失败 → 不暂停、不进入 v2 流程；先按协议 Phase 3 用 `--resume` 修复 V0，检查通过后再执行暂停。
- 驱动在 V0 结束后已自行进入 V1 且 V1 已有部分行 → 这些行在 v1 语义下无效，必须归档（脚本自动处理），之后 V1 从 0 重跑。
- 暂停后确认 GPU 已空：`pgrep -af llama_cpp.server` 应无输出（runner 的 finally 会 SIGTERM 其 server）。

## 2. 重启前置门禁（全部必须通过）

```bash
# A. 单元测试（51 项全过）
PYTHONPATH=code:. runs/e75_agentdojo_env/bin/python -m pytest \
  shared/compatibility/tests/tests/test_strict_atom_representation_attribution.py -q
# B. envelope 产物确定性
PYTHONPATH=code:. runs/e75_agentdojo_env/bin/python \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-whole-call-envelopes.py --check
# C. runner 冻结输入校验（protocol v2 + envelope 哈希门禁）
PYTHONPATH=code:. runs/e75_agentdojo_env/bin/python \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/run-strict-attribution.py \
  --scope smoke --variants all --dry-run     # 期望 status=dry_run_ok, protocol_id=e830b9b24138f8ad
# D. GPU 空闲（无残留 llama server）
pgrep -af llama_cpp.server || echo "no server running (OK)"
```

## 3. 四变体 smoke 重跑（协议 §9 Phase 2 要求；命令给出，**等暂停完成后执行**）

**关键**：smoke 使用 `--repeat-index 1`（repeat-1 目录），避免把 16 行 smoke 结果追加进 V0 的 repeat-0 全量结果文件（否则 726+16 污染，完整性检查会失败）。smoke 结果留在 repeat-1，不进入 finalize。

```bash
cd /data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package
nohup bash -c '
set -u
PKG=$(pwd)
PY="$PKG/runs/e75_agentdojo_env/bin/python"
RUNNER="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/run-strict-attribution.py"
CHECKER="$PKG/experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/check-variant-completeness.py"
MANIFEST="$PKG/experiments/security-analysis-ablation-and-overhead/runs/strict-atom-representation-attribution/qwen32/_smoke_v2_rerun_manifest_2026-08-05.log"
cd "$PKG"
echo "[smoke-v2] $(date -Is) start (four variants serial, repeat-index 1)" >> "$MANIFEST"
for V in tool_identity_only opaque_whole_call raw_schema_fields validated_atom_fields; do
  echo "[smoke-v2] $(date -Is) LAUNCH $V" >> "$MANIFEST"
  PYTHONPATH=code:. "$PY" "$RUNNER" --scope smoke --variants "$V" \
    --repeat-index 1 --port 18087 >> /tmp/smoke-v2-$V.log 2>&1
  RC=$?
  PYTHONPATH=code:. "$PY" "$CHECKER" --variant "$V" --scope smoke --repeat-index 1 >> "$MANIFEST" 2>&1
  CRC=$?
  echo "[smoke-v2] $(date -Is) $V runner_rc=$RC check_rc=$CRC" >> "$MANIFEST"
  if [ $RC -ne 0 ] || [ $CRC -ne 0 ]; then
    echo "[smoke-v2] FAILED at $V; stop here and investigate (do not start full runs)" >> "$MANIFEST"
    exit 1
  fi
done
echo "[smoke-v2] $(date -Is) ALL FOUR VARIANTS PASSED" >> "$MANIFEST"
' > /tmp/smoke-v2-driver.log 2>&1 &
echo "smoke v2 driver pid: $!"
```

说明：runner 的 `resolve_variants` 在 `--scope smoke` 下只读 `--variants`（`--variant` 仅用于 `--scope full`），故上面逐变体传 `--variants "$V"`。执行前可用 `--dry-run` 再验证一次参数解析。

smoke 通过判据：四个变体 runner rc=0 且 `check-variant-completeness.py --scope smoke --repeat-index 1` 各自 rc=0（16 行、字段齐全、frozen hash 一致、protocol_id 全为 `e830b9b24138f8ad`）。

## 4. 全量重启（smoke 全过后）

```bash
# V1 -> V2 -> V3 串行（V0 保留，skip gate 与 protocol v2 preflight 内置于驱动）
nohup bash experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/run-v0v3-full-serial-driver-v2.sh \
  > /tmp/driver-v2.log 2>&1 &
echo "driver v2 pid: $!"
```

驱动 v2 行为：preflight 校验 protocol v2 id 与 envelope 哈希（不通过即拒绝启动）；逐变体启动、等待、read-only 完整性检查；已完整且通过检查的变体跳过；manifest 记录在
`qwen32/_v1v3_full_driver_v2_protocol_v2_manifest_2026-08-05.log`。

## 5. 全量完成后核对

1. 每变体 `check-variant-completeness.py --variant X --scope full` rc=0；
2. finalize（fail-fast）：V0 行携带 v1 protocol_id、V1–V3 携带 v2 protocol_id 属预期（protocol_id 不在 finalize 的跨变体一致性字段元组内）；若配对/完整性门禁意外报 protocol_id 错误，按 protocol v2 文档 §5 处理（修记录规则而非重跑 V0，并在报告披露）；
3. V1 结果解读必须附带 protocol v2 §2.3 的两条预注册说明（whole-call 盲目性 + allow_with_trail fallback）。
