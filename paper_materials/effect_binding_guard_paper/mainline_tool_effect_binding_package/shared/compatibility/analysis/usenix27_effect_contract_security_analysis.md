# Effect-Contract Security Analysis for USENIX Security '27

Status: working specification. This document defines the security argument that the implementation and paper must satisfy. It is not yet a claim that the current E77 code implements every definition below.

## 1. System Model

Let a registered tool be `t`, its structured call arguments be `x`, the pre-call environment state be `s`, and the trusted runtime evidence available before commitment be `h`. Its implementation is a transition function

\[
F_t:(s,x)\mapsto s'.
\]

Executing the tool produces a security-relevant projection of the concrete state difference:

\[
\Delta_{sec}(t,x,s)=\Pi_{sec}(s,F_t(s,x)).
\]

`Pi_sec` is part of the validation boundary. If it omits an asynchronous,
callback, remote, or implicit effect, counterfactual testing cannot recover that
effect later.

The arguments visible in an emitted tool call need not equal the arguments used
by the implementation: a schema or executor may supply defaults. Define the
totalization function

\[
\tau_t(x,s)=\bar{x}
\]

to instantiate every declared static default and to resolve every effect-bearing
implicit argument before authorization. If a required, dynamic, state-dependent,
or undocumented default cannot be determined, `tau_t` returns `unresolved`.
Both the contract and executor consume the same totalized object `bar{x}`.

The runtime does not execute the call to discover this set before commitment. It uses a frozen effect contract:

\[
K_t:(x,s,h)\mapsto A,
\]

where `K_t` contains one or more effect templates and deterministic bindings from tool arguments or trusted runtime evidence to atom fields.

Let `gamma(A)` be the concrete effects conservatively denoted by the atom set.
Contract soundness is an abstract-interpretation obligation:

\[
\Delta_{sec}(t,x,s)\subseteq\gamma(K_t(x,s,h)).
\]

Over-approximation can reduce liveness; under-approximation creates an unsafe
mediation gap.

An instantiated atom is:

\[
a=\langle e,o,r,y,v,m,p,k\rangle,
\]

where `e` is effect kind, `o` operation, `r` resource identity, `y` target principal, `v` visibility, `m` commit mode, `p` provenance source, and `k` control source. A domain may omit fields only when the omitted field cannot alter authorization in that domain.

Before untrusted observations are processed, a trusted task interface supplies
an authority manifest `B_q`. Exact clauses in `B_q` carry request-source spans;
resolver clauses name entries in a fixed resolver catalog and specify permitted
read tools, output projections, and cardinality. An LLM may propose a convenient
permission plan `L_q`, but the deployable envelope is a validated restriction:

\[
\Gamma_q=\operatorname{Bound}(L_q,B_q),\qquad \Gamma_q\preceq B_q.
\]

The relation `preceq` means that the proposal can remove tools, fields, values,
or resolvers, but cannot add authority. In domains without a trusted manifest,
the envelope-soundness obligation remains an assumption rather than an LLM
property. Equivalently, a task-intent compiler may map the original request `q`
directly to the manifest and envelope:

\[
P(q)=\Gamma_q.
\]

For an authenticated multi-turn task, let `u_0,...,u_k` be the trusted user
messages observed so far and let `B^(k)` be the authority bound at epoch `k`.
Only the trusted task interface may apply

\[
B^{(k+1)}=\operatorname{Update}(B^{(k)},u_{k+1}).
\]

The update may legitimately add, revoke, or clarify authority, but it consumes
no tool output, model-generated rationale, or untrusted observation. The LLM
proposal at epoch `k` remains bounded by `B^(k)`. Thus dynamic user
clarification is not confused with replan-driven self-authorization.

The envelope is a set of predicates over concrete atoms. It may contain exact literals explicitly present in `q`, resolver obligations whose values must be grounded in authorized reads, and forbidden fields or effects. A resolver ledger records which predeclared obligation authorized each read, which structured query was executed, and which typed output projection supplied a later value. Untrusted text outside that projection cannot discharge the obligation.

