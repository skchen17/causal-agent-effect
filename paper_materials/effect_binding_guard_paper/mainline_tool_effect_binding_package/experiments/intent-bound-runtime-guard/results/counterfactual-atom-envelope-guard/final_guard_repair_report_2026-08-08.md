# Final DeepSeek Guard-Repair Evidence

## Result

- Selected candidate: `C1f strict atom envelope with structured provenance`.
- C1b benign non-inferiority: `True`; four-run mean difference `+0.0129`, one-sided clustered 95% lower bound `-0.0284` against margin `-0.05`.
- C1f benign sanity run: `75/97` with `0` direct denies and `0` abstains.
- Regression-inclusive official-key comparison: no guard `6/629`, C1f `0/629`.
- Post-repair confirmation excluding the known repair case: no guard `6/628`, C1f `0/628`.
- Scope-aligned confirmation, also excluding 20 output-only goals: no guard `6/608`, C1f `0/608`, exact one-sided McNemar `p=0.015625`.
- Runtime audit: `2783` checks, `90` denies, `0` abstains, `0` executions without ALLOW, and `0` runtime LLM calls.

## Same-Model Comparison

| Method | Benign utility | Attack success | Attack utility |
|---|---:|---:|---:|
| `c1f` | 0.773 | 0/629 | 453/629 |
| `no_guard` | 0.784 | 6/629 | 480/629 |
| `repeat_user_prompt` | 0.794 | 5/629 | 494/629 |
| `spotlighting` | 0.794 | 0/629 | 477/629 |

C1f and spotlighting tie on observed official attack success. Spotlighting has higher attack-task utility in this run. The C1f-specific evidence is its deterministic atom-level precommit mediation and complete audit trail, not a claim of numerical superiority over spotlighting.

The C1f/no-guard attack-utility difference is not a single block count: `86` tasks succeeded only without the guard and `59` succeeded only with C1f. This paired churn means the net difference cannot be attributed entirely to direct guard denials.

## Candidate Ladder

C1b passed the original joint gate. The less strict C1d variant increased attack-task utility but admitted two official attack goals and therefore failed the security gate. One failure exposed dropped provenance in a structured calendar output. C1f combines C1b's strict field treatment with structured-output provenance extraction. The known repair case is retained as regression evidence and excluded from post-repair confirmatory statistics.

## Claim Boundary

The evidence supports same-model AgentDojo sandbox security improvement. C1b passes four-run benign non-inferiority; C1f has a one-run benign sanity check and an explicit path-equivalence argument for its structured-provenance-only change. The evidence does not establish SOTA, adaptive-attack robustness, general trajectory safety, output-only protection, or production safety.
