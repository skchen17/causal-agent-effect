# E2 Policy-Family × Qualifier-Deletion Sensitivity Report

## Runbook

- Script: `experiments/security-analysis-ablation-and-overhead/source/policy-family-sensitivity/run_policy_family_sensitivity.py`
- Command: `python3 experiments/security-analysis-ablation-and-overhead/source/policy-family-sensitivity/run_policy_family_sensitivity.py`
- Inputs (read-only, frozen):
  - `experiments/human-authority-and-causal-validation/results/finite-domain-effect-binding-validation/finite-contexts.jsonl`
  - `experiments/human-authority-and-causal-validation/evaluation/heldout-toolsandbox-effect-binding-validation/heldout-contexts.jsonl`
- Dependencies: Python standard library only; CPU-only; no network.
- Python: 3.10.12

## Definitions

- Retained separating pairs: context pairs with identical post-deletion representations whose source effects remain separable by some authority in the family (authorization-separating collisions created or retained by the deletion).
- Redundant pairs: context pairs with identical representations and different full source effects that the family cannot express (identical family projection); the distinction is policy-invisible under that family.
- Overpartition cells: family-equivalence classes split into more than one representation signature.
- False-rejection pairs: family-equivalent context pairs with different representation signatures (signature-bound authority would treat identically authorized calls differently).
- Vacuous: the deletion changes no representation signature in the domain.

## Family enumeration principle (table note)

The four authority families are the images of the paper's submultiset authority construction under a pre-enumerated lattice of occurrence projections: identity (power-set baseline), effect-name quotient, resource quotient, and the {0,1,>=2} count truncation of the effect-name quotient. Each family contains every submultiset of every observed projected effect multiset, so the families are closed under submultisets by construction. The set is fixed before any metric is computed; it is not selected from observed redundancy rates.

## Qualifier-role mapping

### agentdojo_finite_domain

| Qualifier role | Deletion operation | Instantiated by |
|---|---|---|
| date | drop qualifier keys {'date'} | banking/schedule_transaction qualifiers.date |
| subject | drop qualifier keys {'subject'} | banking/schedule_transaction qualifiers.subject |
| recurrence | drop qualifier keys {'recurring'} | banking/schedule_transaction qualifiers.recurring |
| payload | drop qualifier keys {'content', 'filename'}; mask 'payload:<digest>' resources to 'payload:*' | workspace/create_file qualifiers.content/filename; slack/send_direct_message payload-digest resource |
| visibility | replace atom visibility with '__DELETED__' | workspace/share_file permission visibility |

### toolsandbox_heldout

| Qualifier role | Deletion operation | Instantiated by |
|---|---|---|
| date | drop qualifier keys {'reminder_timestamp'} | add_reminder qualifiers.reminder_timestamp |
| subject | no-op (role not instantiated by the five held-out tools) | (none) |
| recurrence | no-op (role not instantiated by the five held-out tools) | (none) |
| payload | drop qualifier keys {'name', 'relationship', 'is_self', 'removed_contact_identity', 'content'} | add_contact qualifiers.name/relationship/is_self; remove_contact qualifiers.removed_contact_identity; add_reminder qualifiers.content |
| visibility | replace atom visibility with '__DELETED__' | (none) |

## Sensitivity table: agentdojo_finite_domain

