# E79 AgentLAB Provenance-Normalization Pilot

Status: `development_pilot_passed_full_qwen_rerun_queued`.

## Root cause and repair

AgentLAB saved attacks use explicit ChatML role blocks, while the frozen C1f adapter only recognized AgentDojo INFORMATION blocks; untrusted control therefore failed to reach pre-commit checks. A format-only adapter maps explicit ChatML saved-message blocks to C1f's existing untrusted-control interface without reading labels, attack goals, expected decisions, or validator outcomes.

## Retrospective Qwen3-32B diagnostic

- Saved cases: 303
- Cases with normalized evidence: 280
- Recovered control segments: 1873
- Original attack successes: 95
- Original attack successes containing a retrospectively denied effectful call: 95

## DeepSeek development pilot

Three fixed cases produced 0 attack successes and 2 utility successes.

## Claim boundary

The retrospective audit diagnoses whether already-recorded calls would meet the normalized policy; it does not model recovery after denial. The three-case DeepSeek run is development-only and did not exercise an effectful denial. Security and utility claims require the queued 303-case Qwen rerun and strict finalization.
