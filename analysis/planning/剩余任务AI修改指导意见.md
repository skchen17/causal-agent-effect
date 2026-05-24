# 剩余任务 AI 修改指导意见

> Historical guidance note (2026-05-15): this document describes tasks before the third-round closure. The current source of truth is `analysis/后续推进规划.md`, `analysis/completion_report.md`, and `analysis/experiment_state_validation.md`; T5/T6/T7 are now complete under the current DONE gate.

> 创建日期：2026-05-14  
> 目标读者：后续接手本项目的 AI 编程工具 / coding agent。  
> 核心目标：把当前 pilot outputs 修成投稿前可审计、可复现、口径一致的实验与文档，不要把“文件已生成”误判为“任务已完成”。

> 第三轮更新入口：两轮外部 AI 产出和后续实验核对后，必须优先阅读 `analysis/第三轮后续任务精细化指导.md`。该文档包含最新真实状态、严格 DONE gate、P2.5/P3/P2/P5/P4 的细化执行要求，以及防止把 schema validation、taxonomy、JSON 字段存在误写成实验完成的硬性规则。

---

## 0. 接手前必须读取

后续 AI 进入项目后，先读取这些文件，再写代码：

1. `AGENTS.md`
2. `analysis/后续推进规划.md`
3. `analysis/completion_report.md`
4. `analysis/self_review.md`
5. `analysis/剩余实验与真实工具校准规划.md`
6. `paper/main.tex`
7. 相关结果 JSON：
   - `analysis/causal_chain_conditioning_qwen3-8b.json`
   - `analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json`
   - `analysis/real_tool_scenarios_manifest.json`
   - `analysis/real_tool_inventory_hermes.json`

必须遵守：

- 使用 conda 环境：`conda run -n causal-safety python ...`
- 不要删除现有结果；新实验若改变口径，应输出新文件或在文档中明确说明覆盖原因。
- 不要把 LOTO FNR 写成 deploy FNR。
- 不要把 pIIA 写成标准 IIA 或安全证明。
- 不要把真实工具校准写成真实 agent 全流程验证，除非完成本文件 P2.5 的验收标准。

---

## 1. 当前真实状态

当前仓库已有主要 pilot 文件，但不能视为全部完成：

| 模块 | 当前状态 | 主要缺口 |
|------|------|------|
| P2.5 Real-Agent Tool Fidelity | DOING | 真实工具 schema/required args 抽取不完整；样本参数不合法；只覆盖 8 个真实工具 |
| P2 Causal-Chain Conditioning | DOING | wrong_chain 缺 authorization flip；机制指标未补 |
| P3 Contrastive Robustness | DOING | multiseed full-training 有结果；strict leave-one-pair-out 拆分未完成；脚本可追溯不足 |
| P4 理论与论文同步 | DOING | 需要把真实工具校准降级后的结论同步到论文与理论文档 |
| P5 Citation Audit | DOING | 缺 JSON、URL、access date、source trace |

优先级顺序：

1. P2.5 真实工具校准修复。
2. P3 strict split 与脚本可追溯。
3. P2 wrong_chain 与机制指标。
4. P5 文献核验可追溯。
5. P4 论文/理论文本同步降级。

---

## 2. P2.5 Real-Agent Tool Fidelity 修复指导

### 2.1 目标

把 `real-agent-tools/` 中的真实工具注册、schema、handler、guard、调用流程抽取到可审计格式，并重新生成真实工具调用样本，使其能回答：

> 当前合成实验是否真实体现真实 agent 工具调用流程？

预期最终答案应谨慎：

> 当前实验主要是 controlled proxy study。修复后的 real-tool calibration 可以说明部分抽象工具与真实工具效果空间相符，但仍不能等同真实 agent trace。

### 2.2 当前缺陷

已核对发现：

