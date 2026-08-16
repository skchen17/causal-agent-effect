# E79 AgentLAB Protocol-Fix Status

Status: corrected smokes passed; paired 303-case rerun queued.

## Invalidated result

The earlier no-guard and E77 full logs are non-evaluable. Of 303 rows, 294
contained a tool result and all 294 ended with an empty assistant continuation.
The strict finalizer now reports `attack_success_rate=null`, `utility_rate=null`,
and `status=incomplete_or_failed` for those logs.

## Implemented corrections

- Prompt-style local function calls return tool observations using the `user`
  delimiter, because these textual calls do not carry OpenAI `tool_call_id`s.
- The E79 compatibility adapter preserves string tool results without inserting
  per-character separators.
- API/schema failures and empty model outputs propagate as hard errors instead
  of becoming empty assistant messages.
- The finalizer rejects missing, invalid-role, or empty assistant continuations
  after every tool-result group and withholds ASR/utility whenever a hard gate
  fails.
- Full reruns use `--force-rerun`, so invalid cached rows cannot be reused.

## Smoke evidence

- No guard: one workspace case, two tool calls, valid post-tool continuations,
  utility `1/1`, protocol failures `0`.
- E77: the same case and attack, two tool calls, valid post-tool continuations,
  utility `1/1`, and `2/2` executed calls matched by pre-commit checks.
- Relevant E79 tests: `14 passed`.

The smoke attack result is not a benchmark claim. Its purpose is to establish
that the victim can execute a complete multi-step trajectory under the repaired
message protocol.

## Full-run gate

The user service `e79-agentlab-protocol-fix.service` waits for the active E78
Qwen3-32B job to release the GPUs. It then starts a separate local server, reruns
smoke checks, and runs the identical 303 saved attacks on no guard and E77.
Neither ASR nor utility is reportable until both strict finalizers pass.
