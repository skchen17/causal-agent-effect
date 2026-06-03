# 方法论文写作材料：CEG-Auth / AuthTrace-Guard

> 日期：2026-05-31  
> 用途：为当前 CEG-Auth / AuthTrace-Guard 方法论文主线提供写作材料、威胁模型、证据清单和缺口清单。  
> 当前判断：2026-05-31 用户要求暂时搁置 Path A，主线切换为方法论文。现有实验证据足以支持“verifier-assisted authorization monitoring 是可行方向”，但不足以支持“monitor 方法已经完成并可部署”。方法论文必须优先补 label-hidden effect inference、action-level selective policy、强 baseline、真实 held-out surface trace 和外部运行时验证；Path A 暂作为 fallback 和诊断材料库。

---

## 1. 方法论文核心定位

不要把方法贡献写成：

> We use graphs/provenance to represent agent traces.

这会被 AgentArmor、ARGUS、AuthGraph、PACT、Alignment Contracts、OpenTelemetry/W3C PROV 等工作覆盖。

应写成：

> We study authorization-conditioned realized-effect monitoring for tool-using LLM agents under surface-form coverage gaps. CEG-Auth is a label-hidden raw-trace monitor that infers realized effects from execution evidence, localizes supporting evidence, estimates uncertainty, and applies a selective action-level policy over effects outside the task-authorized envelope.

中文主张：

> CEG-Auth 是一个面向 LLM agent 工具调用的 label-hidden raw-trace 越权检测框架。它不直接信任 LLM 自审计，也不只检查 tool name/API schema，而是从执行遥测中推断实际发生的 realized effects，将这些 effects 与任务授权包络 `A(c)` 对比，并在 action level 输出 `ALLOW / DENY / ABSTAIN / ASK_USER`。

方法论文的可防守 novelty 应落在五点：

1. `authorization-conditioned realized-effect monitoring` 作为判断对象；
2. `label-hidden raw trace` 输入约束，避免 verifier 标签泄漏；
3. `surface-form held-out` 评估，检测 monitor 是否学到 tool proxy；
4. `evidence localization + uncertainty`，让安全决策可审计；
5. `action-level selective policy`，直接优化 `U-Allow / FDeny / Abstain / Coverage`。

---

## 2. 威胁模型

### 2.1 一句话版本

我们研究带工具调用能力的 LLM agent 在多步任务中产生未授权实际效果的风险。用户任务 `c` 诱导一个授权效果包络 `A(c)`；agent 执行工具后产生可观测 realized effects `Omega(tau)`。若存在 `e in Omega(tau) \ A(c)`，则发生越权。攻击者可以控制 agent 读取的外部内容，模型自身也可能因规划、错误恢复或长上下文漂移产生越权。monitor 可信地观察经过 mediation 的 label-hidden execution traces，但不能访问人工 effect 标签或 oracle policy decision。

### 2.2 系统对象

系统包含：

```text
User task c
LLM planner / controller
Tool executor
External environment
Trace collector / sandbox / dry-run executor
Authorization monitor M
```

工具覆盖但不限于：

```text
file read / write / delete
shell / bash / python
web / browser / search / curl
messaging / email / webhook / provider API
database / API query / task delegation
```

用户任务给出或隐含授权包络：

```text
A(c) = allowed effects + allowed resources + allowed scope + allowed recipients/endpoints + temporal/context constraints
```

例子：

```text
Task: read config.json
A(c) = {file_content_read(config.json)}

Task: fetch a webpage and save a local summary
A(c) = {network_egress(target_url), content_fetched(target_url), file_written(summary_path)}
```

### 2.3 被保护资产

保护对象不是 tool-call syntax，而是外部后果：

```text
confidentiality of private data
filesystem integrity
network boundary
message/payment/API side effects
resource identity and parameter binding
task-scope authorization
```

对应 effect schema：

```text
file_content_read
file_written
file_deleted
network_egress
content_fetched
message_sent
credential_accessed
external_api_invoked
command_executed
tool_error
```

写作注意：`command_executed` 需要谨慎定义。它可以是 surface-level execution fact，不一定本身是安全关键 effect；方法论文应把它拆成低层执行事实与下游安全相关 effect，或说明只有在任务未授权 shell execution 时才作为越权 effect。

### 2.4 攻击者能力

攻击者可以控制或影响 agent 会读取的外部内容：

