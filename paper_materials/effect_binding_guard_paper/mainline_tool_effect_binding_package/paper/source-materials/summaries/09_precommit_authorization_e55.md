# E55 Pre-Commit Authorization Binding

E55 is a deterministic local-only pre-commit mediation experiment designed to test whether explicit authorization infrastructure reduces the E50 resource/authorization bottleneck. It builds 600 rows across email, calendar, file sharing, Slack-like workspace, and transaction-like API domains, using realistic mock tool schemas and no real external side effects.

Main comparison:

- Existing hard guard: UPA `0.037037037037037035`, FDeny `0.0`, coverage `0.2`.
- Authorization-aware guard: UPA `0.0`, FDeny `0.0`, coverage `0.92`.

Interpretation: E55 can be used as NDSS review-response evidence that explicit authorization contexts, atom expansion, alias resolution, operation mode, provenance overlay, and evidence fallback are useful infrastructure for resource/auth binding. It should not be presented as independent deployment validation because the guard and labels share deterministic mock schemas and authorization contracts.
