# C 线 Artifact 路径参数化补丁方案（P0 草案，2026-08-04）

产出者：GeneralPurpose 执行助手（C 线 Artifact 准备 P0 任务，项目经理委派）
状态：**草案，未应用任何补丁**。v17 实验运行中（runner PID 578021 / llama.cpp server PID 578023 / 端口 18087），且补丁需用户确认后实施。
约束：本任务只读仓库（唯一新建文件即本文档及配套打包脚本/README 草稿）；不执行打包；不启动 GPU；不写入任何真实凭据。

---

## 0. 复核结论（对 2026-08-03 全仓库扫描报告的核实）

| 08-03 报告要点 | 复核结果（2026-08-04） |
|---|---|
| 无真实凭据（sk- 密钥/密码/私钥/真实邮箱 0 命中） | ✅ 复核一致：`sk-[A-Za-z0-9_-]{12,}` 命中仅出现在内部文档 `shared/compatibility/analysis/后续推进规划.md`（描述性文字误报）与打包脚本自身的扫描正则；无真实 API key。邮箱扫描命中均为 AgentDojo 基准合成邮箱（emma.johnson@bluesparrowtech.com 等），非作者身份 |
| git 身份泄漏（.git 含 skchen17） | ✅ 复核确认：`git config` → `skchen17 <skchen17@github.com>`；remote → `git@github.com:skchen17/causal-agent-effect.git`；`skchen17` 字符串另出现于 `paper/current-usenix/submission_war_plan_2026-08-03.md`（内部 md，排除）。打包必须排除 .git |
| 40+ 处硬编码主机路径 | ✅ 复核确认，且规模更大：**进包源码 32 文件 / 59 处**（含 2 处打包脚本自身扫描正则，非泄漏）；不进包数据/结果文件约 1.6 万行命中（traceback/source_artifact_path/stderr_tail 字段） |
| 19 个内部 md 必须排除 | ⚠️ 数量已增至 **23 个**（08-03 后新增 `reviewer_perspective_improvement_evaluation_2026-08-04.md`、`window_execution_decision_2026-08-04.md` 等）。`paper/current-usenix/` 下 25 个 .md 中：README.md 改写进包、claim_to_source_map.md 进包决策待定、其余 23 个内部 md 排除 |
| paper/current-usenix/README.md 提及 "prior NDSS draft" | ✅ 确认第 3 行存在；改写草稿见 `README.artifact.md`（本文档 §6 附录） |
| 根目录 symlink 打包时解析为真实目录 | ✅ 确认根目录 **14 个** symlink（08-03 报告为 15，实际 14）：results/logs/evaluation/baselines/manifests/analysis/data/audit/scripts/reproduction/runs/code/reports/tests → `shared/compatibility/*` |
| artifact/ manifest 三项 release gate 未过 | ✅ 复核确认：`anonymous_stable_url_inserted` / `clean_environment_reproduction_passed` / `full_artifact_credential_identity_path_scan_passed` 均为 false |

额外复核发现（08-03 报告未覆盖）：
- **manifest.json 引用的 6 个 required_evidence 文件全部干净**（0 处主机路径）——进包证据链低风险，见 §3.4
- `code/src`（runtime 源码）**零泄漏**——核心机制代码干净，仅复现脚本层泄漏
- `paper/current-usenix/` 的 tex/sections/tables/appendix/main.txt **零泄漏**
- `shared/compatibility/code/scripts/build_{mainline_tool_effect_binding,e58_consolidated}_package.py` 内嵌扫描正则 `/data/CSK|/home/user|sk-...`——若这两脚本进包会触发复检误报，建议排除或加注释
- 根目录 `README.md` 提及 "legacy root paths / temporary symlinks" 迁移说明——进包需改写（见 §6）

---

## 1. 完整泄漏清单（按进包分类）

> 路径统一缩写：`R=/data/CSK/causal-agent-safety-research`；`P=/home/user/anaconda3/bin`
> `scripts/` 为根目录 symlink → `shared/compatibility/scripts/`，以下按真实位置列示。