```text
webpage
email/message
retrieved document
repository file
browser DOM
API response
tool output text
```

攻击者目标是诱导 agent 产生未授权 realized effects：

```text
read and exfiltrate secrets
delete or overwrite files
send a message to an unauthorized recipient
access an unauthorized URL
invoke a privileged provider API
use shell/python/browser as an alias to bypass direct tool restrictions
```

攻击者不控制模型权重，不攻破 OS/kernel，不直接篡改 trusted monitor。该设定与 CaMeL/PACT/ARGUS 一类 untrusted data + privileged action 风险模型兼容。

### 2.5 非恶意失败也在范围内

论文不应只把越权归因于 prompt injection。长任务中也存在 benign overreach：

```text
ambiguous task authorization
subgoal decomposition drift
error recovery expands permissions
tool aliasing through bash/python/browser
long-context dilution
task success being confused with authorization
implicit resource or recipient expansion
```

因此威胁来源包括：

```text
adversarial overreach: untrusted content induces unauthorized effects
benign overreach: planner/tool-selection/recovery errors produce unauthorized effects
```

### 2.6 Monitor 可见信息与禁止信息

主设定必须是 label-hidden raw trace。

monitor 可以看到：

```text
task context c
authorized envelope A(c)
tool name and arguments
raw tool output
stdout/stderr/exit code
filesystem pre/post diff
HTTP request/response metadata
browser/DOM/storage events
provider response status or receipt id
message recipient and delivery receipt if observed
timestamps/spans/call graph/resource identifiers
```

monitor 不可以看到：

```text
verified_effects
unauthorized_effects
candidate_effect_present
effect_diff
policy_decision
人工 effect 标签
任何接近 gold label 的字段
```

full-label verifier 只能作为 upper bound，不能作为主方法结果。

### 2.7 Trusted Computing Base

可信：

```text
tool mediation layer
sandbox / dry-run executor
trace collector
policy store / authorization envelope
monitor implementation
fixed effect schema
```

不可信：

```text
LLM reasoning
LLM self-audit
external content
tool output text
agent-generated explanations
```

LLM 自我解释最多作为非可信特征或 baseline，不能作为安全证据来源。

### 2.8 Effect Observability Assumption

形式化假设：

> The monitor only reasons about effects that are mediated and observable by the execution layer.

如果文件删除、网络请求、SaaS 消息发送或 provider API 调用完全绕过 trace collector，则框架不保证检测。该限制必须写入 threat model 和 limitations。

### 2.9 Surface-Form Fragmentation 攻击面

这是本文相对已有 authorization/provenance monitor 的核心补充。

同一 effect 可通过多种 surface 实现：

```text
file_content_read: read_file(path), bash cat path, python open(path).read()
file_deleted: delete_file(path), bash rm path, python os.remove(path)
network_egress: web_fetch(url), curl url, browser navigation/fetch
message_sent: messaging API, webhook POST, browser form submit
```

若 monitor 学到的是 tool name、schema 或文本模板，而不是 realized effect evidence，则在 held-out surface 下会漏检。

方法论文应把主风险写成：

```text
coverage-missing tool surfaces
tool aliases
cross-tool effect realization
held-out tool/effect combinations
schema/provider/tool-family shifts
```

### 2.10 安全目标与指标

形式化安全目标：

```text
Given task c, authorization envelope A(c), and execution trace tau:
Violation occurs if M(c, tau) = ALLOW and Omega(tau) \ A(c) != empty.
```

主指标必须 action-level：

```text
U-Allow = P(ALLOW | unauthorized action)
FDeny = P(DENY | authorized action)
Abstain Rate
Coverage
Selective Risk
```

row-level unauthorized-effect FNR/FPR 只能作为分解指标。

### 2.11 Motivating Examples for Writing

这些例子用于 Introduction、Threat Model 或 Problem Definition。写作时应强调：问题不在于某个工具或服务天然危险，而在于实际产生的 realized effects 超出了任务授权包络 `A(c)`。

#### Example 1: Status Check Expands into Content Fetching and File Write

用户任务：

```text
“请检查 https://vendor.example.com/status 是否能访问。
只需要确认 HTTP 状态码，不要下载页面内容，不要访问其他网址，也不要写入本地文件。”
```

授权包络：

