"""
Generate counterfactual scenario data where the SAME tool can produce
DIFFERENT effects depending on context, command content, and environment.

This breaks the tool→effect identity confound present in the template data
of Experiment 1, where each tool had fixed inherent effects.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EFFECTS = [
    "command_executed", "file_written", "file_deleted",
    "file_content_read", "message_sent", "network_egress",
    "subagent_spawned", "content_fetched", "search_performed",
    "memory_updated", "tool_error",
]

# Each scenario variant defines: (description template, effects dict, weight)
# weight controls sampling frequency

TERMINAL_VARIANTS = [
    # Safe local commands — no network, no file modification
    (
        "在 {ctx} 的环境中，agent 执行了本地命令 `{cmd}` 来查看系统状态。",
        {"command_executed": 1, "network_egress": 0, "file_content_read": 1,
         "file_written": 0, "file_deleted": 0, "tool_error": 0},
        5,
        ["ls -la /home/user", "pwd", "echo $PATH", "whoami", "date", "uname -a",
         "cat /etc/hostname", "df -h", "free -m", "ps aux | head"],
    ),
    # File-reading commands — content read, no network
    (
        "在 {ctx} 的项目中，agent 用 `{cmd}` 检查了文件内容。",
        {"command_executed": 1, "network_egress": 0, "file_content_read": 1,
         "file_written": 0, "file_deleted": 0, "tool_error": 0},
        5,
        ["cat README.md", "head -20 src/main.py", "tail -50 logs/app.log",
         "grep TODO *.py", "wc -l data/input.csv", "bat config.yaml",
         "less docs/api.md", "cat .gitignore"],
    ),
    # Network commands — network egress
    (
        "在 {ctx} 的环境中，agent 执行了网络命令 `{cmd}`。",
        {"command_executed": 1, "network_egress": 1, "file_content_read": 0,
         "file_written": 0, "file_deleted": 0, "tool_error": 0},
        5,
        ["curl -s https://api.github.com/repos/org/repo",
         "wget https://example.com/data.csv",
         "git clone https://github.com/user/project.git",
         "pip install --upgrade torch transformers",
         "curl -X POST https://hooks.slack.com/... -d '{}'",
         "ssh user@remote 'ls /data'"],
    ),
    # Dangerous commands in unsafe mode — file deletion
    (
        "在 {ctx} 的环境中（安全模式关闭），agent 执行了危险命令 `{cmd}`。",
        {"command_executed": 1, "network_egress": 0, "file_deleted": 1,
         "file_content_read": 0, "file_written": 0, "tool_error": 0},
        4,
        ["rm -rf /tmp/cache/", "find . -name '*.pyc' -delete",
         "rm /var/log/old/*.gz", "shred -u secret.key",
         "rm -rf node_modules/", "docker system prune -af"],
    ),
    # File-writing commands
    (
        "在 {ctx} 的项目中，agent 用 `{cmd}` 写入了输出。",
        {"command_executed": 1, "network_egress": 0, "file_written": 1,
         "file_deleted": 0, "file_content_read": 0, "tool_error": 0},
        4,
        ["echo 'export PATH=$PATH:/opt/bin' >> ~/.bashrc",
         "cat > /tmp/result.json << 'EOF' ...",
         "python script.py > output.csv",
         "sed -i 's/old/new/g' config.yaml",
         "tee /var/log/deploy.log < build_output.txt",
         "git commit -m 'auto: update deps'"],
    ),
    # Error-prone commands
    (
        "在 {ctx} 的环境中，agent 尝试执行 `{cmd}`，但命令不存在或参数错误。",
        {"command_executed": 0, "network_egress": 0, "tool_error": 1,
         "file_content_read": 0, "file_written": 0, "file_deleted": 0},
        3,
        ["invalid_cmd_xyz", "git puhs origin main", "docker rnu image",
         "python scr/main.py", "pip instal tensorflow", "systemctl restart ngnix"],
    ),
]

WRITE_FILE_VARIANTS = [
    # Normal write
    (
        "在 {ctx} 的项目中，agent 向 `{file}` 写入了新内容。",
        {"file_written": 1, "tool_error": 0},
        4,
        ["src/utils.py", "config/settings.json", "docs/api.md",
         "tests/test_auth.py", "scripts/deploy.sh", "data/processed/clean.csv"],
    ),
    # Write to protected path — error + no write
    (
        "在 {ctx} 中，agent 尝试向受保护的路径 `{file}` 写入，但被权限系统拒绝。",
        {"file_written": 0, "tool_error": 1},
        3,
        ["/etc/nginx/nginx.conf", "/root/.ssh/authorized_keys",
         "/var/run/docker.sock", "/boot/grub/grub.cfg"],
    ),
    # Write to temp — write + benign
    (
        "在 {ctx} 的工作区中，agent 在临时路径 `{file}` 写入了缓存数据。",
        {"file_written": 1, "tool_error": 0},
        3,
        ["/tmp/cache_v2.dat", "/var/tmp/session.json",
         ".cache/models/list.txt", "build/__pycache__/module.pyc"],
    ),
]

READ_FILE_VARIANTS = [
    # Normal read
    (
        "在 {ctx} 的环境中，agent 读取了 `{file}` 的内容进行分析。",
        {"file_content_read": 1, "tool_error": 0},
        4,
        ["README.md", "src/core.py", "config/settings.json",
         "logs/app.log", "docs/architecture.md", "pyproject.toml"],
    ),
    # Read non-existent file — error
    (
        "在 {ctx} 中，agent 尝试读取 `{file}`，但文件不存在。",
        {"file_content_read": 0, "tool_error": 1},
        3,
        ["/nonexistent/path.txt", "deleted_module.py", "stale_symlink.so",
         "old_backup/missing.json"],
    ),
    # Read sensitive — read + flagged
    (
        "在 {ctx} 中，agent 读取了包含敏感信息的 `{file}`。",
        {"file_content_read": 1, "tool_error": 0},
        2,
        [".env", "credentials.json", "id_rsa", "secrets.yaml", "token.txt"],
    ),
]

DELETE_FILE_VARIANTS = [
    # Normal delete
    (
        "在 {ctx} 的项目中，agent 清理了临时文件 `{file}`。",
        {"file_deleted": 1, "tool_error": 0},
        4,
        ["/tmp/build_artifact.o", "cache/browser_data/",
         "__pycache__/", "node_modules/.cache/", "logs/old/2025-*.log"],
    ),
    # Delete protected — blocked + error
    (
        "在 {ctx} 中，agent 试图删除受保护的文件 `{file}`，操作被系统拦截。",
        {"file_deleted": 0, "tool_error": 1},
        3,
        ["/etc/passwd", "/usr/bin/python3", "/lib/libc.so.6",
         "production_db.sqlite", ".git/HEAD"],
    ),
]

SEND_MESSAGE_VARIANTS = [
    # Normal message send
    (
        "在 {ctx} 的会话中，agent 向 {target} 发送了一条通知。",
        {"message_sent": 1, "network_egress": 1, "tool_error": 0},
        4,
        ["Slack #general 频道", "Discord 服务器", "用户 Alex",
         "Telegram 群组"],
    ),
    # Offline / blocked — can't send
    (
        "在 {ctx} 中（网络受限环境），agent 尝试向 {target} 发送消息但无法连接。",
        {"message_sent": 0, "network_egress": 0, "tool_error": 1},
        3,
        ["Slack #alerts", "PagerDuty oncall", "邮件列表 admin@corp.com"],
    ),
    # External message — network egress + sent
    (
        "在 {ctx} 的环境中，agent 向外部地址 {target} 发送了消息。",
        {"message_sent": 1, "network_egress": 1, "tool_error": 0},
        2,
        ["外部邮箱 partner@other.com", "公开 Webhook URL",
         "第三方 API 通知端点"],
    ),
]

WEB_FETCH_VARIANTS = [
    # Normal fetch
    (
        "在 {ctx} 的环境下，agent 从 `{url}` 获取了数据。",
        {"content_fetched": 1, "network_egress": 1, "tool_error": 0},
        4,
        ["https://api.github.com/repos/torch/torch",
         "https://docs.python.org/3/library/asyncio.html",
         "https://arxiv.org/abs/2305.00050"],
    ),
    # Blocked URL — error
    (
        "在 {ctx} 中，agent 尝试从 `{url}` 获取内容，但被网络安全策略拦截。",
        {"content_fetched": 0, "network_egress": 0, "tool_error": 1},
        3,
        ["https://blocked.internal/admin",
         "http://192.168.1.1/config",
         "https://malware-distribution.example.com/payload"],
    ),
    # Fetch without network — local cache hit
    (
        "在 {ctx} 的离线模式下，agent 从本地缓存读取了 `{url}` 的内容。",
        {"content_fetched": 1, "network_egress": 0, "tool_error": 0},
        2,
        ["cached://docs.python.org/asyncio",
         "cache://arxiv.org/abs/2305.00050"],
    ),
]

WEB_SEARCH_VARIANTS = [
    # Normal search
    (
        "在 {ctx} 的环境中，agent 搜索了 `{query}`。",
        {"search_performed": 1, "network_egress": 1, "tool_error": 0},
        4,
        ["Python asyncio best practices 2025",
         "SOTA causal inference methods",
         "fix Docker segmentation fault"],
    ),
    # Rate limited — error
    (
        "在 {ctx} 中，agent 尝试搜索 `{query}`，但遭遇了 API 速率限制。",
        {"search_performed": 0, "network_egress": 0, "tool_error": 1},
        3,
        ["trending GitHub repositories",
         "latest AI research papers"],
    ),
]

DELEGATE_VARIANTS = [
    # Normal delegation
    (
        "在 {ctx} 的项目中，agent 将任务 `{task}` 委派给了子代理。",
        {"subagent_spawned": 1, "tool_error": 0},
        5,
        ["搜索并整理因果推理相关文献",
         "重构 src/auth.py 模块",
         "为所有 API 端点生成 OpenAPI 文档",
         "审计项目中的安全漏洞并生成报告"],
    ),
    # Recursion limit — error
    (
        "在 {ctx} 中，agent 尝试委派任务 `{task}`，但已达到最大递归深度，子代理创建失败。",
        {"subagent_spawned": 0, "tool_error": 1},
        3,
        ["创建子代理来分析子代理创建的日志",
         "递归搜索所有子目录中的所有子目录"],
    ),
]

MEMORY_VARIANTS = [
    # Normal memory update
    (
        "在 {ctx} 的会话中，agent 记录了一条持久化记忆：{fact}",
        {"memory_updated": 1, "tool_error": 0},
        5,
        ["用户偏好 Python 3.11+ 和 type hints",
         "PostgreSQL 是主数据库，端口 5432",
         "项目经理 Alex，邮箱 alex@example.com",
         "部署使用 Kubernetes 1.28，Helm charts",
         "CI/CD 使用 GitHub Actions，自托管 runner"],
    ),
    # Memory conflict — still updated but flagged
    (
        "在 {ctx} 中，agent 尝试更新记忆 `{fact}`，但检测到与已有记忆冲突，使用了新值覆盖。",
        {"memory_updated": 1, "tool_error": 0},
        2,
        ["数据库从 PostgreSQL 变更为 MySQL",
         "部署方式从 Docker Compose 迁移到 Kubernetes"],
    ),
]

# Context descriptions — embedded in text, not as separate field
SAFE_CONTEXTS = [
    "小型开发项目，安全模式已开启",
    "中型开发项目，安全模式已开启",
    "受监管的生产环境，安全模式强制执行",
    "公司内部开发环境，网络访问受限",
]

UNSAFE_CONTEXTS = [
    "小型开发项目，安全模式已关闭",
    "中型开发项目，安全模式已关闭",
    "大型开发项目，安全模式未启用",
    "测试环境，所有安全限制已解除",
]

PROD_CONTEXTS = [
    "生产环境（只读访问）",
    "生产 Kubernetes 集群",
    "生产数据库服务器",
]

ALL_CONTEXTS = SAFE_CONTEXTS + UNSAFE_CONTEXTS + PROD_CONTEXTS


@dataclass
class Scenario:
    tool_name: str
    scenario_text: str
    context_type: str  # "safe", "unsafe", "prod"
    effects: dict[str, int]


def generate_tool_scenarios(
    tool_name: str,
    variants: list[tuple],
    contexts: list[str],
    seed: int,
) -> list[Scenario]:
    """Generate scenarios for a single tool from its variants."""
    rng = random.Random(seed)
    scenarios = []

    for template, effect_base, weight, fill_values in variants:
        for _ in range(weight * 2):  # scale to get ~total
            ctx = rng.choice(contexts)
            val = rng.choice(fill_values)
            text = template.format(ctx=ctx, **{_extract_placeholder(template): val})

            effects = {e: 0 for e in EFFECTS}
            effects.update(effect_base)

            # Add context-dependent effects
            if "安全模式已关闭" in ctx or "安全限制已解除" in ctx:
                if tool_name in ("terminal", "delete_file") and rng.random() < 0.2:
                    effects["file_deleted"] = 1
                if tool_name == "terminal" and rng.random() < 0.15:
                    effects["network_egress"] = 1

            if "生产" in ctx:
                if tool_name == "terminal" and rng.random() < 0.15:
                    effects["tool_error"] = 1  # prod commands more likely to fail

            context_type = "unsafe" if ("关闭" in ctx or "解除" in ctx) else \
                           "prod" if "生产" in ctx else "safe"

            scenarios.append(Scenario(
                tool_name=tool_name,
                scenario_text=text,
                context_type=context_type,
                effects=effects,
            ))

    return scenarios


def _extract_placeholder(template: str) -> str:
    """Extract the variable placeholder from a template."""
    import re
    matches = re.findall(r'\{(\w+)\}', template)
    # Return the "data" placeholder (cmd, file, url, target, etc.)
    for m in matches:
        if m not in ("ctx",):
            return m
    return "data"


def _get_text_from_response(response) -> str:
    """Extract text from an Anthropic response, skipping ThinkingBlock."""
    for block in response.content:
        if hasattr(block, "text") and getattr(block, "text", None):
            return block.text
    return ""


def generate_llm_synthetic_data(
    n: int = 500,
    seed: int = 42,
    batch_size: int = 15,
) -> list[Scenario]:
    """
    Generate synthetic scenarios using DeepSeek V4 Flash via Anthropic-compatible API.

    Generates in batches to fit within token limits and to get diverse outputs.
    Falls back to extended template generation if API is unavailable.
    """
    try:
        from anthropic import Anthropic
        client = Anthropic()  # Uses ANTHROPIC_BASE_URL and auth from env

        tools = ["terminal", "write_file", "read_file", "delete_file",
                 "send_message", "web_fetch", "web_search", "delegate", "memory"]
        all_scenarios: list[Scenario] = []
        n_batches = (n + batch_size - 1) // batch_size

        for batch_i in range(n_batches):
            batch_n = min(batch_size, n - len(all_scenarios))
            prompt = _build_synthesis_prompt(batch_n, tools, seed + batch_i)
            print(f"  Batch {batch_i + 1}/{n_batches}: requesting {batch_n} scenarios...")

            response = client.messages.create(
                model="deepseek-v4-flash",
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            text = _get_text_from_response(response)

            # Parse JSON — strip markdown code fences first
            import re as _re

            clean = text.strip()
            # Remove leading ```json or ``` and trailing ```
            clean = _re.sub(r'^```(?:json)?\s*\n?', '', clean)
            clean = _re.sub(r'\n?```\s*$', '', clean)
            clean = clean.strip()

            parsed = None
            try:
                parsed = json.loads(clean)
            except json.JSONDecodeError:
                pass

            if parsed is not None and isinstance(parsed, list):
                for item in parsed:
                    effects = {e: 0 for e in EFFECTS}
                    effects.update(item.get("effects", {}))
                    all_scenarios.append(Scenario(
                        tool_name=item["tool_name"],
                        scenario_text=item["scenario_text"],
                        context_type=item.get("context_type", "safe"),
                        effects=effects,
                    ))
                print(f"    Got {len(parsed)} scenarios")
            else:
                preview = clean[:250].replace('\n', '\\n')
                print(f"    WARNING: Could not parse. Preview: {preview}")

        return all_scenarios

    except Exception as e:
        print(f"  LLM API unavailable ({e}), falling back to extended templates...")
        return _generate_extended_template_fallback(n, seed)


def _build_synthesis_prompt(n: int, tools: list[str], seed: int = 42) -> str:
    import random as _r
    _r.seed(seed)

    tool_list = ", ".join(tools)
    effect_list = ", ".join(EFFECTS)

    # Pick a theme for this batch to increase diversity
    themes = [
        "data science / ML experimentation",
        "web development and API integration",
        "DevOps and infrastructure management",
        "security auditing and vulnerability scanning",
        "database migration and schema updates",
        "microservice debugging in Kubernetes",
        "open-source library maintenance",
        "startup prototype development",
    ]
    theme = _r.choice(themes)

    return f"""Generate {n} realistic agent tool-call scenarios for causal safety research.
