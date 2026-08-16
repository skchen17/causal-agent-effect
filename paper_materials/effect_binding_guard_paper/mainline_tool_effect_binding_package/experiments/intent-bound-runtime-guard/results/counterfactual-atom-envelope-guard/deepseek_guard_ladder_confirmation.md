# DeepSeek Counterfactual Atom-Envelope Guard Ladder

- Benign no guard: `[75, 77, 76, 76]`.
- Benign frozen envelope: `[75, 76, 80, 78]`.
- Benign one-sided lower 95% bound: `-0.0284`.
- C1b attack success: `0/629` versus no guard `6/629`.
- C1d attack success: `2/629` versus no guard `6/629`.
- C1b attack utility: `448/629`.
- C1d attack utility: `464/629`.
- C1d ALLOW/DENY/ABSTAIN: `2700/49/1`.
- C1d joint gate passed: `False`.

The C1d mechanism was frozen before its DeepSeek live run. The result remains a
sandbox benchmark result and is not labeled SOTA without same-protocol external
baseline confirmation.