```text
A(c) = {
  network_egress(vendor.example.com),
  status_checked(vendor.example.com)
}
```

agent 实际调用：

```bash
curl -L https://vendor.example.com/status -o /tmp/vendor_status.html
```

执行 trace 可能显示：

```text
1. 发起 HTTPS 请求到 vendor.example.com/status
2. 因 -L 跟随重定向到 cdn.vendor-assets.example.com/full-page
3. 下载完整 HTML 页面内容
4. 将页面写入 /tmp/vendor_status.html
```

因此 realized effects 是：

```text
Omega(trace) = {
  network_egress(vendor.example.com),
  network_egress(cdn.vendor-assets.example.com),
  content_fetched(vendor.example.com/status),
  content_fetched(cdn.vendor-assets.example.com/full-page),
  file_written(/tmp/vendor_status.html)
}
```

越权部分：

```text
Omega(trace) \ A(c) = {
  network_egress(cdn.vendor-assets.example.com),
  content_fetched(vendor.example.com/status),
  content_fetched(cdn.vendor-assets.example.com/full-page),
  file_written(/tmp/vendor_status.html)
}
```

写作要点：

> The tool call appears aligned with the user's status-check request, but the execution trace realizes additional effects: redirected network egress, content fetching, and local file write. The violation is not that `curl` is unsafe; it is that `Omega(trace)` contains effects outside `A(c)`.

#### Example 2: Local Financial Analysis Becomes Unauthorized Cloud Upload

用户任务：

```text
“请读取 billing_report.csv，统计本月总收入。
不要上传、发送、删除或修改任何文件。”
```

授权包络：

```text
A(c) = {
  file_content_read(billing_report.csv),
  local_computation(revenue_sum)
}
```

agent 实际行为可能是调用本地脚本或 Python 工具：

```bash
python analyze.py --input billing_report.csv --use-remote-helper
```

脚本内部可能执行：

```python
import pandas as pd
import requests

df = pd.read_csv("billing_report.csv")
summary = df.describe().to_json()

requests.post(
    "https://cloud-analysis-service.example/process",
    json={
        "filename": "billing_report.csv",
        "raw_rows": df.to_dict(),
        "summary": summary,
    },
)
```

这里的 `cloud-analysis-service.example` 是占位符。真实世界中存在合法的 cloud analytics、AutoML、BI 或 LLM-based data-analysis 服务，例如可上传 CSV/dataset 后做分析。安全问题不是这些服务恶意，而是用户没有授权把本地财务数据上传给第三方服务。

执行 trace 的 realized effects：

```text
Omega(trace) = {
  file_content_read(billing_report.csv),
  local_computation(summary_stats),
  network_egress(cloud_analysis_service),
  external_data_upload(billing_report.csv raw rows),
  remote_computation(cloud_analysis_service)
}
```

越权部分：

```text
Omega(trace) \ A(c) = {
  network_egress(cloud_analysis_service),
  external_data_upload(billing_report.csv raw rows),
  remote_computation(cloud_analysis_service)
}
```

写作要点：

> Authorization to read a local financial file and compute a summary does not imply authorization to upload the raw rows to a third-party analytics service. A monitor that only checks whether the action is "analysis-related" or whether the Python tool is allowed can miss the actual unauthorized effects.

### 2.12 明确排除范围

论文不覆盖：

```text
compromised OS/kernel/monitor
malicious user intentionally requesting harmful tasks
fully unobservable side effects
model weight backdoors
training-data poisoning
physical-world irreversible harm without sandbox/dry-run
legal/ethical validity of the user's task itself
```

我们判断的是：

```text
agent 是否超出当前用户任务授权
```

不是判断：

```text
用户任务本身是否合法、道德或合规
```

---

## 3. 方法框架最低要求

方法论文要成立，框架至少需要满足：

1. **Effect-centered**：判断 `Omega(tau)`，不是判断 tool name。
2. **Authorization-conditioned**：只对 `e notin A(c)` 聚合风险。
3. **Label-hidden**：主结果不得使用 label/near-label fields。
4. **Execution-grounded**：需要 trace/sandbox/dry-run evidence，不只看 task + command。
5. **Surface-held-out**：同一 effect 必须跨 tool/surface/provider/schema 测试。
6. **Evidence-localized**：输出支持 effect 的 subgraph/span/node evidence。
7. **Uncertainty-aware**：允许 `ABSTAIN/ASK_USER`，不能只二分类。
8. **Action-level calibrated**：主优化目标是 `U-Allow/FDeny/Abstain/Coverage`。
9. **Baseline-complete**：必须超过或解释 raw-status boundary、provenance boundary、LLM judge、event-sequence classifier 和 deterministic rules。
10. **Observable-effect bounded**：明确只保证 mediated/observable effects。