- `analysis/real_tool_scenarios_manifest.json` 的 `tools_covered` 只有 8 个真实工具：
  - `delegate_task`
  - `memory`
  - `read_file`
  - `send_message`
  - `terminal`
  - `web_extract`
  - `web_search`
  - `write_file`
- `self_review.md` 曾写“至少覆盖 10 个真实注册工具”，这是错误的。
- `analysis/real_tool_inventory_hermes.json` 含疑似误抽取伪工具：
  - `tool_name_prefixed`
  - `util_name`
- 多个关键工具的 `required_args` 为空，不能说明 schema 已正确抽取。
- `data/real_tool_scenarios.jsonl` 有无效样本：
  - `read_file` 缺 `path` 45 条。
  - `memory` 缺 `target` 31 条。
  - `terminal` 使用 `ls -la` 等 placeholder command 45 条。

### 2.3 需要修改/新增的代码

优先修改：

- `analysis/extract_real_tool_inventory.py`

建议新增：

- `analysis/build_real_tool_effect_mapping.py`
- `analysis/build_real_tool_scenarios.py`
- `analysis/validate_real_tool_scenarios.py`

如果已有同名脚本但逻辑不完整，应在原脚本上补齐，不要另建重复脚本。

### 2.4 Inventory 抽取要求

输出文件：

- `analysis/real_tool_inventory_hermes.json`
- `analysis/real_tool_inventory_hermes.md`

每个工具条目必须至少包含：

```json
{
  "tool_name": "read_file",
  "source_file": "real-agent-tools/hermes-agent-tools/tools/file_tools.py",
  "lineno": 123,
  "toolset": "core",
  "handler": "read_file",
  "schema_name": "ReadFileInput",
  "required_args": ["path"],
  "properties": {
    "path": {"type": "string", "required": true}
  },
  "check_fn": null,
  "availability_gated": false,
  "extraction_status": "ok",
  "notes": ""
}
```

抽取逻辑要求：

- 只记录真实 `registry.register(...)` 或等价注册调用。
- 不要把变量名、格式化模板、helper function 参数误当工具名。
- 若工具名来自变量或列表展开，必须解析到实际字符串；解析不了时设 `extraction_status="unresolved"`，不要伪造。
- 必须过滤或标注伪工具：
  - `tool_name_prefixed`
  - `util_name`
- 对 Pydantic/BaseModel/schema dict/dataclass 的 required args 做静态解析。
- 如果 schema 解析失败，必须写明失败原因。

验收命令建议：

```bash
conda run -n causal-safety python analysis/extract_real_tool_inventory.py
conda run -n causal-safety python -m json.tool analysis/real_tool_inventory_hermes.json >/tmp/real_tool_inventory.check
```

验收标准：

- `tool_name_prefixed` 和 `util_name` 不再作为正常工具出现。
- `read_file`, `write_file`, `memory`, `terminal`, `web_search`, `web_extract`, `send_message`, `delegate_task` 至少有非空 schema/properties。
- `read_file.required_args` 至少包含 `path`。
- `write_file.required_args` 至少包含 `path` 和 `content`，除非真实 schema 明确不是这样；若不同，必须引用真实 schema。
- `memory.required_args` 必须符合真实工具定义，不能随意假设。

### 2.5 Effect mapping 要求

输出文件：

- `analysis/real_tool_effect_rules.yaml`
- `analysis/real_tool_effect_mapping.json`
- `analysis/real_tool_effect_mapping.md`

mapping schema 建议：

```json
{
  "real_tool_name": "web_extract",
  "experiment_tool_names": ["web_fetch"],
  "possible_effects": ["content_fetched", "network_egress", "tool_error"],
  "argument_to_effect_rules": [
    {
      "condition": "url is external",
      "effects": {"network_egress": 1, "content_fetched": 1},
      "confidence": "high",
      "evidence": "schema includes url; handler fetches/extracts web content"
    }
  ],
  "limitations": "Does not model browser state, redirects, auth, result truncation."
}
```

