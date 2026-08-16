# Tool-Effect Binding: Standalone Theory and Proofs

This note isolates the theory from the paper narrative and empirical system. It
states exactly what is proved, what must be supplied by an experiment, and what
remains an assumption.

## 1. Execution and Authority Model

An execution context is

\[
u=(t,\bar{x},s,h),
\]

where \(t\) is a tool, \(\bar{x}\) is the totalized call, \(s\) is the
pre-state, and \(h\) is trusted pre-call evidence. Executing \(u\) produces a
finite set of security-relevant concrete effects:

\[
\Delta(u)\subseteq\mathcal{E}.
\]

Let \(\mathcal{B}\subseteq 2^{\mathcal{E}}\) be the admissible family of
independently justified authority bounds. The ideal authorization decision is:

\[
I_B(u)=1 \iff \Delta(u)\subseteq B.
\]

The runtime does not observe \(\Delta(u)\) directly. It observes a
representation:

\[
\rho:\mathcal{U}\rightarrow\mathcal{Z}.
\]

Examples of \(\rho\) include a tool name, a scalar risk score, a whole-call
summary, or a canonical set of effect atoms.

## 2. Authorization Equivalence

Two contexts are authorization-equivalent relative to \(\mathcal{B}\) when no
admissible authority distinguishes them:

\[
u\equiv_{\mathcal{B}}v
\iff
\forall B\in\mathcal{B},\ I_B(u)=I_B(v).
\]

A representation is authorization-sufficient on domain \(D\) when:

\[
\rho(u)=\rho(v)
\Longrightarrow
u\equiv_{\mathcal{B}}v
\quad
\forall u,v\in D.
\]

This definition is policy-relative. Different concrete effects need not be
represented separately if no admissible authority can distinguish them.
Conversely, a representation is insufficient when it merges effects for which
the policy family requires different decisions.

## 3. Representation-Insufficiency Theorem

### Theorem 1

If \(\rho\) is not authorization-sufficient on \(D\), no deterministic monitor
that observes only \((\rho(u),B)\) can be both:

- **sound**: it never allows when \(I_B(u)=0\); and
- **permissive**: it always allows when \(I_B(u)=1\).

### Proof

Insufficiency gives \(u,v\in D\) and \(B^\star\in\mathcal{B}\) such that:

\[
\rho(u)=\rho(v)
\]

but, without loss of generality,

\[
I_{B^\star}(u)=1,\qquad I_{B^\star}(v)=0.
\]

The monitor receives the identical input \((\rho(u),B^\star)\) in both cases,
so it must return the same decision.

- If it returns `ALLOW`, it is unsound on \(v\).
- If it returns `DENY`, it is not permissive on \(u\).
- If it returns `ABSTAIN`, it is also not permissive on \(u\).

Every possible decision violates at least one property. Therefore no such
monitor can be both sound and permissive. QED.

### Interpretation

Abstention can choose safety over utility, but it cannot recover information
already erased by the representation. The theorem does not claim that every
whole-call monitor is insufficient. A whole-call representation preserving all
authorization-equivalence classes is sufficient by definition.

## 4. Compound-Effect Corollary

Suppose:

\[
\rho(u)=\rho(v),\qquad
\Delta(v)=\Delta(u)\cup\{e\},
\]

and an admissible bound \(B\) contains \(\Delta(u)\) but not \(e\). Then the
monitor must either:

- allow unauthorized effect \(e\) in \(v\); or
- deny/abstain on authorized context \(u\).

This is Theorem 1 with \(B\) as the separating authority. It formalizes the
calendar example: if adding an invitation does not change the monitored
representation, complete mediation over that representation cannot allow event
creation while independently rejecting the invitation.

## 5. Quantitative Collision Lower Bound

For representation cell

\[
C_{z,B}=\{u\in D:\rho(u)=z\},
\]

let:

\[
P_{z,B}=|\{u\in C_{z,B}:I_B(u)=1\}|,
\]

\[
N_{z,B}=|\{u\in C_{z,B}:I_B(u)=0\}|.
\]

If both counts are nonzero, one deterministic decision applies to the whole
cell:

- `ALLOW` creates \(N_{z,B}\) unsafe allows;
- `DENY` or `ABSTAIN` withholds \(P_{z,B}\) authorized calls.

Under equal unit cost, every monitor incurs at least:

\[
\min(P_{z,B},N_{z,B})
\]

errors or withheld authorized commitments in that cell. With unsafe-allow cost
\(c_U\) and withholding cost \(c_W\), the lower bound is:

\[
\min(c_UN_{z,B},c_WP_{z,B}).
\]

This proposition gives an empirical quantity: representation collisions imply
a minimum achievable security/utility cost independent of the downstream
classifier.

## 6. Counterfactual Mediation-Gap Proposition

Let \(\rho_K(u)\) be the canonical atom representation emitted by candidate
contract \(K\). Let \(v=do_J(u)\) be a controlled intervention.

If:

\[
\rho_K(u)=\rho_K(v)
\]

