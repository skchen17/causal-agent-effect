# G′ 实验审计说明：protocol manifest `revision_no_think_prefix_env` 字段伪影

日期：2026-08-07（UTC）
记录者：experimental-researcher（执行代理）
状态：文档伪影澄清，**非协议偏离**；预注册判定标准不受影响。

## 观察

G′ rep1/rep2 的 `protocol_manifest.json` 中
`iffix_variant.revision_no_think_prefix_env == "1"`，而预注册
（gfix_preregistration_2026-08-07.json, variant.env）要求
`E77_REVISION_NO_THINK_PREFIX == "0"`。

## 根因（代码实读）

runner 副本 run-recovery-normalization-qwen32-iffix.py 有两处读取：

1. **L273（manifest 披露字段）**：`os.getenv("E77_REVISION_NO_THINK_PREFIX", "1")`
   —— 记录的是**调用方 shell** 的环境，默认值 "1"（冻结行为）。两次运行的
   调用方 shell 均未设置该变量，故记录为 "1"。
2. **L545（实际传给子进程的值）**：`os.getenv("E77_REVISION_NO_THINK_PREFIX", "0")`
   —— 这是**实际生效**的值，默认 "0"。

- **rep2（直接证据）**：运行中子进程 /proc/environ 实测
  （run_e75 pid=2950177 与 agentdojo benchmark pid=2950180）均含
  `E77_REVISION_NO_THINK_PREFIX=0`、`E77_REVISION_REPAIR_ATTEMPTS=2`——
  实际条件与预注册 variant.env 一致。runner 进程（pid=2938959）自身无该变量，
  证实 "0" 来自 L545 默认值路径。
- **rep1（间接证据）**：进程已结束，无法直查；但 rep1 与 rep2 使用同一 runner
  脚本、同一调用方式（顺序紧接启动），且 rep1 revision 行为与 pilot（/no_think
  在场、0/11 成功）显著不同（12/18 成功），与 M4-R1+M4-R2 生效一致。

## 行为佐证

rep1 revision 机制：18 个 revision 事件中 12 个产出合法对象
（raw_output_prefix 分布：`{"action"`:10、`{\n "act`:2、空:6），
repair 次数分布 {0:6, 1:5, 2:7}。对照 pilot 冻结版（/no_think 在场）
11/11 全空输出——行为分布的系统性改变与 M4-R1+M4-R2 生效一致。

## 处置

- 不重跑：实际实验条件与预注册一致，仅 manifest 披露字段的默认值选取有误导性。
- 修正建议（不改冻结产物）：后续 iffix runner 使用时，将 L273 披露字段改为
  与 L545 相同的默认值 "0"，或直接记录"传入子进程的值"。本说明与该 manifest
  一并归档，作为披露字段的权威解读。
- 报告（generalized_fix_execution_2026-08-07.md）中如实披露此伪影及本说明。
