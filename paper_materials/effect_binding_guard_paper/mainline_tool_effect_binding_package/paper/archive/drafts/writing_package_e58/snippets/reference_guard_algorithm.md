# Reference Hard Guard Algorithm

1. Parse non-oracle tool/action views into candidate tuple fields.
2. Compute multi-view disagreement and unknown-field indicators.
3. Use non-oracle evidence fallback only when visible evidence is available.
4. Apply hard provenance overlay.
5. Return `ALLOW`, `DENY`, or `ABSTAIN`.
