# Runtime Policy-View Ablation

| View | Successful attacks intercepted | All attacks blocked | Benign blocked | Successful benign blocked |
|---|---:|---:|---:|---:|
| no_guard | 0/53 | 0/629 | 0/97 | 0 |
| whole_call_provenance | 52/53 | 334/629 | 0/97 | 0 |
| effect_only | 22/53 | 47/629 | 0/97 | 0 |
| registered_field_c1f | 49/53 | 94/629 | 0/97 | 0 |

Retrospective interceptability on fixed trajectories. This isolates deterministic policy views but is not a closed-loop ASR or utility estimate because blocking can change later model actions.
