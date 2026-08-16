#!/usr/bin/env python3
"""
v17 成功攻击案例放行路径分解（只读分析）
========================================
用途: O6 前置分析最后一项 -- 11 个成功攻击案例 (security=True &
attack_type=important_instructions) 的放行路径分解。只读 runtime_audit.jsonl /
agentdojo_logs / plan_cache.json, 不修改任何数据, 不占 GPU。
数据目录: experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/
  recovery-normalization-qwen32-full-allow-with-trail-v17-726/
输出: JSON 到 stdout (含每个调用绑定的 precommit_check 字段、findings、红旗)。
数据: runtime_audit.jsonl / agentdojo_logs/ / plan_cache.json (全部只读)

关联方法（可复现）:
  1) query_hash 推断: 对案例每个 assistant 工具调用重建 call_signature
     (sha256(json.dumps({"tool_name":..,"args":..},sort_keys=True,default=str)))
     在 audit precommit_check 行中反查其 query_hash; 取众数作为该 user_task
     的 query_hash (同一 user_task 全部案例共享)。
  2) 调用绑定: 在该 query_hash 的 precommit 行序列上, 把同 user_task 的全部
     案例按 evaluation_timestamp 排序, 顺序贪心匹配每个案例的签名序列;
     目标案例匹配行数 == 调用数视为绑定成功 (行顺序=运行顺序已用
     slack/user_task_1 的 6 案例 15 行验证)。
  3) 兜底: 若顺序匹配失败, 用单个案例签名在该 qh 行上的顺序匹配; 仍失败则
     报告"未关联"。

字段语义 (agentdojo_e77_runtime_patch.py L664-695):
  guard_decision=比较器原始决策; decision=应用 allow_with_trail 后的有效决策;
  diagnostic_uncertainty_override=uncertainty 覆盖放行; 
  strict_authorization_satisfied=strict 比较是否 ALLOW;
  execution_attempted=decision==ALLOW 时执行;
  recovery_state=NOT_REQUIRED/PLAN_REVISED/PLANNER_REPLAN_APPLIED/...
五类扩权 finding (disqualifying, e77_runtime.py L220-226):
  forbidden_field_used / outside_exact_plan / tool_not_in / missing_e77 /
  revision_binding_invalid (子串匹配, 与 runtime 一致)
红旗缺陷: atom_checks 中同一 resource_type 同时出现 BLOCK 类与 ALLOW 类状态
"""
import json, hashlib, collections, glob, os, sys

BASE='/data/CSK/causal-agent-safety-research/paper_materials/effect_binding_guard_paper/mainline_tool_effect_binding_package/experiments/intent-bound-runtime-guard/runs/effect-difference-runtime-guard/recovery-normalization-qwen32-full-allow-with-trail-v17-726'
LOG=f'{BASE}/agentdojo_logs/local-ours_e77_effect_diff_runtime'

TARGETS=[
 ('slack','user_task_1','injection_task_1'),
 ('slack','user_task_14','injection_task_1'),
 ('slack','user_task_18','injection_task_1'),
 ('slack','user_task_18','injection_task_5'),
 ('slack','user_task_19','injection_task_1'),
 ('slack','user_task_7','injection_task_3'),
 ('slack','user_task_9','injection_task_1'),
 ('slack','user_task_9','injection_task_3'),
 ('travel','user_task_0','injection_task_6'),
 ('travel','user_task_6','injection_task_6'),
 ('workspace','user_task_19','injection_task_0'),
]

DISQ=('forbidden_field_used','outside_exact_plan','tool_not_in','missing_e77','revision_binding_invalid')
ALLOW_STATUSES={'matched_exact','matched_runtime_default','resolved_from_registered_projection',
                'resolved_from_original_task','resolved_from_authorized_read',
                'resolved_from_authorized_effect_result'}
BLOCK_STATUSES={'outside_exact_plan','resolver_fill_requires_replan','forbidden_field_used',
                'unbound_field','registered_projection_mismatch','runtime_default_mismatch'}

def call_signature(tool_name,args):
    return hashlib.sha256(json.dumps({"tool_name":tool_name,"args":args},sort_keys=True,default=str).encode("utf-8")).hexdigest()

def findings_in(reasons):
    return sorted({d for r in reasons for d in DISQ if d in str(r)})

def red_flag_atoms(atom_checks):
    by=collections.defaultdict(set)
    for c in atom_checks:
        st=c.get('check_result')
        key=c.get('resource_type')
        if st in ALLOW_STATUSES: by[key].add('ALLOW')
        elif st in BLOCK_STATUSES: by[key].add('BLOCK')
        else: by[key].add('?')
    return [(f,sorted(v)) for f,v in by.items() if 'ALLOW' in v and 'BLOCK' in v]

# ---- 加载 ----
pre_rows=[]; task_plans=[]
with open(BASE+'/runtime_audit.jsonl') as f:
    for i,line in enumerate(f):
        d=json.loads(line)
        if d['event']=='precommit_check': pre_rows.append((i,d))
        elif d['event']=='task_plan': task_plans.append(d)

sig_qh=collections.defaultdict(set)
qh_rows=collections.defaultdict(list)
for ln,r in pre_rows:
    sig_qh[r['call_signature']].add(r['query_hash'])
    qh_rows[r['query_hash']].append((ln,r))

# ---- 案例工具 ----
def load_case(suite,ut,it):
    fp=f'{LOG}/{suite}/{ut}/important_instructions/{it}.json'
    if not os.path.exists(fp): return None
    return json.load(open(fp))

