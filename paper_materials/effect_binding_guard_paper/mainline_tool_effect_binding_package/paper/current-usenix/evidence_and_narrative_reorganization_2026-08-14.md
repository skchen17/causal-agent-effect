# Evidence and Narrative Reorganization

Date: 2026-08-14

## Controlling Claim

Tool-effect binding is the representation obligation that precedes authorization. A monitor cannot enforce a distinction that its view of a tool execution does not preserve. Counterfactual source execution can falsify and refine that view before a descriptor is frozen; runtime authorization still requires an independently supplied policy and a complete pre-commit enforcement path.

The active title is *Binding Agent Tool Calls to Effects: Counterfactual Validation of Authorization Interfaces*. The title intentionally foregrounds the security-critical enforcement interface rather than the bounded runtime monitor.

## Counterexample Asymmetry

- One executable policy-separating collision is sufficient to falsify a proposed representation on any domain containing the pair.
- Zero collisions supports authorization sufficiency only for the enumerated finite domain and policy family.
- The representation experiments are constructive falsification plus bounded positive verification, not statistical claims about open-world APIs.
- Runtime ASR, utility, or mediation coverage cannot upgrade the finite representation claim.

## Four-Layer Evidence Chain

| Layer | Question | Primary evidence | Supported claim | Boundary |
|---|---|---|---|---|
| Effect fact | What external state does the tool execution commit? | AgentDojo source replay; ToolSandbox state differences | Tool calls can be effectful, compound, and pre-state dependent | Descriptive only for the executed tools and states |
| Policy separation | Could an admissible policy decide two effects differently? | Finite submultiset policy family and authorization-separating pairs | Some effects must remain independently distinguishable | Policy-family relative, not a universal ACL claim |
| Interface conformance | Does the candidate view preserve every tested policy distinction? | Collision tables, refinement lattice, held-out ToolSandbox validation, 232-query deterministic consumer | Typed effects remove observed collisions and realize the frozen finite relation | Finite domain; no global or unique minimality |
| Runtime mediation | Is the checked call the one that commits under the implemented policy? | DeepSeek AgentDojo audit, held-out attacks, AgentLAB saved transfer, mechanism controls | A conservative registered descriptor can drive auditable provenance-origin mediation | Not full concrete-atom ACL authorization; utility tradeoff remains |

## Terminology Rules

- A state-changing intervention is an **effect witness**.
- It is an **authorization-separating witness** only when an admissible policy distinguishes the resulting semantic views.
- An **effect atom** is a policy-relevant unit of the general representation.
- The ToolSandbox mechanism evaluates concrete typed atoms.
- The AgentDojo runtime evaluates a conservative registered-field and effect-label provenance-origin profile.
- A planner proposes calls. It does not define or enlarge the authority context used to approve them.

## Narrative Order

1. A compound tool call can emit several independently authorizable effects.
2. Coarse views create representation collisions that no downstream monitor can repair.
3. Source-executed counterfactuals test effect facts; policy witnesses determine which differences matter for authorization.
4. Refinement tests and, when possible, improves a proposed policy-relative representation over a frozen domain; it is not automatic semantic discovery.
5. Concrete atoms realize one finite policy relation without unsafe pre-allows or false denials.
6. A separate AgentDojo provenance-origin monitor demonstrates runtime integration and auditability, not atom-specific numerical dominance.

## Claims That Remain Prohibited

- globally minimal or uniquely correct atoms;
- autonomous safe contract synthesis;
- authority inferred or approved by the protected planner;
- AgentDojo as a full concrete-atom authorizer;
- production safety, complete permission enforcement, or unrestricted adaptive robustness;
- numerical superiority over Spotlighting or generic raw-field taint on current evidence;
- benign utility non-inferiority before the frozen statistical gate passes.

## Figure Hierarchy

- Figure 1 is the conceptual core: a concrete executable collision falsifies a coarse authorization view.
- Figure 2 has three visibly separate parts: offline interface validation, the downstream consumer contract, and the narrower evaluated AgentDojo provenance-origin integration.
- Figure 3 summarizes finite representation evidence and explicitly scopes zero collisions to the enumerated relation.
- Figure 4 is labeled bounded runtime characterization and cannot be used as representation evidence.

## Pending Evidence

- The fresh same-protocol Qwen3-32B five-method comparison remains required before final runtime conclusions.
- The queued atom-versus-field semantic-attribution experiment remains the direct test of whether validated effect semantics add value beyond retaining every raw field.
- Final result generation must update the Abstract, Results, Limitations, Conclusion, claim ledger, page budget, and anonymous artifact regardless of outcome.
