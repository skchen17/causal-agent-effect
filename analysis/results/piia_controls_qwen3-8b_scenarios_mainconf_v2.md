# pIIA Controls

- Data: `qwen3-8b_scenarios_mainconf_v2`
- Samples: 932
- Control level: direction controls + final-embedding matched-norm controls; hook random/layer/token controls not run here

## Direction And Embedding-Space Controls

| Effect | Random cos | Wrong effect | Wrong cos | Cross-tool dir cos | Random score inc | Wrong score inc |
|---|---:|---|---:|---:|---:|---:|
| `command_executed` | -0.005 | `content_fetched` | 0.0773 | -0.0119 | 0.83 | 0.92 |
| `content_fetched` | 0.0003 | `command_executed` | 0.0773 | 0.1408 | 0.72 | 0.54 |
| `file_content_read` | -0.0182 | `command_executed` | 0.1761 | 0.1691 | 0.74 | 0.44 |
| `file_deleted` | -0.0048 | `command_executed` | 0.1628 | 0.146 | 0.54 | 0.52 |
| `file_written` | 0.0159 | `command_executed` | 0.031 | 0.0804 | 0.55 | 0.71 |
| `memory_updated` | -0.004 | `command_executed` | 0.0031 | 0.2174 | 0.52 | 0.67 |
| `message_sent` | -0.0038 | `command_executed` | 0.0497 | 0.1084 | 0.74 | 0.65 |
| `network_egress` | 0.0029 | `command_executed` | 0.1325 | 0.0835 | 0.43 | 0.96 |
| `search_performed` | 0.0122 | `command_executed` | 0.0099 | 0.0404 | 0.32 | 0.91 |
| `subagent_spawned` | -0.0049 | `command_executed` | 0.0654 | 0.1357 | 0.56 | 0.77 |
| `tool_error` | -0.0094 | `command_executed` | 0.2017 | 0.3452 | 0.67 | 0.94 |

## Hook Raw pIIA Summary

- No hook-based raw pIIA outcomes found for this data name.

## Missing Controls

- hook-based matched-norm random intervention outcomes
- hook-based same-effect wrong-form intervention controls
- hook-based different-effect same-form negative controls
- layer sweep
- token aggregation ablation

## Caveats

- Embedding-space controls are not equivalent to hook-based pIIA through upper-layer propagation.
- Use this file to audit obvious direction/norm artifacts, not as final mechanism evidence.
- T43 remains partial until hook-based controls and layer/token ablations are run.