# Atom-Targeted Multi-Method Pilot Analysis

## Protocol

The pilot freezes eight single-axis clean/injected pairs before inference. The
axes cover resource identity, target principal, operation and amount scope,
multi-target and multi-resource expansion, channel target, and provenance. The
victim is the same local Qwen3-32B checkpoint in all conditions. Labels are in
a separate scoring sidecar, and no tool is executed.

The proposed condition uses only a system-level intent instruction and the
counterfactually registered atom descriptor. It has no runtime guard. Other
methods retain their relevant mechanism: prompt wrapping, released input
detectors, LLM sanitization, masked re-execution, or causal shadow replay.

## Results

| Method | Clean utility | Injected utility | ASR | Coverage | Guard interventions |
|---|---:|---:|---:|---:|---:|
| No defense | 7/8 | 1/8 | 6/8 | 14/16 | 0 |
| Generic intent prompt | 8/8 | 6/8 | 1/8 | 15/16 | 0 |
| Token-matched neutral | 8/8 | 6/8 | 0/8 | 14/16 | 0 |
| Validated atom prompt | 7/8 | 5/8 | 1/8 | 13/16 | 0 |
| Spotlighting | 8/8 | 1/8 | 5/8 | 14/16 | 0 |
| Prompt Sandwiching | 8/8 | 8/8 | 0/8 | 16/16 | 0 |
| ProtectAI PI Detector | 8/8 | 6/8 | 1/8 | 15/16 | 9 |
| PIGuard | 8/8 | 6/8 | 0/8 | 14/16 | 11 |
| PromptArmor-style | 7/8 | 7/8 | 0/8 | 14/16 | 8 |
| MELON-style | 7/8 | 0/8 | 6/8 | 13/16 | 2 |
| AttriGuard adapted | 4/8 | 1/8 | 0/8 | 5/16 | 9 |

## Interpretation

The dataset has useful signal: no defense follows six of eight injected field
changes while retaining seven of eight clean actions. The result is therefore
not explained by a victim that rejects every suspicious-looking case.

This pilot does **not** establish an atom-specific benefit. The validated-atom
condition reduces ASR from 6/8 to 1/8, but generic intent guidance also reaches
1/8 and the token-matched neutral control reaches 0/8. The atom condition also
has lower injected utility than both controls. Its one successful attack is the
channel substitution `engineering -> general`. Two other injected failures are
`NO_ACTION`, so they are not utility-preserving defenses.

Prompt Sandwiching is strongest on this small set: 0/8 ASR and 8/8 utility in
both contexts. PIGuard and PromptArmor also reach 0/8 ASR, but intervene on
11/16 and 8/16 contexts. ProtectAI misses the amount-shift attack. Spotlighting
remains weak, and the MELON-style masked replay blocks only two injected calls
while the other six attack fields survive its tool-call similarity threshold.

The AttriGuard row is not suitable for primary ranking. It applies released
attenuation and shadow/judge prompts to a custom single-action view, and its
5/16 coverage shows that this adaptation is not utility comparable to its
native multi-step protocol.

## Decision

Do not expand this exact template as evidence for the atom contribution. It
mainly measures whether conspicuous `IMPORTANT INSTRUCTIONS` text is ignored,
a setting where generic reminders and input defenses are sufficient.

The next small validation should target the atom hypothesis directly: use an
otherwise authorized call with one nested, implicit, or aliased sub-effect
changed, without an explicit injection marker. Add a field-shuffled atom
control alongside the token-matched neutral control. Expansion is warranted
only if the correct atom mapping improves security or utility over both.

## Claim Boundary

This is a predeclared custom single-action stress pilot, not an AgentDojo-wide
ASR estimate. ProtectAI and PIGuard use released checkpoints on an adapted
input view. PromptArmor and MELON are the same comparable local adapters used
in the prior AgentDojo comparison. AttriGuard uses released prompts and its
mechanism on an adapted view and is not an original-protocol reproduction.
