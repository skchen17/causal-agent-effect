"""Failure-driven rule discovery loop (CEGAR) -- cegar.py.

Replays the counterexample-guided cycle of the design doc (section 5.3):

    failure -> Gate 1 (classify) -> Gate 2 (induce candidate rule)
            -> Gate 3 (counterfactual validate) -> register / refuse.

Gates:
  Gate 1 -- classify.  Every failure case carries a ``classification``:
      "false_negative"      interface/grounding defect; proceed.
      "model_limitation"    model capability defect; proceed (the induced
                            rule is still validated on effects, so a model
                            defect cannot smuggle in an unsafe rule).
      "security_event"      safety-critical; hard stop, no rule induction
                            (fail-closed: keep literal comparison).

  Gate 2 -- induce.  The candidate rule is carried by the failure case
      (scripted here; in the live system an analyst/LLM produces it).  The
      structural sanity check rejects candidates whose transform name is
      unknown or whose schema fails ``validate_rule_spec``.

  Gate 3 -- validate.  The candidate runs through ValidationPipeline:
      ACCEPT  -> register in the registry (deduplicated), mark covered.
      REJECT  -> refuse registration; failure marked unsafe-to-merge
                 (runtime keeps literal comparison -- fail-closed).
      UNDETERMINED -> not registered; fail-closed, not covered.

The output is a replay trace plus a convergence record.  "Disposed" means the
loop reached a final disposition for the failure (registered / refused /
fail-closed); a refusal is itself a convergent outcome (no unsafe rule is
induced).  "Covered" means a registered rule covers the failure.  Deterministic,
CPU-only, stdlib-only.
"""
from __future__ import annotations

from typing import Any

from registry import Registry, validate_rule_spec
from validation import ValidationPipeline, VERDICT_ACCEPT, VERDICT_UNDETERMINED


class CegarReplay:
    """Replayable CEGAR loop against a (possibly empty) registry."""

    def __init__(self, oracle: Any, registry: Registry | None = None) -> None:
        self.oracle = oracle
        self.registry = registry if registry is not None else Registry()
        self.pipeline = ValidationPipeline(oracle)

    def _gate1(self, case: dict[str, Any]) -> dict[str, Any]:
        classification = case.get("classification")
        if classification == "security_event":
            return {
                "decision": "stop",
                "classification": classification,
                "reason": "security event; no rule induction (fail-closed)",
            }
        return {
            "decision": "proceed",
            "classification": classification,
            "reason": "interface/grounding defect; candidate may be induced "
                      "but must pass effect validation",
        }

    def _gate2(self, case: dict[str, Any]) -> dict[str, Any]:
        candidate = case.get("induced_rule")
        if not isinstance(candidate, dict):
            return {
                "decision": "reject",
                "reason": "failure case carries no candidate rule",
                "candidate_rule_id": None,
            }
        errors = validate_rule_spec(candidate)
        if errors:
            return {
                "decision": "reject",
                "reason": f"structural schema failure: {errors}",
                "candidate_rule_id": candidate.get("rule_id"),
            }
        return {
            "decision": "accept_candidate",
            "reason": "structural sanity check passed",
            "candidate_rule_id": candidate.get("rule_id"),
            "field_role": candidate.get("field_role"),
            "tool": candidate.get("tool"),
            "transform": candidate.get("transform"),
        }

    def _gate3(self, candidate: dict[str, Any]) -> dict[str, Any]:
        return self.pipeline.validate_rule(candidate)

    # ------------------------------------------------------------------
    # replay
    # ------------------------------------------------------------------
    def run(self, failure_cases: list[dict[str, Any]]) -> dict[str, Any]:
        """Replay the loop over the given failure cases. Returns trace + record."""
        trace: list[dict[str, Any]] = []
        for case in failure_cases:
            step: dict[str, Any] = {
                "failure_id": case.get("failure_id"),
                "source": case.get("source"),
                "case_label": case.get("case_label"),
                "observed": case.get("observed"),
            }
            g1 = self._gate1(case)
            step["gate1"] = g1
            if g1["decision"] == "stop":
                step["action"] = "no_rule"
                step["covered"] = False
                step["fail_closed"] = True
                trace.append(step)
                continue

            g2 = self._gate2(case)
            step["gate2"] = g2
            if g2["decision"] == "reject":
                step["action"] = "candidate_rejected_structural"
                step["covered"] = False
                step["fail_closed"] = True
                trace.append(step)
                continue

            candidate = case["induced_rule"]
            record = self._gate3(candidate)
            step["gate3"] = {
                "verdict": record["verdict"],
                "verdict_reason": record["verdict_reason"],
                "calibrated": record["calibrated"],
                "evidence_kind": record["evidence_kind"],
                "n_samples": record["n_samples"],
                "n_probes": record["n_probes"],
                "violations": record["violations"],
                "overmerges": record["overmerges"],
            }

            expected = case.get("expected")
            if expected is not None:
                step["matches_expected"] = record["verdict"] == expected

            if record["verdict"] == VERDICT_ACCEPT:
                rule_id = candidate["rule_id"]
                if not self.registry.has_rule(rule_id):
                    self.registry.add_rule(candidate, validation_record=record)
                    step["action"] = "registered"
                else:
                    step["action"] = "already_registered"
                step["covered"] = True
                step["fail_closed"] = False
                step["registered_rule_id"] = rule_id
            elif record["verdict"] == VERDICT_UNDETERMINED:
                step["action"] = "undetermined_fail_closed"
                step["covered"] = False
                step["fail_closed"] = True
            else:  # REJECT
                step["action"] = "refused"
                step["covered"] = False
                step["fail_closed"] = True
                step["rejected_rule_id"] = candidate.get("rule_id")
            trace.append(step)

        return self._convergence_record(trace)

    def _convergence_record(self, trace: list[dict[str, Any]]) -> dict[str, Any]:
        n_cases = len(trace)
        n_covered = sum(1 for step in trace if step.get("covered"))
        n_registered = sum(
            1 for step in trace if step.get("action") in ("registered", "already_registered")
        )
        n_refused = sum(
            1 for step in trace if step.get("action") in ("refused", "candidate_rejected_structural")
        )
        registered_rules = [
            step.get("registered_rule_id")
            for step in trace
            if step.get("registered_rule_id") is not None
        ]
        return {
            "n_failures": n_cases,
            "n_covered": n_covered,
            "n_registered_rules": n_registered,
            "n_refused": n_refused,
            "registered_rule_ids": sorted(set(registered_rules)),
            "registry_n_rules": len(self.registry.rules),
            "all_failures_disposed": n_cases > 0 and all(
                "action" in step for step in trace
            ),
            "all_failures_covered": n_cases > 0 and n_covered == n_cases,
            "trace": trace,
        }
