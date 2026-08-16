#!/usr/bin/env python3
"""Dump message-level trajectories for selected cases (G vs N). Read-only."""
import json, sys

PKG = "/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package"
P = f"{PKG}/experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-pilot-36-allow-with-trail-deepseek-iffix-20260807"

def text(c):
    if isinstance(c, list):
        return "\n".join(p.get("content", "") for p in c if isinstance(p, dict))
    return str(c)

def dump(suite, task, base, tag, maxlen=1400):
    d = json.load(open(f"{base}/{suite}/{task}/none/none.json"))
    print(f"\n########## {tag} {suite}/{task} utility={d['utility']} msgs={len(d['messages'])}")
    for i, m in enumerate(d["messages"]):
        t = text(m["content"])
        print(f"--- [{i}] {m['role']} ({len(t)}ch)")
        print(t[:maxlen])
        if len(t) > maxlen:
            print(f"...[truncated {len(t)-maxlen}ch]...")

if __name__ == "__main__":
    suite, task = sys.argv[1].split("/")
    maxlen = int(sys.argv[2]) if len(sys.argv) > 2 else 1400
    dump(suite, task, f"{P}/agentdojo_logs/local-ours_e77_effect_diff_runtime", "G", maxlen)
    dump(suite, task, f"{P}/agentdojo_logs_noguard/local", "N", maxlen)
