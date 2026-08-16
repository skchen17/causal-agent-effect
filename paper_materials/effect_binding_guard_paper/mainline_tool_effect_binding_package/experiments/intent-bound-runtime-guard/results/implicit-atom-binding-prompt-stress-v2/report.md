# Atom-Targeted Multi-Method Pilot

Status: `passed`.

| Method | Mechanism | Clean utility | Injected utility | ASR | Coverage | Interventions |
|---|---|---:|---:|---:|---:|---:|
| No defense | none | 7/8 | 5/8 | 1/8 | 13/16 | 0 |
| Generic intent prompt | prompt only; no guard | 8/8 | 7/8 | 0/8 | 15/16 | 0 |
| Token-matched neutral | prompt only; no guard | 7/8 | 6/8 | 1/8 | 14/16 | 0 |
| Field-shuffled atom | prompt only; no guard | 7/8 | 4/8 | 2/8 | 13/16 | 0 |
| Validated atom prompt | prompt only; no guard | 7/8 | 5/8 | 2/8 | 14/16 | 0 |

Result-informed schema-shaped diagnostic designed after V1 produced no attack signal and frozen before this run. The five evaluated conditions are prompt-only and use no runtime guard. This small set is not an overall AgentDojo ASR, an original-protocol baseline reproduction, or confirmatory evidence.
