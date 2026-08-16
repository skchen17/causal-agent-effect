# 窗口期执行决策书（2026-08-04）

产出：research-assistant（qwen3.8-max），PM 核实代码证据后收录。
依据：白皮书 TOP 10、accept_path §3/§6（C 框架 + B 目标 + A 保底）、war_plan §4 A 线约束、协议 §2.3/§5/§7.2/§9/§12、模拟审稿 MC1-MC8。
总原则：GPU 阻塞期做足"无论 V0-V3 正负都成立"的 CPU 项；结果依赖项只做占位骨架，禁止预填数字。

## 1. 决策摘要

| 事项 | 决策 | 优先级 | 耗时 | 产出物 |
|---|---|---|---|---|
| E2 粗 policy 族 + qualifier-deletion | 立即启动 | P0 | 2-3 人日 CPU | family×qualifier 敏感性表 + claim boundary |
| T2 前置核实 + O6 | 立即（核实已完成） | P0 | 2 人日 | 重述版 O6 命题 + override 构成测量脚本 |
| T1 单调终止定理 | W1-W2 做 | P1 | 2 人日 | 定理 + 56-call refinement 轨迹检查 |
| T3 原则分离命题 | W2 做 | P1（最先砍） | 1 人日 | 构造性命题 + related-work 对照段 |
| D1 N1/N2/N3 分流预案 | 现在做（v17 前） | P0 | 2 人日 | 三分支 Results 骨架（N1 为基座） |
| W utility 重定位 | 骨架现在、数字延后 | P1 | 2 人日 | 带数字占位符的叙事骨架 |
| C 线 Artifact P0 草案 | W1-W2 做 | P1 | 3 人日 | 参数化 diff + 打包脚本（提交硬门槛） |
| v17 finalize → V0-V3 → E1 | 依 GPU 链顺序 | P0 | GPU 70-110h + 25-35h | 4×726 配对结果 + stability + 9B |
| E5/E6 | 仅写作草案；GPU 行延后 | P2 | — | 处置策略草案 |
| E3 adaptive / E84 / T4 | **本窗口不做** | — | — | E3 留 10 月后预算余项；T4 待 E2 出表后再议 |

## 2. 关键决策与理由

### a) E2：立即启动（选启动不选等待）
- 唯一无论 V0-V3 正负都加分的实验（accept §6 已升为必须），CPU 近零成本
- 同时打 MC5 与 Question 4、反击"contract 是序列化"；只读使用已冻结有限域数据，不触碰协议冻结输入
- 第一版要素：
  - family = {power-set（现状基线）、effect-kind 聚合、resource 聚合、计数截断 {0,1,≥2}}
  - 数据源 = 56-call 有限域 + ToolSandbox 32 域
  - 过程 = 逐 family 重算 separating pairs → 逐 qualifier（date/subject/recurrence/payload/visibility）删除
  - 输出表 = 行 family×qualifier，列：保留分离对数/冗余对数/overpartition 数/假拒绝数（MC5 要求两个方向都报）
  - 验收 = 冻结输入单脚本可复现、5 qualifier×4 family 全覆盖、随表附 claim boundary

### b) T2 前置核实结论：O6 条件可支撑，可推进，但命题必须重述
代码证据（PM 已核实位置）：
1. 审计同时落盘 `guard_decision`（strict）与 `decision`（effective）、`diagnostic_uncertainty_override`、逐字段 `atom_checks.check_result`（e77_runtime.py L162-235，字段 L175/178/211/234）
2. override 仅放行 `resolver_fill_requires_replan` 字段（L197/229）；五类扩权发现（forbidden_field_used/outside_exact_plan/tool_not_in/missing_e77/revision_binding_invalid）在结构化与 fallback 两路均硬阻断
3. override 后的 side-effectful 调用结果不写入证据库（patch 证据回写条件）——override 不扩充后续授权依据

**两个必要条件**：
- O6 的 witness 只能表述为"排除式保证 + 证据隔离"，不能写成"被覆盖效果在 B_q 内的肯定性成员证明"——trail 无填充值事后复验
- fallback 路径（无结构化 checks）无逐字段 trail，须先用 v17 审计测量其占 override 总量比例；**>20% 则 O6 限定于结构化路径并附占比披露**

**操作红线**：协议冻结前不得改 runtime 代码（否则 §5 代码 hash 冻结失效、v17 与 V0-V3 不一致）；O6 只能就现有 trail schema 定理化。resolver-fill 侧完全可支撑（AUTHORIZED_FIELD_STATUSES 六态均经 registered projection/授权证据核验）。

