#!/usr/bin/env python3
"""Dump N-condition successful trajectories for banking/15 & travel/8 (read-only)."""
import json, re

PKG = "/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package"
P = f"{PKG}/experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-pilot-36-allow-with-trail-deepseek-iffix-20260807"
FN = "<" + "function=" + "([A-Za-z0-9_]+)>(.*?)" + "</" + "function>"

for suite, t in [("banking", "user_task_15"), ("travel", "user_task_8"),
                 ("banking", "user_task_3"), ("banking", "user_task_11"),
                 ("slack", "user_task_17")]:
    d = json.load(open(f"{P}/agentdojo_logs_noguard/local/{suite}/{t}/none/none.json"))
    print("=====", suite, t, "N utility=", d["utility"])
    for m in d["messages"]:
        c = m.get("content")
        txt = "\n".join(p.get("content", "") for p in c if isinstance(p, dict)) if isinstance(c, list) else (c or "")
        if m["role"] == "assistant":
            for mm in re.finditer(FN, txt, re.S):
                print("  CALL:", mm.group(1), mm.group(2)[:300].replace("\n", " "))
    print("  N final:", (d["messages"][-1].get("content") if isinstance(d["messages"][-1].get("content"), str) else "")[:200])
