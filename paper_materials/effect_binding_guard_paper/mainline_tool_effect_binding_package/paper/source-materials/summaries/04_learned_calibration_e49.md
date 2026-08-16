# E49 Learned Calibration Diagnostic

E49 tests whether a lightweight learned calibrator over non-oracle tuple/view features improves the hard guard. It improves coverage but increases unsafe pre-allow relative to the hard guard under source-balanced evaluation.

- Learned mean UPA `0.0918918918918919`
- Hard guard same-split mean UPA `0.05135135135135136`
- Learned mean coverage `0.9881656804733728`
- Hard guard mean coverage `0.923076923076923`

Conclusion: E49 is diagnostic/negative evidence. It is not the main method and must not be promoted over the E48/E50 hard guard.
