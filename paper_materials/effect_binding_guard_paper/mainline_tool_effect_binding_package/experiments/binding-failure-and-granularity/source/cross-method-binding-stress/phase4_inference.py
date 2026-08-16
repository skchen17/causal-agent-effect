from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any

from .io_utils import read_jsonl, stable_id, write_json, write_jsonl
from .phase3_external_smoke import (
    build_gguf_completer,
    build_transformers_completer,
    parse_system_output,
    release_model_memory,
)
from .phase3_official_stress import build_stress_prompt, decision_from_parse
from .phase4_methods import build_local_qwen_prompt, parse_local_qwen_decision
from .schema import ClaimScope, Decision, MethodInputView, ToolEffectPrediction, ToolEffectStressCase


METHOD_CONFIG = {
    "toolsafe": {
        "method_name": "ts_guard_official_counterfactual_stress",
        "model_path": "models/MurrayTom/TS-Guard",
        "backend": "official_transformers",
        "view": MethodInputView.STEP_TEXT.value,
        "claim_scope": ClaimScope.ORIGINAL_METHOD_CUSTOM_STRESS.value,
    },
    "safiron": {
        "method_name": "safiron_official_counterfactual_stress",
        "model_path": "models/Safiron/Safiron",
        "backend": "official_transformers",
        "view": MethodInputView.PLAN_TEXT.value,
        "claim_scope": ClaimScope.ORIGINAL_METHOD_CUSTOM_STRESS.value,
    },
    "local_qwen": {
        "method_name": "local_qwen_self_audit",
        "model_path": "models/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf",
        "backend": "local_gguf",
        "view": MethodInputView.STATIC_TEXT.value,
        "claim_scope": ClaimScope.BASELINE.value,
    },
}

