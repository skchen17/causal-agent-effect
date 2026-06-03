# T118 AgentDojo Strong+Max Baseline Matrix

## Scope

- Strong+Max attacks: `important_instructions`, `tool_knowledge`, `injecagent`, `ignore_previous`, `direct`.
- Paper defenses: `none`, `repeat_user_prompt`, `spotlighting_with_delimiting`, `transformers_pi_detector`, `tool_filter_deepseek`.
- DoS attacks are excluded because they instantiate a different threat model.
- API keys are read only from the configured environment variable and are not serialized.
- Skipped defenses: `none`.

## Completed Settings

| suite | attack | defense | n | UR | A.UR | ASR | inj util | ASR 95% CI |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |

## Max-ASR

| defense | suite | attacks present | n cases | Max-ASR | 95% CI |
| --- | --- | ---: | ---: | ---: | --- |

No model-calling shards were run in this invocation.

## Interpretation Boundary

- `ASR=0` must be read with its Wilson upper confidence bound, not as absolute safety.
- Max-ASR is the OR over available attacks for the same `(suite, user_task, injection_task)` case.
- Installed `v1.2.2` full949 is a broader local package setting, not a literal reproduction of the AgentDojo paper's 629-case table.
