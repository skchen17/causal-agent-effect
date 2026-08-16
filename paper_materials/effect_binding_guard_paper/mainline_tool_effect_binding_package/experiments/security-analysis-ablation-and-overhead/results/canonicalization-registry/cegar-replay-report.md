# CEGAR Replay Report (effect-preserving canonicalization)

- generated_utc: 2026-08-07T16:33:42.855859+00:00
- platform: Linux-6.2.0-26-generic-x86_64-with-glibc2.35
- python: 3.10.12

## 1. Finite-domain calibration gate

- calibrated tools: 4/5

## 2. Gate trace

### F-M3-01

- label: double-period prompt artifact (workspace/20 class)
- gate1: proceed (false_negative)
- gate2: accept_candidate candidate=CEGAR-R01
- gate3: verdict=ACCEPT (calibrated=True, evidence=modeled)
- action: registered; covered=True; fail_closed=False
- matches expected: True

### F-M3b-01

- label: sentence-final number grounding (banking/15 class)
- gate1: proceed (false_negative)
- gate2: accept_candidate candidate=CEGAR-R02
- gate3: verdict=ACCEPT (calibrated=True, evidence=modeled)
- action: registered; covered=True; fail_closed=False
- matches expected: True

### F-REJ-01

- label: spurious permission-merge candidate
- gate1: proceed (false_negative)
- gate2: accept_candidate candidate=CEGAR-R03
- gate3: verdict=REJECT (calibrated=True, evidence=observed)
- action: refused; covered=False; fail_closed=True
- matches expected: True

## 3. Convergence record

- n_failures: 3
- n_covered (rules cover): 2
- n_registered_rules: 2
- registered_rule_ids: ['CEGAR-R01', 'CEGAR-R02']
- n_refused (fail-closed): 1
- registry_n_rules: 2
- all_failures_disposed: True
- all_failures_covered: False
- expected matches: 3/3
