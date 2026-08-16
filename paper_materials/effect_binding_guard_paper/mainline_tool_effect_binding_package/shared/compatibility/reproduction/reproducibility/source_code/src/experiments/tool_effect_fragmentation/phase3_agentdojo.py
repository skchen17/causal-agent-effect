from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .metrics import summarize_method
from .phase2_metrics import PHASE2_METRICS, _filter_preds, _preds_by_method, paired_metric_delta
from .schema import PerturbationFamily, ToolEffectPrediction, ToolEffectStressCase
from .splits import tool_family


def agentdojo_phase3_analysis(
    cases: list[ToolEffectStressCase],
    predictions: list[ToolEffectPrediction],
    *,
    bootstrap_iters: int = 500,
) -> dict[str, Any]:
    agentdojo_cases = [case for case in cases if case.source_system == "agentdojo"]
    agentdojo_preds = [pred for pred in predictions if pred.source_system == "agentdojo"]
    protocol_pools = {
        "random": [case for case in agentdojo_cases if case.perturbation_type == PerturbationFamily.ORIGINAL.value],
        "held_out_tool": [
            case
            for case in agentdojo_cases
            if case.perturbation_type == PerturbationFamily.SAME_EFFECT_TOOL_RENAME.value
            or "held_out_tool" in case.surface_seen_status
        ],
        "same_effect_different_tool": [
            case
            for case in agentdojo_cases
            if case.perturbation_type
            in {
                PerturbationFamily.SAME_EFFECT_TOOL_RENAME.value,
                PerturbationFamily.SAME_EFFECT_WRAPPER_TOOL.value,
            }
        ],
    }
    protocols = balance_protocols(protocol_pools)
    methods: dict[str, Any] = {}
    for method, method_preds in _preds_by_method(agentdojo_preds).items():
        protocol_metrics = {
            protocol: summarize_method(protocol_cases, _filter_preds(method_preds, protocol_cases))
            for protocol, protocol_cases in protocols.items()
        }
        methods[method] = {
            "protocols": protocol_metrics,
            "random_vs_heldout_degradation": paired_metric_delta(
                protocols["random"],
                protocols["held_out_tool"],
                method_preds,
                PHASE2_METRICS["fnr"],
                bootstrap_iters=bootstrap_iters,
                seed=len(method),
            ),
            "heldout_vs_same_effect_delta": paired_metric_delta(
                protocols["held_out_tool"],
                protocols["same_effect_different_tool"],
                method_preds,
                PHASE2_METRICS["fnr"],
                bootstrap_iters=bootstrap_iters,
                seed=len(method) + 13,
            ),
            "subgroups": subgroup_metrics(protocols, method_preds),
        }
    return {
        "protocol_case_counts": {name: len(rows) for name, rows in protocols.items()},
        "unbalanced_protocol_case_counts": {name: len(rows) for name, rows in protocol_pools.items()},
        "balance_summary": protocol_balance_summary(protocols),
        "distribution_differences": distribution_differences(protocols["held_out_tool"], protocols["same_effect_different_tool"]),
        "methods": methods,
        "claim_boundary": "AgentDojo Phase 3 is paper-grade only for local T122-derived custom stress artifacts, not an official AgentDojo benchmark reproduction.",
    }


def balance_protocols(protocol_pools: dict[str, list[ToolEffectStressCase]]) -> dict[str, list[ToolEffectStressCase]]:
    strata_by_protocol = {name: _strata(rows) for name, rows in protocol_pools.items()}
    common = set.intersection(*(set(strata) for strata in strata_by_protocol.values())) if strata_by_protocol else set()
    if not common:
        return protocol_pools
    targets = {stratum: min(len(strata_by_protocol[name][stratum]) for name in protocol_pools) for stratum in common}
    balanced: dict[str, list[ToolEffectStressCase]] = {}
    for name, strata in strata_by_protocol.items():
        rows: list[ToolEffectStressCase] = []
        for stratum in sorted(common):
            rows.extend(sorted(strata[stratum], key=lambda case: case.case_id)[: targets[stratum]])
        balanced[name] = rows
    return balanced


