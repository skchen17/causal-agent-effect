# T114 AgentDojo AuthGraph-Style Proxy

## Scope

- Reads existing AgentDojo JSON logs; does not call a model.
- Clean no-injection trajectory is treated as the authorization graph.
- Attacked trajectory is treated as the execution/provenance graph.
- This is a proxy baseline, not the AuthGraph authors' implementation.

## Aggregate Results

| method | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate | prevented attack | denied successful nonattack |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tool_arg_alignment_proxy_v1 | 60 | 0.7167 | 0.1333 | 0.1333 | 0.0000 | 0.8667 | 8/60 | 31/60 |
| tool_sequence_proxy_v1 | 60 | 0.7167 | 0.1333 | 0.2000 | 0.0000 | 0.8000 | 8/60 | 27/60 |

## Per Suite

| method | pipeline | suite | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tool_arg_alignment_proxy_v1 | local-none | banking | 15 | 0.8000 | 0.2000 | 0.0000 | 0.0000 | 1.0000 |
| tool_arg_alignment_proxy_v1 | local-none | slack | 15 | 0.6000 | 0.2667 | 0.0667 | 0.0000 | 0.9333 |
| tool_arg_alignment_proxy_v1 | local-none | travel | 15 | 0.7333 | 0.0000 | 0.0667 | 0.0000 | 0.9333 |
| tool_arg_alignment_proxy_v1 | local-none | workspace | 15 | 0.7333 | 0.0667 | 0.4000 | 0.0000 | 0.6000 |
| tool_sequence_proxy_v1 | local-none | banking | 15 | 0.8000 | 0.2000 | 0.0667 | 0.0000 | 0.9333 |
| tool_sequence_proxy_v1 | local-none | slack | 15 | 0.6000 | 0.2667 | 0.0667 | 0.0000 | 0.9333 |
| tool_sequence_proxy_v1 | local-none | travel | 15 | 0.7333 | 0.0000 | 0.2667 | 0.0000 | 0.7333 |
| tool_sequence_proxy_v1 | local-none | workspace | 15 | 0.7333 | 0.0667 | 0.4000 | 0.0000 | 0.6000 |

## Interpretation Boundary

- A lower proxy ASR is useful only if proxy A.UR does not collapse.
- Denying a mismatched attacked trajectory is not equivalent to safely replaying a clean trajectory.
- This proxy tests whether simple clean-plan alignment is already enough; it does not provide AuthGraph's full graph semantics.
