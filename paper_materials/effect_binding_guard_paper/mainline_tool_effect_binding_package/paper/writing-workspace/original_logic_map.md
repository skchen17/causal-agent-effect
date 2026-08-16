# Original Logic Map

## Source State

The rewrite began from drafts centered on a hard guard, E55-style local authorization contracts, and later task-authority/runtime-recovery experiments. Those drafts contained useful measurements but did not maintain one claim boundary: a general authority architecture, atom representation, prompt-injection defense, and utility recovery were often treated as one contribution.

## Logic That Survived

- Tool surfaces can hide authorization-relevant differences in effects, resources, targets, operation modes, and provenance.
- Counterfactual pairs are useful when they execute a fixed tool implementation and compare committed effects.
- E47--E50 provide controlled problem diagnosis and identify resource/authorization binding as difficult.
- Pre-commit enforcement and exact check–use binding are appropriate systems boundaries.
- Negative results, abstention, false denial, and audit corrections must remain visible.

## Logic That Changed

| Earlier move | Problem | Current replacement |
|---|---|---|
| Treat a fixed atom tuple as the core abstraction | Appears arbitrary and cannot express tool-specific qualifiers | Policy-relative effect occurrences and representation partitions |
| Let LLM-generated contracts stand as semantic evidence | Circular and dependent on prompt quality | Treat proposals as untrusted labels; validate against source-executed effects |
| Make E55-v2 the principal proof | Controlled local schema cannot establish independent or realistic validity | Use finite source and ToolSandbox collision evidence as the representation result |
| Claim a general task-authority envelope | Implementation lacks general ACL, delegation, quota, and semantic authority | Restrict C1f to provenance-origin confinement |
| Attribute zero ASR to minimal atoms | Registry retains 67/67 fields and Spotlighting ties | Present C1f as an auditable mediation case study; attribute atom value through source collisions and bounded ablation |
| Use denial/replan recovery as the main systems story | Utility depended on engineering and model recovery behavior | Measure utility independently; keep runtime checking deterministic and narrow |

## Current Claim Chain

1. Compound effects exist in benchmark tool implementations.
2. Coarse representations merge effects separated by admissible policies.
3. Such collisions force unsafe allow or withheld authorized work for any downstream monitor over that view.
4. Source-executed counterexamples refine the representation on a finite domain.
5. Frozen typed effects remain sufficient on a separate ToolSandbox source domain.
6. Broad AgentDojo registration is conservative and incomplete, not globally minimal.
7. A frozen descriptor can nevertheless drive a narrow, fully audited provenance-origin pre-commit monitor.
8. Same-model, second-model, held-out, transfer, and granularity results bound how far that runtime evidence generalizes.

## Conservation Check

Historical E55/E77/E84 evidence is not deleted from the repository, but it is excluded from the active claim chain unless explicitly labeled as historical or diagnostic. No final statement may infer complete authorization, production safety, global atom minimality, or unrestricted adaptive robustness.
