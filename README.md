# Tool-Effect Binding Research Artifact

This repository snapshot contains the code, frozen inputs, result artifacts, tests,
and manuscript sources for the paper:

> **Binding Agent Tool Calls to Effects: Counterfactually Validated Atoms for
> Pre-Commit Mediation**

The project studies a representation problem in tool-using agents. A single tool
call can commit several independently authorizable effects. If a monitor merges
authorization-distinct effects into the same view, no downstream decision rule can
simultaneously avoid unsafe allows and withheld authorized work. The artifact tests
whether source-executed counterfactuals can expose those collisions and refine a
tool-local effect representation before runtime mediation.

## Scope

The strongest supported result is finite-domain and policy-relative:

- source-executed counterfactuals expose collisions in coarse tool-call views;
- typed effect atoms remove the observed collisions in two frozen domains;
- a concrete atom authorizer exactly realizes a frozen 232-query policy relation;
- a narrower provenance-origin monitor demonstrates audited pre-commit mediation.

This artifact does **not** claim a globally minimal atom schema, a complete ACL or
delegation system, production safety, or unrestricted adaptive robustness. The
AgentDojo runtime monitor is narrower than the concrete ToolSandbox authorizer.

## Repository Layout

| Path | Purpose |
|---|---|
| `experiments/human-authority-and-causal-validation/` | Effect prevalence, finite representation collisions, held-out ToolSandbox validation, and the concrete atom authorizer. |
| `experiments/security-analysis-ablation-and-overhead/` | Refinement monotonicity, policy-family attribution, atom-vs-field attribution, and runtime ablations. |
| `experiments/intent-bound-runtime-guard/` | Frozen descriptors, registration audit, C1f runtime evidence, and deterministic reproduction scripts. |
| `experiments/unified-agent-security-baselines/` | Frozen protocol for the same-checkpoint AgentDojo baseline comparison. Partial model logs are intentionally excluded. |
| `shared/compatibility/scripts/` | Main experiment runners. |
| `shared/compatibility/code/` | Runtime monitor and AgentDojo adapter implementations. |
| `shared/compatibility/tests/` | Tests for the paper's main mechanisms and reproduction paths. |
| `paper/current-usenix/` | Multi-file USENIX manuscript and claim-to-source ledger. |
| `paper/revised-single-file/` | Reviewed single-file manuscript snapshot. |
| `EXPERIMENTS.md` | Claim-to-code-to-result map and commands. |
| `REPRODUCIBILITY.md` | Environment, rerun levels, and limitations. |

## Quick Verification

The deterministic checks do not call an external API or execute real external side
effects:

```bash
git clone git@github.com:skchen17/causal-agent-effect.git
cd causal-agent-effect
python scripts/verify_release.py
```

Run the principal finite-domain experiments directly:

```bash
python shared/compatibility/scripts/run_finite_domain_effect_binding_validation.py
python shared/compatibility/scripts/run_toolsandbox_heldout_validation.py
python shared/compatibility/scripts/run_toolsandbox_concrete_atom_authorizer.py --mode full
python shared/compatibility/scripts/run_representation_mechanism_attribution.py
python shared/compatibility/scripts/run_atom_vs_field_semantic_attribution.py --mode full
```

The ToolSandbox source replay additionally requires the pinned public dependency:

```bash
bash scripts/setup_toolsandbox.sh
python shared/compatibility/scripts/run_toolsandbox_heldout_validation.py
```

Regenerate the paper claim ledger from frozen outputs:

```bash
python scripts/reproduce_usenix_main.py
```

The ledger fails closed while a required model-run artifact is absent. This is
intentional: pending experiments are not silently converted into paper claims.

## Dependencies

Most frozen-result and finite-policy runners use only Python's standard library.
Install the test dependency with:

```bash
python -m pip install -r requirements-core.txt
```

The full AgentDojo/model runs additionally require AgentDojo 0.1.35, an
OpenAI-compatible local model endpoint or explicitly configured API backend, and
the checkpoint named in the frozen protocol. Model weights and API credentials are
not included.

## Safety and Data Handling

- Tool calls are evaluated in copied sandboxes or from saved benchmark artifacts.
- No real email, payment, calendar, Slack, or external SaaS action is executed.
- Gold/source-effect artifacts are used for scoring only and are not runtime input.
- API credentials, model weights, caches, local absolute paths, and user-specific
  metadata are excluded from this release.

See [README.zh-CN.md](README.zh-CN.md) for a Chinese overview.
