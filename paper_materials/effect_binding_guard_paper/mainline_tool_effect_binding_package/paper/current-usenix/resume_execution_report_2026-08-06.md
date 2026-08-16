# V0–V3 实验链恢复执行报告（2026-08-06）

- 签发时间：2026-08-06T10:15+08:00
- 依据：`pause-resume-runbook_2026-08-05.md`、`strict_atom_representation_attribution_protocol_v2_2026-08-05.md`（§5 V0 血缘注记）
- 恢复背景：V0（`tool_identity_only`，repeat-0，full 726-case）在 393/726 处暂停；本报告记录 resume 启动、protocol_id 一致性问题的处置、watch 自动化链与监控点。

---

## 1. 恢复前现场核查（事实）

| 项 | 核查结果 |
|---|---|
| V0 结果文件 | `runs/.../qwen32/tool_identity_only/repeat-0/paired-case-results.jsonl` = **393 行**，末行 `protocol_id=bccf19ea51b13f27`（v1），frozen hashes（decoding/manifest/model 等）与 dry-run 重算一致 |
| GPU | 2×24GB 全空闲（0% 占用）；无 llama_cpp.server 残留；端口 18087 空闲 |
| V1 遗留 | `opaque_whole_call` 目录不存在（v1 驱动在 V0 阶段即被终止，无 v1 语义 V1 行需归档——pause-after-v0.sh 的归档分支不适用） |
| 冻结产物 | `protocol.json` 为 v2（sha256[:16]=`e830b9b24138f8ad`）；`protocol-v1.json` 归档完整（sha256[:16]=`bccf19ea51b13f27`） |

## 2. 关键问题发现与处置：resume 的 protocol_id 一致性

**发现（阻塞级）**：
1. runner 的 `protocol_id` 在**进程启动时**从磁盘 `protocol.json` 计算（`sha256(PROTOCOL_JSON)[:16]`，run-strict-attribution.py L219/L726）。磁盘上已是 v2 → 任何新启动的进程会给新行打上 `e830b9b24138f8ad`。
2. `check-variant-completeness.py` 将 `protocol_id` 列为 `FROZEN_HASH_FIELDS`（L85–95），**要求同一变体文件内所有行一致**（L160–163），否则 Gate 失败。
3. 若直接按磁盘 v2 状态 resume：393 行 v1 + 333 行 v2 混合 → 完整性检查必败 → pause/smoke/driver-v2 链全部 fail-closed；且违背 protocol v2 §5 血缘注记（"全部 726 行将携带 v1 id"）。

**处置**（V0 resume 窗口内临时还原 v1 协议字节）：
1. 备份当前 v2 `protocol.json` → `protocol-v2-backup_2026-08-06.json`（sha256 校验 = `e830b9b2...` ✓）；
2. `protocol-v1.json`（sha256 校验 = `bccf19ea...` ✓）复制为 `protocol.json`；
3. **dry-run 预检通过**：`--scope full --variant tool_identity_only --repeat-index 0 --resume --dry-run` → `status=dry_run_ok`、`protocol_id=bccf19ea51b13f27`、726 cases、frozen input hashes 与既有 393 行逐项一致；
4. 启动 resume；V0 完成 + 完整性检查通过后，watch 脚本**先**将 `protocol.json` 从备份还原为 v2（sha256 双向校验），**再**执行 smoke-v2 与 driver-v2（driver-v2 preflight 会再次独立校验 v2 id，双重保险）。

依据：protocol v2 未修改 V0 的任何代码路径（§5），v1/v2 下 V0 语义与实现完全同一；此操作使 726 行 V0 文件在 `protocol_id` 上保持同源，与 protocol v2 §5 的预注册意图一致。该操作及其窗口期已在 watch 日志与 `_resume_record_protocol_v2_2026-08-06.json`（V0 完成后写入）中留痕。

## 3. V0 resume 启动

```bash
cd /data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package
PYTHONPATH=code:. nohup runs/e75_agentdojo_env/bin/python \
  experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/run-strict-attribution.py \
  --scope full --variant tool_identity_only --repeat-index 0 --port 18087 --resume \
  > /tmp/v0-resume.log 2>&1 &
```

| 项 | 值 |
|---|---|
| runner PID | **2017180**（nohup 父壳 2017179） |
| server PID | **2017190**（`llama_cpp.server --port 18087 --n_gpu_layers 65 --split_mode 1 --tensor_split 0.5 0.5 --n_ctx 65536`，防 OOM 先例配置 ✓） |
| 启动时间 | 2026-08-06T10:04+08:00 |
| resume 语义 | 按 `case_key` 跳过已存在行（runner L648），`--resume` 同时使 benchmark `force_rerun=False`；只追加、不改动已生成的 393 行 ✓ |

**启动后验证（10:12 实测）**：
- runner / server 均存活；GPU 双卡均衡占用（18.9/18.2 GiB，47%/47%）；
- 行数 393→405（+12 新行，无重复 case_key）；
- **最新行 protocol_id=`bccf19ea51b13f27`（v1）✓**（验证项达成）；
- server 日志正常（推理中，无异常）。

## 4. 恢复链自动化：`v0-resume-finalizer-watch.sh`

