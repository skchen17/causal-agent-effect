# E60 Effect Contract Prototype Report

## Purpose

This prototype demonstrates an onboarding workflow in which an LLM-compatible proposer creates candidate effect contracts, field-level counterfactual tests validate those candidates, validated contracts are frozen, and runtime mediation uses only frozen contracts for atom-level authorization.

It is not a production system and does not execute real external side effects.

## Reused Code Summary

The runtime authorization path reuses E55 resource canonicalization, operation-mode, visibility, and provenance/control-source helper semantics, then adds E60-specific target-principal authorization after converting prototype atoms and contexts to compatible forms. The prototype keeps separate contract dataclasses so onboarding, validation, refinement, and freezing metadata remain explicit.

## Architecture

Candidate proposal is isolated from runtime authorization. Stub proposals are treated as untrusted contracts until counterfactual validation passes. Runtime authorization accepts only `FrozenContract` objects and never calls the proposer or an LLM.

## Mock Tools Supported

- `send_email`: final validation passed `True`, refined `False`.
- `create_calendar_event`: final validation passed `True`, refined `False`.
- `share_file`: final validation passed `True`, refined `True`.
- `post_slack_message`: final validation passed `True`, refined `False`.
- `submit_payment`: final validation passed `True`, refined `False`.

## Counterfactual Validation Summary

- Tools tested: `5`.
- Candidate contracts: `5`.
- Counterfactual cases: `33`.
- Field sensitivity accuracy: `1.0`.
- Surface invariance accuracy: `1.0`.
- Unsafe pre-allow rate: `0.0`.
- False deny rate: `0.0`.
- Coverage: `0.924`.
- Atom coverage: `1.0`.
- Expected decision agreement: `1.0`.
- Required atom coverage: `1.0`.
- Required resource binding coverage: `1.0`.
- Required target-principal coverage: `1.0`.

## Authorization Contexts

- Context variants available: `alias_disabled, alias_enabled, default_safe, draft_only, external_recipient_forbidden, limited_payment, no_public_link, untrusted_control_forbidden`.
- Context variants exercised by demo runtime examples: `alias_disabled, alias_enabled, default_safe, draft_only, external_recipient_forbidden, limited_payment, no_public_link, untrusted_control_forbidden`.

## Runtime Authorization Examples

The demo ran `32` runtime examples across safe, unsafe, and unknown inputs. Rows are written to `analysis/results/e60_demo_outputs.jsonl`.

Runtime authorization uses frozen contracts only. The demo records `runtime_llm_or_proposer_calls_after_freeze = 0`.

## Incomplete Contract Detection

The demo intentionally removes the `file_reader_added` template from the initial `share_file` candidate. Counterfactual validation catches the incomplete contract, the deterministic refiner restores the missing template, and only the validated refined contract is frozen.

## Example Effect Contract

The `send_email` contract binds the message body as the operated resource and places `to`, `cc`, and `bcc` entries in `target_principal`. Attachment-disclosure atoms use the disclosed file as `resource_id` and the recipient as `target_principal`. `commit_mode`, `control_source`, and `provenance_source` are security-relevant fields validated by counterfactual cases.

## Example Atomization

A safe `send_email` draft with one recipient and one attachment expands to a `message_sent` atom over `email_body` targeted at the recipient, plus an `attachment_disclosed` atom over `finance-plan.docx` targeted at the same recipient. The frozen runtime authorizer checks both resource and target-principal authorization before allowing the call.

## Limitations

- This is not a production system.
- It does not call real email, calendar, Slack, file, payment, browser, shell, or network APIs.
- It performs no real SaaS/API integration and executes no real external side effects.
- Stub proposal is not proof that LLMs reliably infer contracts for arbitrary tools.
- The LLM-compatible proposal is not trusted and is not used as the final runtime safety judge.
- The runtime authorizer is only as complete as the validated tool effect contract. If a contract omits a security-relevant side effect, the authorizer cannot check it.
- Unknown or high-risk tools should default to `ABSTAIN` or human review.
- The prototype demonstrates onboarding, validation, and frozen runtime authorization, not full deployment generalization.

## Connection to E55/E56/E57

E55 supplied the local authorization-aware atom-checking semantics reused here. E56/E57 supplied the audit and validation discipline that motivates leakage separation, independent checking, and conservative claim boundaries. E60 adds an onboarding prototype for validating and freezing effect contracts before runtime use.
