#!/usr/bin/env python3
"""Compare C1f with same-model AgentDojo prompting baselines."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analyze_deepseek_confirmation import (
    NO_GUARD_ATTACK,
    OUT,
    attack_index,
    exact_mcnemar_lower_p,
)


CONFIRM = NO_GUARD_ATTACK.parent
METHODS = {
    "no_guard": {
        "attack_root": NO_GUARD_ATTACK,
        "benign_root": None,
        "pipeline": "local",
    },
    "c1f": {
        "attack_root": CONFIRM / "deepseek-confirmation-c1f-attack-r1",
        "benign_root": CONFIRM / "deepseek-confirmation-c1f-benign-r1",
        "pipeline": "local-ours_e77_effect_diff_runtime",
    },
    "repeat_user_prompt": {
        "attack_root": CONFIRM / "deepseek-confirmation-repeat_user_prompt-attack-r1",
        "benign_root": CONFIRM / "deepseek-confirmation-repeat_user_prompt-benign-r1",
        "pipeline": "local-repeat_user_prompt",
    },
    "spotlighting": {
        "attack_root": CONFIRM / "deepseek-confirmation-spotlighting-attack-r1",
        "benign_root": CONFIRM / "deepseek-confirmation-spotlighting-benign-r1",
        "pipeline": "local-spotlighting_with_delimiting",
    },
}
SUITES = ("banking", "slack", "travel", "workspace")


def generic_index(root: Path, pipeline: str, mode: str) -> dict[str, dict[str, Any]]:
    rows = {}
    for suite in SUITES:
        base = root / suite / "agentdojo_logs" / pipeline / suite
        pattern = "user_task_*/none/none.json" if mode == "benign" else "user_task_*/important_instructions/*.json"
        for path in base.glob(pattern):
            data = json.loads(path.read_text(encoding="utf-8"))
            task = path.parents[1].name
            key = f"{suite}/{task}" if mode == "benign" else f"{suite}/{task}/{path.stem}"
            rows[key] = {
                "utility": bool(data.get("utility")),
                "attack_success": bool(data.get("security")) if mode == "attack" else None,
                "error": data.get("error"),
                "path": str(path),
            }
    return rows


def paired(no_guard: dict[str, dict[str, Any]], method: dict[str, dict[str, Any]], keys: set[str]) -> dict[str, Any]:
    discordance: Counter[str] = Counter()
    for key in keys:
        pair = (no_guard[key]["attack_success"], method[key]["attack_success"])
        discordance[str(pair)] += 1
    left_only = discordance[str((True, False))]
    right_only = discordance[str((False, True))]
    p_value = exact_mcnemar_lower_p(left_only, right_only)
    return {
        "discordance": dict(discordance),
        "exact_mcnemar_one_sided_p": p_value,
        "security_improvement_passed": left_only > right_only and p_value < 0.05,
    }


def paired_utility(
    no_guard: dict[str, dict[str, Any]], method: dict[str, dict[str, Any]], keys: set[str]
) -> dict[str, Any]:
    discordance: Counter[str] = Counter()
    for key in keys:
        pair = (no_guard[key]["utility"], method[key]["utility"])
        discordance[str(pair)] += 1
    return {
        "discordance": dict(discordance),
        "no_guard_only_successes": discordance[str((True, False))],
        "method_only_successes": discordance[str((False, True))],
        "net_success_difference": (
            discordance[str((False, True))] - discordance[str((True, False))]
        ),
    }


def main() -> int:
    attack = {
        "no_guard": attack_index(NO_GUARD_ATTACK, c1b=False),
        "c1f": attack_index(METHODS["c1f"]["attack_root"], c1b=True),
    }
    for name in ("repeat_user_prompt", "spotlighting"):
        row = METHODS[name]
        attack[name] = generic_index(row["attack_root"], row["pipeline"], "attack")
    keys = set(attack["no_guard"])
    if len(keys) != 629 or any(set(rows) != keys for rows in attack.values()):
        raise RuntimeError("same-model methods do not contain the same 629 attack keys")
    scope_keys = {
        key for key in keys if not (key.startswith("travel/") and key.endswith("/injection_task_6"))
    }
    if len(scope_keys) != 609:
        raise RuntimeError("unexpected scope-aligned key count")

    c1b_joint = json.loads((OUT / "deepseek_c1b_joint_confirmation.json").read_text())
    rows = {}
    for name, values in attack.items():
        benign_root = METHODS[name]["benign_root"]
        if name == "no_guard":
            benign = {
                "repetitions": 4,
                "successes": c1b_joint["benign"]["no_guard_successes"],
                "mean_utility": c1b_joint["benign"]["no_guard_mean_utility"],
            }
        else:
            benign_rows = generic_index(benign_root, METHODS[name]["pipeline"], "benign")
            if len(benign_rows) != 97:
                raise RuntimeError(f"{name} benign result does not contain 97 keys")
            benign = {
                "repetitions": 1,
                "successes": [sum(row["utility"] for row in benign_rows.values())],
                "mean_utility": sum(row["utility"] for row in benign_rows.values()) / 97,
                "errors": sum(row["error"] is not None for row in benign_rows.values()),
            }
        method_metrics = {
            "benign": benign,
            "official_attack": {
                "n": 629,
                "attack_successes": sum(row["attack_success"] for row in values.values()),
                "attack_success_rate": sum(row["attack_success"] for row in values.values()) / 629,
                "utility_successes": sum(row["utility"] for row in values.values()),
                "utility_rate": sum(row["utility"] for row in values.values()) / 629,
                "errors": sum(row["error"] is not None for row in values.values()),
            },
            "scope_aligned_attack": {
                "n": len(scope_keys),
                "attack_successes": sum(values[key]["attack_success"] for key in scope_keys),
                "utility_successes": sum(values[key]["utility"] for key in scope_keys),
            },
        }
        if name != "no_guard":
            method_metrics["paired_vs_no_guard"] = paired(attack["no_guard"], values, keys)
            method_metrics["scope_paired_vs_no_guard"] = paired(attack["no_guard"], values, scope_keys)
            method_metrics["paired_attack_utility_vs_no_guard"] = paired_utility(
                attack["no_guard"], values, keys
            )
        rows[name] = method_metrics

    minimum_asr = min(row["official_attack"]["attack_successes"] for row in rows.values())
    best = sorted(
        name for name, row in rows.items() if row["official_attack"]["attack_successes"] == minimum_asr
    )
    report = {
        "experiment": "DeepSeek same-model AgentDojo strong-baseline comparison",
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agentdojo_version": "v1.1.2",
        "model": "deepseek-v4-flash",
        "methods": rows,
        "lowest_official_attack_successes": minimum_asr,
        "methods_at_lowest_attack_success": best,
        "sota_established": False,
        "claim_boundary": (
            "This is a same-model comparison with AgentDojo no defense and two built-in "
            "prompting defenses. It can establish relative performance among these rows, "
            "but not state of the art across checkpoint detectors, causal-attribution "
            "systems, adaptive attacks, other models, or deployed environments."
        ),
    }
    (OUT / "deepseek_same_model_strong_baselines.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# DeepSeek Same-Model Strong Baselines",
        "",
        "| Method | Benign utility | Official ASR | Attack utility | Scope-aligned attacks | p vs no guard |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, row in rows.items():
        paired_row = row.get("paired_vs_no_guard", {})
        lines.append(
            f"| `{name}` | {row['benign']['mean_utility']:.3f} | "
            f"{row['official_attack']['attack_successes']}/629 | "
            f"{row['official_attack']['utility_successes']}/629 | "
            f"{row['scope_aligned_attack']['attack_successes']}/609 | "
            f"{paired_row.get('exact_mcnemar_one_sided_p', 'n/a')} |"
        )
    lines.extend(["", report["claim_boundary"], ""])
    (OUT / "deepseek_same_model_strong_baselines.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
