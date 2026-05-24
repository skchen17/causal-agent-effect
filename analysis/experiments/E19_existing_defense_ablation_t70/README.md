# E19 T70 Existing-Defense Proxy Ablation

## 目的

用 pre-action rule-only、provenance-only、raw-status boundary 等 proxy baselines 检查 EffectVerif-AuthMonitor 是否真的支配简单已有防御风格。

## 主要结论

T70 显示 label-hidden EffectVerif mean FNR 为 `0.1162`，raw-status boundary row FNR 为 `0.1113` 且 FDeny 很低。这说明不能声称 learned AuthMonitor 支配所有 handcrafted trace-policy defenses；现有 defense proxy 在某些 view 下具有竞争力。

## 关键产物

- `analysis/scripts/auth_existing_defense_ablation_t70.py`
- `analysis/results/auth_existing_defense_ablation_t70.json`
- `analysis/reports/auth_existing_defense_ablation_t70.md`

## 论文可支持的 claim

可以作为 claim boundary：本文不是证明新 monitor 优于所有已有 defenses，而是给出 evaluation target 和诊断。

## 不能支持的 claim

不能把 proxy baseline 当作 AgentArmor/ARGUS/ClawGuard/AttriGuard 的 faithful reimplementation；它们只是概念性对照。