### A 类：进包源码（需参数化补丁）——32 文件 / 59 处

#### A1. `shared/compatibility/scripts/`（= 根 `scripts/`）——11 文件 / 22 处

| # | 文件 | 行 | 泄漏内容 | 类型 |
|---|---|---|---|---|
| A1-1 | run_e77_v3_qwen32_full.py | 25 | `MODEL = Path("R/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 81 | `"P/python"`（server_command） | PY |
| A1-2 | run_e78_qwen32_strong_baselines.py | 24 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 117 | `"P/python", "-m", "llama_cpp.server"` | PY |
| A1-3 | run_e78_capacity_matched_repairs.py | 29 | `"R/models/"`（models 目录） | DIR |
| | | 136 | `"P/python"` | PY |
| A1-4 | run_e79_agentlab_qwen32_queue.py | 25 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 76 | `"P/python", "-m", "llama_cpp.server", "--model", str(MODEL)` | PY |
| | | 100/109/122/132 | `["P/python", "scripts/run_e79_agentlab_saved_transfer.py", ...]` ×4 | PY |
| A1-5 | run_e79_agentlab_saved_transfer.py | 31 | `CONDA = Path("P/conda")` | CONDA |
| A1-6 | run_e79_e77_strict_audit_rerun.py | 28 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 167/221/253/278 | `"P/python"` ×4 | PY |
| A1-7 | run_e79_toolsandbox_qwen32_queue.py | 21 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 70 | `"P/python", "-m", "llama_cpp.server", "--model", str(MODEL)` | PY |
| A1-8 | run_representation_closed_loop_attribution.py | 36 | `MODEL = Path("R/models/" "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 396 | `"P/python"` | PY |
| A1-9 | run_bounded_adaptive_public_family_search.py | 105 | `"P/python"` | PY |
| A1-10 | resume_e78_attriguard_dual_biased.py | 18 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 59 | `"P/python"` | PY |
| A1-11 | resume_e78_attriguard_gpu1.py | 18 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 53 | `"P/python"` | PY |

#### A2. `experiments/*/source/` —— 12 文件 / 27 处

| # | 文件 | 行 | 泄漏内容 | 类型 |
|---|---|---|---|---|
| A2-1 | adaptive-injection-benchmark/source/agent-injection-benchmark-construction/bounded_search.py | 33 | `"R/models/"` | DIR |
| A2-2 | 同目录 staged_runner.py | 26 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 74 | `"P/python"` | PY |
| A2-3 | counterfactual-descriptor-onboarding/source/iterative-counterfactual-refinement/run_e63_gemma4_transformers.py | 24 | `"R/.hf_cache/hub/"` | HF |
| A2-4 | counterfactual-descriptor-onboarding/source/llm-field-counterfactual-sensitivity/run_e68.py | 49 | `DEFAULT_MODEL = "R/models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"` | MODEL |
| A2-5 | intent-bound-runtime-guard/source/atom-targeted-prompt-guidance/atom_specificity_smoke.py | 37 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 165 | `"P/python", "-m", "llama_cpp.server"` | PY |
| A2-6 | 同目录 atom_specificity_corrected.py | 39 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| | | 220 | `"P/python", "-m", "llama_cpp.server"` | PY |
| A2-7 | 同目录 atom_specificity_round2.py | 37 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL |
| A2-8 | 同目录 run_multimethod.py | 48-49 | `PROTECTAI = Path("R/models/protectai_deberta-v3-base-prompt-injection-v2")`；`PIGUARD = Path("R/.hf_cache/hub/models--leolee99--PIGuard/snapshots/dd78b24e...")` | MODEL+HF |
| A2-9 | intent-bound-runtime-guard/source/atomized-tool-description-self-governance/run_pilot.py | 30 | `"R/models/"` | DIR |
| | | 69 | `"P/python", "-m", "llama_cpp.server"` | PY |
| A2-10 | 同目录 build_token_matched_neutral.py | 21 | `"R/models/"` | DIR |
| A2-11 | unified-agent-security-baselines/source/unified-agent-security-comparison/run_e75.py | 66-67 | `PI_DETECTOR_MODEL_PATH = Path("R/models/protectai_deberta-v3-base-prompt-injection-v2")`；`EXTERNAL_PHASE5_RUN_DIR = Path("R/runs/tool_effect_fragmentation_phase5")` | MODEL+DIR |
| | | 499 | `Path("R/models/protectai_...").exists()` | MODEL |
| | | 661-664 | `Path("R/external/systems/{ipiguard,camel,toolsafe}").exists()` ×3 + `Path("R/models/protectai_...").exists()` | EXT+MODEL |
| | | 1019-1021 | `Path("R/models/mistralai/Mistral-7B-v0.1")`、`Path("R/models/Mistral-7B-v0.1")`、`Path("R/.hf_cache/hub/models--mistralai--Mistral-7B-v0.1")` | MODEL+HF |
| | | 2617 | `"HF_HOME": "R/.hf_cache"` | HF |
| A2-12 | 同目录 agentdojo_local_pi_detector_patch.py | 20 | `"R/models/protectai_deberta-v3-base-prompt-injection-v2"` | MODEL |

#### A3. `experiments/*/scripts/` —— 6 文件 / 7 处

| # | 文件 | 行 | 泄漏内容 | 类型 | v17 状态 |
|---|---|---|---|---|---|
| A3-1 | intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/run-recovery-normalization-qwen32.py | 24 | `MODEL = Path("R/models/.../Qwen3-32B-Q4_K_M.gguf")` | MODEL | 🔴 **v17 运行中，禁改** |
| | | 122 | `"P/python"` | PY | 🔴 同上 |
| A3-2 | 同目录 run-plan-normalization-qwen32-full.py | 92 | `"P/python"` | PY | 🟠 v17 协议相关（非运行），保守禁改 |
| A3-3 | 同目录 run-qwen32-context-repair.py | 166 | `"P/python"` | PY | 🟠 同上 |
| A3-4 | security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-protocol.py | 241 | `"file": "R/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"`（写入 protocol.json 的 model 字段） | MODEL | 🔴 **v17 协议链（freeze 步骤），禁改** |
| A3-5 | security-analysis-ablation-and-overhead/scripts/runtime-mechanism-ablation/run-e81-qwen32-runtime-ablations.py | 136 | `"P/python"` | PY | 🟢 可改 |
| A3-6 | 同目录 run-e84-qwen9b-agentdojo-pilot.py | 134 | `"P/python"` | PY | 🟢 可改 |

#### A4. `evaluation/` —— 1 文件 / 1 处

| # | 文件 | 行 | 泄漏内容 | 类型 |
|---|---|---|---|---|
| A4-1 | evaluation/real_model_common.py | 14 | `MODEL_ROOT = Path(os.environ.get("EFFECT_BINDING_MODEL_ROOT", "R/models"))`（已有 env 优先，但 **fallback 硬编码**） | DIR |

#### A5. 其他进包候选 —— 2 文件 / 2 处

| # | 文件 | 行 | 内容 | 说明 |
|---|---|---|---|---|
| A5-1 | shared/compatibility/code/scripts/build_mainline_tool_effect_binding_package.py | 571 | 正则 `/data/CSK\|/home/user\|sk-...` | 泄漏扫描器自身；进包会触发复检误报 → 建议**打包时排除**或保留并白名单 |
| A5-2 | shared/compatibility/code/scripts/build_e58_consolidated_package.py | 734 | 正则 `/data/CSK\|/home/user` | 同上 |

### B 类：不进包数据/结果文件（排除或清洗）——约 1.6 万行命中

| 位置 | 命中行数 | 泄漏形式 | 处置建议 |
|---|---|---|---|
| shared/compatibility/data/data/tool_effect_fragmentation/*.jsonl | ~6900 | `"source_artifact_path": "R/data/agentdojo_effect_verifier_t122_core.jsonl"`（stress 用例数据字段） | 若进包：清洗 source_artifact_path 字段（改相对名）；否则排除 |
| experiments/unified-agent-security-baselines/results/unified-agent-security-comparison/*.{json,jsonl,md} | ~6900 | `stderr_tail` 含完整主机路径、`model_path`、`HF_HOME`、traceback | 排除（attriguard-sharded-run-status.json 单文件 1785 行）；仅保留 manifest 引用的干净结果 |
| shared/compatibility/results/results/canonical/*.json | ~350 | traceback 中 `File "R/src/..."`、`model_path` | 排除或清洗 |
| experiments/binding-failure-and-granularity/results/cross-method-binding-stress/*.json* | ~800 | `source_artifact_path`/`shard_dir`/`model_path`/traceback | 排除或清洗 |
| experiments/security-analysis-ablation-and-overhead/results/** | ~100 | `model_path`（e84 csv/json） | 清洗或排除 |
| experiments/long-horizon-transfer/results/**/*-status.json | ~30 | `"P/conda"`（agentlab 状态） | 排除（manifest 引用的 *-results.json 干净） |
| experiments/intent-bound-runtime-guard/results/** | ~20 | stderr_tail / llama_cpp_server.log 路径 | 清洗或排除 |
| experiments/counterfactual-descriptor-onboarding/results/** | ~10 | model_path | 清洗或排除 |
| shared/compatibility/analysis/results/**（e62/e63 等） | ~40 | model_path | 清洗或排除（e78 两个 manifest 引用文件已验证干净） |
| shared/compatibility/audit/analysis/results/e57_human_audit_validation.json | 1 | `P/python` | 排除（audit 目录为内部审计材料） |
| shared/compatibility/analysis/后续推进规划.md | 3 | 内部工作文档（含路径描述） | 排除 |
| v17_finalizer_watch.sh / v17_finalizer_watch.log | 1+0 | `ROOT=R/paper_materials/...` | 排除（打包清单显式排除） |
| 根目录 README.md | — | 提及 "legacy root paths / temporary symlinks" 迁移说明 | 进包时替换为改写版（§6） |

### C 类：复核验证干净（无需处理）

- `code/src`（runtime 机制源码）：0 命中
- `paper/current-usenix/` tex / sections / tables / appendix / main.txt / references.bib：0 命中
- manifest.json 的 6 个 required_evidence 文件（agentlab-saved-transfer ×2、e78 ×2、closed-loop-attribution、current_evidence.json）：0 命中
- `finalize-recovery-normalization-qwen32-full.py`（v17 finalizer）：0 命中

---

## 2. 参数化方案设计（统一环境变量）

### 2.1 环境变量契约

| 环境变量 | 用途 | 默认值（补丁后） | 说明 |
|---|---|---|---|
| `EFFECT_BINDING_MODEL_ROOT` | 模型根目录 | `Path(__file__).resolve().parents[1] / "models"`（包内相对） | 已在 real_model_common.py 使用；**移除硬编码 fallback** |
| `EFFECT_BINDING_MODEL_FILE` | 主模型 gguf 相对路径（root 下） | `"Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"` | 替代各脚本 `MODEL = Path("R/models/...")` |
| `EFFECT_BINDING_PYTHON` | llama.cpp 解释器 | `sys.executable` | 替代 `"/home/user/anaconda3/bin/python"` 全部出现 |
| `EFFECT_BINDING_CONDA` | conda 可执行 | `shutil.which("conda") or "conda"` | 替代 run_e79_agentlab_saved_transfer.py 的 CONDA |
| `EFFECT_BINDING_HF_CACHE` | HF hub 缓存根 | `Path.home() / ".cache/huggingface/hub"` | 替代 `.hf_cache/hub/`（run_e63/run_multimethod/run_e75 L2617/1021） |
| `EFFECT_BINDING_EXTERNAL_ROOT` | external 系统根 | `PACKAGE_ROOT / "external"` | 替代 run_e75 L661-663 的 `R/external` 存在性检查 |

### 2.2 复用已有模式：`evaluation/real_model_common.py`

`resolve_model_path(default_relative, absolute_fallback, env_name)`（real_model_common.py 现有函数）已实现"env 优先 → 包内相对 → MODEL_ROOT → fallback"四级解析，且 `MODEL_ROOT` 已读 `EFFECT_BINDING_MODEL_ROOT`。补丁以该函数为唯一真源，各脚本引用之，**不再各自定义 MODEL 常量**。

### 2.3 通用 diff 模板（8 种泄漏类型）

**T1 MODEL（单行 gguf 常量）**
```diff
- MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
+ MODEL = Path(os.environ.get("EFFECT_BINDING_MODEL_ROOT", ROOT / "models"))
+          / os.environ.get("EFFECT_BINDING_MODEL_FILE", "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
```
（同时保留现有 `MODEL_BYTES` / `MODEL_SHA256` 校验行不变——校验逻辑本身无泄漏。）

**T2 DIR（models 目录字符串）**
```diff
- "/data/CSK/causal-agent-safety-research/models/"
+ os.environ.get("EFFECT_BINDING_MODEL_ROOT", ROOT / "models") / ""
```

**T3 PY（解释器）**
```diff
- "/home/user/anaconda3/bin/python",
+ os.environ.get("EFFECT_BINDING_PYTHON", sys.executable),
```

**T4 PY-LLAMA（解释器+llama_cpp.server 内联列表）**
```diff
-         "/home/user/anaconda3/bin/python", "-m", "llama_cpp.server", "--model", str(MODEL),
+         os.environ.get("EFFECT_BINDING_PYTHON", sys.executable), "-m", "llama_cpp.server", "--model", str(MODEL),
```

**T5 CONDA**
```diff
- CONDA = Path("/home/user/anaconda3/bin/conda")
+ CONDA = Path(os.environ.get("EFFECT_BINDING_CONDA", shutil.which("conda") or "conda"))
```

**T6 HF（HF hub 缓存）**
```diff
- "/data/CSK/causal-agent-safety-research/.hf_cache/hub/"
+ os.environ.get("EFFECT_BINDING_HF_CACHE", Path.home() / ".cache/huggingface/hub") / ""
```

**T7 EXT（external 系统存在性检查，run_e75 L661-663）**
```diff
- "external_ipiguard_repo_present": Path("/data/CSK/causal-agent-safety-research/external/systems/ipiguard").exists(),
+ "external_ipiguard_repo_present": (EXTERNAL_ROOT / "systems/ipiguard").exists(),
```
（`EXTERNAL_ROOT = Path(os.environ.get("EFFECT_BINDING_EXTERNAL_ROOT", PACKAGE_ROOT / "external"))`）

**T8 模型存在性检查（run_e75 L499/664）**
```diff
- and Path("/data/CSK/causal-agent-safety-research/models/protectai_deberta-v3-base-prompt-injection-v2").exists(),
+ and (PI_DETECTOR_MODEL_PATH.expanduser()).exists(),
```
（`PI_DETECTOR_MODEL_PATH` 本身改由 T2 模板解析）

### 2.4 代表性文件完整 diff 草稿

**D1. `evaluation/real_model_common.py`（A4-1）——基础设施先行**

```diff
@@ 头部 @@
 import hashlib
 import json
 import os
 import re
 from collections import Counter
 from pathlib import Path
 from typing import Any

 ROOT = Path(__file__).resolve().parents[1]
-MODEL_ROOT = Path(os.environ.get("EFFECT_BINDING_MODEL_ROOT", "/data/CSK/causal-agent-safety-research/models"))
+MODEL_ROOT = Path(
+    os.environ.get("EFFECT_BINDING_MODEL_ROOT", ROOT / "models")
+).expanduser()
```

**D2. `scripts/run_e77_v3_qwen32_full.py`（A1-1）——MODEL + PY**

```diff
+import os
+import sys
 from pathlib import Path
 from typing import Any
@@
 ROOT = next(
     candidate
     for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents)
     if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir()
 )
 RESULTS = ROOT / "analysis/results"
-MODEL = Path("/data/CSK/causal-agent-safety-research/models/Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf")
+MODEL = Path(os.environ.get("EFFECT_BINDING_MODEL_ROOT", ROOT / "models")) / os.environ.get(
+    "EFFECT_BINDING_MODEL_FILE", "Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf"
+)
 MODEL_BYTES = 19_762_149_024
 MODEL_SHA256 = "efd971561896866f0e910cce52761ca77b1b138090c7f15fe284676d57d1f689"
@@
 def server_command(port: int, context: int) -> list[str]:
     return [
-        "/home/user/anaconda3/bin/python",
+        os.environ.get("EFFECT_BINDING_PYTHON", sys.executable),
         "-m",
         "llama_cpp.server",
```

**D3. `experiments/unified-agent-security-baselines/source/.../run_e75.py`（A2-11）——11 处**

```diff
+import os
+import sys
@@
-MODEL_NAME = "Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"
-PI_DETECTOR_MODEL_PATH = Path("/data/CSK/causal-agent-safety-research/models/protectai_deberta-v3-base-prompt-injection-v2")
-EXTERNAL_PHASE5_RUN_DIR = Path("/data/CSK/causal-agent-safety-research/runs/tool_effect_fragmentation_phase5")
+MODEL_NAME = os.environ.get("EFFECT_BINDING_MODEL_FILE", "Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf")
+MODEL_ROOT = Path(os.environ.get("EFFECT_BINDING_MODEL_ROOT", PACKAGE_ROOT / "models"))
+EXTERNAL_ROOT = Path(os.environ.get("EFFECT_BINDING_EXTERNAL_ROOT", PACKAGE_ROOT / "external"))
+PI_DETECTOR_MODEL_PATH = MODEL_ROOT / "protectai_deberta-v3-base-prompt-injection-v2"
+EXTERNAL_PHASE5_RUN_DIR = Path(os.environ.get("EFFECT_BINDING_PHASE5_RUN_DIR", PACKAGE_ROOT / "runs/tool_effect_fragmentation_phase5"))
@@ L499
             "local_live_available": env["e75_venv_agentdojo_importable"]
-            and Path("/data/CSK/causal-agent-safety-research/models/protectai_deberta-v3-base-prompt-injection-v2").exists(),
+            and PI_DETECTOR_MODEL_PATH.exists(),
@@ L661-664
-        "external_ipiguard_repo_present": Path("/data/CSK/causal-agent-safety-research/external/systems/ipiguard").exists(),
-        "external_camel_repo_present": Path("/data/CSK/causal-agent-safety-research/external/systems/camel").exists(),
-        "external_toolsafe_repo_present": Path("/data/CSK/causal-agent-safety-research/external/systems/toolsafe").exists(),
-        "local_pi_detector_model_present": Path("/data/CSK/causal-agent-safety-research/models/protectai_deberta-v3-base-prompt-injection-v2").exists(),
+        "external_ipiguard_repo_present": (EXTERNAL_ROOT / "systems/ipiguard").exists(),
+        "external_camel_repo_present": (EXTERNAL_ROOT / "systems/camel").exists(),
+        "external_toolsafe_repo_present": (EXTERNAL_ROOT / "systems/toolsafe").exists(),
+        "local_pi_detector_model_present": PI_DETECTOR_MODEL_PATH.exists(),
@@ L1019-1021
     base_model_candidates = [
-        Path("/data/CSK/causal-agent-safety-research/models/mistralai/Mistral-7B-v0.1"),
-        Path("/data/CSK/causal-agent-safety-research/models/Mistral-7B-v0.1"),
-        Path("/data/CSK/causal-agent-safety-research/.hf_cache/hub/models--mistralai--Mistral-7B-v0.1"),
+        MODEL_ROOT / "mistralai/Mistral-7B-v0.1",
+        MODEL_ROOT / "Mistral-7B-v0.1",
+        Path(os.environ.get("EFFECT_BINDING_HF_CACHE", Path.home() / ".cache/huggingface/hub")) / "models--mistralai--Mistral-7B-v0.1",
@@ L2617
-                "HF_HOME": "/data/CSK/causal-agent-safety-research/.hf_cache",
+                "HF_HOME": str(os.environ.get("EFFECT_BINDING_HF_CACHE", Path.home() / ".cache/huggingface/hub")),
```

**D4. 其余 A1/A2/A3 文件**：按 §2.3 模板 T1–T8 逐点替换，文件×行号映射见 §1 清单表（同一文件内多处按模板批量替换，无每文件独有语义差异）。

---

## 3. v17 禁改标注与执行顺序

### 3.1 🔴 红区：v17 完成前绝对禁改

| 文件 | 泄漏行 | 原因 |
|---|---|---|
| `experiments/intent-bound-runtime-guard/scripts/effect-difference-runtime-guard/run-recovery-normalization-qwen32.py` | 24 (MODEL)、122 (PY) | **v17 runner 正在运行**（PID 578021），运行时读取这些常量 |
| `experiments/security-analysis-ablation-and-overhead/scripts/strict-atom-representation-attribution/build-protocol.py` | 241 | v17 finalizer 成功后自动执行 `build-protocol.py --freeze`（v17_finalizer_watch.sh L49-51），L241 写入 protocol.json 的 model 字段；改动会导致冻结产物与已跑实验不一致 |
| `v17_finalizer_watch.sh` | 5 (ROOT) | 正在轮询的监控进程（PID 751876）持有该文件 |

### 3.2 🟠 保守区：v17 协议链相关（建议 v17 冻结后再改）

- `run-plan-normalization-qwen32-full.py:92`、`run-qwen32-context-repair.py:166`、`finalize-plan-normalization-qwen32-{full,pilot}.py`、`analyze-plan-normalization-pilot.py`：同属 effect-difference-runtime-guard 协议链，虽然当前未被 v17 执行，但协议 §2.3 要求"不得改协议状态"，保守起见 v17 冻结后一并处理。

### 3.3 🟢 绿区：可立即安全修改（v17 无依赖）

- A1 全部 11 文件（`shared/compatibility/scripts/`）
- A2 全部 12 文件（`experiments/*/source/`）
- A3-5、A3-6（runtime-mechanism-ablation）
- A4 `evaluation/real_model_common.py`
- B 类数据/结果文件处置（排除或清洗由打包脚本完成，非源码补丁）

### 3.4 建议执行顺序（v17 完成后）

1. **v17 冻结确认**（`v17_finalizer_watch.log` 尾部 finalizer exit=0 + freeze exit=0 + protocol.json frozen）——前置条件
2. **绿区补丁先行**（可立即实施）：A4 real_model_common.py → A1 scripts/ → A2 source/ → A3-5/6
3. **红区补丁**：v17 冻结后，先补 run-recovery-normalization-qwen32.py → 再补 build-protocol.py（需同步改 strict_atom_representation_attribution_protocol 中引用的路径说明）
4. 每文件补丁后 `python -m py_compile` 验证语法；脚本级验证以 `--help`/`--mode status` 冒烟
5. 补丁后全量复扫（复用打包脚本的泄漏复检步骤）

### 3.5 行为变更提示（需用户确认）

- `EFFECT_BINDING_MODEL_ROOT` 默认值从 `R/models` 改为**包内相对 `./models`**：补丁应用后，本机跑复现前必须 `export EFFECT_BINDING_MODEL_ROOT=/data/CSK/.../models`（或建符号链接），否则脚本报 FileNotFoundError。这是匿名化的**有意行为**，需在包 README 与复现指南中说明。
- `MODEL_BYTES`/`MODEL_SHA256` 校验保留（内容不变，非路径）。
- run_e75.py 的 `external_*_repo_present` 等环境诊断字段在匿名环境下将如实显示 false——不影响论文主张（这些字段仅用于运行诊断，manifest 引用的结果文件已生成）。

---

## 4. 与既有基础设施的关系

- `real_model_common.py` 的 `resolve_model_path()` 已支持 env 优先解析，本次补丁不改变其签名，只移除 `MODEL_ROOT` 的硬编码 fallback。
- `shared/compatibility/code/scripts/build_mainline_tool_effect_binding_package.py`（旧论文材料打包器）与 `build_e58_consolidated_package.py` 内嵌 `/data/CSK|/home/user|sk-...` 扫描正则：打包脚本对这些文件白名单化或排除，避免复检误报（见打包脚本 §2.3）。
- `paper/current-usenix/artifact/build_manifest.py` 为 manifest.json/checksums.sha256 生成器，打包脚本在其上追加"全量泄漏复检 + 文件清单"，不重复实现。

---

## 5. 汇总统计

| 分类 | 文件数 | 泄漏处数 |
|---|---|---|
| A1 scripts/（进包复现脚本） | 11 | 22 |
| A2 experiments/*/source/（进包实验源码） | 12 | 27 |
| A3 experiments/*/scripts/（进包实验脚本） | 6 | 7（含 3 处 v17 禁改/保守区） |
| A4 evaluation/ | 1 | 1 |
| A5 打包脚本正则（进包候选，建议排除） | 2 | 2 |
| **A 类合计（源码，需补丁）** | **32** | **59（其中 2 处为扫描器正则非泄漏）** |
| B 类（数据/结果/状态，排除或清洗） | ~90 | ~16,300 行命中 |
| C 类（复核干净） | — | 0 |

---

## 6. 附录

### 6.1 打包脚本使用说明（README 段落草稿）

> 配套脚本：`shared/workspace-management/pack_anonymous_artifact.py`（仅编写，未执行）

```markdown
## Packaging the anonymous artifact

`shared/workspace-management/pack_anonymous_artifact.py` builds the
anonymous USENIX artifact tarball from the current workspace. It never
executes experiments and never launches GPUs.

Usage (from the package root):

    python3 shared/workspace-management/pack_anonymous_artifact.py \
        --out /tmp/anonymous_artifact.tar.gz \
        --paper-root paper/current-usenix \
        [--staging /tmp/artifact_staging] \
        [--keep-staging] \
        [--skip-scan] [--skip-checksums]

What the script does, in order:
1.  Copies the tree into a staging directory, resolving every symlink to
    its real directory (root-level `scripts/`, `code/`, `evaluation/`,
    `results/`, ... -> `shared/compatibility/*`), so the tarball contains
    no dangling or absolute links.
2.  Applies the explicit exclusion list (git history, caches, `runs/`,
    IDE/config dot-directories, 23 internal working documents, LaTeX build
    intermediates, host-path state files, `v17_finalizer_watch.*`).
3.  Rewrites the packaged `paper/current-usenix/README.md` from the
    anonymized draft (`README.artifact.md`).
4.  Runs the leak re-scan over every packaged file: `/data/CSK`,
    `/home/user`, `sk-` credential patterns, `skchen17`, and e-mail
    patterns; the scan fails the build on any hit.
5.  Generates `checksums.sha256` for every packaged file and a
    `manifest.json` file listing path, size, sha256, and role.
6.  Creates a deterministic `.tar.gz` (sorted entries, no mtimes/owners
    recorded for reproducibility of the archive itself).

Exit code 0 means the package passed the full scan and is ready for the
remaining release gates (clean-environment reproduction and the anonymous
stable URL). Run it only after the v17 experiment chain has finished and
the parameterization patch plan has been applied and reviewed.
```

### 6.2 进包版 README 改写草稿

见 `README.artifact.md`（本目录，进包时以该文件内容替换包内 `README.md`）。
