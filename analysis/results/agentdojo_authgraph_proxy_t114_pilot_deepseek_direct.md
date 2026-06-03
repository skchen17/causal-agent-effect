# T114 AgentDojo AuthGraph-Style Proxy

## Scope

- Reads existing AgentDojo JSON logs; does not call a model.
- Clean no-injection trajectory is treated as the authorization graph.
- Attacked trajectory is treated as the execution/provenance graph.
- This is a proxy baseline, not the AuthGraph authors' implementation.

## Aggregate Results

| method | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate | prevented attack | denied successful nonattack |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tool_arg_alignment_proxy_v1 | 16 | 0.8750 | 0.1250 | 0.3125 | 0.0000 | 0.6875 | 2/16 | 9/16 |
| tool_sequence_proxy_v1 | 16 | 0.8750 | 0.1250 | 0.3750 | 0.0000 | 0.6250 | 2/16 | 8/16 |

## Per Suite

| method | pipeline | suite | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | banking | 4 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | slack | 4 | 1.0000 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | travel | 4 | 1.0000 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | workspace | 4 | 1.0000 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | banking | 4 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 1.0000 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | slack | 4 | 1.0000 | 0.0000 | 0.7500 | 0.0000 | 0.2500 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | travel | 4 | 1.0000 | 0.0000 | 0.2500 | 0.0000 | 0.7500 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | workspace | 4 | 1.0000 | 0.0000 | 0.5000 | 0.0000 | 0.5000 |

## Interpretation Boundary

- A lower proxy ASR is useful only if proxy A.UR does not collapse.
- Denying a mismatched attacked trajectory is not equivalent to safely replaying a clean trajectory.
- This proxy tests whether simple clean-plan alignment is already enough; it does not provide AuthGraph's full graph semantics.
