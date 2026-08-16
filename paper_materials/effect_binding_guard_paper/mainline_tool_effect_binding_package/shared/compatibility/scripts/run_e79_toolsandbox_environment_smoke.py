#!/usr/bin/env python3
"""Run an offline ToolSandbox state-transition and validator smoke.

The script intentionally performs no LLM call and no network/API operation. It
checks whether the public sandbox can support the E79 adapter before expensive
model runs are designed.
"""

from __future__ import annotations

import copy
import importlib.metadata
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOL_SANDBOX = ROOT / "runs/e79_external_benchmarks/ToolSandbox"
RESULTS = ROOT / "analysis/results"


def _configure_import() -> None:
    sys.path.insert(0, str(TOOL_SANDBOX))


def run_smoke() -> dict[str, Any]:
    _configure_import()
    from tool_sandbox.common.execution_context import (  # noqa: PLC0415
        DatabaseNamespace,
        RoleType,
        ToolBackend,
        set_current_context,
    )
    from tool_sandbox.scenarios import named_scenarios  # noqa: PLC0415
    from tool_sandbox.tools.setting import (  # noqa: PLC0415
        set_low_battery_mode_status,
        set_wifi_status,
    )

    scenarios = named_scenarios(preferred_tool_backend=ToolBackend.DEFAULT)
    base_scenarios = {
        name: scenario
        for name, scenario in scenarios.items()
        if not any(token in name for token in ("distraction", "scrambled", "all_tools"))
    }
    categories = Counter(
        str(category)
        for scenario in base_scenarios.values()
        for category in scenario.categories
    )
    milestone_counts = [
        len(scenario.evaluation.milestone_matcher.milestones)
        for scenario in base_scenarios.values()
    ]

    wifi = copy.deepcopy(scenarios["wifi_off"])
    wifi_context = wifi.starting_context
    set_current_context(wifi_context)
    initial_wifi = bool(wifi_context.get_database(DatabaseNamespace.SETTING)["wifi"][0])
    set_wifi_status(False)
    wifi_context.add_to_database(
        DatabaseNamespace.SANDBOX,
        [{"sender": RoleType.AGENT, "recipient": RoleType.USER, "content": "Wifi is turned off"}],
    )
    wifi_result = wifi.evaluation.evaluate(wifi_context, wifi.max_messages)
    final_wifi = bool(wifi_context.get_database(DatabaseNamespace.SETTING)["wifi"][0])

    dependency_context = copy.deepcopy(scenarios["wifi_off"].starting_context)
    set_current_context(dependency_context)
    set_low_battery_mode_status(True)
    dependency_blocked = False
    dependency_error = None
    try:
        set_wifi_status(True)
    except PermissionError as exc:
        dependency_blocked = True
        dependency_error = str(exc)

    no_external_keys = not any(
        key in os.environ for key in ("RAPID_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY")
    )
    status = "passed" if all(
        (
            initial_wifi,
            not final_wifi,
            wifi_result.milestone_similarity == 1.0,
            wifi_result.minefield_similarity == 0.0,
            dependency_blocked,
            no_external_keys,
        )
    ) else "failed"
    return {
        "experiment": "E79",
        "smoke_type": "toolsandbox_offline_environment_and_validator",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": {
            "repository": "https://github.com/apple/ToolSandbox",
            "local_snapshot": str(TOOL_SANDBOX.relative_to(ROOT)),
            "revision": "165848b9a78cead7ca7fe7c89c688b58e6501219",
        },
        "environment": {
            "python": sys.version.split()[0],
            "ccy_expected": "1.3.1",
            "ccy_observed": importlib.metadata.version("ccy"),
            "ccy_version_deviation": importlib.metadata.version("ccy") != "1.3.1",
            "external_api_keys_present": not no_external_keys,
        },
        "inventory": {
            "n_all_scenario_variants": len(scenarios),
            "n_base_scenarios": len(base_scenarios),
            "category_counts": dict(sorted(categories.items())),
            "milestone_count_min": min(milestone_counts),
            "milestone_count_max": max(milestone_counts),
            "n_multi_milestone_base_scenarios": sum(count > 1 for count in milestone_counts),
        },
        "state_transition_check": {
            "scenario": "wifi_off",
            "initial_wifi": initial_wifi,
            "final_wifi": final_wifi,
            "milestone_similarity": wifi_result.milestone_similarity,
            "minefield_similarity": wifi_result.minefield_similarity,
            "passed": wifi_result.similarity == 1.0 and not final_wifi,
        },
        "state_dependency_check": {
            "operation": "enable wifi while low-battery mode is active",
            "blocked": dependency_blocked,
            "error": dependency_error,
        },
        "execution_claim": (
            "A public ToolSandbox state transition and native milestone validator were executed locally. "
            "No LLM, user simulator, search tool, external API, prompt-injection attack, or proposed guard was executed."
        ),
        "next_gate": (
            "Select a fixed offline multi-tool subset, add label-hidden untrusted observations and prefix effect validators, "
            "then run the same victim checkpoint with no guard and the effect-binding guard."
        ),
    }


def write_report(report: dict[str, Any]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e79_toolsandbox_environment_smoke.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    inventory = report["inventory"]
    transition = report["state_transition_check"]
    dependency = report["state_dependency_check"]
    lines = [
        "# E79 ToolSandbox Offline Environment Smoke",
        "",
        f"Status: `{report['status']}`.",
        "",
        report["execution_claim"],
        "",
        "## Observed Checks",
        "",
        f"- Loaded {inventory['n_base_scenarios']} base scenarios and {inventory['n_all_scenario_variants']} total variants.",
        f"- Base scenario milestone counts range from {inventory['milestone_count_min']} to {inventory['milestone_count_max']}; {inventory['n_multi_milestone_base_scenarios']} have multiple milestones.",
        f"- `wifi_off` changed the sandbox state from `{transition['initial_wifi']}` to `{transition['final_wifi']}` and received milestone similarity `{transition['milestone_similarity']}`.",
        f"- The state-dependency check was blocked: `{dependency['blocked']}` (`{dependency['error']}`).",
        "",
        "## Compatibility Note",
        "",
        f"The smoke used Python {report['environment']['python']} with `ccy=={report['environment']['ccy_observed']}` because the repository's pinned `ccy==1.3.1` does not publish a Python 3.12-compatible distribution. A final benchmark environment should use Python 3.11 with the exact pin or establish behavioral equivalence for the replacement.",
        "",
        "## Next Gate",
        "",
        report["next_gate"],
        "",
    ]
    (RESULTS / "e79_toolsandbox_environment_smoke.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = run_smoke()
    write_report(report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
