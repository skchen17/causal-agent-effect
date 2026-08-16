# SOTA Gap Map

| Related Area | What It Addresses | Residual Gap This Paper Tests | Local Evidence Anchor |
|---|---|---|---|
| AgentDojo-style prompt-injection benchmarks | Realistic task and attack evaluation for tool agents. | Benchmarks expose attacks, but the paper's question is whether a monitor binds candidate actions to realized effect, resource, authorization, evidence, and provenance under counterfactual stress. | EB-01, EB-02 |
| Capability and data/control-flow defenses such as CaMeL | Protective layers and capability-style mediation around agent actions. | Capability structure still requires correct binding between proposed action, resource, operation, and authorization. | EB-02, EB-05 |
| Tool dependency graph defenses such as IPIGuard | Structural constraints over tool dependency graphs. | Graph/topology signals can be useful, but realized-effect/resource decisions can still be underdetermined in custom stress. | EB-02 |
| Step-level tool safety and TS-Guard | Proactive tool invocation safety and step-level monitoring. | Released-checkpoint custom stress shows nontrivial behavior, but joint binding remains incomplete under the paper's axis tests. | EB-02 |
| Pre-execution guardrails and Safiron | Pre-execution safety decisions for tool calls. | Custom stress separates effect sensitivity from resource/auth/provenance binding rather than only measuring aggregate pre-execution safety. | EB-02 |
| Programmable privilege control such as Progent | Explicit policy languages and deterministic enforcement over tool names and arguments. | Policy enforcement assumes that the call and its arguments have been bound to the correct policy-relevant effect, resource, operation, and provenance. | EB-05, EB-06 |
| Least-privilege authorization such as MiniScope | Permission hierarchy reconstruction and permission minimization for tool-calling agents. | The paper measures semantic binding at the action boundary and provides only a local contract prototype, not a complete permission system. | EB-06, EB-08, EB-09 |
| Hard rule/tuple guards | Inspectable pre-commit decisions with abstention. | E48 improves some cases but E50 shows resource/auth UPA remains high under targeted stress. | EB-04, EB-05 |
| Explicit authorization infrastructure | Typed policy objects, resource aliases, operation modes, and atom expansion. | E55-v2 tests whether this infrastructure changes mediation coverage under a controlled local contract. | EB-06, EB-09 |

## Gap Statement

The paper's gap is not "no one has studied tool-agent safety." The defensible gap is that current evaluations and defenses often do not isolate whether a pre-commit monitor has jointly bound the candidate action to effect, resource, operation, authorization context, evidence, and provenance, especially when surface form is counterfactually perturbed.