| Family | Qualifier deleted | Rep cells | Separating | Redundant | Redundancy rate | Overpartition cells | False rejections | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| power_set | none | 56 | 0 | 0 | NA | 0 | 0 | no_effect |
| power_set | date | 40 | 16 | 0 | 0.000 | 0 | 0 | necessary |
| power_set | subject | 40 | 16 | 0 | 0.000 | 0 | 0 | necessary |
| power_set | recurrence | 40 | 16 | 0 | 0.000 | 0 | 0 | necessary |
| power_set | payload | 51 | 8 | 0 | 0.000 | 0 | 0 | necessary |
| power_set | visibility | 52 | 4 | 0 | 0.000 | 0 | 0 | necessary |
| effect_kind | none | 56 | 0 | 0 | NA | 6 | 548 | no_effect |
| effect_kind | date | 40 | 0 | 16 | 1.000 | 6 | 532 | redundant |
| effect_kind | subject | 40 | 0 | 16 | 1.000 | 6 | 532 | redundant |
| effect_kind | recurrence | 40 | 0 | 16 | 1.000 | 6 | 532 | redundant |
| effect_kind | payload | 51 | 0 | 8 | 1.000 | 5 | 540 | redundant |
| effect_kind | visibility | 52 | 0 | 4 | 1.000 | 6 | 544 | redundant |
| resource | none | 56 | 0 | 0 | NA | 9 | 262 | no_effect |
| resource | date | 40 | 0 | 16 | 1.000 | 9 | 246 | redundant |
| resource | subject | 40 | 0 | 16 | 1.000 | 9 | 246 | redundant |
| resource | recurrence | 40 | 0 | 16 | 1.000 | 9 | 246 | redundant |
| resource | payload | 51 | 2 | 6 | 0.750 | 8 | 256 | necessary |
| resource | visibility | 52 | 0 | 4 | 1.000 | 9 | 258 | redundant |
| count_truncated | none | 56 | 0 | 0 | NA | 6 | 548 | no_effect |
| count_truncated | date | 40 | 0 | 16 | 1.000 | 6 | 532 | redundant |
| count_truncated | subject | 40 | 0 | 16 | 1.000 | 6 | 532 | redundant |
| count_truncated | recurrence | 40 | 0 | 16 | 1.000 | 6 | 532 | redundant |
| count_truncated | payload | 51 | 0 | 8 | 1.000 | 5 | 540 | redundant |
| count_truncated | visibility | 52 | 0 | 4 | 1.000 | 6 | 544 | redundant |

### Family separability ceilings: agentdojo_finite_domain

| Family | Different-effect pairs | Family-separable | Ceiling |
|---|---:|---:|---:|
| power_set | 1540 | 1540 | 1.000 |
| effect_kind | 1540 | 992 | 0.644 |
| resource | 1540 | 1278 | 0.830 |
| count_truncated | 1540 | 992 | 0.644 |

## Sensitivity table: toolsandbox_heldout

| Family | Qualifier deleted | Rep cells | Separating | Redundant | Redundancy rate | Overpartition cells | False rejections | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| power_set | none | 25 | 0 | 0 | NA | 0 | 0 | no_effect |
| power_set | date | 21 | 4 | 0 | 0.000 | 0 | 0 | necessary |
| power_set | subject | 25 | 0 | 0 | NA | 0 | 0 | vacuous |
| power_set | recurrence | 25 | 0 | 0 | NA | 0 | 0 | vacuous |
| power_set | payload | 15 | 16 | 0 | 0.000 | 0 | 0 | necessary |
| power_set | visibility | 25 | 0 | 0 | NA | 0 | 0 | no_effect |
| effect_kind | none | 25 | 0 | 0 | NA | 5 | 61 | no_effect |
| effect_kind | date | 21 | 0 | 4 | 1.000 | 5 | 57 | redundant |
| effect_kind | subject | 25 | 0 | 0 | NA | 5 | 61 | vacuous |
| effect_kind | recurrence | 25 | 0 | 0 | NA | 5 | 61 | vacuous |
| effect_kind | payload | 15 | 0 | 16 | 1.000 | 5 | 45 | redundant |
| effect_kind | visibility | 25 | 0 | 0 | NA | 5 | 61 | no_effect |
| resource | none | 25 | 0 | 0 | NA | 3 | 57 | no_effect |
| resource | date | 21 | 0 | 4 | 1.000 | 3 | 53 | redundant |
| resource | subject | 25 | 0 | 0 | NA | 3 | 57 | vacuous |
| resource | recurrence | 25 | 0 | 0 | NA | 3 | 57 | vacuous |
| resource | payload | 15 | 0 | 16 | 1.000 | 3 | 41 | redundant |
| resource | visibility | 25 | 0 | 0 | NA | 3 | 57 | no_effect |
| count_truncated | none | 25 | 0 | 0 | NA | 5 | 63 | no_effect |
| count_truncated | date | 21 | 0 | 4 | 1.000 | 5 | 59 | redundant |
| count_truncated | subject | 25 | 0 | 0 | NA | 5 | 63 | vacuous |
| count_truncated | recurrence | 25 | 0 | 0 | NA | 5 | 63 | vacuous |
| count_truncated | payload | 15 | 0 | 16 | 1.000 | 5 | 47 | redundant |
| count_truncated | visibility | 25 | 0 | 0 | NA | 5 | 63 | no_effect |

### Family separability ceilings: toolsandbox_heldout

| Family | Different-effect pairs | Family-separable | Ceiling |
|---|---:|---:|---:|
| power_set | 468 | 468 | 1.000 |
| effect_kind | 468 | 407 | 0.870 |
| resource | 468 | 411 | 0.878 |
| count_truncated | 468 | 405 | 0.865 |

