# Table 1: Existing Methods And Measurement Setup

Use E47/E48 artifacts to separate official-checkpoint custom stress, component stress, proxy diagnostics, non-oracle evidence, oracle/upper-bound, and adapter failures. Do not collapse these scopes into a single leaderboard.

| Scope | Use in paper | Claim boundary |
| --- | --- | --- |
| official-checkpoint custom stress | Comparable method rows when original checkpoint was actually run on custom cases | Not original-paper benchmark reproduction |
| component stress | IPIGuard/CaMeL structural evidence | Component behavior, not full deployed defense |
| proxy diagnostic | Mechanism illustration | No claim about original method failure |
| oracle / upper bound | Feasibility ceiling | Never deployable result |
