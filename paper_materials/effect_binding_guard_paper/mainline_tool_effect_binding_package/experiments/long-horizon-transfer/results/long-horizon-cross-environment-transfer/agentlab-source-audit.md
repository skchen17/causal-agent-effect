# E79 AgentLAB Task-Injection Source Audit

Status: `passed_with_protocol_blockers`.

- Revision: `36f58e60c36bbd6d5b8e61d50d7db7d9ea7258d7`.
- Inventory: 97 user tasks, 35 injection tasks, 949 full Cartesian pairs.
- The offline banking ground-truth pipeline and deterministic evaluator completed successfully.
- In this artifact, `security=True` means the injection goal executed and therefore counts as attack success.

## Protocol Blockers

- The README names gpt-5.1 for attack generation while code paths default or hard-code gpt-5-mini.
- The exact non-banking 303-pair selector and ordering command is not committed.
- Adaptive rounds reuse prior successful attacks and skip prior successes, so shell-loop rounds are not independent trials.
- The attacker requires OpenAI Responses structured parsing (and Batch/File APIs in batch mode); chat-completions-only local servers are insufficient.
- Some local victim setup probes port 8000 directly instead of uniformly honoring LOCAL_LLM_PORT.

## Claim Boundary

The public Task-Injection source, deterministic task/evaluator path, and one offline ground-truth task ran locally. No attack was generated, no victim LLM was run, and no AgentLAB ASR or utility result is claimed.