## Baseline reproduction checks

| Check | Domain | Observed | Expected | Passed |
|---|---|---|---|:---:|
| typed contract is an exact partition under the power-set family with no deletion (reproduces the zero-collision baseline) | agentdojo_finite_domain | {"false_rejection_pairs": 0, "overpartition_cells": 0, "representation_cells": 56, "separating_pairs": 0} | {"false_rejection_pairs": 0, "overpartition_cells": 0, "separating_pairs": 0} | yes |
| typed contract is an exact partition under the power-set family with no deletion (reproduces the zero-collision baseline) | toolsandbox_heldout | {"false_rejection_pairs": 0, "overpartition_cells": 0, "representation_cells": 25, "separating_pairs": 0} | {"false_rejection_pairs": 0, "overpartition_cells": 0, "separating_pairs": 0} | yes |
| dropping all qualifiers reproduces the frozen common-contract separating-pair baseline | agentdojo_finite_domain | {"separating_pairs": 118} | {"separating_pairs": 118} | yes |
| dropping all qualifiers reproduces the frozen common-contract separating-pair baseline | toolsandbox_heldout | {"separating_pairs": 41} | {"separating_pairs": 41} | yes |
| vacuous deletion 'subject' leaves all family metrics unchanged | toolsandbox_heldout | {"mismatched_families": []} | {"mismatched_families": []} | yes |
| vacuous deletion 'recurrence' leaves all family metrics unchanged | toolsandbox_heldout | {"mismatched_families": []} | {"mismatched_families": []} | yes |

## Per-qualifier verdicts

| Domain | Qualifier | Vacuous | Verdict |
|---|---|:---:|---|
| agentdojo_finite_domain | date | no | necessary_only_under_power_set |
| agentdojo_finite_domain | subject | no | necessary_only_under_power_set |
| agentdojo_finite_domain | recurrence | no | necessary_only_under_power_set |
| agentdojo_finite_domain | payload | no | mixed |
| agentdojo_finite_domain | visibility | no | necessary_only_under_power_set |
| toolsandbox_heldout | date | no | necessary_only_under_power_set |
| toolsandbox_heldout | subject | yes | vacuous |
| toolsandbox_heldout | recurrence | yes | vacuous |
| toolsandbox_heldout | payload | no | necessary_only_under_power_set |
| toolsandbox_heldout | visibility | no | never_necessary_under_tested_families |

## Claim boundary (both directions pre-registered)

Selected direction from the observed grid: `mixed`.

> Mixed: qualifier necessity varies by qualifier role and family; see the per-role verdict rows. Necessity claims are scoped to the domain-qualifier-family cells marked 'necessary'; cells marked 'redundant' delimit where the coarser family cannot express the distinction.

Observed summary: Across both domains, 7 of 10 non-baseline power-set deletion rows create authorization-separating collisions (the remainder are vacuous or no-effect); among 24 non-vacuous deletion rows under the three coarser families, 20 have redundancy rate 1.000. Exceptions with residual separating pairs under a coarser family: [{"domain": "agentdojo_finite_domain", "family": "resource", "qualifier": "payload", "redundancy_rate": 0.75, "redundant_pairs": 6, "separating_pairs": 2}].

Templates (both retained regardless of direction):

- Low redundancy: Low redundancy (direction 2): under every tested coarser family, deleting non-vacuous qualifiers still created authorization-separating collisions. The typed qualifiers remain operationally necessary across the tested family lattice, not only under the power-set family. This counters the claim that the contract is a serialization of the state difference whose qualifiers become dispensable once authority is aggregated.
- High redundancy: High redundancy (direction 1): under the coarser families, most or all collisions created by qualifier deletion are policy-invisible (redundant pairs). Qualifier necessity is therefore representation-relative: the paper's qualifier-necessity claim is scoped to the declared power-set authority family, and the coarser families quantify which effect details those policies cannot express. This is positive evidence that the representation is policy-relative rather than a fixed serialization.
- Mixed: Mixed: qualifier necessity varies by qualifier role and family; see the per-role verdict rows. Necessity claims are scoped to the domain-qualifier-family cells marked 'necessary'; cells marked 'redundant' delimit where the coarser family cannot express the distinction.

## Claim boundary (fixed scope)

Deterministic recomputation over two frozen finite domains with source-hash-bound effect oracles. Separability is defined relative to the declared family's projection of source-effect multisets; the families are declared before metric computation. Results do not extend to unenumerated calls, open tool domains, deployment policy languages, or families outside the enumerated lattice.