The pre-commit monitor evaluates:

\[
G(q,t,x,s,h)\in\{\textsc{Allow},\textsc{Deny},\textsc{Abstain}\}.
\]

`Allow` commits the call. `Deny` rejects an atom explicitly outside `Gamma_q`. `Abstain` refuses automatic commitment when contract registration, identity, provenance, or authorization is unresolved.

## 2. Threat Model

The adversary may control content returned by read tools, including emails, documents, web pages, chat messages, search results, and records. It may attempt to:

- induce additional tools or operations;
- replace a resource, recipient, account, channel, file, amount, or destination;
- upgrade preview/draft/schedule behavior to a committed effect;
- introduce aliases or ambiguous identifiers;
- launder an injected value through later agent reasoning;
- repeat a rejected call or exploit replan feedback;
- spread an attack over multiple observations and trajectory steps.

The adversary cannot modify the monitor, frozen registry, tool schema, structured call after the check, or trusted environment state. Malicious tool implementations, compromised operating systems, and post-check argument mutation are outside the base model and must be stated as TCB assumptions.

The user may intentionally request a dangerous effect. The base indirect-injection goal is intent confinement, not global content safety: effects explicitly authorized by the original user are not classified as attacks solely because they are dangerous.

## 3. Contract and Envelope Obligations

### O1: Conservative causal-abstraction soundness

For every registered side-effectful tool and reachable totalized call:

\[
\Delta_{sec}(t,\bar{x},s)\subseteq\gamma(K_t(\bar{x},s,h)),
\qquad \bar{x}=\tau_t(x,s).
\]

The contract may over-approximate actual effects, causing denial or abstention,
but must not omit a committed effect. O1 decomposes into: (O1a) the observation
projection covers the claimed effect boundary; (O1b) interventions cover the
declared finite contract domain; (O1c) equal atoms do not hide distinct security
effects; and (O1d) conditional, default, and multi-resource effects expand
completely.

### O2: Envelope intent soundness

Every atom admitted by `Gamma_q` must be supported by `B_q`, and every clause in
`B_q` must be supported by the original request or by a resolver obligation
explicitly needed to fulfill that request. Untrusted observations may fill a
resolver through its typed projection but cannot create a new resolver, tool,
effect kind, literal, target, or authorization relation.

### O3: Complete mediation

Every side-effectful call reaches `G` before the corresponding environment transition. Read-only calls that can themselves create external effects, such as network requests with attacker-selected destinations, are side-effectful for this obligation.

### O4: Check-use integrity

The tool name, arguments, relevant state version, and evidence checked by `G` are the same values used by the executor. If this cannot be guaranteed, a version or hash must bind the check to execution.

### O5: Fail-closed uncertainty

Missing contracts, unresolved required fields or defaults, ambiguous aliases, untrusted provenance, and contradictory authorization context do not produce `Allow`.

### Lemma 1: Manifest bounding is authority-monotone

If `Bound(L_q,B_q)` accepts a proposal only when every proposed tool, field,
literal, and resolver is contained in `B_q`, then

\[
\Gamma_q(a)=\mathrm{true}\Rightarrow B_q(a)=\mathrm{true}.
\]

The result follows directly from the subset checks. A malformed or expanding
proposal produces no envelope and therefore cannot increase authority. An LLM
error can reduce liveness by omission, but cannot expand the trusted manifest.

### Lemma 2: Default-totalization equivalence

Assume `tau_t` resolves to `bar{x}`, and O4 binds `bar{x}` to execution. Then an
omitted static default and the same default supplied explicitly induce identical
contract atoms and authorization decisions. If `tau_t` is unresolved, O5 prevents
`Allow`. Thus omission cannot hide a known nonempty effect-bearing default.

### Lemma 3: Untrusted-history noninterference for authority epochs

Let two histories contain the same authenticated user-message sequence but
arbitrary different tool outputs, model summaries, and replan feedback. If
`Update` reads only the authenticated sequence and trusted registry, both
histories produce the same `B^(k)`. Therefore indirect prompt injection cannot
change the trusted authority epoch; it can only influence an LLM proposal that
is subsequently bounded by that epoch.

