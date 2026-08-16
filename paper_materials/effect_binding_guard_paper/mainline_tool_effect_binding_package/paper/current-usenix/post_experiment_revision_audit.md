# Post-Experiment Revision Audit

Date: 2026-08-16.

## Artifact Status

All required frozen experiments report `status=passed`. The fresh Qwen3-32B comparison contains the exact same 97 benign and 629 attack keys for no guard, Spotlighting, Prompt Sandwiching, PromptArmor-style, and the provenance monitor. Every row is evaluable, source hashes are frozen, and the monitor records zero execution without an allow decision and zero runtime LLM calls.

## Narrative Integration

- Authorization-interface falsification remains the primary contribution.
- Typed effects remain one candidate interface; the sufficient state-aware request is reported equally.
- Native-delta decisions and descriptor mutations provide mechanically separated positive checks.
- AgentDojo remains a pre-commit integration study.
- Prompt Sandwiching's stronger Qwen security--utility point is visible in the main Results paragraph and the complete appendix table.
- PromptArmor-style's zero observed attack success and large utility cost are both retained.
- All empirical and deployment reservations are consolidated in Limitations.

## Remaining Human Actions

Authors must perform the final prose/number/citation review, provide submission metadata and conflicts, run the anonymous package in a clean environment, and insert the stable anonymous artifact URL.
