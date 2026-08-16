# E79 ToolSandbox Offline Environment Smoke

Status: `passed`.

A public ToolSandbox state transition and native milestone validator were executed locally. No LLM, user simulator, search tool, external API, prompt-injection attack, or proposed guard was executed.

## Observed Checks

- Loaded 129 base scenarios and 1032 total variants.
- Base scenario milestone counts range from 0 to 6; 98 have multiple milestones.
- `wifi_off` changed the sandbox state from `True` to `False` and received milestone similarity `1.0`.
- The state-dependency check was blocked: `True` (`Wifi cannot be turned on in low battery mode`).

## Compatibility Note

The smoke used Python 3.12.2 with `ccy==1.4.1` because the repository's pinned `ccy==1.3.1` does not publish a Python 3.12-compatible distribution. A final benchmark environment should use Python 3.11 with the exact pin or establish behavioral equivalence for the replacement.

## Next Gate

Select a fixed offline multi-tool subset, add label-hidden untrusted observations and prefix effect validators, then run the same victim checkpoint with no guard and the effect-binding guard.
