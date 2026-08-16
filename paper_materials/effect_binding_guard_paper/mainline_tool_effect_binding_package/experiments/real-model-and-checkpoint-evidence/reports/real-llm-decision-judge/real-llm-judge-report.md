# E65 Real Local-LLM Judge Baseline

Model: `Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf` via `http://127.0.0.1:18080/v1`.

Claim boundary: the run is a comparable real-LLM judge on this paper's label-hidden deployable input view. It does not execute tools and is not an original external benchmark reproduction.

| Dataset | Rows | UPA | FDeny | Coverage | Abstain | Accuracy | Parse-valid |
|---|---:|---:|---:|---:|---:|---:|---:|
| E55-v2 | 600 | 0.261 | 0.056 | 0.995 | 0.005 | 0.732 | 0.995 |
| E60 | 480 | 0.039 | 0.087 | 0.998 | 0.002 | 0.815 | 0.998 |
| E61 artifact-generated | 300 | 0.000 | 0.513 | 0.997 | 0.003 | 0.673 | 0.997 |
| E61 external subset | 156 | 0.000 | 0.909 | 0.987 | 0.013 | 0.859 | 0.987 |
