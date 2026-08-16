# E66 Real Local-LLM Atom Extractor

Model: `Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf` via `http://127.0.0.1:18080/v1`.

Claim boundary: the model extracts atoms from label-hidden deployable inputs; the final decision is made by the existing reference authorizer. This is not a production safety guarantee.

| Dataset | Rows | Atom exact | Resource F1 | Control F1 | UPA | FDeny | Coverage | Parse-valid |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E60 | 480 | 0.000 | 0.637 | 0.968 | 0.344 | 0.033 | 1.000 | 1.000 |
| E61 artifact-generated | 300 | 0.000 | 0.852 | 1.000 | 0.189 | 0.000 | 1.000 | 1.000 |
| E61 external subset | 156 | 0.000 | 0.758 | 0.853 | 0.067 | 0.182 | 0.974 | 1.000 |
