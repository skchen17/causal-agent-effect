"""Effect-preserving canonicalization framework (module package).

Modules:
  paths.py      shared path resolution
  transforms.py pure O(len) transform functions
  registry.py   rule schema, frozen hashing, freeze/load
  domain_oracle.py  finite-domain effect oracle + calibration gate
  validation.py counterfactual validation pipeline
  runtime.py    runtime canonicalization entry (symmetry by construction)
  cegar.py      failure-driven rule discovery loop (replayable)

Runners (from this directory):
  python3 run_control_validation.py   # 10-rule pre-registered control set
  python3 run_cegar_replay.py         # M3/M3b failure replay
Tests:
  python3 -m pytest tests/ -q
"""
