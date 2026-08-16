# Artifact Reproducibility Plan

## Existing Artifact Checks

```bash
python scripts/build_effect_binding_guard_paper_materials.py --validate-only
python scripts/build_effect_binding_writing_package_e58.py --validate-only
```

## Experiment Reproduction Commands

Use the canonical scripts documented in `paper_materials/effect_binding_guard_paper/reproduction/` and the E48-E57 experiment READMEs. Treat any command not already validated in the repo as "needs verification".

## E58 Validation

```bash
python -m py_compile scripts/build_effect_binding_writing_package_e58.py
python scripts/build_effect_binding_writing_package_e58.py
python scripts/build_effect_binding_writing_package_e58.py --validate-only
```

No E58 step calls APIs, models, or real tools.
