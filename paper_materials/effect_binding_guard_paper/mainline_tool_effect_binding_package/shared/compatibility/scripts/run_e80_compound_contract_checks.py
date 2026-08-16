#!/usr/bin/env python3
"""Check compound-effect contract coverage on a real AgentDojo tool.

Run with the pinned AgentDojo environment. The tool executes only against a
fresh in-memory benchmark state and performs no external side effect.
"""

from __future__ import annotations

import copy
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis/results"


def atom(effect: str, resource: str, target: str, **scope: Any) -> tuple[Any, ...]:
    return effect, resource, target, tuple(sorted(scope.items()))


def actual_atoms(before: dict[str, Any], after: dict[str, Any]) -> set[tuple[Any, ...]]:
    before_events = before["calendar"]["events"]
    after_events = after["calendar"]["events"]
    new_events = [row for key, row in after_events.items() if key not in before_events]
    before_sent = {row["id_"]: row for row in before["inbox"]["sent"]}
    after_sent = {row["id_"]: row for row in after["inbox"]["sent"]}
    new_sent = [row for key, row in after_sent.items() if key not in before_sent]
    atoms: set[tuple[Any, ...]] = set()
    for event in new_events:
        atoms.add(atom(
            "calendar_event_created",
            f"calendar_event:{event['id_']}",
            "calendar_owner",
            title=event["title"],
            start_time=event["start_time"],
            end_time=event["end_time"],
            location=event.get("location"),
        ))
    for message in new_sent:
        for recipient in message.get("recipients") or []:
            atoms.add(atom(
                "calendar_invitation_disclosed",
                f"calendar_event:{new_events[0]['id_']}",
                recipient,
                subject=message["subject"],
            ))
    return atoms


def contracted_atoms(output: Any, arguments: dict[str, Any], calendar_owner: str) -> set[tuple[Any, ...]]:
    """Instantiate two templates, including implicit-owner recipient expansion."""

    event = output.model_dump(mode="json")
    event_id = event["id_"]
    atoms = {
        atom(
            "calendar_event_created",
            f"calendar_event:{event_id}",
            "calendar_owner",
            title=event["title"],
            start_time=event["start_time"],
            end_time=event["end_time"],
            location=event.get("location"),
        )
    }
    # The native calendar implementation always inserts the calendar owner and
    # then sends one invitation email to the resulting participant set. The
    # owner is trusted runtime context, not an LLM-derived or post-execution fact.
    recipients = set(arguments.get("participants") or ()) | {calendar_owner}
    for recipient in recipients:
        atoms.add(atom(
            "calendar_invitation_disclosed",
            f"calendar_event:{event_id}",
            recipient,
            subject=f"Invitation: {arguments['title']}",
        ))
    return atoms


def run_agentdojo_cases() -> list[dict[str, Any]]:
    suite = get_suite("v1.1.2", "workspace")
    runtime = FunctionsRuntime(suite.tools)
    rows = []
    for participants, location in itertools.product((None, ["alice@example.com", "bob@example.com"]), (None, "R1")):
        environment = suite.load_and_inject_default_environment({})
        before = environment.model_dump(mode="json")
        calendar_owner = before["calendar"]["account_email"]
        arguments = {
            "title": "Counterfactual coverage check",
            "start_time": "2024-05-16 10:00",
            "end_time": "2024-05-16 11:00",
            "description": "bounded sandbox check",
            "participants": copy.deepcopy(participants),
            "location": location,
        }
        output, error = runtime.run_function(environment, "create_calendar_event", arguments)
        after = environment.model_dump(mode="json")
        actual = actual_atoms(before, after)
        contracted = contracted_atoms(output, arguments, calendar_owner) if error is None else set()
        rows.append({
            "participants": participants,
            "location": location,
            "runtime_error": error,
            "actual_atoms": [repr(item) for item in sorted(actual, key=repr)],
            "contracted_atoms": [repr(item) for item in sorted(contracted, key=repr)],
            "actual_subset_of_contract": actual <= contracted,
            "extra_contract_atoms": [repr(item) for item in sorted(contracted - actual, key=repr)],
        })
    return rows


def synthetic_interaction_check() -> dict[str, Any]:
    """Show why one-field tests miss a conjunction-triggered effect."""

    def effect(recipients: tuple[str, ...], publish: bool) -> bool:
        return bool(recipients) and publish

    base = effect((), False)
    one_recipient = effect(("alice",), False)
    publish_only = effect((), True)
    joint = effect(("alice",), True)
    return {
        "base_effect": base,
        "recipient_only_effect": one_recipient,
        "publish_only_effect": publish_only,
        "joint_effect": joint,
        "one_field_tests_miss_joint_branch": not base and not one_recipient and not publish_only and joint,
        "required_registration_extension": "pairwise_or_condition-aware_counterfactuals",
    }


def run() -> dict[str, Any]:
    cases = run_agentdojo_cases()
    interaction = synthetic_interaction_check()
    passed = all(row["runtime_error"] is None and row["actual_subset_of_contract"] for row in cases)
    return {
        "experiment": "E80",
        "check_type": "compound_effect_contract_coverage",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_scope_boundary" if passed and interaction["one_field_tests_miss_joint_branch"] else "failed",
        "agentdojo": {
            "version": "v1.1.2",
            "suite": "workspace",
            "tool": "create_calendar_event",
            "n_cases": len(cases),
            "effect_templates": [
                "calendar_event_created",
                "calendar_invitation_disclosed_per_explicit_recipient_and_implicit_calendar_owner",
            ],
            "cases": cases,
        },
        "interaction_counterexample": interaction,
        "obligation_status": {
            "O1": "enumerated_compound_tool_cases_pass; general_reachable_state_soundness_remains_conditional"
        },
        "claim_boundary": (
            "The check executes four schema-valid create_calendar_event calls in fresh AgentDojo sandbox states and "
            "shows coverage by a two-template contract with explicit-recipient and implicit-owner expansion. It does not prove coverage for "
            "other tools or states. The synthetic conjunction demonstrates that E77's one-field base-state tests are "
            "insufficient and motivates pairwise or condition-aware registration."
        ),
    }


def main() -> int:
    report = run()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "e80_compound_contract_checks.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# E80 Compound-Effect Contract Checks",
        "",
        f"Status: `{report['status']}`.",
        "",
        f"- AgentDojo tool cases: `{report['agentdojo']['n_cases']}`.",
        "- Templates checked: event creation and per-recipient invitation disclosure.",
        "- Every observed sandbox effect is covered by the explicit contract in the enumerated cases.",
        "- A conjunction-triggered synthetic effect is invisible to isolated one-field tests.",
        "",
        "## Claim Boundary",
        "",
        report["claim_boundary"],
        "",
    ]
    (RESULTS / "e80_compound_contract_checks.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed_with_scope_boundary" else 1


if __name__ == "__main__":
    raise SystemExit(main())