### c) T1、T3：都做，顺序 T2→T1→T3
- 不选"只做一个"或"都不做"：accept 路径缺"一个强信号"，J2（Originality 3/5）只能靠理论轴抬升；方案 A 保底形态以 T 系就绪为前提
- 砍单顺序：时间挤压先砍 T3（与实证耦合最弱）、次砍 T1，**T2 不可砍**（MC2 是 Major Concern）
- T4 不做：其反序列化论证与 E2 重叠，E2 出表后再决定是否需要 ε-噪声引理

### d) D1：现在做，不等方向明朗
1. H1-H5 判定在 finalize 当天按协议 §2.3 矩阵释放，届时才起草会把写作压上关键路径
2. N1 是"无论正负都成立的骨架"，预写零浪费；N2/N3 仅写结构占位不写数字

### e) 写作套件：现在起草骨架，数字待 v17 落地
- 论证结构（pathway audit 归因、frontier 定位、26-task 归一化 20→15/26）不依赖 v17 数字
- 具体数值一律占位，按 B 线顺序（Evaluation→Results→Abstract）在 Phase D 回填
- 绝不预填数字（R1 overclaim 触发器）

### f) 窗口期补充三项
1. claim map **分支 diff 模板**（正/负/混合三套占位；现在禁止预更新，R1）
2. E2 代码骨架（并入 a）
3. C 线 P0 参数化 + 打包脚本草案（纯 CPU、提交硬门槛）

## 3. 执行时间线（周粒度）

| 周 | GPU 链 | CPU/写作 | 依赖与缓冲 |
|---|---|---|---|
| W1 08-03→08-09 | v17 完成→finalizer+freeze→16-case smoke | E2 v1 跑完；T2 O6 草案+override 构成测量；T1 草案；D1 骨架；W 骨架；C 线 P0 草案 | CPU 项独立于 v17；finalizer 失败见风险① |
| W2 08-10→08-16 | V0-V3 主实验 V0→V1→V2→V3（约 2-3 天） | T2/T1/T3 证明定稿；E2 表定稿；D1 v2；claim map 模板 | 条件失败不跳过其余（协议 §9 Phase 3） |
| W3 08-17→08-23 | stability repeat 1/2 → fail-fast finalize | finalize 后 2 天内出 H1-H5 判定 → 分支决策；Phase D 启动换数；E1 于 finalize 后启动 | 分支决策是本窗口唯一决策节点 |
| W4 08-24→08-30 | E1 subset/全量（1-2 天） | Results 按分支写入（D1 骨架）；Phase 5 26-task 次级分析（CPU）；E4 预注册设计稿（不动 GPU） | E4 设计先行，守住"禁止事后加 parser" |
| W5 08-31→09-06 | E4 pilot GPU（10-20h，预算允许时） | Phase D 全稿（Abstract/Intro 最后）；Artifact P0 补丁实施 + 打包演练 | — |
| W6 09-07→09-13 | 缓冲：bug 修复后受影响条件全量重跑 | E5/E6 可选项；artifact 干净环境 dry-run | 9 月中旬检查点：主 Results 证据齐备 |

## 4. 风险与回退

1. **v17 finalizer/freeze 失败（exit≠0）**：按 08-02 交接 §6.4 人工排查重跑 finalizer；先参数化 EXPECTED_RUNTIME；若需重跑 v17 则 +3-5 天，由 W6 缓冲吸收；E2/T/D1 全部独立运行，零空转。
2. **E2 粗族下 qualifier 冗余率两极**：冗余率过高 → 如实报告（"表示是 policy-relative"的正面证据，MC5 照关），正文 qualifier 主张收缩到 power-set 族；冗余率过低 → 同一组 qualifier 仍必要同样回答 Question 4。两个方向均可发表，风险仅在措辞——随表预写双向 claim boundary。
3. **T2 fallback 路径 override 占比过高**：先测后写；>20% 则 O6 限定结构化路径并披露占比；若命题仍反噬，T2 降级为 obligation-to-evidence mapping 披露段（MC2 既有缓解），理论重心转 T1+T3。红线：测量完成前论文层面零承诺。

## 5. 一致性声明

与白皮书 TOP 10、ACCEPT 3 件事（V0-V3/E4/E1）完全一致。调整三处并已说明理由：
- T3 由"可选"升为窗口内做（低成本、服务方案 A 保底）
- E6 明确延后至 V0-V3 后（其主成分已并入协议 Phase 4，不另占 GPU）
- T4 不做（功能被 E2 覆盖）
