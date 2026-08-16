# Closed-Loop Monitor Representation Attribution

## Design

The run contains 321 frozen AgentDojo v1.1.2 cases. The atom-field and tool-call variants use identical initial plan material, model, tasks, attacks, descriptors, totalization, recovery implementation, and tool environment.

## Results

| Variant | Benign n | Benign utility | Attack n | Attack utility | ASR |
|---|---:|---:|---:|---:|---:|
| Atom-field monitor | 48 | 18.8% | 273 | 20.9% | 0.0% |
| Tool-call-level monitor | 48 | 18.8% | 273 | 17.9% | 1.1% |

## Claim boundary

Closed-loop effect of monitor granularity on a targeted applicability subset. Selection is conditioned on the atom-field monitor having emitted field-level feedback, so aggregate rates are not full-benchmark estimates.
