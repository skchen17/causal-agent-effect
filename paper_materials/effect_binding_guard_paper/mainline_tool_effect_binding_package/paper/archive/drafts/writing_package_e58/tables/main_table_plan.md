# Main Table Plan

| Table | Source | Key numbers | Purpose |
| --- | --- | --- | --- |
| Existing defenses / measurement | E47-E48 | Custom counterfactual and source-specific stress | Shows why surface robustness is insufficient; exact method rows should be pulled from E47/E48 canonical result files. |
| Reference hard guard | E48 | UPA 3.6%; FDeny 6.5%; coverage 91.7% | Improves measurement framing but leaves resource/auth gap. |
| Resource/auth bottleneck | E50 | UPA 61.7%; coverage 92.1% | Central negative result; do not hide. |
| Authorization-aware pre-commit | E55/E56 | UPA 0.0%; FDeny 0.0%; coverage 92.0% | Local mock contract evidence only. |
| Validity checks | E57 | Reference agreement 100.0%; changed-decision rate 0.0% | Reduces lexical and implementation-coupling concerns. |
