# E47 Phase 5 CaMeL

## Original Pipeline Local-Model Evaluation

- Rows: `3138`
- `original_camel_generator_interpreter_no_policy`: runtime errors `0.0019 [0.0005, 0.0069]`, policy denials `0.0000 [0.0000, 0.0037]`, benign utility `0.2371 [0.1635, 0.3307]`, attack utility `0.2914 [0.2634, 0.3212]`, attack success `0.0011 [0.0002, 0.0060]`.
- `original_camel_generator_interpreter_inline_policy_normal`: runtime errors `0.0000 [0.0000, 0.0037]`, policy denials `0.0822 [0.0671, 0.1004]`, benign utility `0.2268 [0.1548, 0.3196]`, attack utility `0.2276 [0.2021, 0.2554]`, attack success `0.0011 [0.0002, 0.0059]`.
- `original_camel_generator_interpreter_inline_policy_strict`: runtime errors `0.0048 [0.0020, 0.0111]`, policy denials `0.0612 [0.0482, 0.0774]`, benign utility `0.2211 [0.1494, 0.3144]`, attack utility `0.2505 [0.2240, 0.2791]`, attack success `0.0011 [0.0002, 0.0060]`.

## Original Component Custom Stress

```json
{
  "n_rows": 54,
  "overall_accuracy": {
    "successes": 48,
    "total": 54,
    "rate": 0.8888888888888888,
    "ci_low": 0.7780505106792327,
    "ci_high": 0.9480704818244324
  },
  "unsafe_execution_blocked": {
    "successes": 18,
    "total": 24,
    "rate": 0.75,
    "ci_low": 0.5510017468789357,
    "ci_high": 0.8800079652065766
  },
  "safe_false_denial": {
    "successes": 0,
    "total": 30,
    "rate": 0.0,
    "ci_low": 0.0,
    "ci_high": 0.113517091390478
  },
  "default_deny_rate": {
    "successes": 6,
    "total": 6,
    "rate": 1.0,
    "ci_low": 0.6096569663469354,
    "ci_high": 0.9999999999999999
  },
  "structural_invariance": {
    "rate": 1.0,
    "ci_low": 1.0,
    "ci_high": 1.0,
    "n_groups": 6
  },
  "by_variant": {
    "trusted_source": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    },
    "untrusted_source": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    },
    "same_flow_tool_rename_policy_synced": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    },
    "same_flow_tool_rename_policy_missing": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    },
    "data_dependency_private": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    },
    "control_dependency_private": {
      "n": 6,
      "accuracy": {
        "successes": 0,
        "total": 6,
        "rate": 0.0,
        "ci_low": 0.0,
        "ci_high": 0.3903430336530645
      }
    },
    "capability_reader_narrowed": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    },
    "no_side_effect_tool": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    },
    "synonymous_control_flow": {
      "n": 6,
      "accuracy": {
        "successes": 6,
        "total": 6,
        "rate": 1.0,
        "ci_low": 0.6096569663469354,
        "ci_high": 0.9999999999999999
      }
    }
  },
  "claim_boundary": [
    "This runs CaMeL's original generic SecurityPolicyEngine component, not the full generated-code AgentDojo pipeline.",
    "Tool rename without synchronized policy is reported as policy coverage failure.",
    "Source-only changes do not necessarily imply denial; readers and dependencies determine the generic policy result."
  ]
}
```

## Claim Boundary
- Local GGUF pipeline results are original-pipeline/local-model evidence, not original-paper numeric reproduction.
- IPIGuard custom stress uses the released DAG construction prompt/parser, not the full construct-traverse-execute pipeline.
- IPIGuard DAG outputs do not expose realized-effect labels, so planned-effect coverage is not identifiable without an external effect mapper.
- CaMeL component stress uses the original generic policy engine but not the full generated-code pipeline.
- AgentDojo tools execute only inside simulated environments; real_side_effects is always false.
- Pipeline/model compatibility failures are reproduction failures, not evidence that the safety method fails.
