# Causal-Chain Mechanism Analysis

- Model: `qwen3-8b`
- Data: `qwen3-8b_causal_chain_conditioning_v2`
- Samples: `2290`
- Wrong-chain types: `{'effect_omission': 153, 'authorization_flip': 153, 'effect_flip': 152}`

| Effect | Group | N | N+ | max Held-FNR | max Within-FNR | ToolProxyGap | ToolDisc(E=1) | CrossDist | EffAUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| content_fetched | effect_chain | 458 | 41 | 0.6562 | 0.0312 | 0.6250 | - | 18.4401 | 0.9264 |
| content_fetched | raw | 458 | 41 | 0.7812 | 0.1250 | 0.6875 | - | 21.5240 | 0.8791 |
| content_fetched | task_causal_chain | 458 | 41 | 1.0000 | 0.0000 | 0.0000 | - | 17.5891 | 1.0000 |
| content_fetched | tool_only | 458 | 41 | 1.0000 | 0.6250 | 0.5000 | - | 28.5193 | 0.5628 |
| content_fetched | wrong_chain | 458 | 41 | 0.7188 | 0.2500 | 0.7188 | - | 19.6033 | 0.9518 |
| content_fetched | wrong_chain:authorization_flip | 153 | 7 | 1.0000 | 0.1667 | 0.8333 | - | - | 0.9405 |
| content_fetched | wrong_chain:effect_flip | 152 | 21 | 0.8571 | 0.1667 | 0.0000 | - | 20.0289 | 0.9405 |
| content_fetched | wrong_chain:effect_omission | 153 | 13 | 0.7500 | 0.0000 | 0.7500 | - | - | 0.8646 |
| file_written | effect_chain | 458 | 51 | 1.0000 | 0.2353 | 0.8788 | - | 12.9186 | 0.7910 |
| file_written | raw | 458 | 51 | 1.0000 | 0.4118 | 0.9697 | - | 15.2308 | 0.7679 |
| file_written | task_causal_chain | 458 | 51 | 1.0000 | 0.0000 | 0.7059 | - | 21.6733 | 0.9817 |
| file_written | tool_only | 458 | 51 | 1.0000 | 0.6970 | 0.4706 | - | 23.7036 | 0.2998 |
| file_written | wrong_chain | 458 | 51 | 1.0000 | 0.2353 | 0.9091 | - | 13.4566 | 0.8084 |
| file_written | wrong_chain:authorization_flip | 153 | 19 | 1.0000 | 0.3333 | 1.0000 | - | 13.4285 | 0.6986 |
| file_written | wrong_chain:effect_flip | 152 | 17 | 1.0000 | 0.5000 | 0.0000 | 0.7667 | 17.0146 | 0.6845 |
| file_written | wrong_chain:effect_omission | 153 | 15 | 1.0000 | 0.2000 | 1.0000 | 1.0000 | 17.6818 | 0.7250 |
| network_egress | effect_chain | 458 | 120 | 0.3448 | 0.1379 | 0.2069 | 0.9583 | 15.2116 | 0.9912 |
| network_egress | raw | 458 | 120 | 0.7308 | 0.2069 | 0.5769 | 0.9250 | 19.6657 | 0.7721 |
| network_egress | task_causal_chain | 458 | 120 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 18.3039 | 1.0000 |
| network_egress | tool_only | 458 | 120 | 1.0000 | 0.7241 | 0.5588 | 1.0000 | 27.3252 | 0.3929 |
| network_egress | wrong_chain | 458 | 120 | 0.4231 | 0.1379 | 0.3462 | 0.9417 | 13.8807 | 0.9779 |
| network_egress | wrong_chain:authorization_flip | 153 | 32 | 0.3333 | 0.7143 | 0.1111 | - | 15.4477 | 0.9992 |
| network_egress | wrong_chain:effect_flip | 152 | 45 | 0.4444 | 0.3333 | 0.2500 | 0.8889 | 14.1678 | 0.9522 |
| network_egress | wrong_chain:effect_omission | 153 | 43 | 0.6250 | 0.2500 | 0.3750 | - | 25.1484 | 0.9500 |
| tool_error | effect_chain | 458 | 121 | 0.2308 | 0.5000 | 0.0000 | 0.9673 | 19.8747 | 0.9962 |
| tool_error | raw | 458 | 121 | 0.2692 | 0.5000 | 0.1250 | 0.9093 | 23.1735 | 0.9795 |
| tool_error | task_causal_chain | 458 | 121 | 0.0000 | 0.1818 | 0.0000 | 0.9919 | 20.6436 | 1.0000 |
| tool_error | tool_only | 458 | 121 | 1.0000 | 0.9231 | 0.4615 | 1.0000 | 25.3037 | 0.5197 |
| tool_error | wrong_chain | 458 | 121 | 0.2308 | 0.5000 | 0.0000 | 0.8677 | 17.2032 | 0.9941 |
| tool_error | wrong_chain:authorization_flip | 153 | 48 | 0.5000 | 0.6000 | 0.0000 | 0.5417 | 15.9220 | 0.9901 |
| tool_error | wrong_chain:effect_flip | 152 | 33 | 0.6667 | 1.0000 | 0.0000 | - | 18.5917 | 0.9912 |
| tool_error | wrong_chain:effect_omission | 153 | 40 | 0.0000 | 0.7500 | 0.0000 | - | 19.3098 | 0.9951 |