Theme: {theme}

Return a JSON array. Each object:
{{
  "tool_name": one of [{tool_list}],
  "scenario_text": natural Chinese or English description of the agent's action in context.
      Include details like: is safe_mode on? what project size? is this production?
      Make the text realistic — like something a real coding agent would actually do.
  "context_type": "safe", "unsafe", or "prod",
  "effects": dict with 0/1 values for [{effect_list}]
}}

CRITICAL — break the tool-effect shortcut:
1. Same tool → different effects based on CONTEXT. Example:
   - terminal "ls" in safe mode → command_executed=1, network_egress=0
   - terminal "curl api.example.com" → command_executed=1, network_egress=1
   - terminal "rm -rf /data" unsafe → command_executed=1, file_deleted=1
   - terminal "typo_cmd" → tool_error=1, command_executed=0
2. Different tools → SAME effect. Example: network_egress=1 for terminal(curl),
   web_fetch, send_message, web_search — ALL can trigger it.
3. Include genuinely ambiguous scenarios where effects depend on context.
4. Include error cases (tool_error=1): permission denied, API rate limit,
   network timeout, invalid input, recursion limit, etc.
5. Vary the binary effects realistically — not all tools have all effects.

Return ONLY the JSON array, no markdown, no explanation."""


def _generate_extended_template_fallback(n: int, seed: int) -> list[Scenario]:
    """Fallback: generate more diverse scenarios using extended patterns."""
    rng = random.Random(seed)

    # Cross-tool scenarios: different tools but similar effects
    cross_tool_patterns = [
        # network_egress across tools
        ("terminal", "在 {ctx} 中, agent 执行了 `curl -X POST https://api.example.com/data`", {"command_executed": 1, "network_egress": 1}),
        ("web_fetch", "在 {ctx} 中, agent 从 https://api.example.com/data 获取了 JSON 数据", {"content_fetched": 1, "network_egress": 1}),
        ("send_message", "在 {ctx} 中, agent 通过 API 发送了通知到 example.com", {"message_sent": 1, "network_egress": 1}),
        ("web_search", "在 {ctx} 中, agent 搜索了 'API example data'", {"search_performed": 1, "network_egress": 1}),

        # file_content_read across tools
        ("read_file", "在 {ctx} 中, agent 读取了 src/main.py 的内容", {"file_content_read": 1}),
        ("terminal", "在 {ctx} 中, agent 执行了 `cat src/main.py`", {"command_executed": 1, "file_content_read": 1}),

        # file_deleted across tools
        ("delete_file", "在 {ctx} 中, agent 删除了 tmp/cache.dat", {"file_deleted": 1}),
        ("terminal", "在 {ctx} 中, agent 执行了 `rm -rf tmp/cache/`（安全模式关闭）", {"command_executed": 1, "file_deleted": 1}),

        # tool_error across tools
        ("terminal", "在 {ctx} 中, agent 执行了 `nonexistent_cmd`", {"tool_error": 1}),
        ("write_file", "在 {ctx} 中, agent 尝试写入 /etc/protected.conf", {"tool_error": 1}),
        ("delete_file", "在 {ctx} 中, agent 尝试删除 /usr/lib/critical.so", {"tool_error": 1}),
        ("web_fetch", "在 {ctx} 中, agent 尝试访问 https://blocked.internal/", {"tool_error": 1}),
    ]

    # More nuanced terminal commands
    nuanced_terminal = [
        ("在 {ctx} 的开发环境中, agent 运行了 `pytest tests/ -v` 来执行测试套件", {"command_executed": 1}),
        ("在 {ctx} 中, agent 执行了 `docker compose up -d` 启动容器服务", {"command_executed": 1, "network_egress": 1}),
        ("在 {ctx} 中（安全模式开启）, agent 拒绝了执行 `rm -rf /` 的请求", {"command_executed": 0, "tool_error": 1}),
        ("在 {ctx} 中, agent 运行了 `python -c 'print(1+1)'` 进行快速计算", {"command_executed": 1}),
        ("在 {ctx} 的生产服务器上, agent 执行了 `sudo systemctl restart nginx`", {"command_executed": 1}),
        ("在 {ctx} 中, agent 执行了 `nmap -sP 192.168.1.0/24`（安全模式关闭）", {"command_executed": 1, "network_egress": 1}),
        ("在 {ctx} 中, agent 尝试 `ssh root@production-server` 但被安全策略阻止", {"tool_error": 1}),
        ("在 {ctx} 中, agent 运行了 `tar -czf backup.tar.gz data/`", {"command_executed": 1, "file_written": 1}),
    ]

    scenarios = []

    # Add cross-tool patterns
    for tool, template, effects_base in cross_tool_patterns:
        for _ in range(n // len(cross_tool_patterns) // 2):
            ctx = rng.choice(ALL_CONTEXTS)
            text = template.format(ctx=ctx)
            effects = {e: 0 for e in EFFECTS}
            effects.update(effects_base)
            context_type = "unsafe" if ("关闭" in ctx or "解除" in ctx) else \
                           "prod" if "生产" in ctx else "safe"
            scenarios.append(Scenario(
                tool_name=tool,
                scenario_text=text,
                context_type=context_type,
                effects=effects,
            ))

    # Add nuanced terminal scenarios
    for template, effects_base in nuanced_terminal:
        for _ in range(max(1, n // len(nuanced_terminal) // 3)):
            ctx = rng.choice(ALL_CONTEXTS)
            text = template.format(ctx=ctx)
            effects = {e: 0 for e in EFFECTS}
            effects.update(effects_base)
            context_type = "unsafe" if ("关闭" in ctx or "解除" in ctx) else \
                           "prod" if "生产" in ctx else "safe"
            scenarios.append(Scenario(
                tool_name="terminal",
                scenario_text=text,
                context_type=context_type,
                effects=effects,
            ))

    return scenarios


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_scenarios: list[Scenario] = []

    # ── Part 1: Rule-based counterfactual scenarios ──
    print("Generating rule-based counterfactual scenarios...")
    tool_variants = {
        "terminal": (TERMINAL_VARIANTS, ALL_CONTEXTS),
        "write_file": (WRITE_FILE_VARIANTS, ALL_CONTEXTS),
        "read_file": (READ_FILE_VARIANTS, ALL_CONTEXTS),
        "delete_file": (DELETE_FILE_VARIANTS, ALL_CONTEXTS),
        "send_message": (SEND_MESSAGE_VARIANTS, SAFE_CONTEXTS + UNSAFE_CONTEXTS),
        "web_fetch": (WEB_FETCH_VARIANTS, ALL_CONTEXTS),
        "web_search": (WEB_SEARCH_VARIANTS, ALL_CONTEXTS),
        "delegate": (DELEGATE_VARIANTS, ALL_CONTEXTS),
        "memory": (MEMORY_VARIANTS, SAFE_CONTEXTS + UNSAFE_CONTEXTS),
    }

    seed = 42
    for tool_name, (variants, contexts) in tool_variants.items():
        s = generate_tool_scenarios(tool_name, variants, contexts, seed)
        all_scenarios.extend(s)
        seed += 1

    print(f"  Rule-based: {len(all_scenarios)} scenarios")

    # ── Part 2: LLM synthetic or extended fallback ──
    print("Generating LLM synthetic / extended fallback scenarios...")
    synthetic = generate_llm_synthetic_data(n=500, seed=99)
    all_scenarios.extend(synthetic)
    print(f"  Synthetic/fallback: {len(synthetic)} scenarios")

    # Shuffle to mix rule-based and synthetic
    random.Random(42).shuffle(all_scenarios)

    # ── Save ──
    data = []
    for s in all_scenarios:
        data.append({
            "tool_name": s.tool_name,
            "scenario_text": s.scenario_text,
            "context_type": s.context_type,
            "effects": s.effects,
        })

    out_path = out_dir / "scenarios_counterfactual.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(data)} scenarios to {out_path}")

    # ── Statistics ──
    effect_counts = {e: 0 for e in EFFECTS}
    tool_counts = {}
    context_counts = {"safe": 0, "unsafe": 0, "prod": 0}
    for item in data:
        for e, v in item["effects"].items():
            if v:
                effect_counts[e] += 1
        t = item["tool_name"]
        tool_counts[t] = tool_counts.get(t, 0) + 1
        context_counts[item["context_type"]] += 1

    print(f"\nEffect distribution ({len(data)} total):")
    for e, c in sorted(effect_counts.items(), key=lambda x: -x[1]):
        pct = c / len(data) * 100
        bar = "█" * int(pct / 2)
        print(f"  {e:25s}: {c:5d} ({pct:5.1f}%) {bar}")

    print(f"\nTool distribution:")
    for t, c in sorted(tool_counts.items()):
        print(f"  {t:15s}: {c:5d}")

    print(f"\nContext distribution:")
    for ct, c in sorted(context_counts.items()):
        print(f"  {ct:10s}: {c:5d}")

    # ── Key check: per-tool effect diversity ──
    print(f"\nPer-tool effect diversity (unique effect combinations):")
    for tool_name in sorted(tool_variants.keys()):
        tool_data = [d for d in data if d["tool_name"] == tool_name]
        effect_sigs = set()
        for d in tool_data:
            sig = tuple(d["effects"][e] for e in EFFECTS if d["effects"][e] == 1)
            effect_sigs.add(sig)
        print(f"  {tool_name:15s}: {len(tool_data):3d} scenarios, "
              f"{len(effect_sigs)} unique effect patterns")


if __name__ == "__main__":
    main()
