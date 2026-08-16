# T1 Refinement-Monotonicity Trajectory Check Report

## Runbook

- Script: `experiments/security-analysis-ablation-and-overhead/source/refinement-monotonicity-check/run_refinement_monotonicity_check.py`
- Command: `python3 experiments/security-analysis-ablation-and-overhead/source/refinement-monotonicity-check/run_refinement_monotonicity_check.py`
- Inputs (read-only, frozen):
  - `experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-contexts.jsonl` (sha256 `89ba86ca3f74e093...`), 56 contexts
  - `experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-domain-validation-report.json`
- Dependencies: Python standard library only; CPU-only; no network.
- Python: 3.10.12

## Definitions

- Refinement lattice: representation $\\rho_K$ keeps exactly the qualifier roles in $K\\subseteq\{\textsf{date},\textsf{subject},\textsf{recurrence},\textsf{payload},\textsf{visibility}\}$ and erases the rest with the E2 deletion operations. The lattice is the subset lattice of the five roles (32 vertices, ordered by inclusion).
- Separating pairs: context pairs with identical representation signature and different authority-family signatures (same decision procedure as E2 under the power-set family).
- Order preservation (T1(a)): $\\rho_{K'}$ refines $\\rho_K$ when $K'\supset K$ (fine equality implies coarse equality on every pair), and separating pairs are monotone non-increasing along every lattice edge.
- Termination (T1(b)): the recorded coarse-to-fine trajectory has bounded length $\leq |D|-1$ and reaches a fixed point (zero separating pairs).
- Collision monotonicity (T1(c)): separating-pair count and the ambiguous-cell lower bound are non-increasing along the trajectory.
- Ambiguous-cell lower bound: $\\sum_{\\text{cells}}(|\text{cell}|-\max_{\\text{class}}|\text{cell}\cap\text{class}|)$, the minimum number of authorized members a sound monitor must withhold from mixed representation cells.

## Domain

- agentdojo_finite_domain: 56 contexts; frozen input hash recorded above.

## Baseline cross-checks

Representation-semantics note: the lattice erased end $\rho_{\emptyset}$ applies all five E2 deletion operations (qualifier sub-keys dropped, payload resource masked, visibility set to a constant), whereas the E2 common-contract baseline strips only the entire qualifiers key. These are two different coarse representations; both converge to the same typed end. The script therefore reproduces the common baseline independently (below) rather than conflating it with a lattice vertex.

| Check | Observed | Expected | Passed |
|---|---|---|:---:|
| common-contract semantics (entire qualifiers key stripped, E2 baseline path) reproduce the frozen common-contract separating-pair baseline | 118 | 118 | yes |
| typed end (all qualifier roles kept) reproduces the frozen typed-contract zero-separating-pair baseline | 0 | 0 | yes |
| trajectory separates pairs monotonically non-increasing (T1(a) instance) | [124, 60, 28, 12, 4, 0] | non-increasing | yes |
| ambiguous-cell lower bound monotonically non-increasing along trajectory (Ambiguous-cell lower bound instance) | [37, 33, 25, 9, 4, 0] | non-increasing | yes |
| refinement holds on every subset-lattice edge (fine equality implies coarse equality) | 0 violations over 211 comparable pairs | 0 | yes |
| separating pairs monotone on every lattice edge | 0 violations over 211 comparable pairs | 0 | yes |
| ambiguous-cell lower bound monotone on every lattice edge | 0 violations over 211 comparable pairs | 0 | yes |
| trajectory length within the partition-lattice bound |D|-1 | 5 | <= 55 | yes |
| trajectory reaches a fixed point (zero separating pairs) | 0 | 0 | yes |

## Recorded refinement trajectory (coarse to fine, 5 steps)

| Step | Qualifier added | Rep cells | Separating pairs | Mixed cells | Ambiguous-cell LB | Strict |
|---|---|---:|---:|---:|---:|:---:|
| 0 | (baseline) | 19 | 124 | 11 | 37 | no |
| 1 | date | 23 | 60 | 15 | 33 | yes |
| 2 | subject | 31 | 28 | 23 | 25 | yes |
| 3 | recurrence | 47 | 12 | 7 | 9 | yes |
| 4 | payload | 52 | 4 | 4 | 4 | yes |
| 5 | visibility | 56 | 0 | 0 | 0 | yes |

## Trajectory assertions (T1(a) order preservation along the trajectory)

| Step | Refinement holds | SP non-increasing | Cells non-decreasing |
|---|---|---:|---:|
| 1 | yes | yes | yes |
| 2 | yes | yes | yes |
| 3 | yes | yes | yes |
| 4 | yes | yes | yes |
| 5 | yes | yes | yes |

## Full-lattice edge checks (T1(a) on every subset-lattice edge)

- Vertices: 32 (all subsets of the five qualifier roles).
- Comparable pairs checked: 211.
- Refinement violations: 0 (expect 0).
- Edges with non-monotone separating pairs: 0 (expect 0).
- Edges with non-monotone ambiguous-cell lower bound: 0 (expect 0).

## Termination (T1(b))

- Trajectory length: 5 (bound |D|-1 = 55).
- Length within bound: yes.
- Fixed point reached (zero separating pairs): yes.
- Cycle-free: yes (each subset vertex visited at most once).

## Collision monotonicity (T1(c))

- Separating pairs non-increasing along trajectory: yes.
- Ambiguous-cell lower bound non-increasing along trajectory: yes.

## E2 cross-checks

| Single-role deletion from typed contract | Observed SP | E2 power-set grid SP | Passed |
|---|---|---|:---:|
| date | 16 | 16 | yes |
| subject | 16 | 16 | yes |
| recurrence | 16 | 16 | yes |
| payload | 8 | 8 | yes |
| visibility | 4 | 4 | yes |

## Conclusion

Status: `passed`.

Interpretation: on the frozen 56-call domain, the lattice instantiation satisfies order preservation, bounded termination, and collision-count monotonicity. This is an execution-grounded instance of the T1 theorem draft; it is not an open-domain certificate. The trajectory is policy-relative (power-set authority family, E2 decision procedure, frozen oracle).