- 位置：`experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/v0-resume-finalizer-watch.sh`
- **watch PID：2033988**（修正等待模式后于 10:18 重启，旧实例 2026484 已终止）；日志：`v0_resume_watch_2026-08-06.log`
- 模式：仿 `v17r2_finalizer_watch.sh`（轮询等待 runner 退出 → server 退出 → fail-closed 门禁链）。

V0 runner 退出后自动执行（每一 Gate 失败即 ABORT、不进入后续）：

| Phase | 内容 | 失败处置 |
|---|---|---|
| 1 | 行数门禁（必须 =726）+ `check-variant-completeness.py` rc=0 | ABORT，提示查 `/tmp/v0-resume.log`，必要时再 `--resume` |
| 2 | **还原 protocol.json 为 v2**（备份 sha256 → cp → 复验 sha256） | ABORT |
| 3 | runbook §2 门禁：pytest 51 项 + envelope `--check` + smoke dry-run（期望 protocol_id=`e830b9b24138f8ad`） | ABORT |
| 4 | GPU 清洁确认（无 llama_cpp.server 残留）+ 写 `_resume_record_protocol_v2_2026-08-06.json`（pause-after-v0.sh 第 6 步等价物；终止驱动/归档 V1 分支在本场景不适用——runner 独立启动、无 V1 遗留） | ABORT |
| 5 | smoke-v2：四变体串行，**`--repeat-index 1`**（repeat-1 目录，绝不触碰 V0 repeat-0 文件；runbook §3 防坑），每变体 runner_rc 与 smoke 完整性检查均须 0 | 任一失败即停，不启动全量 |
| 6 | `run-v0v3-full-serial-driver-v2.sh`（V1→V2→V3 串行；preflight 复核 v2 id + envelope 哈希；skip gate 保护已完成变体） | 驱动自身 fail-closed |

**手动备选触发点清单**（若 watch 意外死亡，按序人工执行）：
1. `wc -l .../tool_identity_only/repeat-0/paired-case-results.jsonl` == 726；
2. `check-variant-completeness.py --variant tool_identity_only --scope full --repeat-index 0` rc=0；
3. `cp protocol-v2-backup_2026-08-06.json protocol.json` 并 `sha256sum` 复核为 `e830b9b2...`；
4. runbook §2 门禁 A/B/C/D；
5. runbook §3 smoke-v2 命令块（repeat-index=1）；
6. runbook §4 driver-v2 启动。

## 5. ETA 估算

- 剩余 321 案例（726−405，启动时 333）；速率取用户给定的 ~44.6 s/case（与前段 393 行实测一致）；
- 估算 321×44.6 ≈ 14 317 s ≈ **4.0 h**；
- **预计 V0 完成：2026-08-06 14:15±30min**；随后 smoke-v2（约 0.5 h）→ driver-v2（V1→V3 共 3×726 case，约 27 h，预计 08-07 晚间至 08-08 完成）。

## 6. 监控点

| 监控项 | 命令 |
|---|---|
| V0 进度 | `wc -l experiments/.../qwen32/tool_identity_only/repeat-0/paired-case-results.jsonl` |
| runner/server 存活 | `pgrep -af "run-strict-attribution.py"` / `pgrep -af llama_cpp.server` |
| runner 日志 | `tail /tmp/v0-resume.log` |
| server 日志 | `tail experiments/.../qwen32/_server-repeat-0/llama_cpp_server.log` |
| watch 日志 | `tail v0_resume_watch_2026-08-06.log` |
| GPU | `nvidia-smi`（双卡应均衡占用；watch 期间不 kill、不加并发） |
| smoke/driver 阶段日志 | `/tmp/smoke-v2-*.log`、`/tmp/driver-v2.log`、`_smoke_v2_rerun_manifest_2026-08-05.log`、`_v1v3_full_driver_v2_protocol_v2_manifest_2026-08-05.log` |

## 7. 约束符合性声明

- V0 使用 `--resume` 续跑，已完成案例按 case_key 跳过，未重跑；既有 393 行未被修改（追加模式写入）；
- resume 期间不 kill、不加 GPU 并发；server 配置 `tensor_split 0.5 0.5`（防 OOM 先例）✓；
- smoke-v2 使用 `--repeat-index 1`，不污染 V0 repeat-0 文件（runbook §3 关键防坑）✓；
- protocol.json 的临时 v1 窗口有备份、双向 sha256 校验与留痕记录，V0 完整性检查通过后立即还原 v2。

## 8. 已知局限与风险

1. **protocol.json v1 窗口**：V0 resume 运行期间（约 4 h）磁盘 protocol.json 为 v1 字节；窗口内不应运行任何依赖 v2 id 的检查（smoke/driver 均已排在还原之后；driver-v2 preflight 提供第二道校验）。若窗口内有其它流程误触发 v2 门禁会 fail，属预期行为，不是故障。
2. **finalize 跨 protocol_id**：V0 行（v1 id）与 V1–V3 行（v2 id）在 finalize 时属预期差异（runbook §5 已预注册）；若配对门禁意外报错，按 protocol v2 §5 修记录规则而非重跑，并另行披露。
3. ETA 依赖历史速率外推；若 case 尾部（banking/travel 长尾）显著偏慢，完成时间相应顺延，watch 链不受影响（基于退出事件触发）。