## 4. Counterfactual Registration and Causal Mediation

For intervention set `J`, hold the initial state, prior trajectory, implementation
version, nonintervened fields, and observation projection fixed, and define

\[
x'=do(x_J\leftarrow v_J).
\]

The concrete and abstract change relations are

\[
R_\Delta(x,x')=[\Delta_{sec}(t,x,s)\ne\Delta_{sec}(t,x',s)],
\]

\[
R_K(x,x')=[K_t(x,s,h)\ne K_t(x',s,h)].
\]

Canonical equivalence removes ordering, aliases, and declared harmless surface
forms before these comparisons.

The pair classification is:

| Concrete relation | Atom relation | Classification |
|---|---|---|
| changed | changed and all effects covered | faithful mediation |
| invariant | invariant and all effects covered | true invariance |
| changed | invariant or incompletely covered | mediation gap |
| invariant | changed | over-sensitive abstraction |

Checking only whether both sets changed is insufficient: a contract may represent
one changed effect while omitting another. Every concrete effect in both branches
must therefore be covered by an atom. A finite set of invariant tests does not
prove global irrelevance, and isolated one-field tests are incomplete when an
effect is triggered only by a conjunction.

For fields that share a branch condition or jointly determine a resource,
recipient, visibility, or commit effect, registration must add pairwise or
condition-aware tests. The real `create_calendar_event` check also demonstrates
implicit expansion: the implementation adds the calendar owner and sends an
invitation even when the explicit participant list is empty. A sound template
therefore expands over explicit recipients plus trusted runtime owner state.

This framework separates two causal questions. Action-source attribution, as in
AttriGuard, intervenes on untrusted observations and replays the agent to ask why
a call was proposed. Effect-semantics validation intervenes on the structured
call or tool state to ask what execution does and whether the contract mediates
that distinction. The first does not establish contract soundness; the second
does not establish that the model proposed a call for a trusted reason.

The LLM onboarding loop is a bounded form of counterexample-guided inductive
synthesis: the LLM proposes `K_i`, the validator finds a counterexample, and a
sanitized failure category informs `K_(i+1)`. Because the validator samples an
open domain rather than deciding a complete formal specification, this is
counterexample-guided refinement, not complete synthesis or proof.

E77 implements only a predecessor of this criterion. It executes one-field
counterfactuals and compares raw sandbox state/output snapshots, then retains
changed or unresolved fields. It does not independently project security
effects, compare the candidate atom relation, or require concrete-effect
coverage. Its result is conservative registration evidence, not causal
abstraction certification.

## 5. Single-Commit Confinement

### Proposition 1

Assume Lemmas 1--2 and O1--O5. If the monitor returns `Allow` for `(q,t,x,s,h)`, then every committed effect of the totalized call is authorized by `Gamma_q`:

\[
G(q,t,\bar{x},s,h)=\textsc{Allow}
\Rightarrow
\forall a\in\Delta(t,\bar{x},s),\ \Gamma_q(a)=\mathrm{true}.
\]

### Proof sketch

By Lemma 2, the guard and executor consume the same totalized argument object,
or unresolved default semantics fail closed. By O3, the call is checked before
commitment. The monitor permits it only if every atom in `widehat{Delta}`
satisfies `Gamma_q`; unresolved checks cannot allow by O5. By O1, every actual
effect is contained in `widehat{Delta}`. O4 ensures that the checked call is the
committed call. Lemma 1 prevents an LLM plan from exceeding the trusted manifest.
Therefore every committed effect satisfies the envelope and its authority bound.

## 6. Long-Trajectory Confinement

Let a trajectory contain committed calls `c_1,...,c_n`, with states `s_0,...,s_n`. Let `Delta_i` be the effects committed at step `i`. In a single-turn task the envelope is fixed from the original request; authorized reads may discharge existing resolver obligations but cannot enlarge it.

### Theorem 1: Prefix confinement

Assume Proposition 1 holds at every commit and untrusted observations cannot expand `Gamma_q`. Then for every trajectory prefix `j <= n`:

