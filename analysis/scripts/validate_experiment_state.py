"""Global experiment state validator.

Checks: JSON parseability, embedding/text/effect length consistency,
real-tool semantics, wrong_chain type coverage, citation audit completeness,
paper/main.tex forbidden claims.
"""

from __future__ import annotations
import json, sys, re
from pathlib import Path


def check_json_parseable(path: Path) -> dict:
    try:
        with open(path) as f:
            return {"status": "ok", "data": json.load(f)}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def main():
    base = Path(__file__).parent.parent
    results = {}

    # 1. Embedding consistency
    emb_dir = base / "embeddings"
    emb_files = list(emb_dir.glob("embeddings_qwen3-8b_scenarios_merged.npy"))
    if emb_files:
        import numpy as np
        X = np.load(emb_files[0])
        Y_path = Path(str(emb_files[0]).replace("embeddings_", "effects_"))
        texts_path = Path(str(emb_files[0]).replace("embeddings_", "texts_")).with_suffix(".jsonl")
        if Y_path.exists() and texts_path.exists():
            Y = np.load(Y_path)
            texts = [json.loads(line) for line in open(texts_path)]
            results["embeddings_consistency"] = {
                "X_shape": list(X.shape),
                "Y_shape": list(Y.shape),
                "n_texts": len(texts),
                "consistent": X.shape[0] == Y.shape[0] == len(texts),
            }

    # 2. Real-tool semantics
    val_path = base / "analysis/real_tool_scenarios_v2_validation.json"
    if val_path.exists():
        v = check_json_parseable(val_path)
        if v["status"] == "ok":
            d = v["data"]
            results["real_tool_semantics"] = {
                "num_schema_errors": d.get("num_schema_errors", -1),
                "num_missing_flow_fields": d.get("num_missing_flow_fields", -1),
                "num_semantic_conflicts": d.get("num_semantic_conflicts", -1),
                "all_clear": d.get("num_semantic_conflicts", 1) == 0 and d.get("num_missing_flow_fields", 1) == 0,
            }

    # 3. Wrong-chain type coverage
    cc_path = base / "data/causal_chain_conditioning.jsonl"
    if cc_path.exists():
        types_seen = set()
        with open(cc_path) as f:
            for line in f:
                d = json.loads(line)
                if d.get("condition") == "wrong_chain":
                    types_seen.add(d.get("wrong_chain_type", "none"))
        results["wrong_chain_coverage"] = {
            "types_found": sorted(types_seen),
            "authorization_flip_present": "authorization_flip" in types_seen,
        }

    cc_v2_path = base / "data/causal_chain_conditioning_v2.jsonl"
    if cc_v2_path.exists():
        type_counts = {}
        n_rows = 0
        with open(cc_v2_path) as f:
            for line in f:
                d = json.loads(line)
                n_rows += 1
                if d.get("condition") == "wrong_chain":
                    key = d.get("wrong_chain_type", "none")
                    type_counts[key] = type_counts.get(key, 0) + 1
        required_types = {"effect_omission", "effect_flip", "authorization_flip"}
        results["causal_chain_v2_input"] = {
            "n_rows": n_rows,
            "wrong_chain_type_counts": type_counts,
            "all_required_types_present": required_types.issubset(type_counts),
            "all_clear": required_types.issubset(type_counts),
            "note": "Input coverage check; corresponding v2 mechanism results are validated separately when present.",
        }

    cc_result_path = base / "analysis/causal_chain_mechanism_qwen3-8b_causal_chain_conditioning_v2.json"
    if cc_result_path.exists():
        r = check_json_parseable(cc_result_path)
        if r["status"] == "ok":
            d = r["data"]
            required_types = {"effect_omission", "effect_flip", "authorization_flip"}
            wrong_counts = d.get("summary", {}).get("wrong_chain_type_counts", {})
            required_groups = {f"wrong_chain:{t}" for t in required_types}
            effects = d.get("effects", {})
            group_coverage = {
                effect: required_groups.issubset(set(groups.keys()))
                for effect, groups in effects.items()
            }
            results["causal_chain_v2_results"] = {
                "schema_version": d.get("schema_version"),
                "n_samples": d.get("summary", {}).get("n_samples"),
                "wrong_chain_type_counts": wrong_counts,
                "all_required_types_present": required_types.issubset(wrong_counts),
                "all_effects_have_required_wrong_groups": all(group_coverage.values()) if group_coverage else False,
                "all_clear": (
                    d.get("schema_version") == "causal_chain_mechanism_v2"
                    and d.get("summary", {}).get("n_samples") == 2290
                    and required_types.issubset(wrong_counts)
                    and (all(group_coverage.values()) if group_coverage else False)
                ),
            }

    # 4. Citation audit completeness
    cit_path = base / "analysis/citation_audit_v2.json"
    if not cit_path.exists():
        cit_path = base / "analysis/citation_audit.json"
    if cit_path.exists():
        c = check_json_parseable(cit_path)
        if c["status"] == "ok":
            entries = c["data"]
            null_urls = sum(1 for e in entries if e.get("url") is None)
            anon_authors = sum(1 for e in entries if "Anonymous" in str(e.get("authors", [])))
            placeholder_authors = sum(
                1
                for e in entries
                if any(re.fullmatch(r"arXiv:\d{4}\.\d+\s+authors", str(a)) for a in e.get("authors", []))
            )
            results["citation_audit"] = {
                "n_entries": len(entries),
                "null_urls": null_urls,
                "anonymous_authors": anon_authors,
                "placeholder_authors": placeholder_authors,
                "all_clear": null_urls == 0 and anon_authors == 0 and placeholder_authors == 0,
            }

    # 5. Strict LOPO result consistency
    strict_path = base / "analysis/contrastive_strict_lopo_qwen3-8b_scenarios_merged.json"
    if strict_path.exists():
        s = check_json_parseable(strict_path)
        if s["status"] == "ok":
            d = s["data"]
            rows = [
                tr
                for effect in d.get("effects", {}).values()
                for pair in effect.get("pairs", [])
                for tr in pair.get("tool_results", [])
            ]
            vals = [r.get("delta_fnr") for r in rows if r.get("delta_fnr") is not None]
            recomputed = {
                "num_evaluable_effects": sum(
                    1 for effect in d.get("effects", {}).values() if effect.get("status") == "evaluable"
                ),
                "num_strict_tool_cases": len(rows),
                "num_improved": sum(1 for v in vals if v > 0),
                "mean_delta_fnr": round(sum(vals) / len(vals), 4) if vals else 0,
            }
            results["strict_lopo"] = {
                **recomputed,
                "summary_matches": recomputed == d.get("summary", {}),
                "all_clear": recomputed == d.get("summary", {}),
            }

    multiseed_path = base / "analysis/contrastive_multiseed_qwen3-8b_scenarios_merged.json"
    if multiseed_path.exists():
        m = check_json_parseable(multiseed_path)
        if m["status"] == "ok":
            d = m["data"]
            cfg = d.get("config", {})
            results["contrastive_multiseed"] = {
                "schema_version": d.get("schema_version"),
                "generated_by": d.get("generated_by"),
                "seeds": cfg.get("seeds"),
                "train_protocol": cfg.get("train_protocol"),
                "n_effects": len(d.get("results", {})),
                "all_clear": (
                    d.get("schema_version") == "contrastive_multiseed_v2"
                    and d.get("generated_by") == "run_contrastive_multiseed.py"
                    and cfg.get("seeds") == [0, 1, 2, 3, 4]
                    and cfg.get("train_protocol") == "full_training"
                    and len(d.get("results", {})) > 0
                ),
            }

    # 6. Paper forbidden claims
    paper_path = base / "paper/main.tex"
    forbidden = []
    stale_claims = []
    if paper_path.exists():
        text = paper_path.read_text()
        # Check for removed claims
        if "improving 40/68 strict leave-one-pair-out cases" in text:
            forbidden.append("unsupported_40_68_strict_in_abstract")
        if "improves 40/68 cases (59%)" in text:
            forbidden.append("unsupported_40_68_strict_in_body")
        if "real-agent validation" in text.lower() or "real execution" in text.lower():
            forbidden.append("may_claim_real_agent_validation")
        if "strict leave-one-pair-out evaluation is currently limited to taxonomy classification" in text:
            stale_claims.append("strict_lopo_stale_taxonomy_only")
        if "pair-level strict reruns require dedicated scripts" in text:
            stale_claims.append("strict_lopo_stale_rerun_pending")

    results["paper_forbidden_claims"] = forbidden
    results["paper_stale_claims"] = stale_claims

    # Summary
    all_ok = (
        results.get("embeddings_consistency", {}).get("consistent", False)
        and results.get("real_tool_semantics", {}).get("all_clear", False)
        and results.get("causal_chain_v2_results", {}).get("all_clear", False)
        and results.get("citation_audit", {}).get("null_urls", 1) == 0
        and results.get("citation_audit", {}).get("anonymous_authors", 1) == 0
        and results.get("citation_audit", {}).get("placeholder_authors", 1) == 0
        and results.get("strict_lopo", {}).get("summary_matches", False)
        and results.get("contrastive_multiseed", {}).get("all_clear", False)
        and len(forbidden) == 0
        and len(stale_claims) == 0
    )
    results["overall"] = "ok" if all_ok else "issues_found"

    out = base / "analysis/experiment_state_validation.json"
    out.write_text(json.dumps(results, indent=2))

    print("Experiment State Validation:")
    for k, v in results.items():
        if k != "overall":
            status = "✅" if (isinstance(v, dict) and v.get("all_clear", False)) or (isinstance(v, list) and len(v) == 0) else "⚠️"
            print(f"  {status} {k}: {v}")
    print(f"\nOverall: {results['overall']}")
    print(f"Saved to {out}")

if __name__ == "__main__":
    main()