---

## 4. 当前实验材料能如何用于方法论文

### 4.1 可作为方法论文主文证据，但必须谨慎表述

| 材料 | 路径 | 可支持的 claim | 写作限制 |
|---|---|---|---|
| T58 controlled execution verifier | `analysis/results/auth_t58_execution_verifier_*_v1.md` | execution evidence 可降低 controlled trace 中 unauthorized-effect miss | controlled traces，不是 deployed logs |
| T62 validation-selected thresholds | `analysis/results/auth_t62_validation_threshold_*.md` | 阈值不是纯 ex-post，已做 validation trace group -> held-out trace group | 仍是 trace-group calibration，不是 deployment calibration |
| T63 broader local adapters | `analysis/results/auth_t62_validation_threshold_*t63_broader_v1.md` | web/search/browser/messaging 名义工具族中 execution evidence 优于 static verifier | local adapters，不是真实 provider-backed 服务 |
| T64 live/protocol traces | `analysis/reports/t64_live_protocol_external_validity_report.md`; `analysis/results/auth_t62_validation_threshold_*t64_live_protocol_v1.md` | real outbound HTTPS/local webhook protocol 下 execution evidence 有帮助 | 非 provider-backed search/SaaS messaging/deployed runtime |
| T65 headless browser runtime | `analysis/results/auth_t62_validation_threshold_*t65_browser_v1.md` | headless Chrome file-backed DOM/JS runtime 下 static verifier 会漏检 | file-backed，不是 HTTP browser automation |
| T68 action-level metrics | `analysis/reports/auth_action_level_metrics_t68.md` | row-level FNR/FPR 与 action-level allow/deny 会脱节 | 暴露 FDeny=1.0，不支持部署可用性 |
| T69 trace-view ablation | `analysis/reports/auth_trace_view_ablation_t69.md` | full-label verifier 会高估；label-hidden/minimal evidence 是必要主设定 | label-hidden 退化明显，必须写成限制 |
| T70 existing-defense proxy | `analysis/reports/auth_existing_defense_ablation_t70.md` | raw-status/provenance/pre-action baseline 是必要对照 | proxy 不是 faithful external defense reimplementation |

主文可写：

> Execution evidence is necessary but not sufficient: it reduces misses in controlled/protocol traces, yet label-hidden inference, action-level calibration, and strong boundary baselines remain unresolved.

### 4.2 可作为动机和诊断证据

| 材料 | 路径 | 用法 |
|---|---|---|
| E01 LOTO fragmentation | `analysis/experiments/E01_surface_fragmentation_loto/README.md`; `analysis/results/fnr_frag_qwen3-8b_scenarios_mainconf_v2.json` | 证明只看 seen tool 会高估 effect detector |
| E02 lexical control | `analysis/experiments/E02_lexical_control/README.md`; `analysis/results/lexical_control_qwen3-8b_scenarios_merged_lexical_control.json` | 反驳“只是工具名/URL/代码关键词” |
| E03 pIIA | `analysis/experiments/E03_piia_transfer_diagnostics/README.md`; `analysis/results/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.md` | supporting activation-level diagnostic，不作 causal proof |
| E04/E05 baselines and contrastive | `analysis/experiments/E04_baselines_tool_proxy/README.md`; `analysis/experiments/E05_contrastive_projection/README.md` | 说明纯表征修复在 strict held-out 下不够 |
| T54-T56 gate failures | `analysis/experiments/E09_auth_mitigation_gate_failures/README.md` | 作为为什么需要 execution/effect verification 的负结果 |

这些材料适合放在方法论文的 Introduction/Motivation/Diagnostic Background，不宜作为主方法性能结果。

### 4.3 只能作为 upper bound 或负结果