\[
\bigcup_{i=1}^{j}\Delta_i\subseteq\{a\mid\Gamma_q(a)=\mathrm{true}\}.
\]

### Proof

Base case `j=0` is immediate. For the inductive step, assume the union through `j-1` is authorized. Proposition 1 establishes that every effect in `Delta_j` is authorized under the unchanged envelope. The union through `j` is therefore authorized. This proves the property for all prefixes.

The theorem is a safety property, not a liveness or utility guarantee. A monitor may preserve confinement by denying all calls. Long-horizon evaluation must separately report task completion, attack-side utility, false replan, and recovery.

### Theorem 2: Authority-epoch prefix confinement

For a multi-turn trajectory, let `eta(i)` identify the latest authenticated user
epoch before commit `i`. Assume Lemma 3 and Proposition 1 with
`Gamma^(eta(i)) <= B^(eta(i))` at each commit. Then every prefix `j` satisfies

\[
\forall i\le j,\ \forall a\in\Delta_i,\quad B^{(\eta(i))}(a)=\mathrm{true}.
\]

The proof applies Proposition 1 at each transition using the epoch bound to
that checked call. Later revocation need not make an already committed effect
belong to the final bound, so the correct property is per-commit historical
authorization rather than set inclusion in `B^(k)` after all updates. When no
trusted update occurs, Theorem 2 reduces to Theorem 1.

## 7. Deterministic Decision Witnesses

Each pre-commit result should emit a machine-checkable witness:

- contract and template identifier;
- instantiated atom and bound field values;
- value source: original request, structured call, trusted state, or authorized resolver;
- matching envelope clause;
- decision and mismatch reason;
- registry and envelope hashes.

These witnesses are the paper's explanation mechanism. LLM chain-of-thought and post-hoc natural-language rationales are not security evidence.

## 8. Current E77 Alignment and Gaps

Current evidence supports:

- frozen per-tool `effect_kind`, `security_fields`, and `field_roles`;
- sandbox field state/output differences with unresolved fields fail closed;
- an initial LLM-generated exact/resolve/forbidden plan before tool output;
- deterministic comparison of supplied security-field values;
- authorized-read grounding and pre-commit interception in AgentDojo.
- exact pre-commit interception for all 3,173 valid calls reaching the E77
  AgentDojo executor;
- a two-template contract covering four enumerated `create_calendar_event`
  calls, including per-recipient and implicit-owner invitation effects;
- isolated implementations of manifest bounding and static-default
  totalization, with negative witnesses for the legacy paths.

Current evidence does not yet prove:

- multi-template expansion for every compound tool effect;
- O1 over all reachable tool states and argument combinations;
- independent soundness of the LLM-generated permission envelope;
- integration of the independent manifest and totalization mechanisms into the
  completed E77 benchmark run;
- check-use integrity under concurrent real services;
- production provenance integrity or alias canonicalization;
- long-trajectory confinement beyond AgentDojo's current task distribution.
- independent compilation of authenticated multi-turn user updates into
  authority epochs; the ToolSandbox candidate-envelope adapter isolates the
  visible trusted-user transcript but is not itself an O2 proof.

Before the paper states the full theorem as an implementation guarantee, the code must either implement and test these obligations or present the theorem explicitly as conditional on them.

## 9. Required Validation Map

| Obligation | Required evidence |
|---|---|
| O1 causal-abstraction soundness | Independent security-effect projection, single and interaction interventions, default and expansion checks, mediation-gap and over-sensitivity analysis, held-out audit |
| O2 envelope soundness | Independent source-span manifest, fixed resolver catalog, typed resolver ledger, envelope overreach audit |
| O3 complete mediation | Executor instrumentation and coverage test over every mutating/network-effect tool |
| O4 check-use integrity | Immutable call object or call/state hash verified at execution |
| O5 fail closed | Static-default totalization equivalence; dynamic/hidden default abstention; missing/ambiguous/contradictory context tests |
| Prefix confinement | Long-horizon attacks at early/middle/late/repeated positions with per-step state audit |
