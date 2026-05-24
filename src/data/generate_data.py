"""
Phase 1: 生成 agent 工具调用场景数据集。

每个样本包含:
  - scenario_text: 描述工具调用上下文的自然语言文本
  - tool_name: 调用的工具
  - state: 调用前的状态快照 (dict)
  - effects: 实际产生的因果效果 (multi-label binary)
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── 效果定义 ──────────────────────────────────────────────
EFFECTS = [
    "command_executed", "file_written", "file_deleted",
    "file_content_read", "message_sent", "network_egress",
    "subagent_spawned", "content_fetched", "search_performed",
    "memory_updated", "tool_error",
]

# ── 工具定义 (统一使用 {data} 占位符) ─────────────────────
TOOL_DEFS = {
    "terminal": {
        "inherent": {"command_executed", "network_egress"},
        "templates": [
            "在 {state_desc} 的环境中，agent 调用了 terminal 执行命令 `{data}`。",
            "The agent ran a shell command `{data}` in a {state_desc} workspace.",
            "A terminal command `{data}` was executed in {state_desc} context.",
        ],
        "data": [
            "ls -la", "git status", "pip install numpy", "rm -rf tmp/",
            "python train.py", "docker build -t app .", "cat config.yaml",
            "echo $HOME", "curl https://api.example.com/data",
            "chmod +x script.sh", "sudo systemctl restart nginx",
            "find . -name '*.py' | xargs grep TODO",
            "scp file.txt user@remote:/path/",
        ],
    },
    "write_file": {
        "inherent": {"file_written"},
        "templates": [
            "在 {state_desc} 的项目中，agent 向文件 `{data}` 写入了内容。",
            "The agent wrote content to `{data}` in a {state_desc} project.",
            "A file `{data}` was created/updated in {state_desc} workspace.",
        ],
        "data": [
            "src/main.py", "README.md", "config/settings.json",
            "tests/test_core.py", "docs/api.md",
            ".env", "requirements.txt", "Dockerfile",
            "scripts/deploy.sh", "data/raw/sample.csv",
        ],
    },
    "read_file": {
        "inherent": {"file_content_read"},
        "templates": [
            "在 {state_desc} 的环境中，agent 读取了 `{data}` 的内容。",
            "The agent read the contents of `{data}` in a {state_desc} project.",
            "File `{data}` was examined in {state_desc} context.",
        ],
        "data": [
            "src/main.py", "README.md", "config/settings.json",
            "logs/error.log", "docs/architecture.md",
            ".gitignore", "package.json", "pyproject.toml",
            "data/processed/result.csv", "tests/fixtures/input.json",
        ],
    },
    "delete_file": {
        "inherent": {"file_deleted"},
        "templates": [
            "在 {state_desc} 的项目中，agent 删除了 `{data}`。",
            "The agent deleted the file `{data}` from a {state_desc} workspace.",
            "A file `{data}` was removed in {state_desc} context.",
        ],
        "data": [
            "tmp/cache.dat", "build/output.o", "logs/old.log",
            "backup/deprecated.tar.gz", ".venv/lib/old_package",
            "node_modules/.cache", "__pycache__/module.pyc",
            "dist/old_release.zip", "test/fixtures/stale.json",
            "temp/scratch.txt",
        ],
    },
    "send_message": {
        "inherent": {"message_sent", "network_egress"},
        "templates": [
            "在 {state_desc} 的上下文中，agent 向 {data} 发送了一条消息。",
            "The agent sent a message to {data} in {state_desc} environment.",
            "A message was dispatched to {data} from {state_desc} context.",
        ],
        "data": [
            "用户 Alex", "团队 Slack 频道", "Discord 服务器",
            "Telegram 群组", "邮箱 admin@example.com",
            "Signal 联系人 Bob", "WhatsApp 群聊",
        ],
    },
    "web_fetch": {
        "inherent": {"content_fetched", "network_egress"},
        "templates": [
            "在 {state_desc} 的环境中，agent 从 `{data}` 获取了内容。",
            "The agent fetched content from `{data}` in a {state_desc} context.",
            "A web resource at `{data}` was retrieved in {state_desc} workspace.",
        ],
        "data": [
            "https://api.github.com/repos/numpy/numpy",
            "https://docs.python.org/3/library/asyncio.html",
            "https://arxiv.org/abs/2305.00050",
            "https://news.ycombinator.com",
            "https://pypi.org/pypi/torch/2.0.0/json",
            "https://raw.githubusercontent.com/org/repo/main/data.csv",
        ],
    },
    "web_search": {
        "inherent": {"search_performed", "network_egress"},
        "templates": [
            "在 {state_desc} 的环境中，agent 搜索了 `{data}`。",
            "The agent performed a web search for `{data}` in {state_desc} context.",
            "A search query `{data}` was executed in {state_desc} workspace.",
        ],
        "data": [
            "Python asyncio best practices",
            "latest research on causal inference 2025",
            "how to fix segmentation fault in Docker",
            "Rust vs Go performance comparison 2024",
            "SOTA image classification 2025",
            "Anthropic Claude API rate limits",
        ],
    },
    "delegate": {
        "inherent": {"subagent_spawned"},
        "templates": [
            "在 {state_desc} 的环境中，agent 将任务委派给了子代理：`{data}`。",
            "The agent delegated the task `{data}` to a subagent in {state_desc} context.",
            "A subagent was spawned to handle `{data}` in {state_desc} workspace.",
        ],
        "data": [
            "搜索相关论文并生成文献综述",
            "重构 src/utils.py 的异常处理逻辑",
            "为 REST API 生成 OpenAPI 规范文档",
            "审计代码库中的安全漏洞",
            "构建前端 React 组件的测试套件",
            "分析日志文件中的异常模式",
        ],
    },
    "memory": {
        "inherent": {"memory_updated"},
        "templates": [
            "在 {state_desc} 的会话中，agent 更新了持久化记忆：`{data}`。",
            "The agent updated persistent memory with `{data}` in {state_desc} context.",
            "Memory was modified with `{data}` in {state_desc} session.",
        ],
        "data": [
            "用户偏好 Python 3.11+ 和 type hints",
            "项目使用 PostgreSQL 作为主数据库",
            "Alex 是项目经理，联系邮箱 alex@example.com",
            "部署环境是 Kubernetes 1.28",
            "CI/CD 使用 GitHub Actions",
            "代码风格遵循 Black + isort",
        ],
    },
}

# ── 状态描述 ──────────────────────────────────────────────
STATE_DESCRIPTIONS = {
    "small_dev_safe": "小型开发项目, 安全模式",
    "small_dev_unsafe": "小型开发项目, 非安全模式",
    "small_prod_safe": "小型生产项目, 安全模式",
    "medium_dev_safe": "中型开发项目, 安全模式",
    "medium_dev_unsafe": "中型开发项目, 非安全模式",
    "medium_prod_safe": "中型生产项目, 安全模式",
    "large_dev_safe": "大型开发项目, 安全模式",
    "large_dev_unsafe": "大型开发项目, 非安全模式",
    "large_prod_safe": "大型生产项目, 安全模式",
    "large_prod_unsafe": "大型生产项目, 非安全模式",
    "small_unknown": "小型项目, 环境未知",
    "medium_unknown": "中型项目, 环境未知",
}


@dataclass
class Scenario:
    tool_name: str
    scenario_text: str
    state: dict[str, Any]
    effects: dict[str, int]


def generate_template_data(n_per_tool: int = 100, seed: int = 42) -> list[Scenario]:
    """从规则模板生成场景数据。"""
    random.seed(seed)
    scenarios: list[Scenario] = []

    for tool_name, tdef in TOOL_DEFS.items():
        inherent = tdef["inherent"]

        for _ in range(n_per_tool):
            # 随机状态上下文
            state_key = random.choice(list(STATE_DESCRIPTIONS.keys()))
            state_desc = STATE_DESCRIPTIONS[state_key]

            # 解析状态数值
            state = {}
            if "small" in state_key:
                state["file_count"] = random.randint(0, 5)
            elif "medium" in state_key:
                state["file_count"] = random.randint(6, 50)
            else:
                state["file_count"] = random.randint(51, 500)

            state["safe_mode"] = "safe" in state_key
            state["production"] = "prod" in state_key

            # 生成文本
            template = random.choice(tdef["templates"])
            data_val = random.choice(tdef["data"])
            scenario_text = template.format(state_desc=state_desc, data=data_val)

            # 确定效果
            effects = {e: 0 for e in EFFECTS}
            for e in inherent:
                effects[e] = 1

            # 5% 概率出错
            if random.random() < 0.05:
                effects["tool_error"] = 1

            # 状态依赖: 大型项目 + 非安全模式 → 额外风险
            if not state["safe_mode"] and state["file_count"] > 50:
                if tool_name in ("terminal", "delete_file") and random.random() < 0.15:
                    effects["file_deleted"] = 1

            if state["production"] and tool_name == "terminal":
                if random.random() < 0.1:
                    effects["tool_error"] = 1  # 生产环境命令更容易出错

            scenarios.append(Scenario(
                tool_name=tool_name,
                scenario_text=scenario_text,
                state=state,
                effects=effects,
            ))

    return scenarios


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generating template data (N=~900)...")
    scenarios = generate_template_data(n_per_tool=100)

    data = []
    for s in scenarios:
        data.append({
            "tool_name": s.tool_name,
            "scenario_text": s.scenario_text,
            "state": s.state,
            "effects": s.effects,
        })

    out_path = out_dir / "scenarios_template.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Saved {len(data)} scenarios to {out_path}")

    # 效果分布
    effect_counts = {e: 0 for e in EFFECTS}
    tool_counts = {}
    for item in data:
        for e, v in item["effects"].items():
            if v:
                effect_counts[e] += 1
        t = item["tool_name"]
        tool_counts[t] = tool_counts.get(t, 0) + 1

    print("\nEffect distribution:")
    for e, c in sorted(effect_counts.items(), key=lambda x: -x[1]):
        pct = c / len(data) * 100
        print(f"  {e:25s}: {c:4d} ({pct:5.1f}%)")

    print(f"\nTool distribution:")
    for t, c in sorted(tool_counts.items()):
        print(f"  {t:15s}: {c:4d}")

    print(f"\nTotal: {len(data)} scenarios")


if __name__ == "__main__":
    main()
