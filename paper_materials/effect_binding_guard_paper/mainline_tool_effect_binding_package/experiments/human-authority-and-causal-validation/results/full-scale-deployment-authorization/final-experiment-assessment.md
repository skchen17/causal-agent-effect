# Final Experiment Assessment

规范数字来源为 `full-scale-authorization-report.json`，不是本文档中的自然语言摘要。

## 最终结果

- 注册期：8 个工具、144 条 context、72 个 counterfactual pair；descriptor/source exact-set match 为 `144/144`，relation accuracy 为 `72/72`。
- Held-out：8 个工具、192 条 context、96 个 policy-separating pair；理想标签为 96 ALLOW / 96 DENY。
- Direct policy consumer：typed effects 为 100% coverage、100% decision accuracy、0 UPA、0 false denial；common fields 为 44.8% coverage，已覆盖行准确率为 100%，其余 55.2% 因缺少 policy qualifier 而 abstain。
- Representation capacity：tool name、raw arguments、common fields 和 typed effects 分别产生 8、25、7、0 个 mixed cells；对应 minimum unavoidable row errors 为 96、26、18、0。
- Uniform mixed-cell completion：raw arguments 的 fail-open UPA 为 27.1%，fail-closed false denial 为 57.3%；common fields 分别为 18.8% 和 65.6%。
- State-dependent subset：26 个 pair 使用相同显式 arguments。raw arguments 碰撞 `26/26`，common fields 碰撞 `5/26`，typed effects 碰撞 `0/26`。

## 回答核心问题

1. **粗粒度表示是否丢失 policy-separating distinctions？** 是，在冻结策略族与 context 集上成立。三个 coarse views 都出现 mixed cells；同一个表示值对应相反的理想授权结果，因此任何统一确定性 completion 都必须产生 unsafe allow 或 withheld authorized work。
2. **validated typed effects 是否改善 end-to-end authorization correctness？** 是，在该受控范围内成立。typed effects 与 source execution 在 192 条 held-out context 上逐条一致，并由同一个 direct policy engine 正确判定全部 192 条；state-dependent pair 也全部被区分。

## 解释限制

- 该 benchmark 是作者构造的 deployment-style policy domain，不是生产日志的流行度估计。
- descriptor 与 source-diff oracle 是两份独立实现，但仍由同一研究团队编写；未进行独立人工审查。
- typed effect 的零错误只适用于冻结的工具、干预族、pre-state 和策略族。
- tool-name 和 raw-argument direct views 因无法提供完整 effect inventory 而 fail closed；它们的安全/效用两难主要通过统一 mixed-cell completion 诊断衡量。

## 复现命令

```bash
python shared/compatibility/scripts/run_full_scale_deployment_authorization.py --mode full
PYTHONPATH=. python -m pytest \
  shared/compatibility/tests/tests/test_full_scale_deployment_authorization.py -q
```