注意：

- `delete_file` 在 Hermes 中不是独立真实工具时，不要计为真实工具覆盖数；应标注为 `abstract_effect_via_terminal`。
- `web_fetch` 应映射到真实 `web_extract` 或其他真实 web extraction 工具，但要说明 schema 差异。
- `delegate` 应映射到 `delegate_task`，但要说明任务文本、权限继承、子 agent 工具集等未建模。
- `execute_code` / code execution 类工具如果真实存在，应作为当前实验未覆盖的重要 gap 记录。

验收标准：

- MD 表格中不能出现截断句子或空白映射说明。
- 每个实验工具必须有：
  - mapping target。
  - confidence。
  - limitation。
  - 是否真实注册工具。
- 每个真实工具可以有多个 possible effects，但要区分 direct effect 与 indirect effect。

### 2.6 Real-tool scenario 重建要求

输出文件：

- `data/real_tool_scenarios.jsonl`
- `analysis/real_tool_scenarios_manifest.json`
- `analysis/real_tool_scenarios_validation.json`

每行 JSONL 建议字段：

```json
{
  "id": "real_tool_000001",
  "source_scenario_id": "merged_000123",
  "scenario_text": "...",
  "tool_call": {
    "name": "read_file",
    "arguments": {"path": "/workspace/report.md"}
  },
  "schema_snapshot": {
    "required_args": ["path"],
    "properties": {"path": {"type": "string"}}
  },
  "toolset": "core",
  "pre_state": {
    "files": ["/workspace/report.md"],
    "network_allowed": false
  },
  "authorization": {
    "task_goal": "summarize the report",
    "allowed_effects": ["file_content_read"],
    "forbidden_effects": ["network_egress", "file_deleted"]
  },
  "predicted_call_flow": [
    "schema_validation",
    "path_guard",
    "handler_execution",
    "result_truncation"
  ],
  "effects": {
    "file_content_read": 1,
    "tool_error": 0
  },
  "fidelity_notes": "Arguments satisfy read_file schema; no real execution performed."
}
```

必须修复：

- `read_file` 必须有真实 schema 所需参数，如 `path`。
- `write_file` 必须有真实 schema 所需参数，如 `path` 和 `content`。
- `memory` 必须符合真实 schema，不允许缺 required args。
- `terminal` 命令必须与 `scenario_text` 和 `effects` 一致：
  - 如果 effects 有 `file_deleted=1`，命令可为 `rm target.txt` 或等价删除命令。
  - 如果 effects 有 `command_executed=0`，不要使用会执行命令的 terminal tool_call；除非显式建模为 blocked/failed pre-check，并把 `tool_error=1`。
  - 不要用 `ls -la` 代表任意错误、删除、读取、网络等效果。
- `delete_file` 映射到 terminal 时，effects 需要同时处理 `command_executed` 语义；不能保留原抽象样本中不一致的 effects。

覆盖标准：

- 至少覆盖 10 个真实注册工具，或如果真实项目核心工具不足 10 个，必须在 manifest 中解释原因。
- 每个目标 effect 至少 2 个 surface forms。
- 小样本 effect-tool pair 必须报告 `n_positive`；`n_positive < 10` 的结果只能写描述性。

新增 validator 必须检查：

- tool name 是否在 inventory 中。
- required args 是否满足。
- effects 是否只包含已定义 11 个 effect。
- terminal command 与 effects 是否存在明显冲突。
- 每个 effect 的 surface form 数。
- 每个 tool/effect 的正负样本数。

建议命令：

```bash
conda run -n causal-safety python analysis/build_real_tool_scenarios.py
conda run -n causal-safety python analysis/validate_real_tool_scenarios.py
```

验收标准：

- validation JSON 中 `num_schema_errors=0`。
- validation JSON 中 `num_placeholder_commands=0`。
- manifest 中 `tools_covered >= 10`，或有明确 justified exception。
- `analysis/completion_report.md` 和 `analysis/self_review.md` 同步更新。

