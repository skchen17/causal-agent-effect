#!/usr/bin/env python3
"""R2 inspection: for each of the 11 cost cases, show pilot plan-cache entry
(keyed by task_plan prompt_hash) and guard intervention flags. Read-only."""
import json, os, re, collections

PKG = "/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package"
P = f"{PKG}/experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-pilot-36-allow-with-trail-deepseek-iffix-20260807"
FUNC = "<" + "function=" + "([A-Za-z0-9_]+)>"

def tools_of(logdir):
    d = json.load(open(logdir))
    tools = []
    for m in d["messages"]:
        c = m.get("content")
        if isinstance(c, list):
            txt = "\n".join(p.get("content", "") for p in c if isinstance(p, dict))
        else:
            txt = c or ""
        if m["role"] == "assistant":
            tools.extend(re.findall(FUNC, txt))
    return d["evaluation_timestamp"], tools

paired = json.load(open(f"{P}/paired_accounting_deepseek_pilot.json"))
cache = json.load(open(f"{P}/plan_cache.json"))
evs = [json.loads(l) for l in open(f"{P}/runtime_audit.jsonl")]

segments, cur = [], None
for e in evs:
    if e["event"] == "task_plan":
        if cur: segments.append(cur)
        cur = {"qh": e["query_hash"], "plan": e, "events": [e]}
    else:
        cur["events"].append(e)
segments.append(cur)

GLOG = f"{P}/agentdojo_logs/local-ours_e77_effect_diff_runtime"
meta = {}
for suite in ["banking", "slack", "travel", "workspace"]:
    for task in sorted(os.listdir(f"{GLOG}/{suite}")):
        end, tools = tools_of(f"{GLOG}/{suite}/{task}/none/none.json")
        meta[f"{suite}/{task}"] = (end, collections.Counter(tools))

order = sorted(meta, key=lambda k: meta[k][0])
segmap, si = {}, 0
for k in order:
    if si >= len(segments): continue
    sc = collections.Counter(e.get("tool_name") for e in segments[si]["events"] if e["event"] == "precommit_check")
    if all(sc[t] <= meta[k][1][t] for t in sc):
        segmap[k] = segments[si]; si += 1

cost = ["banking/user_task_3", "banking/user_task_11", "banking/user_task_15",
        "slack/user_task_17", "slack/user_task_8", "travel/user_task_8",
        "workspace/user_task_16", "workspace/user_task_18",
        "workspace/user_task_20", "workspace/user_task_4", "workspace/user_task_6"]

for k in cost:
    seg = segmap.get(k)
    print("=" * 100)
    print("CASE:", k, "| G:", paired["G"].get(k), "| N:", paired["N"].get(k),
          "| layer:", ("target" if k in paired["target"] else "control"),
          "| seed:", k in paired["seeds"])
    if not seg:
        print("  (no guard segment)")
        continue
    pe = seg["plan"]
    ph = pe["prompt_hash"]
    print(f"  task_plan hash={ph[:16]}... cache_hit={pe.get('cache_hit')} seed={pe.get('seed_case_key')} "
          f"accepted={pe.get('plan_accepted')} repair={pe.get('repair_attempts')} "
          f"errors={pe.get('plan_validation_errors')}")
    entry = cache.get(ph)
    if entry:
        plan = entry.get("plan")
        if plan is None:
            print("  cached plan: None")
        else:
            print("  cached plan:")
            print(json.dumps(plan, indent=1)[:2600])
    else:
        print("  (no cache entry)")
    for e in seg["events"]:
        ev = e["event"]
        if ev == "task_plan": continue
        if ev == "precommit_check":
            if e.get("decision") != "ALLOW" or (e.get("recovery_state") not in ("NOT_REQUIRED", None)) or e.get("revision_attempt"):
                print(f"  PRECOMMIT {e.get('tool_name')} initial={e.get('initial_decision')}->{e.get('decision')} "
                      f"rec={e.get('recovery_state')} rev={e.get('revision_attempt')} reasons={e.get('reasons')}")
        elif ev == "call_revision_feedback":
            print(f"  REVFB {e.get('tool_name')} action={e.get('action')} errors={e.get('revision_errors')} parse={e.get('revision_parse_errors')}")
        elif ev == "plan_revision":
            print(f"  PLANREV attempt={e.get('revision_attempt')} errors={e.get('revision_errors')} parse={e.get('revision_parse_errors')}")
        elif ev == "planner_replan":
            print(f"  REPLAN action={e.get('action')} accepted={e.get('plan_accepted')} errors={e.get('plan_validation_errors')} hash={e.get('prompt_hash','')[:16]}")