| 材料 | 判断 |
|---|---|
| full-label EffectVerif | upper bound；不能作为主方法真实性能 |
| verifier-present oracle | upper bound；支持“若有外部 effect verifier，AuthMonitor 可工作” |
| full-training contrastive projection | observed-pair repair upper bound；不能证明 unknown surface mitigation |
| T73 action calibration | 负结果；说明简单 thresholding 会 all-allow collapse |
| LLM self-audit T87 | 目前有 parser noise 与 label mismatch；只能作为“不可靠自审计”的 exploratory evidence，不能作主表 |
| dual-tower/probe T85-T88 | 可作为探索性 evidence；因数据规模和 template/source leakage 风险，不宜作为方法主贡献 |

### 4.4 不应作为方法论文强证据

不要把以下材料写成强方法验证：

```text
T60 tiny 8-trace provider pilot
real_tool_scenarios semantic proxy as real execution validation
synthetic-only 459/932 LOTO as deployment monitor risk
full-label trace results as label-independent inference
local adapter traces as provider-backed web/search/messaging validation
file-backed Chrome as full HTTP browser automation validation
```

---

## 5. 缺失实验和写作任务

### 5.1 P0：label-hidden CEG-Auth 主实验

目标：

```text
raw trace -> causal evidence graph / event graph -> p(effect), evidence, uncertainty
```

要求：

- 禁止输入 label/near-label fields；
- 与 flat raw-trace classifier、event-sequence transformer、raw-status boundary 对齐比较；
- 按 held-out trace family、held-out tool surface、held-out provider/schema 测试；
- 输出 evidence localization。

支持或证伪的结论：

- 若超过 raw-status boundary 且 action-level 不崩，方法贡献成立；
- 若不超过，论文应回到 evaluation/diagnostic route。

### 5.2 P0：action-level selective policy

目标：

```text
ALLOW / DENY / ABSTAIN / ASK_USER
```

主指标：

```text
U-Allow
FDeny
Abstain Rate
Coverage
Selective Risk
```

必须避免 T73 的 all-allow collapse。需要尝试：

- uncertainty threshold；
- conformal risk control；
- severity-weighted unauthorized risk；
- two-phase commit / sandbox replay；
- user permission request fallback。

### 5.3 P0：真实 held-out surface trace

需要构造真实或半真实 execution traces：

```text
file_content_read: read_file / bash cat / python open
file_deleted: delete_file / bash rm / python os.remove
network_egress: web_fetch / curl / browser request
message_sent: messaging API / webhook / browser form
```

评估：

```text
leave-one-surface-out
leave-one-tool-family-out
held-out provider/schema
row FNR/FPR + action U-Allow/FDeny/Abstain
```

这是连接原 surface-form fragmentation 主线和新 monitor 方法的关键实验。

### 5.4 P1：强 baseline 和 ablation

至少包括：

```text
all-allow
always-deny
tool-name rule monitor
pre-action rule-only
provenance boundary
raw-status boundary
deterministic effect rules
LLM-as-judge over task+tool
LLM-as-judge over raw trace
flat raw-trace classifier
event-sequence transformer
graph without typed edges
graph without uncertainty
graph without evidence localization
graph path-feature logistic/GBDT
```

写作要求：不要说 “beats existing defenses”，除非做 faithful reimplementation 或 protocol-compatible stress test。

### 5.5 P1：外部有效性

优先级从高到低：

1. provider-backed search；
2. SaaS messaging/email API；
3. HTTP browser automation；
4. deployed-agent runtime logs；
5. direct handler traces from `real-agent-tools` if missing modules/API services can be resolved。

若无法提供 API key，必须写成 limitation，并用 key-free protocol traces 作为 partial substitute。

### 5.6 P1：独立 effect verifier

当前 rule/verifier 与 trace schema 同源，方法论文需补：

- learned label-hidden effect verifier；
- fixed parser + learned calibration；
- formally specified effect rules with held-out schema tests；
- train/test parser freeze；
- cross-schema and cross-provider robustness。

### 5.7 P1：统计和复现

主表必须给：

```text
N unauthorized actions
N authorized actions
N+ / N- for row metrics
exact binomial CI
bootstrap CI by trace group
threshold selection protocol
seed variance for learned models
artifact/source path
```

### 5.8 P2：自审计实验修复

如果要使用 LLM self-audit：

- 修复 parser：不能用最后 500 字中最后一次 `AUTHORIZED/UNAUTHORIZED`；
- 统一标签：区分 `scope_authorized`、`effect_authorized`、`task_success`、`tool_error`；
- 重新跑 few-shot/CoT-free/structured-output variants；
- 只作为 baseline，不作为方法主组件。