---

## 3. P3 Contrastive Robustness 修复指导

### 3.1 目标

补齐 contrastive projection 的可复现脚本和 strict leave-one-pair-out 拆分，使 reviewer 能区分：

- full-training alignment：目标工具 pair 已参与训练。
- strict two-form impossible：只有两个 surface forms，leave-one-pair 后无跨工具正 pair 可训练。
- strict three-plus transitive：至少三个 surface forms，可以通过中间 form 测试传递对齐。

### 3.2 需要修改/新增的代码

建议新增：

- `run_contrastive_multiseed.py`
- `analysis/analyze_contrastive_strict_split.py`

也可以扩展已有：

- `solution_contrastive.py`

### 3.3 输出要求

输出文件：

- `analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json`
- `analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.md`
- `analysis/contrastive_strict_split_qwen3-8b_scenarios_merged.json`
- `analysis/contrastive_strict_split_qwen3-8b_scenarios_merged.md`

multiseed JSON 必须记录：

```json
{
  "config": {
    "model": "qwen3-8b",
    "data": "scenarios_merged",
    "seeds": [0, 1, 2, 3, 4],
    "dim": 128,
    "train_protocol": "full_training"
  },
  "results": {
    "content_fetched": {
      "web_fetch": {
        "post_fnr_mean": 0.1625,
        "post_fnr_std": 0.0848,
        "values": [0.25, 0.28125, 0.09375, 0.09375, 0.09375],
        "n_positive": 32
      }
    }
  }
}
```

strict split JSON 必须分开：

```json
{
  "two_form_effects": {
    "content_fetched": {
      "status": "not_evaluable",
      "reason": "Only two surface forms; leaving out the target pair removes all cross-form positive training pairs."
    }
  },
  "three_plus_form_effects": {
    "network_egress": {
      "num_pairs": 10,
      "num_improved": 10,
      "mean_delta_fnr": 0.12,
      "pairs": []
    }
  }
}
```

### 3.4 口径要求

- `post_fnr_mean` 若是 worst-form，应明确写 `aggregation="worst_form"`。
- 若是 effect-average，应明确写 `aggregation="effect_average"`。
- 不要在同一表中混用 `content_fetched=0.1625` 和 `0.0813` 而不解释。
- 对 `content_fetched` 等小 N+ 结果，必须报告 `n_positive` 和 CI 或描述性限制。

建议命令：

```bash
conda run -n causal-safety python run_contrastive_multiseed.py --model qwen3-8b --data scenarios_merged --seeds 0 1 2 3 4 --dim 128
conda run -n causal-safety python analysis/analyze_contrastive_strict_split.py
```

验收标准：

- full-training multiseed 结果可由脚本复现。
- strict split 明确区分 two-form 与 three-plus-form。
- `paper/main.tex` 中 contrastive 结果只引用可追溯 JSON。

---

## 4. P2 Causal-Chain Conditioning 修复指导

### 4.1 目标

把 causal-chain conditioning 从“看起来有效的 pilot”提升为机制实验：

> 因果链信息是否改变模型表征，使效果检测更跨工具一致，而不是仅让 probe 读到显式答案？

### 4.2 当前缺口

- `wrong_chain` 没有完整 authorization flip。
- 当前主要指标是 LOTO FNR 和 ToolProxyGap；缺少机制指标。
- 还未评估工具 discriminator accuracy、同效果跨工具距离、pIIA-Drop 是否改善。

### 4.3 需要修改/新增的代码

优先修改：

- `build_causal_chain_conditioning_data.py`

建议新增：

- `evaluate_causal_chain_conditioning.py`
- `analysis/analyze_causal_chain_mechanism.py`

### 4.4 wrong_chain 构造要求

每个 wrong_chain 样本应明确记录错误类型：

