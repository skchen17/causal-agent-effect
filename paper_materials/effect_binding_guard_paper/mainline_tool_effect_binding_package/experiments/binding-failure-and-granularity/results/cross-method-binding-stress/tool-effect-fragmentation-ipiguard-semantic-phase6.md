# E47 Phase 6 IPIGuard Effect/Resource Semantic Layer

- Semantic core: `240` cases / `24` groups.
- Parsed IPIGuard DAGs: `240`.
- Local-Qwen predictions: `240`.
- Local-Qwen parse-valid: `1.000`.
- Non-oracle forbidden-access count: `0`.

## Methods

- `deterministic_effect_resource_mapper`: effect `0.375`, authorization `0.375`, resource `0.375`, unsafe pre-allow `0.000`, safe false deny `0.060`, abstain `0.579`, effect extraction `0.954`, resource extraction `0.354`.
  Hidden-label rows: accuracy `0.319`, unsafe pre-allow `0.000`, safe false deny `0.056`, abstain `0.644`.
- `ipiguard_normalized_content`: effect `0.375`, authorization `0.375`, resource `0.375`, unsafe pre-allow `0.000`, safe false deny `0.060`, abstain `0.579`, effect extraction `0.954`, resource extraction `0.354`.
  Hidden-label rows: accuracy `0.319`, unsafe pre-allow `0.000`, safe false deny `0.056`, abstain `0.644`.
- `ipiguard_topology_only`: decision metrics `N/A` (Topology-only DAG has no authorization decision interface.)
- `local_qwen_effect_resource_mapper`: effect `0.833`, authorization `0.375`, resource `0.125`, unsafe pre-allow `0.333`, safe false deny `0.018`, abstain `0.062`, effect extraction `0.708`, resource extraction `0.779`.
  Hidden-label rows: accuracy `0.806`, unsafe pre-allow `0.333`, safe false deny `0.021`, abstain `0.069`.
- `oracle_effect_resource_mapper`: effect `1.000`, authorization `1.000`, resource `1.000`, unsafe pre-allow `0.000`, safe false deny `0.000`, abstain `0.000`, effect extraction `1.000`, resource extraction `1.000`.
  Hidden-label rows: accuracy `1.000`, unsafe pre-allow `0.000`, safe false deny `0.000`, abstain `0.000`.

## Claim Boundary
- The semantic mappers are added E47 evaluation layers and are not part of the original IPIGuard method.
- The deterministic mapper is a transparent hand-built diagnostic; the local-Qwen mapper is label-hidden but not human ground truth.
- The oracle mapper is an upper bound and must not be presented as deployable evidence.
