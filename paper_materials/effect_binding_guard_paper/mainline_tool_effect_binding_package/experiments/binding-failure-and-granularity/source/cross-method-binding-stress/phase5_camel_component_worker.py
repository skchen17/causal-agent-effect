from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CaMeL original security-policy component on Phase 5 structures.")
    parser.add_argument("--cases", default="data/tool_effect_fragmentation/camel_structural_counterfactual_phase5.jsonl")
    parser.add_argument("--output", default="analysis/results/tool_effect_fragmentation_camel_component_phase5.jsonl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sys.path.insert(0, str(ROOT / "external/systems/camel/src"))
    from camel.capabilities import Capabilities
    from camel.capabilities import readers, sources
    from camel.interpreter.value import CaMeLStr
    from camel.security_policy import Allowed, SecurityPolicyEngine

    class StructuralEngine:
        check_policy = SecurityPolicyEngine.check_policy

        def __init__(self, policy_name: str, no_side_effect: bool) -> None:
            self.no_side_effect_tools = {policy_name} if no_side_effect else set()
            self.policies = [(policy_name, lambda tool_name, kwargs: Allowed())]

    inputs = [json.loads(line) for line in (ROOT / args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for case in inputs:
        structure = case["structure"]
        public = structure["readers"] == "public"
        reader_set = readers.Public() if public else frozenset({"owner"})
        source = sources.SourceEnum.User if structure["data_source"] == "user" else sources.Tool(structure["data_source"])
        metadata = Capabilities(frozenset({source}), reader_set)
        value = CaMeLStr.from_raw(str(structure["resource"]), metadata, ())
        dependency = value if structure["control_source"] != "user" or not public else None
        engine = StructuralEngine(structure["policy_name"], no_side_effect=not structure["side_effectful"])
        decision = engine.check_policy(
            structure["tool_name"],
            {"resource": value},
            [dependency] if dependency is not None else [],
        )
        predicted = "ALLOW" if type(decision).__name__ == "Allowed" else "DENY"
        rows.append(
            {
                "case_id": case["case_id"],
                "counterfactual_group_id": case["counterfactual_group_id"],
                "variant": case["variant"],
                "expected_decision": case["expected_decision"],
                "predicted_decision": predicted,
                "policy_result_type": type(decision).__name__,
                "policy_reason": getattr(decision, "reason", ""),
                "claim_scope": "original_component_custom_stress",
                "original_component": "camel.security_policy.SecurityPolicyEngine.check_policy",
                "tools_executed_in_simulation": False,
                "real_side_effects": False,
            }
        )
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(json_ready(row), ensure_ascii=False, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


if __name__ == "__main__":
    main()