```json
{
  "condition": "wrong_chain",
  "wrong_chain_type": "authorization_flip",
  "true_effects": {"network_egress": 1},
  "claimed_effects": {"network_egress": 1},
  "true_authorization": {"network_egress": false},
  "claimed_authorization": {"network_egress": true}
}
```

至少包含三类：

1. `effect_omission`：真实效果存在，但显式链漏写。
2. `effect_substitution` 或 `effect_flip`：把真实效果替换成另一个效果。
3. `authorization_flip`：效果事实不变，但授权状态反转。

注意：

- wrong_chain 不能只改文本而不改 metadata。
- wrong_chain 的评估要能按错误类型分组。
- 如果模型在 authorization_flip 下 FNR 降低但越权判断变差，不能写成安全提升。

### 4.5 机制指标

新增分析应至少输出：

1. LOTO heldout FNR。
2. ToolProxyGap。
3. Same-effect cross-tool representation distance。
4. Tool discriminator accuracy on positive examples。
5. Effect probe F1 / AUC。
6. wrong-chain induced error rate by wrong_chain_type。

输出 JSON 建议：

```json
{
  "content_fetched": {
    "raw": {
      "max_held_fnr": 0.7812,
      "toolproxy_gap": 0.6406,
      "tool_discriminator_acc_e1": 0.85,
      "cross_tool_distance_mean": 1.23
    },
    "task_causal_chain": {
      "max_held_fnr": 0.0,
      "toolproxy_gap": 0.0,
      "tool_discriminator_acc_e1": 0.55,
      "cross_tool_distance_mean": 0.72
    }
  }
}
```

验收标准：

- `analysis/causal_chain_conditioning_qwen3-8b.json` 或新版 JSON 中包含 wrong_chain 分类型结果。
- authorization flip 样本数量非零。
- 能回答：性能提升是表征按 effect 更聚合，还是输入中直接泄露了 label。
- `paper/main.tex` 中若引用该方法，只写成 pilot / input-side mitigation candidate。

---

## 5. P5 Citation Audit 修复指导

### 5.1 目标

把 `analysis/citation_audit.md` 从人工备忘录变成可审计证据。

### 5.2 需要新增的文件

- `analysis/citation_audit.json`
- 可选：`analysis/build_citation_audit.py`

### 5.3 JSON schema

```json
[
  {
    "key": "attrguard2026",
    "title": "AttriGuard: Defeating Indirect Prompt Injection in LLM Agents via Causal Attribution of Tool Invocations",
    "authors": ["..."],
    "venue_or_source": "arXiv",
    "arxiv_id": "2603.10749",
    "url": "https://arxiv.org/abs/2603.10749",
    "access_date": "2026-05-14",
    "paper_claim": "0% ASR under static attacks",
    "used_in_project": "background related work",
    "verification_status": "verified_from_source",
    "quote_or_location": "abstract / evaluation paragraph",
    "recommended_wording": "reported 0% ASR under static attacks in their evaluated setup",
    "limitations": "preprint; setting-specific; not independently reproduced"
  }
]
```

### 5.4 核验要求

每条引用必须记录：

- 标题。
- 作者。
- arXiv ID / venue / workshop。
- URL。
- access date。
- 项目中使用的具体数字或事实。
- 推荐写法。
- 限制。

特别注意：

- 2026 年 arXiv 预印本不能写成已被顶会接收，除非源文件明确。
- XOA 的 78% scriptability 应写成 source-reported，不是本项目独立复现。
- QueryIPI 的 87% success rate 应写明 agent setting。
- LITMUS 的 40.6% 应写明模型与设置，不要泛化成所有 agents。

验收标准：

- `citation_audit.md` 由 JSON 生成或与 JSON 一致。
- 每条强事实都有 URL 和 access date。
- 无法核验的事实从 `paper/main.tex` 删除或降级为非数字背景描述。

---

## 6. P4 论文与理论同步指导