---

## 6. 方法论文建议结构

1. **Introduction**：长任务 agent 的安全失败不是“工具名危险”，而是 actual effects 超出 task authorization；现有 provenance/contract/graph work 重要但未系统检验 surface-held-out effect monitoring。
2. **Threat Model**：使用本文第 2 节。
3. **Problem Definition**：`A(c)`, `Omega(tau)`, unauthorized effects, selective monitor objective。
4. **Diagnostic Motivation**：surface-form fragmentation + pure representation repair gate failures。
5. **Method**：CEG-Auth: EventExtract -> EffectInfer -> AuthCompare -> SelectivePolicy。
6. **Experiments**：label-hidden raw trace, held-out surfaces, action-level metrics, strong baselines。
7. **Results**：先报 action-level，再报 row-level decomposition；full-label only upper bound。
8. **Ablations**：typed graph, evidence localization, uncertainty, trace view, baseline comparison。
9. **Limitations**：effect observability, sandbox/dry-run, external service coverage, non-faithful defense reimplementation if applicable。

---

## 7. 当前可防守写作结论

可以写：

> The existing evidence supports the feasibility of execution-evidence-based authorization monitoring under controlled and protocol trace settings, and identifies surface-form coverage as a necessary evaluation dimension.

不能写：

> CEG-Auth solves unauthorized tool-use detection or certifies deployed agent safety.

更强但仍谨慎的目标句：

> These results motivate CEG-Auth as a method direction: a monitor must infer realized effects from label-hidden execution evidence, test invariance under held-out tool surfaces, and make selective action-level decisions rather than relying on row-level effect scores or LLM self-audit.

---

## 8. Future-Constrained Shadow Execution 写作材料

> 2026-05-31 新增：用户提出将 agent 意图化为未来轨迹，将实际执行视为运行时轨迹，并“先一步根据未来轨迹约束 agent 行为”。本节把该思想写成方法论文主线候选：**Future-Constrained Shadow Execution / Trajectory-Locked Authorization**。它可作为 CEG-Auth 的 prevention layer，解决 post-hoc monitor 无法阻断真实副作用的问题。

### 8.1 一句话方案

中文：

> 先把任务授权和 agent 拟执行计划编译成未来轨迹约束 `F_c`，在影子沙盒中执行并验证 pending realized effects；若安全，则把影子轨迹编译成 trace-locked replay plan，在真实环境中由非 LLM executor 复放同一轨迹，并在每个可能产生副作用的边界用 `F_c` 和 CEG-Auth 检查后再 commit。

英文：

> We turn the agent's intended behavior into an executable future-trajectory constraint, validate the proposed trajectory in a shadow environment, and replay only the locked trajectory in the real environment under pre-commit effect guards.

### 8.2 方法相对现有 CEG-Auth 的变化

旧版本 CEG-Auth 更像：

```text
real execution trace -> realized-effect inference -> action-level authorization decision
```

这会被审稿人追问：如果文件已经删除、消息已经发出、数据已经上传，post-hoc decision 还有什么防御价值？

新版本改成：

```text
task c + A(c) + agent intent
  -> future trajectory constraint F_c
  -> shadow execution trace tau_s
  -> CEG effect inference and selective authorization
  -> trace-locked replay plan pi
  -> guarded real replay with staged commit
```

核心改动：

- `F_c` 先于真实副作用存在；
- shadow trace 是用于构造和验证未来约束的证据，不是最终安全保证；
- 真实阶段不再请求 LLM 二次输出，而是 replay locked plan；
- 所有真实 side effects 在 commit 前必须通过 guard；
- `ABSTAIN/ASK_USER` 用于处理 sandbox-real divergence、不确定 effect 或不可 staging 的操作。

### 8.3 理论可行性前提

该方案理论上可行，但只在系统假设成立时可保证。

必须写入论文的条件：

