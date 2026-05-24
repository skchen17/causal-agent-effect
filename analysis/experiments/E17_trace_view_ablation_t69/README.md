# E17 T69 Trace View Ablation

## 目的

检验 full-label trace verifier 是否依赖结构化标签字段，并评估 label-hidden / minimal-evidence raw trace view 下性能退化。

## 主要结论

T69 显示 full-label mean FNR `0.0353`，label-hidden mean FNR `0.1162`，minimal-evidence mean FNR `0.1465`。这支持 Layer 2 trace-label over-optimism：含 verified/effect/unauthorized 等结构化字段的 trace view 会高估 verifier 能力。

## 关键产物

- `analysis/scripts/auth_trace_view_ablation_t69.py`
- `analysis/results/auth_trace_view_ablation_t69.json`
- `analysis/reports/auth_trace_view_ablation_t69.md`

## 论文可支持的 claim

可以把 label-hidden/minimal-evidence 结果作为主实验，full-label 结果作为 upper bound。

## 不能支持的 claim

不能说 label-hidden 已等价于 arbitrary sparse logs；它仍有固定 schema 和 controlled generator。

