# E55 Review Response Notes

## What concrete information must a pre-commit mediator provide?

Typed authorization context, resource aliases, operation mode, multi-resource expansion surface, provenance/control-source metadata, and enough non-oracle evidence to canonicalize opaque resources.

## Does this solve deployment safety?

No. E55 is a deterministic local mock evaluation. It tests whether explicit authorization infrastructure addresses the E50 bottleneck under controlled schemas; it does not validate production SaaS, browser, banking, messaging, or filesystem behavior.

## Why is this useful despite the controlled setup?

The ablations isolate which infrastructure pieces matter: alias resolution, multi-resource expansion, operation-mode binding, provenance overlay, and evidence fallback. The correct reviewer-facing claim is that these pieces are necessary engineering structure for effect binding, not that the current prototype generalizes universally.

## What changed after human audit?

The E57 human spot audit found a corrected-label subset: 6/60 audited rows need decision corrections and 14/60 need atom/resource/reason corrections. The main issue is transaction-domain atom design: `amount` should be treated as a value/operation constraint, not as a resource authorization atom. A minimal corrected sensitivity keeps the full guard's unsafe pre-allow at zero but introduces FDeny `4/230 = 0.017`. E55-v2 corrects the atom schema and unknown-resource fallback behavior; its strict rerun keeps UPA and FDeny at zero with lower coverage (`0.880`). E57-style checks on E55-v2 also pass: changed decisions `0`, UPA delta `0.0`, coverage delta `0.0`, and independent reference-authorizer decision/atom/resource-set agreement `1.0`. Reviewer-facing language should explicitly report this correction rather than claiming perfect label validation.

Outcome: `Outcome B`.