and some admissible authority separates the concrete effects:

\[
\exists B\in\mathcal{B}:I_B(u)\neq I_B(v),
\]

then \(K\) is not authorization-sufficient on any domain containing both
contexts.

### Proof

The pair directly violates the definition of authorization sufficiency.
Theorem 1 then applies to every downstream monitor restricted to
\(\rho_K\). QED.

### Important Qualification

A changed sandbox state is not automatically a witness. The experiment must
show that:

1. the observed difference is a security-relevant effect;
2. the intervention did not change uncontrolled variables; and
3. an admissible authority can require different decisions.

Without item 3, the pair may show causal relevance but not authorization
relevance.

## 7. Finite-Domain Adequacy Theorem

An intervention suite is **collision-complete** for finite domain \(D\) when it
checks every pair \(u,v\in D\) with \(\rho_K(u)=\rho_K(v)\), using a sound oracle
for authorization equivalence.

### Theorem 2

If a collision-complete suite finds no authorization-separating collision, then
\(\rho_K\) is authorization-sufficient on \(D\).

### Proof

Assume \(\rho_K\) is not sufficient. Then some equal-representation pair in
\(D\) is authorization-inequivalent. Collision completeness requires the suite
to check that pair, and oracle soundness marks it as separating. This
contradicts the premise that no separating collision was found. Therefore
\(\rho_K\) is sufficient on \(D\). QED.

### Scope

This is a positive result only for a finite declared domain with complete
collision coverage and a sound oracle. Sampled counterfactual tests over open
tool domains remain falsification procedures.

## 8. Relative Atom Necessity

Let \(\pi_{-f}\) erase atom field or qualifier \(f\). Field \(f\) is necessary
on \((D,\mathcal{B})\) when:

\[
\rho_K \text{ is sufficient}
\quad\text{and}\quad
\pi_{-f}\circ\rho_K \text{ is insufficient}.
\]

By Theorem 1, erasing a necessary field creates an unavoidable unsafe allow or
withheld authorized call for some admissible bound.

Necessity is relative to the domain and policy family. A field need not change
whenever its raw input changes; it must distinguish only changes that can alter
authorization.

## 9. Conditional Effect-Confinement Theorem

Let \(A_i=K(u_i)\) be the atoms for commit \(i\), and let \(\gamma(A_i)\) be
their concrete effect over-approximation. Let \(\Gamma_i\) be the atom-level
runtime envelope, with concrete closure:

\[
\mathsf{Cl}(\Gamma_i)
=
\bigcup_{\Gamma_i(a)=\mathrm{true}}\gamma(a).
\]

Assume:

1. **O1, abstraction soundness**:
   \(\Delta(u_i)\subseteq\gamma(A_i)\).
2. **O2, envelope soundness**:
   \(\mathsf{Cl}(\Gamma_i)\subseteq B^{(\eta(i))}\).
3. **O3, complete mediation**:
   every committed effectful transition has a preceding guard decision.
4. **O4, check-use integrity**:
   the executed call and versions equal the checked call and versions.
5. **O5, fail-closed uncertainty**:
   unresolved effect-bearing inputs cannot produce `ALLOW`.

### Theorem 3

Every committed transition satisfies:

\[
\Delta(u_i)
\subseteq
\mathsf{Cl}(\Gamma_i)
\subseteq
B^{(\eta(i))}.
\]

### Proof

O3 supplies a preceding guard decision, and O5 ensures that commitment follows
a fully resolved `ALLOW`. The allow rule requires every \(a\in A_i\) to satisfy
\(\Gamma_i(a)\), so:

\[
\gamma(A_i)\subseteq\mathsf{Cl}(\Gamma_i).
\]

O1 and O2 give:

\[
\Delta(u_i)
\subseteq\gamma(A_i)
\subseteq\mathsf{Cl}(\Gamma_i)
\subseteq B^{(\eta(i))}.
\]

O4 guarantees that these inclusions apply to the transition actually
committed. QED.

## 10. Trajectory-Prefix Corollary

Applying Theorem 3 to every committed transition gives:

\[
\forall i\le j:
\Delta(u_i)\subseteq B^{(\eta(i))}.
\]

If the authority epoch is fixed:

\[
\bigcup_{i=1}^{j}\Delta(u_i)\subseteq B_q.
\]

This follows by induction over committed transitions. It is a safety property,
not a task-completion or recovery guarantee.

## 11. Final Theory Status

The proofs are logically complete under their stated assumptions. They
establish:

- an information-loss limitation on coarse monitoring representations;
- an executable counterfactual witness of representation insufficiency;
- a bounded positive result for collision-complete finite domains; and
- conditional effect confinement for a correctly instantiated runtime.

They do not establish:

- that the current atom contract satisfies O1 globally;
- that an LLM-generated authority satisfies O2;
- that sampled interventions are collision-complete;
- that recovery terminates successfully; or
- production or deployed-service safety.

Experiments must therefore test the premises and practical relevance, not
"prove" the logical implications again.
