# T120 AgentDojo Strong+Max / FC-Guard Summary

## Loaded Artifacts

- Baseline JSON loaded: `True`
- FC JSON loaded: `True`
- Baseline shards: `6`
- FC shards: `12`
- Baseline case records: `24`
- FC case records: `48`

## Paired Comparisons

| method | comparison | n | baseline A.UR | baseline ASR | FC A.UR | FC ASR | U-Commit | FDeny | Abstain | Coverage | Replay err | prevented | regressions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| allow_all | none | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| deny_all | none | 8 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| effect_resource_boundary | none | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| fc_prod_proxy_v1 | none | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| no_staging_posthoc_checker | none | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| tool_whitelist_only | none | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| allow_all | best_official | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| deny_all | best_official | 8 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| effect_resource_boundary | best_official | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| fc_prod_proxy_v1 | best_official | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| no_staging_posthoc_checker | best_official | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |
| tool_whitelist_only | best_official | 8 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |

## AuthGraph-Style Proxy Reference

| method | n | proxy A.UR | proxy ASR | deny rate | source |
| --- | ---: | ---: | ---: | ---: | --- |
| tool_arg_alignment_proxy_v1 | 949 | 0.2466 | 0.0000 | 0.7397 | analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_full949.json |
| tool_sequence_proxy_v1 | 949 | 0.3340 | 0.0000 | 0.6459 | analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_full949.json |

## Boundary

- `best_official` is selected from completed official-defense shards by lowest ASR for the same suite and attack.
- This summary does not fill missing attacks, defenses, or suites; absent cells remain absent.