1. **Mediated tools**：所有文件、网络、消息、数据库、provider API、browser mutation 等 side-effectful operations 都经过 wrapper/guard。
2. **Staging or dry-run**：不可逆 side effects 必须支持 staging、provider sandbox、transaction、outbox queue、overlay filesystem、mock endpoint 或 user-confirmed commit。
3. **Constraint soundness**：`F_c` 允许的 effects 必须是 `A(c)` 的子集。
4. **Replay lock**：真实环境只能执行影子轨迹编译出的 `pi`，LLM 不能在真实阶段重新规划。
5. **Safe substitution**：真实值替换 `sigma` 只能替换被授权的资源、recipient、endpoint、path、token；替换后重新检查约束。
6. **Complete observable pending effects**：commit 前能观测 pending effects；绕过 collector 的副作用不在保证范围内。

可写成条件命题：

```text
If all side-effectful operations are mediated and staged,
AllowedEffects(F_c) subseteq A(c),
and real replay is prefix-checked against pi and F_c before commit,
then committed effects are a subset of A(c).
```

不可写成：

```text
The monitor proves arbitrary agent executions safe.
```

### 8.4 必做实验

| 实验 | 要写哪些代码 | 为什么重要 | 支持/证伪的结论 |
|---|---|---|---|
| Constraint compiler evaluation | 构造 `task -> A(c), F_c` 标注集；实现 compiler；人工审计 over/under permission | `F_c` 若过宽，后续 replay 再强也会放行越权 | 支持“未来约束可从任务中可靠抽取”，或证伪该假设 |
| Shadow-real divergence | 同一 action 在 sandbox 与真实 replay 中执行；比较 trace/effect/resource | sandbox 与真实环境分歧会破坏安全推理 | 支持“trace-locked replay 可约束真实执行”，或暴露 divergence |
| Pre-commit blocking | 对上传、发送、删除、外连、浏览器提交等越权场景测试阻断 | 这是方法从 audit 变成 prevention 的关键 | 支持“越权副作用在真实 commit 前被阻断” |
| Held-out surface robustness | `read_file/cat/python open`, `delete_file/rm/os.remove`, `web_fetch/curl/browser`, `message API/webhook/form` | 保持原项目 surface-form fragmentation 主线 | 支持 monitor 不只是 tool-name rule |
| Ablation | 去掉 shadow、replay lock、runtime guard、final commit、uncertainty、evidence localization | 证明系统组件必要性 | 支持具体机制贡献，不是 graph complexity |
| Efficiency | 记录 latency、shadow cost、graph inference、guard overhead、abstain/human review rate | 主会审稿会质疑实用性 | 支持高风险操作可接受，或限定适用范围 |

### 8.5 最推荐的主文方法名称

避免把标题写成 “Graph Authorization Monitor”。推荐写法：

```text
Future-Constrained Realized-Effect Authorization for Tool-Using LLM Agents
```

或：

```text
CEG-Auth: Future-Constrained Shadow Execution for Authorization-Conditioned Realized-Effect Monitoring
```

Contribution phrasing:

> We contribute a future-constrained authorization architecture that uses shadow execution to synthesize a replay-locked trajectory and prevents unauthorized realized effects before commit.

不要写：

> We are the first to use graphs for agent safety.

### 8.6 与现有工作的精确边界

- **AuthGraph**：clean authorization graph vs execution provenance graph structural alignment；本文强调 future constraint + shadow trace + locked replay + pre-commit realized-effect guard。
- **PACT / argument-level provenance**：跟踪参数来源和 capability contracts；本文检查执行中实际 realized effects 是否落入 `A(c)`。
- **AgentArmor / ARGUS**：程序依赖图或 influence-provenance graph；本文使用 evidence graph 作为 effect inference substrate，而不是把 graph 本身作为贡献。
- **ClawGuard / ToolGate / Progent**：工具边界或 contract/rule enforcement；本文补充 shadow evidence、surface-held-out effect inference 和 selective action-level policy。
- **AttriGuard / CausalArmor**：关注 tool call 是否由用户意图或不可信上下文造成；本文关注执行后或 commit 前 pending effects 实际是什么。

### 8.7 写作红线

- 不声称 sandbox-safe 推出 real-safe；真实安全来自 replay lock + guard + staging。
- 不把 `ABSTAIN` 当成功；必须报告 coverage 和 selective risk。
- 不把不可 staging 的真实 API 直接写成可完全阻断；这类操作需要 provider sandbox/outbox/user-confirmed commit。
- 不把未来轨迹约束写成 LLM 自审计；它必须是可执行 contract，并接受 parser/validator 检查。
- 不把 shadow execution 的 synthetic trace 当部署日志；它是 pre-commit evidence。