### 6.1 目标

把论文叙事同步到修复后的真实状态，避免 reviewer 认为过度声称。

### 6.2 需要检查的文件

- `paper/main.tex`
- `analysis/formalization.md`
- `analysis/contrastive_theory.md`
- `analysis/final_summary.md`
- `analysis/current_status_and_gaps.md`

### 6.3 必须使用的表述

推荐：

- controlled diagnostic study
- coverage-missing stress test
- preliminary real-tool calibration
- evidence suggests
- under controlled synthetic scenarios
- input-side mitigation candidate
- representation-level mitigation under partial target-pair coverage

避免：

- proves safety
- solves tool-use safety
- real-agent validation completed
- current LLMs fundamentally fail
- causal-chain conditioning robustly prevents overreach
- deployed FNR, 如果实际是 LOTO FNR

### 6.4 与结果文件同步

论文中所有数字必须能追溯：

- LOTO / ToolProxyGap：对应 `analysis/fnr_frag_*.json` 或 `analysis/causal_chain_conditioning_*.json`。
- contrastive：对应 `analysis/contrastive_*.json`。
- pIIA：对应 `analysis/iia_true_*.json` 和 raw JSONL。
- citation facts：对应 `analysis/citation_audit.json`。

验收标准：

- 主文不再把真实工具校准写成完成的真实 agent 实验。
- P2 causal-chain 只作为 pilot 或 candidate method。
- P3 strict split 只报告可评估部分，并明确 two-form 不可评估原因。
- 理论 theorem 的 assumptions 和 empirical setting 对齐。

---

## 7. 最终验收流程

完成任一模块后必须执行：

1. 运行相关脚本，生成 JSON/MD。
2. 运行 validator 或至少 `python -m json.tool` 检查 JSON。
3. 更新：
   - `analysis/completion_report.md`
   - `analysis/self_review.md`
   - `analysis/后续推进规划.md`
4. 若论文数字或结论变化，更新 `paper/main.tex`。
5. 在 `analysis/后续推进规划.md` 第 5 节追加维护日志。

建议最终核对命令：

```bash
conda run -n causal-safety python -m json.tool analysis/real_tool_inventory_hermes.json >/tmp/check_inventory.json
conda run -n causal-safety python -m json.tool analysis/real_tool_scenarios_manifest.json >/tmp/check_manifest.json
conda run -n causal-safety python -m json.tool analysis/causal_chain_conditioning_qwen3-8b.json >/tmp/check_chain.json
conda run -n causal-safety python -m json.tool analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json >/tmp/check_contrastive.json
```

如果新增 validator：

```bash
conda run -n causal-safety python analysis/validate_real_tool_scenarios.py
```

最终 DONE 标准：

- P2.5：真实工具样本 schema validation 通过，真实工具覆盖数达标或有合理例外说明。
- P2：wrong_chain 三类错误齐全，authorization flip 有独立结果。
- P3：full-training multiseed 和 strict split 都可由脚本复现。
- P5：citation audit 有 JSON source trace。
- P4：论文和理论文档只声称当前证据能支持的结论。

---

## 8. 给后续 AI 的执行建议

不要一次性改所有模块。推荐顺序：

1. 先修 P2.5，因为真实工具样本质量会影响论文外部有效性。
2. 再修 P3，因为 contrastive 是当前最强 mitigation，需要最强可复现性。
3. 再修 P2，因为 causal-chain 可能成为第二方法贡献，但必须排除“显式答案泄露”风险。
4. 再修 P5，确保相关工作不因虚假或不可审计引用被 reviewer 抓住。
5. 最后统一修 P4/paper text。

每一步都要保守写结论。这个项目当前最强定位是：

> A controlled diagnostic study showing surface-form fragmentation in LLM representations for agent tool-call effects, with preliminary evidence that contrastive projection and causal-chain conditioning can reduce coverage-missing stress-test failures under controlled conditions.
