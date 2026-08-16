# E55 Pre-Commit Authorization Schema

`AuthorizationContext` is visible infrastructure supplied by the local pre-commit mediator. It lists allowed effects, operations, resources, aliases, recipient/account/channel/file sets, operation-mode permissions, visibility/public-link permissions, multi-resource policy, and trusted/untrusted/private control sources.

`EffectAtom` is the local mediator's effect-resource-operation unit: effect, operation, resource id/type, aliases, visibility, recipient role, commit mode, provenance source, and control source.

`label_hidden_input` is the only deployable method input. It includes task text, visible authorization context, tool inventory, tool name/arguments, non-oracle views, provenance summary, and optional non-oracle evidence summary. It excludes expected decisions, violation reasons, gold expanded atoms, oracle labels, and direct safety labels.
