# Benign Utility Causal Audit

This audit isolates the seven benign AgentDojo tasks whose utility labels differ
between the Qwen3-32B no-guard run and the E84 reviewed-authority run.

The audit does not call a model or execute a tool. It:

1. reloads the official AgentDojo v1.1.2 task evaluators;
2. recomputes utility from the complete final assistant message;
3. recomputes utility after removing hidden `<think>` content;
4. compares the recorded tool-call sequences;
5. checks whether any runtime `DENY` or `ABSTAIN` feedback occurred; and
6. records a case-level root-cause classification.

Run it with the benchmark environment:

```bash
experiments/unified-agent-security-baselines/runs/unified-agent-security-comparison/agentdojo-env/bin/python \
  experiments/security-analysis-ablation-and-overhead/source/benign-utility-causal-audit/run_audit.py
```

The generated artifacts are written to
`experiments/security-analysis-ablation-and-overhead/results/benign-utility-causal-audit/`.

