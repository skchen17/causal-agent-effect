# Binding Agent Tool Calls to Effects — Artifact

This package accompanies the paper *"Binding Agent Tool Calls to Effects:
Counterfactual Validation of Authorization Interfaces"*. It contains the full
LaTeX sources of the manuscript, the runtime implementation, the experiment
and evaluation scripts, the frozen evidence files admitted by the paper, and
the reproduction entry points.

## Package structure

```
.
├── paper/current-usenix/        # Manuscript (LaTeX sources + compiled PDF)
│   ├── main.tex                 # Main file (USENIX template)
│   ├── sections/                # Narrative sections
│   ├── tables/                  # Generated result tables
│   ├── figures/                 # Paper figures
│   ├── appendix/                # Ethics / Open Science appendices
│   └── reproduction/            # active claim/reference fail-fast checks
├── code/                        # Runtime implementation (effect contract kernel)
│   └── src/experiments/effect_binding_guard/
├── scripts/                     # Top-level experiment/evaluation scripts
├── evaluation/                  # Shared evaluation helpers (e.g. real_model_common.py)
├── experiments/                 # Per-family sources, tests, and evaluation code
│   ├── intent-bound-runtime-guard/
│   ├── binding-failure-and-granularity/
│   ├── counterfactual-descriptor-onboarding/
│   ├── adaptive-injection-benchmark/
│   ├── unified-agent-security-baselines/
│   ├── security-analysis-ablation-and-overhead/
│   ├── long-horizon-transfer/
│   └── ...                      # Remaining experiment families
├── data/                        # Registered relation catalogs and shared inputs
├── tests/                       # Unit / regression tests
├── manifests/                   # Package manifest
├── checksums.sha256             # SHA-256 over every packaged file
└── manifest.json                # File inventory (path, size, sha256, role)
```

## Building the manuscript

From `paper/current-usenix/`:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The main technical body remains within the submission page limit under the
bundled USENIX style file; references and appendices are excluded from that
limit.

## Reproduction

The claims admitted to the PDF are gated by `scripts/reproduce_usenix_main.py`.
It regenerates `paper/current-usenix/reproduction/main_claims.{json,csv,md}`
and fails if a required final result, JSON key, or displayed table value is
missing. Reference closure is checked by
`paper/current-usenix/reproduction/audit_references.py`.

## Environment

- Python 3.10+ (standard library only for the core runtime; experiment
  scripts additionally require the dependencies listed in each script's
  header).
- No credentials are required. Any API-style keys are read from the
  environment at runtime and never bundled.

### Model checkpoints

Experiments that exercise a real LLM expect a local GGUF checkpoint. All
scripts resolve the model root through the environment variable:

```bash
export EFFECT_BINDING_MODEL_ROOT=/path/to/your/models
```

Place the checkpoints used in the paper under that root with the names given
in the respective script constants (`Qwen3-32B-GGUF/Qwen3-32B-Q4_K_M.gguf`
and `Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf`; SHA-256 sums are enforced by
the scripts). The llama.cpp server interpreter is selected with
`EFFECT_BINDING_PYTHON` (defaults to the interpreter running the script).

## Artifact policy

- This archive contains no VCS history, no cache directories, no IDE
  configuration, no raw run logs, and no internal working documents.
- All paths are relative to the package root; absolute host paths are
  parameterized via the environment variables above.
- A full credential / identity / path scan is applied at packaging time and
  its report is included as `leak_scan_report.txt`.
- The anonymous review copy is made available through the stable anonymous
  URL listed in the submission system.
