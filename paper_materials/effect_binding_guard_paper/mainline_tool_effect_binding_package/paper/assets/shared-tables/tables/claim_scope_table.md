# Claim Scope Table

| claim_scope | meaning | allowed_use |
|---|---|---|
| baseline | Rule or local-LLM baseline; not a target system result. | No deployable safety claim. |
| paper_grade_custom_stress | AgentDojo local custom stress anchor. | Paper-grade for local stress only. |
| official_method_custom_stress | Released checkpoint evaluated on E47 transformed inputs. | Not original-paper benchmark reproduction. |
| original_component_custom_stress | Released mechanism component evaluated on E47 custom core. | Component evidence only. |
| original_pipeline_local_model | Full pipeline using local non-paper model. | Feasibility only when no-defense utility/ASR is low. |
| diagnostic | Added mapper or evidence diagnostic. | Not original method or deployable guard. |
| upper_bound | Oracle/effect/evidence upper bound. | Not deployable. |
| audited_custom_stress | Human-audited corrected custom stress labels. | Valid for E47 counterfactual claims. |
