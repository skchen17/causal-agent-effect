# Atom Utility-Preservation Evidence

## Fixed Successful Trajectories

Atom projection and reconstruction preserves 20/20 recorded effectful calls (1.000).

## Full AgentDojo Benign Comparison

| Condition | Utility | Total | Rate |
|---|---:|---:|---:|
| pristine | 168 | 194 | 0.866 |
| compact_neutral | 177 | 194 | 0.912 |
| compact_atoms | 173 | 194 | 0.892 |

## Primary Paired Test

Compact atoms minus pristine: 0.026; task-clustered bootstrap 95% interval [-0.010, 0.067]; one-sided lower bound -0.005; 5-point non-inferiority: `True`.

Compact atoms minus character-matched neutral: -0.021; task-clustered bootstrap 95% interval [-0.062, 0.021]; one-sided lower bound -0.057; 5-point non-inferiority: `False`. This secondary control precludes claiming an atom-specific utility improvement.

## Boundary

The fixed replay tests representation round-trip on a reviewed successful-call subset. The DeepSeek experiment tests whether compact atom descriptions reduce native benign AgentDojo utility with the runtime guard disabled. Neither result establishes attack resistance, authority-interface completeness, or zero loss for every model and task.