def subgroup_metrics(protocols: dict[str, list[ToolEffectStressCase]], predictions: list[ToolEffectPrediction]) -> dict[str, Any]:
    dimensions = {
        "realized_effect": lambda case: case.realized_effect,
        "tool_family": lambda case: _case_tool_family(case),
        "perturbation_family": lambda case: case.perturbation_type,
        "risk_label": lambda case: case.risk_label,
        "action_type": lambda case: case.granularity,
    }
    out: dict[str, Any] = {}
    for protocol, cases in protocols.items():
        out[protocol] = {}
        for dim, key_fn in dimensions.items():
            out[protocol][dim] = {}
            groups: dict[str, list[ToolEffectStressCase]] = defaultdict(list)
            for case in cases:
                groups[str(key_fn(case))].append(case)
            for key, rows in sorted(groups.items()):
                out[protocol][dim][key] = summarize_method(rows, _filter_preds(predictions, rows))
    return out


def protocol_balance_summary(protocols: dict[str, list[ToolEffectStressCase]]) -> dict[str, Any]:
    return {
        name: {
            "n_cases": len(rows),
            "by_effect": dict(Counter(case.realized_effect for case in rows)),
            "by_risk": dict(Counter(case.risk_label for case in rows)),
            "by_perturbation": dict(Counter(case.perturbation_type for case in rows)),
        }
        for name, rows in protocols.items()
    }


def distribution_differences(left: list[ToolEffectStressCase], right: list[ToolEffectStressCase]) -> dict[str, Any]:
    return {
        "held_out_tool": protocol_balance_summary({"held_out_tool": left})["held_out_tool"],
        "same_effect_different_tool": protocol_balance_summary({"same_effect_different_tool": right})["same_effect_different_tool"],
        "explanation": "Balanced protocols use common effect/risk strata where possible; remaining differences come from perturbation-family composition.",
    }


def agentdojo_phase3_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# AgentDojo Phase 3 Tool-Effect Fragmentation",
        "",
        "## Protocol Counts",
        "",
        "| Protocol | Balanced N | Unbalanced N |",
        "|---|---:|---:|",
    ]
    for protocol, n in result["protocol_case_counts"].items():
        lines.append(f"| `{protocol}` | {n} | {result['unbalanced_protocol_case_counts'].get(protocol, 0)} |")
    lines.extend(["", "## Main Metrics", ""])
    lines.extend(_main_table(result))
    lines.extend(["", "## Claim Boundary", "", f"- {result['claim_boundary']}"])
    return "\n".join(lines) + "\n"


def _main_table(result: dict[str, Any]) -> list[str]:
    lines = [
        "| Method | Protocol | N | FNR | Held-out-tool FNR | Unsafe pre-allow | Action error | ToolProxyGap |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method, payload in result["methods"].items():
        for protocol, metrics in payload["protocols"].items():
            lines.append(
                "| `{}` | `{}` | {} | {} | {} | {} | {} | {} |".format(
                    method,
                    protocol,
                    metrics["n_cases"],
                    _fmt_rate(metrics["fnr"]),
                    _fmt_rate(metrics["held_out_tool_fnr"]),
                    _fmt_rate(metrics["unsafe_action_pre_allow"]),
                    _fmt_rate(metrics["action_level_decision_error"]),
                    _fmt(metrics["tool_proxy_gap"]),
                )
            )
    return lines


def _strata(cases: list[ToolEffectStressCase]) -> dict[tuple[str, str], list[ToolEffectStressCase]]:
    groups: dict[tuple[str, str], list[ToolEffectStressCase]] = defaultdict(list)
    for case in cases:
        groups[(case.realized_effect, case.risk_label)].append(case)
    return groups


def _case_tool_family(case: ToolEffectStressCase) -> str:
    payload = case.tool_call_or_plan
    name = str(payload.get("tool_name") or payload.get("function") or payload.get("tool") or "unknown")
    if name == "unknown":
        for tool in case.tool_inventory:
            if tool.get("name"):
                name = str(tool["name"])
                break
    return tool_family(name)


def _fmt_rate(metric: dict[str, Any]) -> str:
    rate = metric.get("rate")
    if rate is None:
        return "NA"
    return f"{rate:.3f} [{metric.get('ci_low', 0):.3f}, {metric.get('ci_high', 0):.3f}]"


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)

