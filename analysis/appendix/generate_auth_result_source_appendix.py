"""Generate an Auth-SafeInv result-source appendix.

The appendix maps each current Auth-SafeInv claim-bearing artifact to:

* the script that produces it;
* the intended reproduction command;
* key result numbers read from JSON/JSONL files;
* whether the required files exist.

It is intentionally descriptive and does not rerun expensive experiments.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def exists_all(paths: list[str]) -> bool:
    return all((ROOT / p).exists() for p in paths)


def load_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def load_jsonl(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (ROOT / path).read_text(encoding="utf-8").splitlines()]


def file_size(path: str) -> int:
    p = ROOT / path
    return p.stat().st_size if p.exists() else 0


def counterfactual_summary() -> dict[str, Any]:
    rows = load_jsonl("data/authorization_counterfactuals_v1.jsonl")
    focus = Counter()
    tool_surfaces: dict[str, set[str]] = {}
    for row in rows:
        for effect in row.get("unauthorized_effects", []):
            focus[effect] += 1
            tool_surfaces.setdefault(effect, set()).add(row.get("tool_name", "unknown"))
    return {
        "rows": len(rows),
        "unauthorized_effect_counts": dict(sorted(focus.items())),
        "unauthorized_tool_surface_counts": {k: len(v) for k, v in sorted(tool_surfaces.items())},
    }


def counterfactual_v2_summary() -> dict[str, Any]:
    rows = load_jsonl("data/authorization_counterfactuals_v2.jsonl")
    manifest = load_json("analysis/authorization_counterfactuals_v2_manifest.json")
    gates = manifest["focus_surface_graph_gates"]
    return {
        "rows": len(rows),
        "rows_added": manifest["surface_graph_expansion"]["rows_added"],
        "target_effects": manifest["surface_graph_expansion"]["target_effects"],
        "all_focus_unauthorized_tools_ge_3": all(info["unauthorized_tools_ge_3"] for info in gates.values()),
        "focus_unauthorized_tool_counts": {
            effect: info["unauthorized_tool_count"] for effect, info in sorted(gates.items())
        },
    }


def embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_authorization_counterfactuals_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_authorization_counterfactuals_v1.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def embedding_v2_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_authorization_counterfactuals_v2.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_authorization_counterfactuals_v2.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def schema_conditioned_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_effect_schema_conditioned_v2_manifest.json")
    return {
        "rows": manifest["n_total"],
        "base_rows": manifest["n_base_rows"],
        "conditions": manifest["schema_conditions"],
        "candidate_effects": manifest["candidate_effects"],
        "unauthorized_positive_counts_by_condition": manifest["unauthorized_positive_counts_by_condition"],
        "leakage_checks": manifest["leakage_checks"],
    }


def schema_conditioned_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_effect_schema_conditioned_v2.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_effect_schema_conditioned_v2.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def trace_schema_conditioned_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_trace_effect_schema_conditioned_v1_manifest.json")
    return {
        "rows": manifest["n_rows"],
        "traces": manifest["n_traces"],
        "conditions": manifest["conditions"],
        "trace_type_counts": manifest["trace_type_counts"],
        "candidate_effects": manifest["candidate_effects"],
        "unauthorized_by_candidate_effect": manifest["unauthorized_by_candidate_effect"],
        "leakage_checks": manifest["leakage_checks"],
        "caveat": "Trace rows are controlled observed/sandbox/static traces, not live deployed-agent traffic.",
    }


def trace_schema_conditioned_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_v1.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def auth_eval_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v1.json")
    loto = payload["leave_one_tool_out"]
    family = payload["leave_one_family_out"]
    return {
        "random_effects": len(payload["random_group_split"]["aggregate"]),
        "loto_rows": len(loto),
        "family_rows": len(family),
        "max_loto_unauthorized_fnr": max(row["unauthorized_fnr"] for row in loto),
        "max_loto_auth_tool_proxy_gap": max(row["auth_tool_proxy_gap"] or 0.0 for row in loto),
        "max_family_unauthorized_fnr": max(row["unauthorized_fnr"] for row in family),
    }


def auth_eval_v2_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.json")
    loto = payload["leave_one_tool_out"]
    family = payload["leave_one_family_out"]
    return {
        "random_effects": len(payload["random_group_split"]["aggregate"]),
        "loto_rows": len(loto),
        "family_rows": len(family),
        "max_loto_unauthorized_fnr": max(row["unauthorized_fnr"] for row in loto),
        "max_loto_auth_tool_proxy_gap": max(row["auth_tool_proxy_gap"] or 0.0 for row in loto),
        "max_family_unauthorized_fnr": max(row["unauthorized_fnr"] for row in family),
    }


def trace_summary(path: str) -> dict[str, Any]:
    manifest = load_json(path)
    return {
        "rows": manifest["n_total"],
        "trace_type_counts": manifest["trace_type_counts"],
        "observed_execution_count": manifest["observed_execution_count"],
        "observed_execution_sufficient": manifest["observed_execution_sufficient"],
        "leakage_checks": manifest["leakage_checks"],
    }


def graph_summary() -> dict[str, Any]:
    payload = load_json("analysis/surface_graph_alignment_authorization_counterfactuals_v1.json")
    by_effect = payload.get("by_effect", {})
    verified_identifiable = [
        effect for effect, row in by_effect.items() if row.get("verified_graph", {}).get("strict_pair_identifiable")
    ]
    unauthorized_identifiable = [
        effect for effect, row in by_effect.items() if row.get("unauthorized_graph", {}).get("strict_pair_identifiable")
    ]
    return {
        "effects": len(by_effect),
        "strict_identifiable_verified": verified_identifiable,
        "strict_identifiable_unauthorized": unauthorized_identifiable,
    }


def graph_v2_summary() -> dict[str, Any]:
    payload = load_json("analysis/surface_graph_alignment_authorization_counterfactuals_v2.json")
    by_effect = payload.get("by_effect", {})
    verified_identifiable = [
        effect for effect, row in by_effect.items() if row.get("verified_graph", {}).get("strict_pair_identifiable")
    ]
    unauthorized_identifiable = [
        effect for effect, row in by_effect.items() if row.get("unauthorized_graph", {}).get("strict_pair_identifiable")
    ]
    return {
        "effects": len(by_effect),
        "strict_identifiable_verified": verified_identifiable,
        "strict_identifiable_unauthorized": unauthorized_identifiable,
    }


def piia_summary() -> dict[str, Any]:
    payload = load_json("analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json")
    return {
        "raw_rows": payload["n_raw_rows"],
        "effects": payload["effects_run"],
        "spearman_piia_drop_vs_loto_gap": payload["piia_loto_correlation"]["spearman_piia_drop_vs_loto_gap"],
        "spearman_piia_drop_vs_heldout_fnr": payload["piia_loto_correlation"]["spearman_piia_drop_vs_heldout_fnr"],
    }


def baseline_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.json")
    key_rows = {}
    for row in payload["fixed_threshold_aggregate"]:
        if row["split_type"] == "leave_one_tool_out" and row["method"] in {
            "pooled_logistic",
            "domain_adversarial",
            "supervised_contrastive",
            "irm_linear",
            "open_set_abstain",
        }:
            key_rows[row["method"]] = {
                "mean_fnr": row["mean_unauthorized_fnr"],
                "mean_fpr": row["mean_absent_not_authorized_fpr"],
                "max_fnr": row["max_unauthorized_fnr"],
            }
    fpr10 = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] == "leave_one_tool_out" and row["target_fpr"] == 0.1
    ]
    return {
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "open_set_reject_all_rows": payload["open_set_diagnostics"]["reject_all_rows"],
        "loto_fixed_threshold": key_rows,
        "loto_best_tradeoff_fpr_0_1": fpr10,
    }


def baseline_v2_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json")
    fpr10 = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] == "leave_one_tool_out" and row["target_fpr"] == 0.1
    ]
    return {
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "open_set_reject_all_rows": payload["open_set_diagnostics"]["reject_all_rows"],
        "loto_best_tradeoff_fpr_0_1": fpr10,
    }


def mitigation_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v1.json")
    comparison = payload["same_cell_baseline_comparison"]
    comparison_rows = comparison.get("rows", []) if comparison.get("available") else []
    key_rows = {
        f"{row['split_type']}::{row['mitigation_method']}": {
            "cells": row["mitigation_cells"],
            "cell_coverage": row["cell_coverage"],
            "mitigation_mean_fnr": row["mitigation_mean_fnr"],
            "mitigation_mean_fpr": row["mitigation_mean_fpr"],
            "best_baseline_method": row["best_baseline_method"],
            "best_baseline_mean_fnr": row["best_baseline_mean_fnr"],
            "delta_fnr_vs_best_baseline": row["delta_fnr_vs_best_baseline"],
        }
        for row in comparison_rows
    }
    return {
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "skipped_rows": len(payload["skipped_rows"]),
        "skip_summary": payload["skip_summary"],
        "same_cell_fpr_0_1": key_rows,
    }


def mitigation_v2_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.json")
    comparison = payload["same_cell_baseline_comparison"]
    comparison_rows = comparison.get("rows", []) if comparison.get("available") else []
    key_rows = {
        f"{row['split_type']}::{row['mitigation_method']}": {
            "cells": row["mitigation_cells"],
            "cell_coverage": row["cell_coverage"],
            "mitigation_mean_fnr": row["mitigation_mean_fnr"],
            "mitigation_mean_fpr": row["mitigation_mean_fpr"],
            "best_baseline_method": row["best_baseline_method"],
            "best_baseline_mean_fnr": row["best_baseline_mean_fnr"],
            "delta_fnr_vs_best_baseline": row["delta_fnr_vs_best_baseline"],
        }
        for row in comparison_rows
    }
    return {
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "skipped_rows": len(payload["skipped_rows"]),
        "skip_summary": payload["skip_summary"],
        "same_cell_fpr_0_1": key_rows,
    }


def schema_mitigation_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_schema_conditioned_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json")
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["schema_condition"] == "full_tool_chain"
        and row["method"] in {"schema_sgd_logistic", "schema_per_effect_sgd"}
    ]
    comparison_rows = [
        row
        for row in payload["same_cell_baseline_comparison"].get("rows", [])
        if row["schema_condition"] == "full_tool_chain"
    ]
    return {
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "skipped_rows": len(payload["skipped_rows"]),
        "full_tool_chain_best_tradeoffs_fpr_0_1": key_tradeoffs,
        "full_tool_chain_same_cell_comparison": comparison_rows,
    }


def decomposed_verifier_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json")
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["schema_condition"] == "full_tool_chain"
        and row["method"] in {"decomposed_per_effect_sgd_product", "decomposed_per_effect_sgd_mean"}
    ]
    comparison_rows = [
        row
        for row in payload["same_cell_baseline_comparison"].get("rows", [])
        if row["schema_condition"] == "full_tool_chain"
    ]
    return {
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "skipped_rows": len(payload["skipped_rows"]),
        "full_tool_chain_best_tradeoffs_fpr_0_1": key_tradeoffs,
        "full_tool_chain_same_cell_comparison": comparison_rows,
    }


def verifier_present_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2_verifier_present_full.json"
    )
    return {
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "skipped_rows": len(payload["skipped_rows"]),
        "best_tradeoffs_fpr_0_1": payload["best_tradeoffs"],
        "same_cell_comparison": payload["same_cell_baseline_comparison"].get("rows", []),
        "caveat": "verifier_present methods use candidate_effect_present at evaluation and require an external/execution-level effect-present verifier.",
    }


def t57_effect_present_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.json")
    comparison_rows = payload["same_cell_baseline_comparison"].get("rows", [])
    key_rows = {
        f"{row['split_type']}::{row['decomposed_method']}": {
            "cells": row["decomposed_cells"],
            "baseline_cells_matched": row["baseline_cells_matched"],
            "t57_mean_fnr": row["decomposed_mean_fnr"],
            "t57_mean_fpr": row["decomposed_mean_fpr"],
            "best_baseline_method": row["best_baseline_method"],
            "best_baseline_mean_fnr": row["best_baseline_mean_fnr"],
            "delta_fnr_vs_best_baseline": row["delta_fnr_vs_best_baseline"],
        }
        for row in comparison_rows
    }
    return {
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "skipped_rows": len(payload["skipped_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": payload["best_tradeoffs"],
        "same_cell_fpr_0_1": key_rows,
        "caveat": "T57 uses deterministic trace-calibrated static tool-call rules, not live deployed-agent execution.",
    }


def t58_execution_verifier_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json"
    )
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] in {"schema_to_trace_all", "schema_to_trace_type"}
    ]
    return {
        "train_rows_used": payload["n_train_rows_used"],
        "trace_rows": payload["n_trace_rows_total"],
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": key_tradeoffs,
        "caveat": "T58 uses controlled execution trace verifier outputs and remains a setting-shifted, non-deployment evaluation.",
    }


def real_agent_tool_t59_summary() -> dict[str, Any]:
    inventory = load_json("analysis/real_agent_tool_inventory_t59_v1.json")
    manifest = load_json("analysis/agent_tool_traces_real_agent_tools_t59_v1_manifest.json")
    return {
        "registered_tools_static": inventory["n_registered_tools_static"],
        "execution_status_counts": inventory["execution_status_counts"],
        "local_trace_count": manifest["n_traces"],
        "local_tool_counts": manifest["tool_counts"],
        "verified_effect_counts": manifest["verified_effect_counts"],
        "unauthorized_effect_counts": manifest["unauthorized_effect_counts"],
        "manual_intervention_needed": inventory["manual_intervention_needed"],
        "import_blockers": inventory["import_blockers"],
        "caveat": "T59 executes local handler-equivalent adapters for file/terminal tools because direct Hermes handler import is blocked by missing upstream runtime modules; external services/API tools are inventoried but not invoked.",
    }


def trace_schema_conditioned_t59_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.json")
    return {
        "rows": manifest["n_rows"],
        "traces": manifest["n_traces"],
        "conditions": manifest["conditions"],
        "trace_type_counts": manifest["trace_type_counts"],
        "candidate_effects": manifest["candidate_effects"],
        "unauthorized_by_candidate_effect": manifest["unauthorized_by_candidate_effect"],
        "leakage_checks": manifest["leakage_checks"],
        "caveat": "T59 rows come from real-agent-tools grounded local adapters, not direct live agent-handler/API execution.",
    }


def trace_schema_conditioned_t59_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def t59_real_agent_execution_verifier_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json"
    )
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] in {"schema_to_trace_all", "schema_to_trace_type"}
    ]
    return {
        "train_rows_used": payload["n_train_rows_used"],
        "trace_rows": payload["n_trace_rows_total"],
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": key_tradeoffs,
        "caveat": "T59 is a real-agent-tools grounded local-adapter stress test. It is useful external-validity evidence, but not direct Hermes handler execution or live deployed-agent traffic.",
    }


def deepseek_api_t60_summary() -> dict[str, Any]:
    manifest = load_json("analysis/agent_tool_traces_deepseek_api_t60_v1_manifest.json")
    return {
        "traces": manifest["n_traces"],
        "success_count": manifest["success_count"],
        "error_count": manifest["error_count"],
        "tool_counts": manifest["tool_counts"],
        "verified_effect_counts": manifest["verified_effect_counts"],
        "unauthorized_effect_counts": manifest["unauthorized_effect_counts"],
        "api_key_value_stored": manifest["api_key_value_stored"],
        "caveat": "T60 DeepSeek traces are direct provider API calls. They cover provider network/content/error effects, not browser/search/messaging side effects.",
    }


def trace_schema_conditioned_t60_deepseek_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.json")
    return {
        "rows": manifest["n_rows"],
        "traces": manifest["n_traces"],
        "conditions": manifest["conditions"],
        "trace_type_counts": manifest["trace_type_counts"],
        "candidate_effects": manifest["candidate_effects"],
        "unauthorized_by_candidate_effect": manifest["unauthorized_by_candidate_effect"],
        "leakage_checks": manifest["leakage_checks"],
        "caveat": "T60 candidate-effect rows come from eight DeepSeek provider API calls and are a pilot only.",
    }


def trace_schema_conditioned_t60_deepseek_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def t60_deepseek_execution_verifier_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.json"
    )
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] in {"schema_to_trace_all", "schema_to_trace_type"}
    ]
    return {
        "train_rows_used": payload["n_train_rows_used"],
        "trace_rows": payload["n_trace_rows_total"],
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": key_tradeoffs,
        "caveat": "T60 DeepSeek is a tiny provider-API pilot. The execution verifier succeeds on one unauthorized evaluation cell, while static verifiers miss provider effects; this should be treated as smoke-test evidence only.",
    }


def deepseek_api_t61_summary() -> dict[str, Any]:
    manifest = load_json("analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.json")
    return {
        "traces": manifest["n_traces"],
        "success_count": manifest["success_count"],
        "error_count": manifest["error_count"],
        "tool_counts": manifest["tool_counts"],
        "verified_effect_counts": manifest["verified_effect_counts"],
        "unauthorized_effect_counts": manifest["unauthorized_effect_counts"],
        "api_key_value_stored": manifest["api_key_value_stored"],
        "caveat": "T61 expands DeepSeek direct provider API traces to cell counts >=30 for provider network/content/error effects; it remains a single provider tool surface.",
    }


def trace_schema_conditioned_t61_deepseek_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.json")
    return {
        "rows": manifest["n_rows"],
        "traces": manifest["n_traces"],
        "conditions": manifest["conditions"],
        "trace_type_counts": manifest["trace_type_counts"],
        "candidate_effects": manifest["candidate_effects"],
        "present_by_candidate_effect": manifest["present_by_candidate_effect"],
        "unauthorized_by_candidate_effect": manifest["unauthorized_by_candidate_effect"],
        "leakage_checks": manifest["leakage_checks"],
        "caveat": "T61 candidate-effect rows come from 120 DeepSeek provider API calls and cover one provider tool surface.",
    }


def trace_schema_conditioned_t61_deepseek_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def t61_deepseek_execution_verifier_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json"
    )
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] in {"schema_to_trace_all", "schema_to_trace_type"}
    ]
    return {
        "train_rows_used": payload["n_train_rows_used"],
        "trace_rows": payload["n_trace_rows_total"],
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": key_tradeoffs,
        "caveat": "T61 gives better provider-effect counts than T60, but it is still one provider API surface. T62 adds validation-selected threshold evaluation for this trace dataset.",
    }


def t62_validation_threshold_summary(path: str) -> dict[str, Any]:
    payload = load_json(path)
    key_methods = [
        "execution_trace_sgd_auth_validation_selected",
        "static_trace_semantic_sgd_auth_validation_selected",
        "static_monitored_effect_only_sgd_auth_validation_selected",
    ]
    test_by_method = {
        row["method"]: {
            "threshold": row["threshold"],
            "test_unauthorized_fnr": row["test_unauthorized_fnr"],
            "test_absent_not_authorized_fpr": row["test_absent_not_authorized_fpr"],
            "test_n_unauth": row["test_n_unauth"],
            "test_n_absent_not_authorized": row["test_n_absent_not_authorized"],
        }
        for row in payload["test_rows"]
        if row["method"] in key_methods
    }
    return {
        "trace_data_name": payload["trace_data_name"],
        "validation_rows": payload["n_validation_rows"],
        "test_rows": payload["n_test_rows"],
        "target_fpr": payload["target_fpr"],
        "validation_selected_test": test_by_method,
        "caveat": "Thresholds are selected on validation trace groups and evaluated on held-out trace groups. Trace provenance is inherited from the source dataset; this is not deployment safety certification.",
    }


def broader_t63_trace_summary() -> dict[str, Any]:
    manifest = load_json("analysis/agent_tool_traces_broader_tools_t63_v1_manifest.json")
    return {
        "traces": manifest["n_traces"],
        "toolset_counts": manifest["toolset_counts"],
        "tool_counts": manifest["tool_counts"],
        "verified_effect_counts": manifest["verified_effect_counts"],
        "unauthorized_effect_counts": manifest["unauthorized_effect_counts"],
        "caveat": "T63 uses controlled local adapters for real-agent-tools web/search/browser/messaging tool names; it does not invoke live external services.",
    }


def trace_schema_conditioned_t63_broader_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.json")
    return {
        "rows": manifest["n_rows"],
        "traces": manifest["n_traces"],
        "conditions": manifest["conditions"],
        "trace_type_counts": manifest["trace_type_counts"],
        "candidate_effects": manifest["candidate_effects"],
        "present_by_candidate_effect": manifest["present_by_candidate_effect"],
        "unauthorized_by_candidate_effect": manifest["unauthorized_by_candidate_effect"],
        "leakage_checks": manifest["leakage_checks"],
        "caveat": "T63 candidate-effect rows come from controlled broader local-adapter traces over web/browser/messaging tool families.",
    }


def trace_schema_conditioned_t63_broader_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.npy")
    return {"embedding_shape": list(x.shape), "effect_shape": list(y.shape)}


def t63_broader_execution_verifier_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json"
    )
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] in {"schema_to_trace_all", "schema_to_trace_type"}
    ]
    return {
        "train_rows_used": payload["n_train_rows_used"],
        "trace_rows": payload["n_trace_rows_total"],
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": key_tradeoffs,
        "caveat": "T63 broadens controlled local-adapter tool-family coverage. Use T62 validation-threshold output for calibrated trace-group wording.",
    }


def live_protocol_t64_trace_summary() -> dict[str, Any]:
    manifest = load_json("analysis/agent_tool_traces_live_protocol_t64_v1_manifest.json")
    return {
        "traces": manifest["n_traces"],
        "trace_type_counts": manifest["trace_type_counts"],
        "tool_counts": manifest["tool_counts"],
        "verified_effect_counts": manifest["verified_effect_counts"],
        "unauthorized_effect_counts": manifest["unauthorized_effect_counts"],
        "live_http_status_counts": manifest["live_http_status_counts"],
        "evidence_level": manifest["evidence_level"],
        "caveat": "T64 uses key-free live outbound HTTPS plus local webhook protocol traces; it is not provider-backed search/SaaS messaging/deployed-runtime validation.",
    }


def trace_schema_conditioned_t64_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.json")
    return {
        "rows": manifest["n_rows"],
        "traces": manifest["n_traces"],
        "conditions": manifest["conditions"],
        "trace_type_counts": manifest["trace_type_counts"],
        "candidate_effects": manifest["candidate_effects"],
        "present_by_candidate_effect": manifest["present_by_candidate_effect"],
        "unauthorized_by_candidate_effect": manifest["unauthorized_by_candidate_effect"],
        "leakage_checks": manifest["leakage_checks"],
        "caveat": "T64 candidate-effect rows come from key-free live HTTP and local protocol traces.",
    }


def trace_schema_conditioned_t64_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.npy")
    meta = load_json("embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json")
    return {
        "embedding_shape": list(x.shape),
        "effect_shape": list(y.shape),
        "use_4bit": meta.get("use_4bit"),
        "caveat": "T64 embeddings have been rerun with full-precision Qwen3-8B on cuda1.",
    }


def t64_live_protocol_execution_verifier_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json"
    )
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] in {"schema_to_trace_all", "schema_to_trace_type"}
    ]
    return {
        "train_rows_used": payload["n_train_rows_used"],
        "trace_rows": payload["n_trace_rows_total"],
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": key_tradeoffs,
        "caveat": "T64 uses key-free live/protocol traces. Use T62 validation-threshold output for calibrated trace-group wording.",
    }


def headless_browser_t65_trace_summary() -> dict[str, Any]:
    manifest = load_json("analysis/agent_tool_traces_headless_browser_t65_v1_manifest.json")
    return {
        "traces": manifest["n_traces"],
        "trace_types": manifest["trace_types"],
        "tools": manifest["tools"],
        "verified_effect_counts": manifest["verified_effect_counts"],
        "unauthorized_effect_counts": manifest["unauthorized_effect_counts"],
        "chrome_binary": manifest["chrome_binary"],
        "caveat": "T65 uses actual headless Chrome over file-backed pages; it is not HTTP browser networking, provider-backed search/SaaS messaging, or deployed-agent runtime validation.",
    }


def trace_schema_conditioned_t65_browser_summary() -> dict[str, Any]:
    manifest = load_json("analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.json")
    return {
        "rows": manifest["n_rows"],
        "traces": manifest["n_traces"],
        "conditions": manifest["conditions"],
        "trace_type_counts": manifest["trace_type_counts"],
        "candidate_effects": manifest["candidate_effects"],
        "present_by_candidate_effect": manifest["present_by_candidate_effect"],
        "unauthorized_by_candidate_effect": manifest["unauthorized_by_candidate_effect"],
        "leakage_checks": manifest["leakage_checks"],
        "caveat": "T65 candidate-effect rows come from file-backed headless Chrome browser-runtime traces.",
    }


def trace_schema_conditioned_t65_browser_embedding_summary() -> dict[str, Any]:
    import numpy as np

    x = np.load(ROOT / "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.npy")
    y = np.load(ROOT / "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.npy")
    meta = load_json("embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json")
    return {
        "embedding_shape": list(x.shape),
        "effect_shape": list(y.shape),
        "use_4bit": meta.get("use_4bit"),
        "caveat": "T65 browser-runtime embeddings use full-precision Qwen3-8B.",
    }


def t65_browser_execution_verifier_summary() -> dict[str, Any]:
    payload = load_json(
        "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json"
    )
    key_tradeoffs = [
        row
        for row in payload["best_tradeoffs"]
        if row["split_type"] in {"schema_to_trace_all", "schema_to_trace_type"}
    ]
    return {
        "train_rows_used": payload["n_train_rows_used"],
        "trace_rows": payload["n_trace_rows_total"],
        "present_rows": len(payload["present_verifier_rows"]),
        "fixed_rows": len(payload["fixed_threshold_rows"]),
        "threshold_curve_rows": len(payload["threshold_curve_rows"]),
        "present_verifier_aggregate": payload["present_verifier_aggregate"],
        "best_tradeoffs_fpr_0_1": key_tradeoffs,
        "caveat": "T65 validates file-backed headless Chrome runtime effects. Use T62 validation-threshold output for calibrated trace-group wording.",
    }


def auth_action_level_t68_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_action_level_metrics_t68.json")
    keep_verifiers = {"execution_trace", "static_trace_semantic"}
    datasets = {}
    for dataset in payload["datasets"]:
        methods = {}
        for method in dataset["methods"]:
            verifier = method["present_verifier"]
            if verifier not in keep_verifiers:
                continue
            methods[verifier] = {
                "n_actions": method["n_actions"],
                "n_unauthorized_actions": method["n_unauthorized_actions"],
                "unauthorized_action_allow_rate": method["unauthorized_action_allow_rate"],
                "authorized_action_false_denial_rate": method["authorized_action_false_denial_rate"],
                "row_macro_unauthorized_effect_fnr": method["row_macro_unauthorized_effect_fnr"],
                "row_macro_absent_not_authorized_fpr": method["row_macro_absent_not_authorized_fpr"],
            }
        datasets[dataset["trace_data_name"]] = methods
    return {
        "datasets": datasets,
        "caveat": "T68 aggregates candidate-effect predictions to action-level allow/deny metrics. It exposes false-denial tradeoffs hidden by row-level FNR/FPR, especially for provider API traces.",
    }


def trace_view_ablation_t69_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_trace_view_ablation_t69.json")
    return {
        "aggregate": payload["aggregate"],
        "views": payload["views"],
        "datasets": [dataset["trace_data_name"] for dataset in payload["datasets"]],
        "caveat": "T69 changes the effect-present verifier view, not the authorization embedding model. label_hidden_raw hides explicit trace label fields; minimal_evidence tests stricter raw evidence.",
    }


def existing_defense_ablation_t70_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_existing_defense_ablation_t70.json")
    return {
        "aggregate": payload["aggregate"],
        "methods": payload["methods"],
        "datasets": [dataset["trace_data_name"] for dataset in payload["datasets"]],
        "caveat": "T70 uses proxy baselines for boundary analysis, not faithful reimplementations of external defense systems. raw_status_boundary is a strong handcrafted trace-policy baseline in these controlled traces.",
    }


def action_level_calibration_t73_summary() -> dict[str, Any]:
    payload = load_json("analysis/auth_action_level_calibration_t73.json")
    keep_verifiers = {"execution_trace", "static_trace_semantic"}
    datasets = {}
    for dataset in payload["datasets"]:
        methods = {}
        for method in dataset["methods"]:
            verifier = method["present_verifier"]
            if verifier not in keep_verifiers:
                continue
            methods[verifier] = {
                "validation": method["validation"],
                "test": method["test"],
            }
        datasets[dataset["trace_data_name"]] = methods
    return {
        "target_action_fdr": payload["target_action_fdr"],
        "datasets": datasets,
        "caveat": "T73 calibrates action-level thresholds on validation trace groups. Several datasets satisfy false-denial constraints only via degenerate all-allow thresholds, so this is a diagnostic rather than a deployable calibration policy.",
    }


def artifact_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "auth_counterfactuals",
            "task": "T39 authorization counterfactual dataset",
            "script": "build_authorization_counterfactuals.py",
            "command": "python build_authorization_counterfactuals.py",
            "outputs": [
                "data/authorization_counterfactuals_v1.jsonl",
                "analysis/authorization_counterfactuals_v1_manifest.json",
                "analysis/authorization_counterfactuals_v1_manifest.md",
            ],
            "summary_fn": counterfactual_summary,
        },
        {
            "id": "auth_counterfactuals_v2",
            "task": "T53 authorization surface-graph expansion dataset",
            "script": "build_authorization_counterfactuals_v2.py",
            "command": "python build_authorization_counterfactuals_v2.py",
            "outputs": [
                "data/authorization_counterfactuals_v2.jsonl",
                "analysis/authorization_counterfactuals_v2_manifest.json",
                "analysis/authorization_counterfactuals_v2_manifest.md",
            ],
            "summary_fn": counterfactual_v2_summary,
        },
        {
            "id": "auth_embeddings",
            "task": "T39 Qwen3-8B authorization embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "python extract_embeddings_llm.py Qwen/Qwen3-8B authorization_counterfactuals_v1.jsonl --batch-size 8",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_authorization_counterfactuals_v1.npy",
                "embeddings/effects_qwen3-8b_authorization_counterfactuals_v1.npy",
                "embeddings/meta_qwen3-8b_authorization_counterfactuals_v1.json",
            ],
            "summary_fn": embedding_summary,
        },
        {
            "id": "auth_embeddings_v2",
            "task": "T54 Qwen3-8B authorization v2 embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "python extract_embeddings_llm.py Qwen/Qwen3-8B authorization_counterfactuals_v2.jsonl --batch-size 8",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_authorization_counterfactuals_v2.npy",
                "embeddings/effects_qwen3-8b_authorization_counterfactuals_v2.npy",
                "embeddings/meta_qwen3-8b_authorization_counterfactuals_v2.json",
            ],
            "summary_fn": embedding_v2_summary,
        },
        {
            "id": "auth_traces_v2",
            "task": "T40/T49 auth execution traces",
            "script": "build_auth_observed_execution_traces.py",
            "command": "python build_auth_observed_execution_traces.py",
            "outputs": [
                "data/agent_tool_traces_auth_v2.jsonl",
                "analysis/agent_tool_traces_auth_v2_manifest.json",
                "analysis/agent_tool_traces_auth_v2_manifest.md",
                "data/agent_tool_traces_auth_observed_v1.jsonl",
                "analysis/agent_tool_traces_auth_observed_v1_manifest.json",
            ],
            "summary_fn": lambda: trace_summary("analysis/agent_tool_traces_auth_v2_manifest.json"),
        },
        {
            "id": "auth_safeinv_eval",
            "task": "T41 Auth-SafeInv held-out evaluation",
            "script": "experiment_auth_safeinv.py",
            "command": "python experiment_auth_safeinv.py qwen3-8b_authorization_counterfactuals_v1",
            "outputs": [
                "analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v1.json",
                "analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v1.md",
            ],
            "summary_fn": auth_eval_summary,
        },
        {
            "id": "auth_safeinv_eval_v2",
            "task": "T54 Auth-SafeInv v2 held-out evaluation",
            "script": "experiment_auth_safeinv.py",
            "command": "python experiment_auth_safeinv.py qwen3-8b_authorization_counterfactuals_v2",
            "outputs": [
                "analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.json",
                "analysis/auth_safeinv_qwen3-8b_authorization_counterfactuals_v2.md",
            ],
            "summary_fn": auth_eval_v2_summary,
        },
        {
            "id": "surface_graph_alignment",
            "task": "T42 surface graph alignment",
            "script": "analyze_surface_graph_alignment.py",
            "command": "python analyze_surface_graph_alignment.py authorization_counterfactuals_v1",
            "outputs": [
                "analysis/surface_graph_alignment_authorization_counterfactuals_v1.json",
                "analysis/surface_graph_alignment_authorization_counterfactuals_v1.md",
            ],
            "summary_fn": graph_summary,
        },
        {
            "id": "surface_graph_alignment_v2",
            "task": "T54 v2 surface graph alignment",
            "script": "analyze_surface_graph_alignment.py",
            "command": "python analyze_surface_graph_alignment.py authorization_counterfactuals_v2",
            "outputs": [
                "analysis/surface_graph_alignment_authorization_counterfactuals_v2.json",
                "analysis/surface_graph_alignment_authorization_counterfactuals_v2.md",
            ],
            "summary_fn": graph_v2_summary,
        },
        {
            "id": "piia_hook_confirmatory",
            "task": "T48 hook-based pIIA controls",
            "script": "interchange_intervention_hook_controls.py",
            "command": (
                "python interchange_intervention_hook_controls.py --data-name qwen3-8b_scenarios_mainconf_v2 "
                "--max-effects 6 --max-eval-tools 2 --pairs-per-mode 3 "
                "--out-json analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json "
                "--out-md analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.md"
            ),
            "outputs": [
                "analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json",
                "analysis/piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.md",
            ],
            "summary_fn": piia_summary,
        },
        {
            "id": "auth_baseline_confirmatory",
            "task": "T47 strong baseline confirmatory sweep",
            "script": "experiment_auth_baseline_confirmatory.py",
            "command": "python experiment_auth_baseline_confirmatory.py qwen3-8b_authorization_counterfactuals_v1",
            "outputs": [
                "analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.json",
                "analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v1.md",
            ],
            "summary_fn": baseline_summary,
        },
        {
            "id": "auth_baseline_confirmatory_v2",
            "task": "T54 strong baseline confirmatory sweep on v2",
            "script": "experiment_auth_baseline_confirmatory.py",
            "command": "python experiment_auth_baseline_confirmatory.py qwen3-8b_authorization_counterfactuals_v2",
            "outputs": [
                "analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.json",
                "analysis/auth_baseline_confirmatory_qwen3-8b_authorization_counterfactuals_v2.md",
            ],
            "summary_fn": baseline_v2_summary,
        },
        {
            "id": "auth_mitigation_vs_baseline",
            "task": "T51 final mitigation-vs-baseline comparison",
            "script": "experiment_auth_mitigation_comparison.py",
            "command": "python experiment_auth_mitigation_comparison.py qwen3-8b_authorization_counterfactuals_v1",
            "outputs": [
                "analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v1.json",
                "analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v1.md",
            ],
            "summary_fn": mitigation_summary,
        },
        {
            "id": "auth_mitigation_vs_baseline_v2",
            "task": "T54 mitigation-vs-baseline comparison on v2",
            "script": "experiment_auth_mitigation_comparison.py",
            "command": "python experiment_auth_mitigation_comparison.py qwen3-8b_authorization_counterfactuals_v2",
            "outputs": [
                "analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.json",
                "analysis/auth_mitigation_vs_baseline_qwen3-8b_authorization_counterfactuals_v2.md",
            ],
            "summary_fn": mitigation_v2_summary,
        },
        {
            "id": "auth_schema_conditioned_data_v2",
            "task": "T55 effect-schema conditioned candidate-effect data",
            "script": "build_auth_effect_schema_conditioned_data.py",
            "command": "python build_auth_effect_schema_conditioned_data.py",
            "outputs": [
                "data/auth_effect_schema_conditioned_v2.jsonl",
                "analysis/auth_effect_schema_conditioned_v2_manifest.json",
                "analysis/auth_effect_schema_conditioned_v2_manifest.md",
            ],
            "summary_fn": schema_conditioned_summary,
        },
        {
            "id": "auth_schema_conditioned_embeddings_v2",
            "task": "T55 Qwen3-8B effect-schema conditioned embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "python extract_embeddings_llm.py Qwen/Qwen3-8B auth_effect_schema_conditioned_v2.jsonl --batch-size 8",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_effect_schema_conditioned_v2.npy",
                "embeddings/effects_qwen3-8b_auth_effect_schema_conditioned_v2.npy",
                "embeddings/meta_qwen3-8b_auth_effect_schema_conditioned_v2.json",
            ],
            "summary_fn": schema_conditioned_embedding_summary,
        },
        {
            "id": "auth_schema_conditioned_mitigation_v2",
            "task": "T55 pair-free schema-conditioned mitigation evaluation",
            "script": "experiment_auth_schema_conditioned_mitigation.py",
            "command": "python experiment_auth_schema_conditioned_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2",
            "outputs": [
                "analysis/auth_schema_conditioned_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json",
                "analysis/auth_schema_conditioned_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.md",
            ],
            "summary_fn": schema_mitigation_summary,
        },
        {
            "id": "auth_decomposed_verifier_mitigation_v2",
            "task": "T56 full decomposed/verifier mitigation evaluation",
            "script": "experiment_auth_decomposed_verifier_mitigation.py",
            "command": "python experiment_auth_decomposed_verifier_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2",
            "outputs": [
                "analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.json",
                "analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2.md",
            ],
            "summary_fn": decomposed_verifier_summary,
        },
        {
            "id": "auth_verifier_present_upper_bound_v2",
            "task": "T56 verifier-present full-tool-chain upper-bound evaluation",
            "script": "experiment_auth_decomposed_verifier_mitigation.py",
            "command": "python experiment_auth_decomposed_verifier_mitigation.py qwen3-8b_auth_effect_schema_conditioned_v2 --conditions full_tool_chain --methods verifier_present_sgd_auth verifier_present_per_effect_sgd_auth --output-suffix _verifier_present_full",
            "outputs": [
                "analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2_verifier_present_full.json",
                "analysis/auth_decomposed_verifier_mitigation_qwen3-8b_auth_effect_schema_conditioned_v2_verifier_present_full.md",
            ],
            "summary_fn": verifier_present_summary,
        },
        {
            "id": "auth_t57_effect_present_verifier_v2",
            "task": "T57 trace-calibrated non-oracle effect-present verifier",
            "script": "experiment_auth_t57_effect_present_verifier.py",
            "command": "python experiment_auth_t57_effect_present_verifier.py qwen3-8b_auth_effect_schema_conditioned_v2 --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.json",
                "analysis/auth_t57_effect_present_verifier_qwen3-8b_auth_effect_schema_conditioned_v2.md",
            ],
            "summary_fn": t57_effect_present_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_v1",
            "task": "T58 trace candidate-effect data",
            "script": "build_auth_trace_effect_schema_conditioned_data.py",
            "command": "python build_auth_trace_effect_schema_conditioned_data.py --conditions full_tool_chain",
            "outputs": [
                "data/auth_trace_effect_schema_conditioned_v1.jsonl",
                "analysis/auth_trace_effect_schema_conditioned_v1_manifest.json",
                "analysis/auth_trace_effect_schema_conditioned_v1_manifest.md",
            ],
            "summary_fn": trace_schema_conditioned_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_embeddings_v1",
            "task": "T58 Qwen3-8B trace candidate-effect embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_v1.jsonl --batch-size 16",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_v1.npy",
                "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_v1.npy",
                "embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_v1.json",
            ],
            "summary_fn": trace_schema_conditioned_embedding_summary,
        },
        {
            "id": "auth_t58_execution_verifier_v1",
            "task": "T58 execution-level effect-present verifier",
            "script": "experiment_auth_t58_execution_verifier.py",
            "command": "python experiment_auth_t58_execution_verifier.py --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json",
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.md",
            ],
            "summary_fn": t58_execution_verifier_summary,
        },
        {
            "id": "real_agent_tools_t59_inventory_and_traces",
            "task": "T59 real-agent-tools inventory and local-adapter traces",
            "script": "build_real_agent_tool_execution_traces_t59.py",
            "command": "python build_real_agent_tool_execution_traces_t59.py",
            "outputs": [
                "analysis/real_agent_tool_inventory_t59_v1.json",
                "analysis/real_agent_tool_inventory_t59_v1.md",
                "data/agent_tool_traces_real_agent_tools_t59_v1.jsonl",
                "analysis/agent_tool_traces_real_agent_tools_t59_v1_manifest.json",
                "analysis/agent_tool_traces_real_agent_tools_t59_v1_manifest.md",
            ],
            "summary_fn": real_agent_tool_t59_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t59_v1",
            "task": "T59 real-agent-tools candidate-effect data",
            "script": "build_auth_trace_effect_schema_conditioned_data.py",
            "command": "python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_real_agent_tools_t59_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t59_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.md --conditions full_tool_chain",
            "outputs": [
                "data/auth_trace_effect_schema_conditioned_t59_v1.jsonl",
                "analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.json",
                "analysis/auth_trace_effect_schema_conditioned_t59_v1_manifest.md",
            ],
            "summary_fn": trace_schema_conditioned_t59_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t59_embeddings",
            "task": "T59 Qwen3-8B real-agent-tools candidate-effect embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t59_v1.jsonl --batch-size 16",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.npy",
                "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.npy",
                "embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json",
            ],
            "summary_fn": trace_schema_conditioned_t59_embedding_summary,
        },
        {
            "id": "auth_t59_real_agent_execution_verifier",
            "task": "T59 real-agent-tools execution-level verifier stress test",
            "script": "experiment_auth_t58_execution_verifier.py",
            "command": "python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1 --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json",
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.md",
            ],
            "summary_fn": t59_real_agent_execution_verifier_summary,
        },
        {
            "id": "deepseek_api_t60_traces",
            "task": "T60 DeepSeek provider API traces",
            "script": "build_deepseek_api_traces_t60.py",
            "command": "DEEPSEEK_API_KEY=<redacted> python build_deepseek_api_traces_t60.py --repetitions 2",
            "outputs": [
                "data/agent_tool_traces_deepseek_api_t60_v1.jsonl",
                "analysis/agent_tool_traces_deepseek_api_t60_v1_manifest.json",
                "analysis/agent_tool_traces_deepseek_api_t60_v1_manifest.md",
            ],
            "summary_fn": deepseek_api_t60_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t60_deepseek_v1",
            "task": "T60 DeepSeek candidate-effect data",
            "script": "build_auth_trace_effect_schema_conditioned_data.py",
            "command": "python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_deepseek_api_t60_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t60_deepseek_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.md --conditions full_tool_chain",
            "outputs": [
                "data/auth_trace_effect_schema_conditioned_t60_deepseek_v1.jsonl",
                "analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.json",
                "analysis/auth_trace_effect_schema_conditioned_t60_deepseek_v1_manifest.md",
            ],
            "summary_fn": trace_schema_conditioned_t60_deepseek_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t60_deepseek_embeddings",
            "task": "T60 Qwen3-8B DeepSeek candidate-effect embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t60_deepseek_v1.jsonl --batch-size 16",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.npy",
                "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.npy",
                "embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.json",
            ],
            "summary_fn": trace_schema_conditioned_t60_deepseek_embedding_summary,
        },
        {
            "id": "auth_t60_deepseek_execution_verifier",
            "task": "T60 DeepSeek execution-level verifier pilot",
            "script": "experiment_auth_t58_execution_verifier.py",
            "command": "python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1 --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.json",
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t60_deepseek_v1.md",
            ],
            "summary_fn": t60_deepseek_execution_verifier_summary,
        },
        {
            "id": "deepseek_api_t61_traces",
            "task": "T61 expanded DeepSeek provider API traces",
            "script": "build_deepseek_api_traces_t60.py",
            "command": "DEEPSEEK_API_KEY=<redacted> python build_deepseek_api_traces_t60.py --repetitions 30 --output data/agent_tool_traces_deepseek_api_t61_v1.jsonl --manifest analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.json --manifest-md analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.md",
            "outputs": [
                "data/agent_tool_traces_deepseek_api_t61_v1.jsonl",
                "analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.json",
                "analysis/agent_tool_traces_deepseek_api_t61_v1_manifest.md",
            ],
            "summary_fn": deepseek_api_t61_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t61_deepseek_v1",
            "task": "T61 expanded DeepSeek candidate-effect data",
            "script": "build_auth_trace_effect_schema_conditioned_data.py",
            "command": "python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_deepseek_api_t61_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.md --conditions full_tool_chain",
            "outputs": [
                "data/auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl",
                "analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.json",
                "analysis/auth_trace_effect_schema_conditioned_t61_deepseek_v1_manifest.md",
            ],
            "summary_fn": trace_schema_conditioned_t61_deepseek_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t61_deepseek_embeddings",
            "task": "T61 Qwen3-8B expanded DeepSeek candidate-effect embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t61_deepseek_v1.jsonl --batch-size 16",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.npy",
                "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.npy",
                "embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json",
            ],
            "summary_fn": trace_schema_conditioned_t61_deepseek_embedding_summary,
        },
        {
            "id": "auth_t61_deepseek_execution_verifier",
            "task": "T61 expanded DeepSeek execution-level verifier",
            "script": "experiment_auth_t58_execution_verifier.py",
            "command": "python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1 --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json",
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.md",
            ],
            "summary_fn": t61_deepseek_execution_verifier_summary,
        },
        {
            "id": "auth_t62_validation_threshold_t58_trace",
            "task": "T62 validation-selected threshold on controlled trace dataset",
            "script": "experiment_auth_t62_validation_threshold.py",
            "command": "python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_v1",
            "outputs": [
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json",
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.md",
            ],
            "summary_fn": lambda: t62_validation_threshold_summary(
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_v1.json"
            ),
        },
        {
            "id": "auth_t62_validation_threshold_t59_real_agent_tools",
            "task": "T62 validation-selected threshold on real-agent-tools local-adapter traces",
            "script": "experiment_auth_t62_validation_threshold.py",
            "command": "python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1",
            "outputs": [
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json",
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.md",
            ],
            "summary_fn": lambda: t62_validation_threshold_summary(
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t59_v1.json"
            ),
        },
        {
            "id": "auth_t62_validation_threshold_t61_deepseek",
            "task": "T62 validation-selected threshold on expanded DeepSeek provider traces",
            "script": "experiment_auth_t62_validation_threshold.py",
            "command": "python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1",
            "outputs": [
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json",
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.md",
            ],
            "summary_fn": lambda: t62_validation_threshold_summary(
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t61_deepseek_v1.json"
            ),
        },
        {
            "id": "broader_tools_t63_traces",
            "task": "T63 broader web/search/browser/messaging local-adapter traces",
            "script": "build_broader_agent_tool_traces_t63.py",
            "command": "python build_broader_agent_tool_traces_t63.py",
            "outputs": [
                "data/agent_tool_traces_broader_tools_t63_v1.jsonl",
                "analysis/agent_tool_traces_broader_tools_t63_v1_manifest.json",
                "analysis/agent_tool_traces_broader_tools_t63_v1_manifest.md",
            ],
            "summary_fn": broader_t63_trace_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t63_broader_v1",
            "task": "T63 broader tool-family candidate-effect data",
            "script": "build_auth_trace_effect_schema_conditioned_data.py",
            "command": "python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_broader_tools_t63_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.md --conditions full_tool_chain",
            "outputs": [
                "data/auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl",
                "analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.json",
                "analysis/auth_trace_effect_schema_conditioned_t63_broader_v1_manifest.md",
            ],
            "summary_fn": trace_schema_conditioned_t63_broader_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t63_broader_embeddings",
            "task": "T63 Qwen3-8B broader trace candidate-effect embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t63_broader_v1.jsonl --batch-size 16",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.npy",
                "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.npy",
                "embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json",
            ],
            "summary_fn": trace_schema_conditioned_t63_broader_embedding_summary,
        },
        {
            "id": "auth_t63_broader_execution_verifier",
            "task": "T63 broader tool-family execution-level verifier evaluation",
            "script": "experiment_auth_t58_execution_verifier.py",
            "command": "python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1 --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json",
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.md",
            ],
            "summary_fn": t63_broader_execution_verifier_summary,
        },
        {
            "id": "auth_t63_broader_validation_threshold",
            "task": "T63 validation-selected threshold on broader tool-family traces",
            "script": "experiment_auth_t62_validation_threshold.py",
            "command": "python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1",
            "outputs": [
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json",
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.md",
            ],
            "summary_fn": lambda: t62_validation_threshold_summary(
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t63_broader_v1.json"
            ),
        },
        {
            "id": "live_protocol_t64_traces",
            "task": "T64 key-free live/protocol external-validity traces",
            "script": "build_live_protocol_tool_traces_t64.py",
            "command": "python build_live_protocol_tool_traces_t64.py",
            "outputs": [
                "data/agent_tool_traces_live_protocol_t64_v1.jsonl",
                "analysis/agent_tool_traces_live_protocol_t64_v1_manifest.json",
                "analysis/agent_tool_traces_live_protocol_t64_v1_manifest.md",
            ],
            "summary_fn": live_protocol_t64_trace_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t64_live_protocol_v1",
            "task": "T64 live/protocol candidate-effect data",
            "script": "build_auth_trace_effect_schema_conditioned_data.py",
            "command": "python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_live_protocol_t64_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.md --conditions full_tool_chain",
            "outputs": [
                "data/auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl",
                "analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.json",
                "analysis/auth_trace_effect_schema_conditioned_t64_live_protocol_v1_manifest.md",
            ],
            "summary_fn": trace_schema_conditioned_t64_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t64_embeddings",
            "task": "T64 Qwen3-8B live/protocol candidate-effect embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t64_live_protocol_v1.jsonl --batch-size 4",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.npy",
                "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.npy",
                "embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json",
            ],
            "summary_fn": trace_schema_conditioned_t64_embedding_summary,
        },
        {
            "id": "auth_t64_live_protocol_execution_verifier",
            "task": "T64 live/protocol execution-level verifier evaluation",
            "script": "experiment_auth_t58_execution_verifier.py",
            "command": "python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1 --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json",
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.md",
            ],
            "summary_fn": t64_live_protocol_execution_verifier_summary,
        },
        {
            "id": "auth_t64_live_protocol_validation_threshold",
            "task": "T64 validation-selected threshold on live/protocol traces",
            "script": "experiment_auth_t62_validation_threshold.py",
            "command": "python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1",
            "outputs": [
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json",
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.md",
            ],
            "summary_fn": lambda: t62_validation_threshold_summary(
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t64_live_protocol_v1.json"
            ),
        },
        {
            "id": "headless_browser_t65_traces",
            "task": "T65 file-backed headless Chrome browser-runtime traces",
            "script": "build_headless_browser_runtime_traces_t65.py",
            "command": "python build_headless_browser_runtime_traces_t65.py --repetitions 30",
            "outputs": [
                "data/agent_tool_traces_headless_browser_t65_v1.jsonl",
                "analysis/agent_tool_traces_headless_browser_t65_v1_manifest.json",
                "analysis/agent_tool_traces_headless_browser_t65_v1_manifest.md",
            ],
            "summary_fn": headless_browser_t65_trace_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t65_browser_v1",
            "task": "T65 browser-runtime candidate-effect data",
            "script": "build_auth_trace_effect_schema_conditioned_data.py",
            "command": "python build_auth_trace_effect_schema_conditioned_data.py --input data/agent_tool_traces_headless_browser_t65_v1.jsonl --output data/auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl --manifest analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.json --manifest-md analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.md --conditions full_tool_chain",
            "outputs": [
                "data/auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl",
                "analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.json",
                "analysis/auth_trace_effect_schema_conditioned_t65_browser_v1_manifest.md",
            ],
            "summary_fn": trace_schema_conditioned_t65_browser_summary,
        },
        {
            "id": "auth_trace_effect_schema_conditioned_t65_browser_embeddings",
            "task": "T65 Qwen3-8B browser-runtime candidate-effect embeddings",
            "script": "extract_embeddings_llm.py",
            "command": "CUDA_VISIBLE_DEVICES=1 python extract_embeddings_llm.py Qwen/Qwen3-8B auth_trace_effect_schema_conditioned_t65_browser_v1.jsonl --batch-size 4",
            "outputs": [
                "embeddings/embeddings_qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.npy",
                "embeddings/effects_qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.npy",
                "embeddings/meta_qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json",
            ],
            "summary_fn": trace_schema_conditioned_t65_browser_embedding_summary,
        },
        {
            "id": "auth_t65_browser_execution_verifier",
            "task": "T65 browser-runtime execution-level verifier evaluation",
            "script": "experiment_auth_t58_execution_verifier.py",
            "command": "python experiment_auth_t58_execution_verifier.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1 --conditions full_tool_chain",
            "outputs": [
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json",
                "analysis/auth_t58_execution_verifier_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.md",
            ],
            "summary_fn": t65_browser_execution_verifier_summary,
        },
        {
            "id": "auth_t65_browser_validation_threshold",
            "task": "T65 validation-selected threshold on browser-runtime traces",
            "script": "experiment_auth_t62_validation_threshold.py",
            "command": "python experiment_auth_t62_validation_threshold.py --trace-data-name qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1",
            "outputs": [
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json",
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.md",
            ],
            "summary_fn": lambda: t62_validation_threshold_summary(
                "analysis/auth_t62_validation_threshold_qwen3-8b_auth_effect_schema_conditioned_v2__qwen3-8b_auth_trace_effect_schema_conditioned_t65_browser_v1.json"
            ),
        },
        {
            "id": "auth_action_level_metrics_t68",
            "task": "T68 action-level Auth-SafeInv allow/deny metrics",
            "script": "analysis/auth_action_level_metrics.py",
            "command": "python analysis/auth_action_level_metrics.py",
            "outputs": [
                "analysis/auth_action_level_metrics_t68.json",
                "analysis/auth_action_level_metrics_t68.md",
            ],
            "summary_fn": auth_action_level_t68_summary,
        },
        {
            "id": "auth_trace_view_ablation_t69",
            "task": "T69 verifier-independence trace-view ablation",
            "script": "analysis/auth_trace_view_ablation_t69.py",
            "command": "python analysis/auth_trace_view_ablation_t69.py",
            "outputs": [
                "analysis/auth_trace_view_ablation_t69.json",
                "analysis/auth_trace_view_ablation_t69.md",
            ],
            "summary_fn": trace_view_ablation_t69_summary,
        },
        {
            "id": "auth_existing_defense_ablation_t70",
            "task": "T70 existing-defense proxy ablation",
            "script": "analysis/auth_existing_defense_ablation_t70.py",
            "command": "python analysis/auth_existing_defense_ablation_t70.py",
            "outputs": [
                "analysis/auth_existing_defense_ablation_t70.json",
                "analysis/auth_existing_defense_ablation_t70.md",
            ],
            "summary_fn": existing_defense_ablation_t70_summary,
        },
        {
            "id": "auth_action_level_calibration_t73",
            "task": "T73 action-level threshold calibration diagnostic",
            "script": "analysis/auth_action_level_calibration_t73.py",
            "command": "python analysis/auth_action_level_calibration_t73.py",
            "outputs": [
                "analysis/auth_action_level_calibration_t73.json",
                "analysis/auth_action_level_calibration_t73.md",
            ],
            "summary_fn": action_level_calibration_t73_summary,
        },
    ]


def build_appendix() -> dict[str, Any]:
    artifacts = []
    for spec in artifact_specs():
        outputs = spec["outputs"]
        present = exists_all(outputs)
        artifacts.append(
            {
                "id": spec["id"],
                "task": spec["task"],
                "script": spec["script"],
                "command": spec["command"],
                "outputs": [
                    {"path": output, "exists": (ROOT / output).exists(), "size_bytes": file_size(output)}
                    for output in outputs
                ],
                "all_outputs_present": present,
                "summary": spec["summary_fn"]() if present else None,
            }
        )
    return {
        "title": "Auth-SafeInv Result-Source Appendix",
        "environment": {
            "conda_env": "causal-safety",
            "primary_model": "Qwen/Qwen3-8B",
            "timezone": "Asia/Shanghai",
        },
        "reproduction_entrypoint": "reproduce_auth_safeinv.sh",
        "artifacts": artifacts,
        "all_outputs_present": all(item["all_outputs_present"] for item in artifacts),
        "caveats": [
            "This appendix maps existing artifacts to commands; it does not rerun GPU-heavy experiments.",
            "Observed traces are controlled local sandbox executions, not live deployed-agent logs.",
            "pIIA results are probe-mediated activation diagnostics, not SCM-style IIA proofs.",
            "T51 compares mitigation against T47 baselines under identical held-out cells; strict train-only projection remains coverage-limited.",
            "T54 shows v2 improves strict-train-only coverage but does not make contrastive projection beat the best non-degenerate baseline.",
            "T55 effect-schema conditioned monitors are pair-free but currently underperform the best T54 non-degenerate baselines.",
            "T57 replaces the oracle present label with deterministic static verifier rules; it is verifier-assisted framework evidence, not live deployment validation.",
            "T58 replaces static present inference with controlled execution-trace verifier outputs, but the traces are still controlled observed/sandbox/static artifacts rather than live deployed-agent logs.",
            "T59 grounds additional traces in real-agent-tools Hermes tool registrations and local file/terminal semantics, but direct handler imports require missing upstream runtime modules and external API tools were not invoked.",
            "T60 DeepSeek traces are direct provider API calls, but they are a tiny pilot over one provider tool surface and do not cover browser/search/messaging tools.",
            "T61 expands the DeepSeek provider API pilot to 120 calls and useful provider-effect counts, but it still covers only one provider API surface.",
            "T62 selects thresholds on validation trace groups and evaluates them on held-out trace groups. It fixes the ex-post-threshold caveat for the tested trace datasets, but it is still not a deployment guarantee.",
            "T63 broadens controlled local-adapter traces to web/search/browser/messaging tool families, but it still does not invoke live external services or deployed-agent logs.",
            "T64 has been rerun with full-precision Qwen3-8B embeddings. It covers key-free live outbound HTTPS plus local webhook protocol boundaries, not provider-backed search/SaaS messaging/deployed runtime.",
            "T65 uses actual headless Chrome over file-backed pages. It closes part of the browser-runtime gap, but not HTTP browser networking, provider-backed search/SaaS messaging, or deployed-agent runtime validation.",
            "T68 aggregates candidate-effect rows to action-level allow/deny metrics. It shows that row-level unauthorized-effect FNR/FPR can hide policy tradeoffs, including high authorized-action false-denial on the T61 provider API and T65 browser-runtime splits.",
            "T69 indicates label-hidden raw trace evidence degrades relative to the full-label verifier after adding T65; the framework should be described as requiring structured execution evidence.",
            "T70 proxy baselines distinguish the framework from pre-action/provenance-only monitors, but the strong raw_status_boundary result means the paper should not claim that learned AuthMonitor dominates all handcrafted trace-policy defenses.",
            "T73 action-level calibration shows that a simple false-denial-constrained threshold can collapse to all-allow on several trace families; this is not a deployable calibration policy.",
        ],
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Auth-SafeInv Result-Source Appendix",
        "",
        f"- Reproduction entrypoint: `{payload['reproduction_entrypoint']}`",
        f"- Conda environment: `{payload['environment']['conda_env']}`",
        f"- Primary model: `{payload['environment']['primary_model']}`",
        f"- All outputs present: {payload['all_outputs_present']}",
        "",
        "## Artifact Map",
        "",
        "| ID | Task | Script | Outputs present | Key summary |",
        "|---|---|---|---:|---|",
    ]
    for artifact in payload["artifacts"]:
        summary = json.dumps(artifact["summary"], ensure_ascii=False, sort_keys=True)
        if len(summary) > 240:
            summary = summary[:237] + "..."
        lines.append(
            f"| `{artifact['id']}` | {artifact['task']} | `{artifact['script']}` | "
            f"{artifact['all_outputs_present']} | `{summary}` |"
        )
    lines.extend(["", "## Commands", ""])
    for artifact in payload["artifacts"]:
        lines.extend([f"### {artifact['id']}", "", "```bash", artifact["command"], "```", ""])
    lines.extend(["## Caveats", ""])
    for caveat in payload["caveats"]:
        lines.append(f"- {caveat}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_appendix()
    out_json = ROOT / "analysis/auth_result_source_appendix.json"
    out_md = ROOT / "analysis/auth_result_source_appendix.md"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(out_md, payload)
    print(f"Saved JSON: {rel(out_json)}")
    print(f"Saved MD:   {rel(out_md)}")
    print(f"All outputs present: {payload['all_outputs_present']}")


if __name__ == "__main__":
    main()
