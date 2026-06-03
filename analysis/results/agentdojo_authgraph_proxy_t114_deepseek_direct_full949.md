# T114 AgentDojo AuthGraph-Style Proxy

## Scope

- Reads existing AgentDojo JSON logs; does not call a model.
- Clean no-injection trajectory is treated as the authorization graph.
- Attacked trajectory is treated as the execution/provenance graph.
- This is a proxy baseline, not the AuthGraph authors' implementation.

## Aggregate Results

| method | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate | prevented attack | denied successful nonattack |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tool_arg_alignment_proxy_v1 | 949 | 0.8746 | 0.0421 | 0.2466 | 0.0000 | 0.7397 | 40/949 | 564/949 |
| tool_sequence_proxy_v1 | 949 | 0.8746 | 0.0421 | 0.3340 | 0.0000 | 0.6459 | 40/949 | 481/949 |

## Per Suite

| method | pipeline | suite | n | baseline A.UR | baseline ASR | proxy A.UR | proxy ASR | deny rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | banking | 144 | 0.9236 | 0.1806 | 0.0556 | 0.0000 | 0.9444 |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | slack | 105 | 0.9238 | 0.1238 | 0.1238 | 0.0000 | 0.8762 |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | travel | 140 | 0.7714 | 0.0071 | 0.1214 | 0.0000 | 0.8571 |
| tool_arg_alignment_proxy_v1 | deepseek-v4-flash-none | workspace | 560 | 0.8786 | 0.0000 | 0.3500 | 0.0000 | 0.6321 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | banking | 144 | 0.9236 | 0.1806 | 0.0903 | 0.0000 | 0.9097 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | slack | 105 | 0.9238 | 0.1238 | 0.3524 | 0.0000 | 0.6381 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | travel | 140 | 0.7714 | 0.0071 | 0.2000 | 0.0000 | 0.7786 |
| tool_sequence_proxy_v1 | deepseek-v4-flash-none | workspace | 560 | 0.8786 | 0.0000 | 0.4268 | 0.0000 | 0.5464 |

## Interpretation Boundary

- A lower proxy ASR is useful only if proxy A.UR does not collapse.
- Denying a mismatched attacked trajectory is not equivalent to safely replaying a clean trajectory.
- This proxy tests whether simple clean-plan alignment is already enough; it does not provide AuthGraph's full graph semantics.
