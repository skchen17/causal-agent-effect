"""T50: Generate result-source appendix mapping paper claims to artifact files."""
import json
from pathlib import Path

def main():
    base = Path(__file__).parent.parent
    results_dir = base / "analysis/results"

    # Scan results directory
    artifacts = {}
    if results_dir.exists():
        for f in sorted(results_dir.glob("*.json")):
            try:
                d = json.loads(f.read_text())
                key_count = len(d) if isinstance(d, dict) else len(d) if isinstance(d, list) else 1
                artifacts[f.name] = {"size": f.stat().st_size, "keys": key_count, "exists": True}
            except: artifacts[f.name] = {"size": f.stat().st_size, "exists": True, "parse_error": True}

    # Map paper sections to files
    mapping = [
        {"paper_section": "Layer 1 — LOTO fragmentation", "files": [
            "fnr_frag_qwen3-8b_scenarios_merged.json",
            "baseline_comparison_qwen3-8b_scenarios_merged.json",
            "baseline_comparison_qwen3-8b_scenarios_mainconf_v2.json"]},
        {"paper_section": "Layer 1 — pIIA diagnostics", "files": [
            "iia_true_qwen3-8b_scenarios_merged.json",
            "piia_controls_qwen3-8b_scenarios_mainconf_v2.json",
            "piia_hook_controls_confirmatory_qwen3-8b_scenarios_mainconf_v2.json"]},
        {"paper_section": "Layer 1 — Lexical control", "files": [
            "lexical_control_qwen3-8b_scenarios_merged_lexical_control.json"]},
        {"paper_section": "Layer 2 — Trace-label ablation (T69)", "files": [
            "auth_trace_view_ablation_*.json"]},
        {"paper_section": "Layer 3 — Action-level (T68/T73)", "files": [
            "auth_action_level_*.json",
            "auth_action_level_calibration_*.json"]},
        {"paper_section": "Auth-SafeInv evaluation", "files": [
            "auth_safeinv_*.json",
            "auth_baseline_confirmatory_*.json",
            "auth_mitigation_vs_baseline_*.json"]},
        {"paper_section": "Existing defense proxy (T70)", "files": [
            "auth_existing_defense_ablation_*.json"]},
        {"paper_section": "Reproducibility", "files": [
            "reproduce_auth_safeinv.sh"]},
    ]

    appendix = {"artifacts": artifacts, "paper_mapping": mapping,
                "all_outputs_present": all(a["exists"] for a in artifacts.values() if not a.get("parse_error"))}

    out_json = base / "analysis/results/auth_result_source_appendix.json"
    out_json.parent.mkdir(exist_ok=True)
    out_json.write_text(json.dumps(appendix, indent=2))
    print(f"Saved to {out_json}")

    # MD version
    md = ["# Auth-SafeInv Result-Source Appendix", "", f"**{len(artifacts)} artifacts found**", "",
          "## Paper Section → Result Files", ""]
    for m in mapping:
        md.append(f"### {m['paper_section']}")
        for f in m["files"]:
            md.append(f"- `analysis/results/{f}`")
        md.append("")
    out_md = base / "analysis/results/auth_result_source_appendix.md"
    out_md.write_text("\n".join(md))
    print(f"Saved to {out_md}")

if __name__ == "__main__": main()
