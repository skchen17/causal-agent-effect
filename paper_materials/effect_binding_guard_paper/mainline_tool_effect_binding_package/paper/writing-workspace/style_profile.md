# Final USENIX Style Profile

## Controlling Voice

The paper uses concise systems-security prose: concrete mechanism, explicit trust boundary, direct result, and evidence-backed implication. It avoids marketing adjectives and repeated defensive qualifiers. The writing rhythm follows recent accepted agent-security papers: open with a concrete failure, name one central insight, pair each design element with the obstacle it addresses, and state empirical outcomes without burying them in caveats.

The stylistic reference set is AttriGuard (USENIX Security 2026), AgentDoS (USENIX Security 2026), and AgentFuzz (USENIX Security 2025). These papers inform structure and pacing only; all technical claims and evidence remain project-derived.

## Section Rules

| Section | Final rule |
|---|---|
| Abstract | Security boundary, impossibility, executable method, core evidence, and downstream consumption in one chain. |
| Introduction | Calendar failure first; authorization-observability principle second; agent-specific systems gap third; method and contributions last. |
| Related Work | Organize by the object each system observes: action cause, provenance/authority, effect specification, or interface validation. |
| Threat Model | State attacker power, trusted state, commit objective, and TCB as operational facts. |
| Method | Treat the descriptor as an untrusted hypothesis and explain each registration stage through its evidence object. |
| Security Analysis | Keep assumptions adjacent to the formal statement; avoid apology or novelty commentary. |
| Evaluation | Define the asymmetric evidence rule once, then describe frozen protocols. |
| Results | Begin each paragraph with the finding, follow with counts or rates, and end with the security implication. |
| Limitations | Collect semantic coverage, independence, state freshness, interface economy, and runtime-consumer boundaries here. |
| Conclusion | Return to authorization observability and executable failure certificates. |

## Terminology

Use consistently: `authorization interface`, `candidate descriptor`, `frozen descriptor`, `typed-effect interface`, `state-aware request`, `policy-separating collision`, `failure certificate`, `validation record`, and `pre-commit consumer`.

## Claim Style

- Use `falsifies` only for an executable policy-separating collision.
- Use `preserves the exercised distinctions` or `reproduces decisions` for positive evaluations.
- Use `demonstrates consumption` for the runtime case study.
- Present protocol scope in Evaluation and proof premises in Security Analysis; place empirical and deployment reservations in Limitations.
- Report percentages in prose and tables, with denominators at first use or in captions.
- Never claim SOTA, production safety, universal descriptor correctness, or independently authored semantics.
