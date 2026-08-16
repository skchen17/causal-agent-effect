# Fixed-trajectory atom utility preservation

- Status: `passed`
- Reviewed overlap: `34` tasks
- Primary denominator: `17` authorized effectful calls

| Condition | Preserved | Total | Rate |
|---|---:|---:|---:|
| no_guard_recorded_execution | 17 | 17 | 1.000 |
| atom_projection_roundtrip | 20 | 20 | 1.000 |
| strict_atom_interface | 1 | 17 | 0.059 |
| validated_equivalence | 1 | 17 | 0.059 |

## Interpretation

This fixed replay removes model sampling and planning variation. A blocked primary row is therefore a representation or authority-interface incompatibility, not a failure to generate the original successful call.

Unsafe authority expansions: `0`.
Acceptance threshold met: `False`.

## Claim boundary

Fixed replay of officially successful benign trajectories over the reviewed-manifest overlap. This isolates representation compatibility but does not measure replanning or full benchmark utility.
