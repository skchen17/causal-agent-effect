# B8 Adapter Limitations

This is a comparable local adapter, not a reproduction of the original ToolSafe/TS-Guard benchmark or model checkpoint protocol. It uses only fields available in this artifact's deployable input views and maps a step-level guardrail decision to `ALLOW`, `DENY`, or `ABSTAIN`.

The adapter is intentionally non-atom-level: it does not consume gold atoms, expand multi-resource atoms with the paper's mediator, or use expected decisions. Its results should be read as a released-guardrail-style baseline under a constrained common input contract, not as a global comparison against ToolSafe, TS-Guard, Safiron, IPIGuard, or CaMeL.
