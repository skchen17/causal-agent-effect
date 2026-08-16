#!/usr/bin/env python3
"""Task A/B: extract guard intervention chains per case from G-run audit + logs.

Segment attribution: audit events are chronological; each task_plan event starts a
case segment. Cases whose agent never triggered the guard pipeline have no segment
(slack/user_task_8: zero tool calls; workspace/user_task_0: guard never planned).
Alignment is greedy chronological with tool-multiset containment verification.

Read-only on the pilot run dir; derived JSON written into this analysis dir.
"""
import json, os, re, collections

PKG = "/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package"
P = f"{PKG}/experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-pilot-36-allow-with-trail-deepseek-iffix-20260807"
OUT = os.path.dirname(os.path.abspath(__file__))

FUNC = "<" + "function=" + "([A-Za-z0-9_]+)>"  # assistant tool-call markup

def load_case(logdir):
    d = json.load(open(logdir))
    tools, texts = [], []
    final_assistant = None
    for m in d["messages"]:
        c = m.get("content")
        txt = ""
        if isinstance(c, list):
            txt = "\n".join(p.get("content", "") for p in c if isinstance(p, dict))
        elif isinstance(c, str):
            txt = c
        if m["role"] == "assistant":
            tools.extend(re.findall(FUNC, txt))
            final_assistant = txt
        texts.append({"role": m["role"], "text": txt})
    return {"end": d["evaluation_timestamp"], "utility": d["utility"],
            "tools": tools, "messages": texts, "final": final_assistant,
            "duration": d["duration"]}

def main():
    paired = json.load(open(f"{P}/paired_accounting_deepseek_pilot.json"))
    G, N = paired["G"], paired["N"]
    evs = [json.loads(l) for l in open(f"{P}/runtime_audit.jsonl")]
    segments, cur = [], None
    for i, e in enumerate(evs):
        if e["event"] == "task_plan":
            if cur:
                segments.append(cur)
            cur = {"qh": e["query_hash"], "idx": len(segments), "events": [e]}
        else:
            cur["events"].append(e)
    segments.append(cur)

    GLOG = f"{P}/agentdojo_logs/local-ours_e77_effect_diff_runtime"
    NLOG = f"{P}/agentdojo_logs_noguard/local"
    cases = {}
    for suite in ["banking", "slack", "travel", "workspace"]:
        for task in sorted(os.listdir(f"{GLOG}/{suite}")):
            key = f"{suite}/{task}"
            g = load_case(f"{GLOG}/{suite}/{task}/none/none.json")
            np = f"{NLOG}/{suite}/{task}/none/none.json"
            n = load_case(np) if os.path.exists(np) else None
            cases[key] = {"G": g, "N": n}

    order = sorted(cases, key=lambda k: cases[k]["G"]["end"])

    def seg_tools(seg):
        return collections.Counter(e.get("tool_name") for e in seg["events"]
                                   if e["event"] == "precommit_check")

    segmap, skipped, si = {}, [], 0
    for k in order:
        if si >= len(segments):
            skipped.append(k); continue
        cc = collections.Counter(cases[k]["G"]["tools"])
        sc = seg_tools(segments[si])
        if all(sc[t] <= cc[t] for t in sc):
            segmap[k] = segments[si]; si += 1
        else:
            skipped.append(k)
    assert si == len(segments), f"segments left unassigned: {len(segments)-si}"
    print("cases without guard segment:", skipped)

    result = {}
    for key in sorted(cases):
        g, n = cases[key]["G"], cases[key]["N"]
        seg = segmap.get(key)
        chain = []
        if seg:
            for e in seg["events"]:
                ev = e["event"]
                if ev == "task_plan":
                    chain.append({"type": "task_plan", "cache_hit": e.get("cache_hit"),
                                  "seed": e.get("seed_case_key"),
                                  "validation_passed": e.get("validation_passed")})
                elif ev == "precommit_check":
                    chain.append({"type": "precommit", "tool": e.get("tool_name"),
                                  "decision": e.get("decision"), "initial": e.get("initial_decision"),
                                  "recovery_state": e.get("recovery_state"),
                                  "reasons": e.get("reasons"),
                                  "initial_reasons": e.get("initial_reasons"),
                                  "revision_attempt": e.get("revision_attempt"),
                                  "llm": e.get("runtime_called_llm")})
                elif ev == "call_revision_feedback":
                    chain.append({"type": "revision_feedback", "tool": e.get("tool_name"),
                                  "action": e.get("action"),
                                  "errors": e.get("revision_errors"),
                                  "parse_errors": e.get("revision_parse_errors")})
                elif ev == "plan_revision":
                    chain.append({"type": "plan_revision", "errors": e.get("revision_errors"),
                                  "parse_errors": e.get("revision_parse_errors"),
                                  "attempt": e.get("revision_attempt"),
                                  "budget": e.get("total_revision_budget")})
                elif ev == "planner_replan":
                    chain.append({"type": "planner_replan", "action": e.get("action")})
                elif ev == "authorized_read_evidence":
                    chain.append({"type": "read_evidence", "tool": e.get("tool_name")})
        result[key] = {
            "G_utility": G[key], "N_utility": N[key],
            "layer": "target" if key in paired["target"] else "control",
            "seed": key in paired["seeds"],
            "guard_chain": chain,
            "G_tools": g["tools"], "N_tools": n["tools"] if n else None,
            "G_final_prefix": (g["final"] or "")[:400],
            "N_final_prefix": (n["final"] or "")[:400] if n else None,
        }
    json.dump(result, open(f"{OUT}/case_guard_chains.json", "w"), indent=1)

    # verification printout for the 11 COST cases
    cost = [k for k in sorted(result) if (not result[k]["G_utility"]) and result[k]["N_utility"]]
    for k in cost:
        r = result[k]
        ev = [c for c in r["guard_chain"] if c["type"] != "read_evidence"]
        flags = []
        for c in ev:
            if c["type"] == "precommit" and (c["decision"] != "ALLOW" or
                    (c["recovery_state"] not in ("NOT_REQUIRED", None)) or c.get("revision_attempt")):
                flags.append(f"precommit:{c['tool']}:{c['initial']}->{c['decision']}:{c['recovery_state']}")
            elif c["type"] == "revision_feedback":
                flags.append(f"revfb:{c['tool']}:{(c['errors'] or [])+(c['parse_errors'] or [])}")
            elif c["type"] == "plan_revision":
                flags.append(f"planrev:{(c['errors'] or [])+(c['parse_errors'] or [])}")
            elif c["type"] == "planner_replan":
                flags.append("REPLAN")
        print(f"\n== {k} ({r['layer']}) G={r['G_utility']} N={r['N_utility']}")
        print("   G_tools:", r["G_tools"])
        print("   N_tools:", r["N_tools"])
        print("   flags:", flags if flags else "(no nontrivial intervention)")

if __name__ == "__main__":
    main()