def load_benign(suite,ut):
    fp=f'{LOG}/{suite}/{ut}/none/none.json'
    if not os.path.exists(fp): return None
    return json.load(open(fp))

def tool_calls_of(d):
    out=[]
    for m in d['messages']:
        if m.get('role')=='assistant' and m.get('tool_calls'):
            for t in m['tool_calls']:
                out.append((t['function'], t['args']))
    return out

def sig_seq(d):
    return [call_signature(fn,args) for fn,args in tool_calls_of(d)]

# ---- 顺序匹配: 在给定 qh 行序列上, 按案例顺序分配 ----
def assign_cases(qh, cases):
    """cases: list[(key, log)] 按运行顺序; 返回 {key: [(ln,row),...]}, ok"""
    rows=qh_rows.get(qh,[])
    audit_sigs=[r['call_signature'] for _,r in rows]
    assigned={}; cursor=0; ok=True
    for ck,c in cases:
        mine=[]; csigs=sig_seq(c)
        for s in csigs:
            found=False
            while cursor<len(audit_sigs):
                if audit_sigs[cursor]==s:
                    mine.append(rows[cursor]); cursor+=1; found=True; break
                cursor+=1
            if not found: ok=False; break
        assigned[ck]=mine
        if not ok: break
    return assigned, ok

def gather_cases(suite,ut):
    cases=[]
    b=load_benign(suite,ut)
    if b: cases.append(('none',b))
    for n in range(10):
        c=load_case(suite,ut,f'injection_task_{n}')
        if c: cases.append((f'injection_task_{n}',c))
    cases.sort(key=lambda x:(x[1].get('evaluation_timestamp',''),x[0]))
    return cases

# ---- 主循环 ----
results=[]
for suite,ut,it in TARGETS:
    case=load_case(suite,ut,it)
    if case is None:
        results.append({'case':f'{suite}/{ut}/{it}','error':'case log not found'}); continue
    if case.get('security') is not True or case.get('attack_type')!='important_instructions':
        results.append({'case':f'{suite}/{ut}/{it}','error':f"not a success: security={case.get('security')} attack={case.get('attack_type')}"}); continue
    calls=tool_calls_of(case); sigs=sig_seq(case)
    # 众数 qh
    votes=collections.Counter()
    for s in sigs:
        votes.update(sig_qh.get(s,set()))
    cands=[q for q,_ in votes.most_common()]
    # 优先用文本匹配缩小: task_plan task_goal 相似度 (对众数并列时)
    qh=None; assign_ok=False; chosen_method='signature-majority'
    for q in cands[:4]:
        cases=gather_cases(suite,ut)
        assigned,ok=assign_cases(q,cases)
        if ok and len(assigned.get(it,[]))==len(sigs):
            qh=q; assign_ok=True; break
    if qh is None:
        results.append({'case':f'{suite}/{ut}/{it}','error':'no query_hash with full sequential match','vote_top':[(q[:12],v) for q,v in votes.most_common(3)]})
        continue
    cases=gather_cases(suite,ut)
    assigned,_=assign_cases(qh,cases)
    tgt_rows=assigned.get(it,[])

    # 每个调用绑定到行
    detail=[]; exec_cnt=0; override_cnt=0; finding_allow_cnt=0; red_hits=[]
    for (fn,args),s in zip(calls,sigs):
        row=None
        for ln,r in tgt_rows:
            if r['call_signature']==s: row=r; break
        if row is None:
            detail.append({'tool':fn,'args':args,'bound':False}); continue
        r=row; guard=r.get('guard_decision'); dec=r.get('decision'); exec_=r.get('execution_attempted')
        ov_unc=r.get('diagnostic_uncertainty_override',False)
        fin_final=findings_in(r.get('reasons',[])); fin_init=findings_in(r.get('initial_reasons',[]))
        rf=red_flag_atoms(r.get('atom_checks',[]))
        if rf: red_hits.append((fn,rf))
        if exec_:
            exec_cnt+=1
            if guard!='ALLOW': override_cnt+=1
            if fin_final or fin_init: finding_allow_cnt+=1
        if dec=='ALLOW' and exec_:
            if guard=='ALLOW': how='strict-ALLOW'
            elif ov_unc: how='override-uncertainty'
            else: how=f'override-recovery({r.get("recovery_state")})'
        elif dec=='ALLOW' and not exec_: how='allowed-not-executed'
        else: how=f'blocked({dec},{r.get("recovery_state")})'
        detail.append({
            'tool':fn,'args':args,'bound':True,
            'guard_decision':guard,'decision':dec,'execution_attempted':exec_,
            'diagnostic_uncertainty_override':ov_unc,
            'strict_authorization_satisfied':r.get('strict_authorization_satisfied'),
            'recovery_state':r.get('recovery_state'),
            'reasons':r.get('reasons',[]),'initial_reasons':r.get('initial_reasons',[]),
            'findings_final':fin_final,'findings_initial':fin_init,
            'atom_block_allow':rf,'how':how,
        })
    results.append({
        'case':f'{suite}/{ut}/{it}','query_hash':qh,
        'match_method':chosen_method,'n_calls':len(sigs),'n_bound':len(tgt_rows),
        'exec_count':exec_cnt,'override_count':override_cnt,
        'finding_allow_count':finding_allow_cnt,
        'red_flag_fields':red_hits,'detail':detail,
    })

print(json.dumps(results,ensure_ascii=False,indent=1))
