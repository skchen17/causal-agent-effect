"""Counterfactual validation pipeline for canonicalization rules.

For a rule r and a field role, the pipeline takes sample pairs (v, w) and,
against the finite-domain effect oracle (``domain_oracle.DomainOracle``),
computes the differential that instantiates the design definition:

    v1 ~= v2 (for field role r)  <=>  filling the call and executing yields
    the same safety-relevant effects AND the same authorization conclusions.

Because authorization conclusions are a deterministic function of the
projected effect signature in this framework, the differential reduces to
comparing projected effect signatures ``sig(.)``:

  D1 : sig(v)  == sig(r(v))   -- applying the transform to v preserves the
                                 projected safety-relevant effect signature;
  D2 : sig(w)  == sig(r(w))   -- same for w;
  merge : if r(v) == r(w) (the rule collapses the two values) then the oracle
          must already deem v and w equivalent: sig(v) == sig(w).

Decision rules (fail-closed):
  ACCEPT       <=>  tool calibrated AND samples non-empty AND no sample
                    violates D1/D2/merge AND no probe over-merges
                    (rule collapses oracle-distinct values).
  REJECT       <=>  a sample violates the preservation condition, or a probe
                    over-merges.
  UNDETERMINED <=>  tool uncalibrated (the oracle cannot reproduce its
                    observed effects, e.g. slack's opaque payload digest), or
                    no samples were provided, or the role is not declared for
                    the tool.  The runtime therefore keeps literal comparison.

The pipeline records per-sample evidence (D1/D2/merge flags, merged flag,
evidence kind observed/mixed/modeled) and per-probe over-merge checks.
Deterministic, CPU-only, stdlib-only; reads the frozen domain read-only.
"""
from __future__ import annotations

from typing import Any

from transforms import apply_transform

VERDICT_ACCEPT = "ACCEPT"
VERDICT_REJECT = "REJECT"
VERDICT_UNDETERMINED = "UNDETERMINED"


class ValidationPipeline:
    """Runs the counterfactual differential for one rule at a time."""

    def __init__(self, oracle: Any) -> None:
        self.oracle = oracle

    # ------------------------------------------------------------------
    # primitives
    # ------------------------------------------------------------------
    def _signature(self, tool: str, role: str, value: Any) -> str:
        """Projected effect signature of the call with ``role`` = value."""
        return self.oracle.signature_for_role_value(tool, role, value)

    def _evidence_kind(self, tool: str, role: str, v: Any, w: Any) -> str:
        v_obs = self.oracle.value_observed(tool, role, v)
        w_obs = self.oracle.value_observed(tool, role, w)
        if v_obs and w_obs:
            return "observed"
        if v_obs or w_obs:
            return "mixed"
        return "modeled"

    # ------------------------------------------------------------------
    # main entry
    # ------------------------------------------------------------------
    def validate_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        """Validate a rule spec and return a full validation record."""
        rule_id = rule["rule_id"]
        tool = rule["tool"]
        role = rule["field_role"]
        transform = rule["transform"]
        samples = list(rule.get("samples", []))
        probes = list(rule.get("probes", []))

        base: dict[str, Any] = {
            "rule_id": rule_id,
            "field_role": role,
            "tool": tool,
            "transform": transform,
        }

        # Gate: calibration (the oracle must reproduce observed effects).
        if not self.oracle.is_calibrated(tool):
            return {
                **base,
                "calibrated": False,
                "verdict": VERDICT_UNDETERMINED,
                "verdict_reason": (
                    f"tool '{tool}' is uncalibrated; fail-closed (literal "
                    "comparison retained)"
                ),
                "n_samples": len(samples),
                "n_probes": len(probes),
                "evidence_kind": "none",
                "samples": [],
                "probes": [],
                "violations": [],
                "overmerges": [],
            }

        if not samples:
            return {
                **base,
                "calibrated": True,
                "verdict": VERDICT_UNDETERMINED,
                "verdict_reason": "no samples provided; fail-closed",
                "n_samples": 0,
                "n_probes": len(probes),
                "evidence_kind": "none",
                "samples": [],
                "probes": [],
                "violations": [],
                "overmerges": [],
            }

        # Role must be declared for the tool (arg_field_for_role).
        if self.oracle.arg_field_for_role(tool, role) is None:
            return {
                **base,
                "calibrated": True,
                "verdict": VERDICT_UNDETERMINED,
                "verdict_reason": (
                    f"role '{role}' not declared for tool '{tool}'; fail-closed"
                ),
                "n_samples": len(samples),
                "n_probes": len(probes),
                "evidence_kind": "none",
                "samples": [],
                "probes": [],
                "violations": [],
                "overmerges": [],
            }

        sample_records: list[dict[str, Any]] = []
        violations: list[int] = []
        for idx, sample in enumerate(samples):
            v, w = sample["v"], sample["w"]
            rv = apply_transform(transform, v)
            rw = apply_transform(transform, w)
            sv = self._signature(tool, role, v)
            srv = self._signature(tool, role, rv)
            sw = self._signature(tool, role, w)
            srw = self._signature(tool, role, rw)
            d1_ok = sv == srv
            d2_ok = sw == srw
            merged = str(rv) == str(rw)
            merge_ok = (not merged) or (sv == sw)
            violation = not (d1_ok and d2_ok and merge_ok)
            if violation:
                violations.append(idx)
            sample_records.append(
                {
                    "index": idx,
                    "kind": sample.get("kind", "positive"),
                    "v": v,
                    "w": w,
                    "rv": rv,
                    "rw": rw,
                    "merged": merged,
                    "d1_effect_preserved": d1_ok,
                    "d2_effect_preserved": d2_ok,
                    "merge_oracle_equivalent": merge_ok,
                    "violation": violation,
                    "evidence": self._evidence_kind(tool, role, v, w),
                    "sig_v": sv,
                    "sig_w": sw,
                }
            )

        probe_records: list[dict[str, Any]] = []
        overmerges: list[int] = []
        for idx, probe in enumerate(probes):
            v, w = probe["v"], probe["w"]
            rv = apply_transform(transform, v)
            rw = apply_transform(transform, w)
            sv = self._signature(tool, role, v)
            sw = self._signature(tool, role, w)
            merged = str(rv) == str(rw)
            oracle_distinct = sv != sw
            overmerge = merged and oracle_distinct
            if overmerge:
                overmerges.append(idx)
            probe_records.append(
                {
                    "index": idx,
                    "v": v,
                    "w": w,
                    "rv": rv,
                    "rw": rw,
                    "merged": merged,
                    "oracle_distinct": oracle_distinct,
                    "overmerge": overmerge,
                }
            )

        # Dominant evidence kind across samples.
        kinds = {rec["evidence"] for rec in sample_records}
        if kinds == {"observed"}:
            evidence_kind = "observed"
        elif "modeled" in kinds:
            evidence_kind = "modeled"
        else:
            evidence_kind = "mixed"

        if violations or overmerges:
            verdict = VERDICT_REJECT
            reasons = []
            if violations:
                reasons.append(f"sample violations at indices {violations}")
            if overmerges:
                reasons.append(f"probe over-merges at indices {overmerges}")
            reason = "; ".join(reasons)
        else:
            verdict = VERDICT_ACCEPT
            reason = "all samples effect-preserving; no probe over-merged"

        return {
            **base,
            "calibrated": True,
            "verdict": verdict,
            "verdict_reason": reason,
            "n_samples": len(samples),
            "n_probes": len(probes),
            "evidence_kind": evidence_kind,
            "samples": sample_records,
            "probes": probe_records,
            "violations": violations,
            "overmerges": overmerges,
        }
