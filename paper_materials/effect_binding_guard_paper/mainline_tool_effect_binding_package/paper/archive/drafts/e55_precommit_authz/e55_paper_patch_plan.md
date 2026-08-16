# E55 NDSS Integration Plan

Recommended integration: Use E55 as central review-response evidence that explicit authorization infrastructure improves the E50 bottleneck, while framing the system as a controlled prototype.

Patch plan:

- Add a short subsection after E50 resource/auth stress explaining the E55 local pre-commit setup.
- Report the main existing-hard-guard vs authorization-aware comparison, the ablation table, and the human-corrected sensitivity table.
- If using E55-v2 as paper-facing numbers, state that it is a corrected rerun of the same controlled local mock design: full guard UPA `0/276 = 0.000`, FDeny `0/252 = 0.000`, coverage `528/600 = 0.880`; E57-style perturbation/reference-authorizer checks on E55-v2 also passed with changed decisions `0` and decision/atom/resource-set agreement `1.0`.
- If retaining original E55 as the main table, add a note that E57 human audit found 6/60 decision corrections; minimal correction keeps UPA at zero but changes FDeny to `4/230 = 0.017`.
- Keep the core limitation that labels and the guard share deterministic mock authorization contracts.
- Do not claim production safety, complete permission-system coverage, perfect original-label correctness, or original-paper benchmark reproduction.
