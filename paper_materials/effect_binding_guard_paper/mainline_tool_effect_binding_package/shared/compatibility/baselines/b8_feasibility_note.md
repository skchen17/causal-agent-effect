# B8 Released Guardrail Adapter Feasibility Note

Status: `separate_comparable_adapter_available`.

B8 is implemented separately under `baselines/b8_released_guardrail/` as a ToolSafe/TS-Guard-style comparable local adapter. The run consumes label-hidden deployable inputs and must be presented as a comparable local adapter, not as an original benchmark reproduction.

| Candidate | Public source | Adapter status |
|---|---|---|
| ToolSafe / TS-Guard | https://github.com/MurrayTom/ToolSafe | Selected as the released-guardrail anchor for the separate comparable local adapter. |
| Safiron / Agentic-Guardian | https://github.com/HowieHwong/Agentic-Guardian | Public artifact noted, not selected for this comparable adapter pass. |
| IPIGuard | https://github.com/Greysahy/ipiguard | Used as the source family for the E61 saved external replay subset, not selected as the B8 adapter. |
| CaMeL | https://github.com/google-research/camel-prompt-injection | Public artifact noted, not selected for this comparable adapter pass. |