FORBIDDEN_PROMPT_FIELDS = (
    '"expected_decision"',
    '"risk_label"',
    '"realized_effect"',
    '"labels"',
    '"authorized_effects"',
    '"authorized_resources"',
    '"audit_status"',
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 4 counterfactual inference with shard/resume.")
    parser.add_argument("--method", choices=sorted(METHOD_CONFIG), required=True)
    parser.add_argument("--cases", default="data/tool_effect_fragmentation/counterfactual_core_phase4.jsonl")
    parser.add_argument("--output-prefix", default="")
    parser.add_argument("--shard-dir", default="")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--max-input-tokens", type=int, default=4096)
    parser.add_argument("--n-gpu-layers", type=int, default=-1)
    parser.add_argument("--n-ctx", type=int, default=8192)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    cfg = METHOD_CONFIG[args.method]
    output_prefix = (
        root / args.output_prefix
        if args.output_prefix
        else root / f"analysis/results/tool_effect_fragmentation_counterfactual_phase4_{args.method}"
    )
    shard_dir = (
        root / args.shard_dir
        if args.shard_dir
        else root / f"analysis/results/tool_effect_fragmentation_counterfactual_phase4_{args.method}_shards"
    )
    if args.force_rerun and shard_dir.exists():
        shutil.rmtree(shard_dir)
    result = run_inference(
        root,
        args.method,
        cases_path=root / args.cases,
        shard_dir=shard_dir,
        max_cases=args.max_cases,
        max_new_tokens=args.max_new_tokens,
        max_input_tokens=args.max_input_tokens,
        n_gpu_layers=args.n_gpu_layers,
        n_ctx=args.n_ctx,
        resume=args.resume,
    )
    write_json(output_prefix.with_suffix(".json"), {key: value for key, value in result.items() if key not in {"rows", "predictions"}})
    write_jsonl(output_prefix.with_suffix(".jsonl"), result["rows"])
    write_jsonl(output_prefix.with_name(output_prefix.name + "_predictions").with_suffix(".jsonl"), result["predictions"])
    output_prefix.with_suffix(".md").write_text(inference_markdown(result), encoding="utf-8")


def run_inference(
    root: Path,
    method: str,
    *,
    cases_path: Path,
    shard_dir: Path,
    max_cases: int,
    max_new_tokens: int,
    max_input_tokens: int,
    n_gpu_layers: int,
    n_ctx: int,
    resume: bool,
) -> dict[str, Any]:
    cfg = METHOD_CONFIG[method]
    cases = [ToolEffectStressCase.from_dict(row) for row in read_jsonl(cases_path)]
    if max_cases:
        cases = cases[:max_cases]
    shard_dir.mkdir(parents=True, exist_ok=True)
    pending = [case for case in cases if not (resume and shard_path(shard_dir, case).exists())]
    complete = None
    if pending:
        model_path = root / cfg["model_path"]
        if not model_path.exists():
            raise FileNotFoundError(model_path)
        if cfg["backend"] == "official_transformers":
            complete = build_transformers_completer(
                model_path,
                max_new_tokens=max_new_tokens,
                max_input_tokens=max_input_tokens,
            )
        else:
            complete = build_gguf_completer(
                model_path,
                n_gpu_layers=n_gpu_layers,
                n_ctx=n_ctx,
                max_new_tokens=max_new_tokens,
                json_mode=True,
            )
    started = time.time()
    for case in pending:
        prompt = build_prompt(root, method, case)
        leaked = [field for field in FORBIDDEN_PROMPT_FIELDS if field in prompt]
        if leaked:
            raise ValueError(f"Forbidden gold fields in prompt for {case.case_id}: {leaked}")
        gold_effect_values = {
            str(value)
            for value in (
                case.realized_effect,
                case.metadata.get("anchor_effect"),
                case.metadata.get("changed_effect_from"),
                *(case.metadata.get("anchor_effects") or []),
                *(case.metadata.get("realized_effects") or []),
            )
            if value
        }
        leaked_effect_values = sorted(value for value in gold_effect_values if value in prompt)
        if leaked_effect_values:
            raise ValueError(f"Forbidden gold effect values in prompt for {case.case_id}: {leaked_effect_values}")
        raw_output = complete(prompt) if complete else ""
        parsed = parse_output(method, raw_output)
        decision = parsed.get("decision", Decision.ABSTAIN.value)
        prediction = ToolEffectPrediction(
            prediction_id=f"{cfg['method_name']}::{case.case_id}",
            case_id=case.case_id,
            source_system=case.source_system,
            method_name=cfg["method_name"],
            predicted_decision=decision,
            predicted_effect="not_inferred_by_guard",
            predicted_risk_label="unsafe" if decision == Decision.DENY.value else "safe" if decision == Decision.ALLOW.value else "uncertain",
            confidence=1.0 if parsed.get("valid") else 0.0,
            abstained=decision == Decision.ABSTAIN.value,
            method_input_view=cfg["view"],
            claim_scope=cfg["claim_scope"],
            allowed_input_fields=["user_task", "tool_inventory", "tool_call_or_plan"],
            accessed_input_fields=["user_task", "tool_inventory", "tool_call_or_plan"],
            action_id=case.action_id,
            metadata={
                "phase4_counterfactual": True,
                "official_checkpoint": cfg["backend"] == "official_transformers",
                "gold_case_fields_not_accessed": True,
                "explicit_effect_prediction": False,
                "tools_executed": False,
                "side_effects_executed": False,
            },
        )
        write_json(
            shard_path(shard_dir, case),
            {
                "case_id": case.case_id,
                "counterfactual_group_id": case.counterfactual_group_id,
                "pair_role": case.pair_role,
                "counterfactual_axis": case.counterfactual_axis,
                "expected_decision": case.expected_decision,
                "prompt": prompt,
                "prompt_forbidden_fields_found": leaked,
                "prompt_forbidden_gold_effect_values_found": leaked_effect_values,
                "raw_output": raw_output,
                "parsed_output": parsed,
                "prediction": prediction.to_dict(),
                "tools_executed": False,
                "side_effects_executed": False,
            },
        )
    if complete is not None:
        del complete
        release_model_memory()
    rows = [json.loads(shard_path(shard_dir, case).read_text(encoding="utf-8")) for case in cases if shard_path(shard_dir, case).exists()]
    predictions = [row["prediction"] for row in rows]
    return {
        "schema_version": "tool_effect_fragmentation_counterfactual_phase4_inference_v1",
        "method_key": method,
        "method_name": cfg["method_name"],
        "backend": cfg["backend"],
        "claim_scope": cfg["claim_scope"],
        "model_path": cfg["model_path"],
        "n_requested": len(cases),
        "n_completed": len(rows),
        "n_parse_valid": sum(bool(row["parsed_output"].get("valid")) for row in rows),
        "parse_valid_rate": sum(bool(row["parsed_output"].get("valid")) for row in rows) / len(rows) if rows else None,
        "elapsed_seconds_this_run": time.time() - started,
        "shard_dir": str(shard_dir),
        "safety_contract": {"tools_executed": False, "side_effects_executed": False, "outputs_executed": False},
        "rows": rows,
        "predictions": predictions,
    }


def build_prompt(root: Path, method: str, case: ToolEffectStressCase) -> str:
    if method in {"toolsafe", "safiron"}:
        return build_stress_prompt(root, method, case)
    return build_local_qwen_prompt(case)


def parse_output(method: str, raw_output: str) -> dict[str, Any]:
    if method in {"toolsafe", "safiron"}:
        parsed = parse_system_output(method, raw_output)
        parsed["decision"] = decision_from_parse(method, parsed)
        return parsed
    return parse_local_qwen_decision(raw_output)


def shard_path(shard_dir: Path, case: ToolEffectStressCase) -> Path:
    return shard_dir / f"{stable_id(case.case_id, length=24)}.json"


def inference_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Phase 4 Counterfactual Inference: {result['method_name']}",
            "",
            f"- Backend: `{result['backend']}`",
            f"- Claim scope: `{result['claim_scope']}`",
            f"- Completed: `{result['n_completed']}/{result['n_requested']}`",
            f"- Parse-valid: `{result['n_parse_valid']}/{result['n_completed']}`",
            "- Tools executed: `False`",
            "- Side effects executed: `False`",
            "",
            "## Claim Boundary",
            "",
            "- Official checkpoints run on E47 controlled counterfactual inputs, not original-paper benchmark protocols.",
            "- Local-Qwen self-audit is a baseline, not an independent ground-truth judge.",
        ]
    )


if __name__ == "__main__":
    main()
