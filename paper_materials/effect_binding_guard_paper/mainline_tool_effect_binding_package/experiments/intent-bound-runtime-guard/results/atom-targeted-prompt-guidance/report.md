# Atom-Targeted Multi-Method Pilot

Status: `passed`.

| Method | Mechanism | Clean utility | Injected utility | ASR | Coverage | Interventions |
|---|---|---:|---:|---:|---:|---:|
| No defense | none | 7/8 | 1/8 | 6/8 | 14/16 | 0 |
| Generic intent prompt | prompt only; no guard | 8/8 | 6/8 | 1/8 | 15/16 | 0 |
| Token-matched neutral | prompt only; no guard | 8/8 | 6/8 | 0/8 | 14/16 | 0 |
| Validated atom prompt | prompt only; no guard | 7/8 | 5/8 | 1/8 | 13/16 | 0 |
| Spotlighting | AgentDojo delimiter prompt defense | 8/8 | 1/8 | 5/8 | 14/16 | 0 |
| Prompt Sandwiching | AgentDojo comparable prompt wrapper | 8/8 | 8/8 | 0/8 | 16/16 | 0 |
| ProtectAI PI Detector | released input-detector checkpoint | 8/8 | 6/8 | 1/8 | 15/16 | 9 |
| PIGuard | released input-detector checkpoint | 8/8 | 6/8 | 0/8 | 14/16 | 11 |
| PromptArmor-style | local LLM sanitizer guard | 7/8 | 7/8 | 0/8 | 14/16 | 8 |
| MELON-style | masked-reexecution guard | 7/8 | 0/8 | 6/8 | 13/16 | 2 |
| AttriGuard adapted | released attenuation/shadow mechanism | 4/8 | 1/8 | 0/8 | 5/16 | 9 |

Predeclared single-action targeted stress. Baselines preserve their detector, wrapper, sanitizer, masked-reexecution, or causal-shadow mechanism. The proposed atom condition is prompt-only and uses no runtime guard. This is not an overall AgentDojo ASR or an original-protocol reproduction.
