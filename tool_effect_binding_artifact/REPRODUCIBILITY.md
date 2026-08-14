# Reproducibility Guide

## Levels

1. **Integrity check.** `python scripts/verify_release.py` verifies hashes,
   required files, status fields, and secret/path hygiene.
2. **Frozen-result reproduction.** `python scripts/reproduce_usenix_main.py`
   rebuilds the claim ledger from JSON/CSV artifacts. It fails closed when a
   required final model result is unavailable.
3. **Finite source rerun.** The commands in `EXPERIMENTS.md` recompute the finite
   representation, held-out, concrete-authorizer, and policy-attribution results.
4. **Full model/benchmark rerun.** Requires the exact AgentDojo version, model
   checkpoint, and local inference endpoint in the frozen protocol. Model weights
   are intentionally not redistributed.

## Tested Environment

- Python 3.10/3.12 for deterministic scripts
- pytest 9.1.1
- AgentDojo 0.1.35 for the current AgentDojo v1.1.2 live protocol
- Qwen3-32B GGUF checkpoint hash recorded in
  `paper/current-usenix/artifact/environment.lock`

The deterministic scripts primarily use the Python standard library. Optional
runtime/model adapters import `agentdojo`, `openai`, `torch`, or `transformers`.
The held-out source replay uses Apple's public ToolSandbox repository pinned to
commit `165848b9a78cead7ca7fe7c89c688b58e6501219`; install it with
`bash scripts/setup_toolsandbox.sh`.

## Result Discipline

- Required rows are never silently skipped.
- Parse or execution failures remain in denominators or fail the relevant gate.
- Source effects and labels are scoring artifacts, not deployable monitor inputs.
- Saved replay is described as saved replay, not as a live deployment.
- Pending strong-baseline rows are excluded until the final result reports
  `status=passed` and exact key counts.

## External Side Effects

All source executions use copied benchmark sandboxes. The artifact does not send
messages, make payments, alter calendars, or invoke external SaaS tools.
