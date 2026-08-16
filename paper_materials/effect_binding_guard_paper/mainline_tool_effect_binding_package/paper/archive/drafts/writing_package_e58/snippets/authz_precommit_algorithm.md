# Authorization-Aware Pre-Commit Prototype

1. Expand each visible tool call into effect-resource-operation atoms.
2. Canonicalize resources and aliases.
3. Check all atoms against the typed authorization context.
4. Apply operation-mode, multi-resource, visibility, and provenance constraints.
5. Abstain if evidence or canonicalization is insufficient.
6. Commit only if all atoms are authorized.
