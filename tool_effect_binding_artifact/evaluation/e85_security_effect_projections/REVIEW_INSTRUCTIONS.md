# E85 Independent Security-Effect Projection Review

This review checks whether each candidate projection faithfully represents the
security-relevant state transitions of one frozen AgentDojo v1.1.2 tool
instance. Candidate projections are hypotheses, not trusted contracts.

## Files

- Immutable template: `review_packet.template.jsonl`
- Frozen source manifest: `source_freeze_manifest.json`
- Reviewer output: `review_packet.reviewed.jsonl`
- Compiled approved subset: `trusted_security_effect_projections.jsonl`
- Direct JSONL editing guide: `MANUAL_REVIEW_GUIDE.md`

Do not edit immutable tool, schema, source, evidence, or candidate-projection
fields. The local interface writes only the nested `review` object.

## Permitted Evidence

The reviewer may inspect:

- the frozen tool schema and description;
- the frozen function implementation and its source hash;
- controlled base/mutated calls and state-mutation evidence;
- AgentDojo environment models needed to understand the implementation.

The reviewer must not inspect attack tasks, injection goals, attack success,
utility labels, method decisions, expected ALLOW/DENY labels, or aggregate
method performance while judging a projection.

## Required Review

For every schema field, select one of:

- `SECURITY_RELEVANT`, with a role and rationale;
- `NON_SECURITY`, with an invariance rationale;
- `UNCERTAIN`, with the unresolved reason.

For every candidate projection, select `APPROVE`, `REJECT`, or `UNCERTAIN` and
give a source-grounded rationale. Check all of the following independently:

1. concrete state mutation paths;
2. omitted and default parameter behavior;
3. pairwise or condition-triggered compound effects;
4. per-resource and per-target expansion;
5. surface/negative-control invariance;
6. implicit notifications, invitations, external requests, credential changes,
   transfers, and permission propagation.

Set the tool-level decision to `APPROVE` only if every candidate projection is
approved, every field is classified without uncertainty, and no security effect
is missing. Otherwise select `REJECT` or `UNCERTAIN`. A rejected tool remains a
valid completed review outcome but is not compiled.

## Local Interface

```bash
python scripts/run_e85_projection_review_web.py --no-browser --port 8785
```

Open `http://127.0.0.1:8785/`. The service binds to localhost and does not send
review data to an external service.

To regenerate the immutable packet from the frozen local AgentDojo environment:

```bash
runs/e75_agentdojo_env/bin/python scripts/build_e85_agentdojo_projection_review_packet.py
```

## Validation

```bash
python scripts/validate_e85_projection_review.py
```

The validator verifies all immutable hashes, exact tool-instance keys, review
completeness, source-inspection confirmations, field classifications, and
projection decisions. A complete packet may pass with rejections; only approved
rows are written to `trusted_security_effect_projections.jsonl`.
