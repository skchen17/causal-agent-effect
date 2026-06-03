# T120 AgentDojo Strong+Max / FC-Guard Summary

## Loaded Artifacts

- Baseline JSON loaded: `True`
- FC JSON loaded: `True`
- Baseline shards: `1`
- FC shards: `1`
- Baseline case records: `1`
- FC case records: `1`

## Paired Comparisons

| method | comparison | n | baseline A.UR | baseline ASR | FC A.UR | FC ASR | U-Commit | FDeny | Abstain | Coverage | Replay err | prevented | regressions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fc_prod_proxy_v1 | none | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0 | 0 |

## Boundary

- `best_official` is selected from completed official-defense shards by lowest ASR for the same suite and attack.
- This summary does not fill missing attacks, defenses, or suites; absent cells remain absent.
