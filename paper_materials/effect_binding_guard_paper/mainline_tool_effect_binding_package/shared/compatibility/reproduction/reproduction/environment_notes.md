# Environment Notes

- E51 itself does not require GPU, model inference, external APIs, or real tool execution.
- E48 local-Qwen prediction regeneration requires the local GGUF setup documented in the E48 experiment README.
- Do not merge partial local-Qwen shards unless the final file has exactly 822 unique case IDs.
- E47 official-checkpoint custom stress results are custom-stress evaluations, not original-paper benchmark reproduction.
- E55 uses deterministic mock pre-commit tools and explicit authorization contexts; it is not production or SaaS validation.
