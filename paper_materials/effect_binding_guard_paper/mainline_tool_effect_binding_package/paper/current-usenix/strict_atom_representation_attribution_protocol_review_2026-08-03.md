# 严格表示归因协议草案审阅（§7.2.4）

日期：2026-08-03  
审阅对象：`paper/current-usenix/strict_atom_representation_attribution_protocol_2026-08-03.md`（419 行，状态 `protocol-draft`）  
审阅结论：**审阅通过（approved-with-amendments）**。发现 1 项过时陈述（§14.3）、2 项建议性备注；无阻塞性缺陷。状态维持 `protocol-draft`，冻结条件不变。

---

## 1. 内部一致性核验（全部通过）

| 检查项 | 协议声明 | 核验结果 |
|---|---|---|
| case 总数分解 | 726 = 97 benign + 629 attack | 一致（§3.1、§7.1、§11.2） |
| suite 计数 | workspace 280 + slack 126 + travel 160 + banking 160 | 求和 = 726，一致 |
| stability subset | 4 suites × (8 benign + 32 attack) = 160 | 一致；97 benign 总量支持每 suite 取 8 个 |
| 执行量 | 4×726 + 4×160×2 = 2,904 + 1,280 = 4,184 | 一致（§12） |
| registry 覆盖 | 25/25 tools registered，V2 与 V3 同集 | 实测 `"registered": true` 计数 = 25，一致 |
| 引用文件存在性 | §3.4 五个共同输入 + §Phase 5 trusted manifests | 全部存在（2026-08-03 实测） |
| finalizer 前置 | Phase 1 要求 full finalizer 参数化 | 已完成（交接文档 §7.2.1，2026-08-02） |

## 2. 与接线缺陷教训的对齐（关键审阅点）

Round 1--5 位置布尔 tuple 接线错误（`is_atom` 被传入 `shuffle`）是本协议存在的直接原因。核验：

- §Phase 0.1 明确"显式 dataclass/enum，禁止位置布尔 tuple"——与修正版 runner
  `atom_specificity_corrected.py` 的 `ConditionSpec` 设计一致。
- §11.1"correct 与 shuffled condition 的 registry/prompt hash 必须不同"——现已由
  `shared/compatibility/tests/tests/test_atom_specificity_condition_schema.py`
  （8 项测试，2026-08-03 全部通过）落实为可执行门禁；该测试同时固化了
  "correct 条件保留 registry 原 roles"与"neutral control tokenizer-exact"两条不变量。
- 实施时（Phase 0）必须把同一门禁移植到 `test_strict_atom_representation_attribution.py`，
  不得仅引用 prompt-guidance 侧测试。

## 3. 发现的问题

### 3.1 过时陈述（应修订）：§14 第 3 条

协议写"修复 E71 的 sidecar/expected-field 回流和旧路径，重跑 label-independent
descriptor necessity"。E71 artifact 链修复已于 2026-08-02 完成并通过全部 9 项测试
（`test_effect_binding_guard_e71_atom_field_necessity_runtime_guard.py`，2026-08-03
复验 9/9 passed）。该条应理解为：**修复已完成，剩余的只是重跑
label-independent descriptor necessity 实验本身**。顺序语义不变（它仍不能替代本协议）。

### 3.2 建议性备注（不阻塞）

1. **V4 退化保护**：`shuffled_roles` 在 registry 行只有单一 role 值时旋转结果与
   原样相同（修正版 runner 已按此实现）。协议的 `non_applicable` 规则（§4 可选诊断 V4）
   已覆盖该情形，但建议实现时在 semantic influence test 中显式记录"退化行占比"，
   避免把退化的 V4 当成有效对照。
2. **GPU 时长估算**：§12 的 70--110 GPU 小时依赖 v17 最终 median seconds/case；
   v17 尚在运行（2026-08-03 12:5x 仍在 slack suite），Phase 1 冻结时应以实测
   median 替换当前经验估计并写入 `protocol.json`。

## 4. 冻结前置条件核对（当前状态）

| 条件 | 状态 |
|---|---|
| v17 正常结束并通过 726-key finalizer | ❌ 未完成（slack suite 运行中，PID 578021/578023） |
| finalizer `EXPECTED_RUNTIME` 参数化 | ✅ 完成 |
| plan cache hash 冻结 | ⏳ 依赖上一行，禁止提前冻结运行中的 cache（§15 已正确声明） |
| Round 1--5 正面结果隔离 | ✅ 完成（summary 横幅 + claim map 禁令 + 修正版 runner + 门禁测试） |
| E71 修复 | ✅ 完成（9/9） |

**结论：维持 `protocol-draft`。冻结动作只能在 v17 finalizer 通过后执行；任何提前改
`protocol-frozen` 的操作均视为违反协议自身规定（§Phase 1.5）。**

## 5. 后续执行者须知

1. v17 结束后：跑 full finalizer（命令见交接文档 §6.4 验收节）→ 通过后执行
   `build-protocol.py --freeze` → 改状态为 `protocol-frozen`。
2. Phase 0 的 CPU 工作（variant semantics、V2 raw schema registry、manifest 生成器、
   hash/leakage 检查、单元测试）不依赖 v17 结果，可在等待期间实施；
   但不得启动新 GPU server 与 v17 竞争。
3. 本审阅不改变协议的假设、界限、统计规则或停止规则；若后续需要修改，
   必须按 §Phase 1.5 产生新 protocol ID。
