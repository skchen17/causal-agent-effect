# Authorization-Interface Validation Research Artifact

This repository contains the code, frozen inputs, result artifacts, tests, and
manuscript sources for:

> **Falsifying Authorization Interfaces for Tool-Using Agents: Counterfactual
> Validation of Policy-Relevant Effects**

Authorization logic can enforce only distinctions preserved by its observation
interface. If two executions require different policy decisions but map to the
same representation, every downstream authorizer must either admit an
unauthorized execution or withhold authorized work. This artifact turns that
obligation into an executable test: copied-sandbox interventions expose
committed transitions, a separately supplied policy identifies decision-relevant
differences, and representation collisions become reproducible failure
certificates.

Typed effects are one evaluated authorization interface, not a privileged or
universal representation. The artifact also evaluates a strong state-aware
request interface and records where the two designs place semantic adaptation,
state exposure, code, and runtime cost.

## Evidence Included

- source-executed representation-collision and failure-certificate studies;
- 11 tools from three pinned public MCP implementations;
- mechanically separated native-delta and typed authorization paths;
- a 1,024-context ACL, capability, and delegation benchmark;
- interface-economy and descriptor-mutation audits;
- a 30-call concrete pre-commit integration study;
- matched DeepSeek and Qwen3-32B runtime comparisons, including the final
  five-method 97-benign/629-attack protocol;
- a 360-row fail-fast claim ledger and a 7,001-row compact outcome export.

## Repository Layout

| Path | Purpose |
|---|---|
| `experiments/human-authority-and-causal-validation/` | Source execution, explicit authority, state-aware comparison, third-party MCP validation, native-delta checks, and interface economy. |
| `experiments/security-analysis-ablation-and-overhead/` | Refinement, representation attribution, policy-view controls, and mechanism diagnostics. |
| `experiments/intent-bound-runtime-guard/` | Frozen descriptors and pre-commit runtime evidence. |
| `experiments/unified-agent-security-baselines/` | Final matched five-method Qwen3-32B result. |
| `shared/compatibility/scripts/` | Main deterministic experiment and audit runners. |
| `shared/compatibility/code/` | Runtime consumer and AgentDojo adapters. |
| `shared/compatibility/tests/` | Tests for the main evidence and reproduction paths. |
| `paper/current-usenix/` | Active USENIX manuscript, tables, reports, and claim ledger. |
| `EXPERIMENTS.md` | Claim-to-code-to-result map. |
| `REPRODUCIBILITY.md` | Verification levels and environment requirements. |

## Quick Verification

These commands do not call an external API or execute real external side effects:

```bash
python -m pip install -r requirements-core.txt
python scripts/verify_release.py
python scripts/reproduce_usenix_main.py
```

The reproduction entry point must report:

```json
{"status": "passed", "n_claim_rows": 360, "pending": []}
```

The active paper is available at `paper/current-usenix/main.pdf`. Its technical
body occupies 12 of the 13 allowed pages in the included USENIX-template build.

## Dependencies and Data Handling

Most frozen-result checks use only Python's standard library. Full source and
model reruns additionally require the pinned ToolSandbox/AgentDojo packages and
the model checkpoint recorded in `paper/current-usenix/artifact/environment.lock`.
Model weights and API credentials are not redistributed.

All tool executions use copied sandboxes or saved benchmark artifacts. The
release contains no real email, payment, calendar, workspace, or SaaS action.
Credentials, model weights, caches, local absolute paths, and user-specific
metadata are excluded.

See [README.zh-CN.md](README.zh-CN.md) for a Chinese overview.
