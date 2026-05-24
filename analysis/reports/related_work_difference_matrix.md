# Related Work Difference Matrix

> Date: 2026-05-21  
> Task: T66  
> Purpose: make the novelty boundary explicit before the next paper rewrite.

## Core Boundary

This paper should not compete with large agent benchmarks on breadth and should not be framed as a generic runtime defense. Its distinct object is:

> whether a monitor can detect realized effects that fall outside the task-authorized envelope, consistently across tool surface forms.

## Matrix

| Work type | Representative work | Primary judgment object | Primary signal | Difference from this paper |
|---|---|---|---|---|
| Prompt-injection benchmark | AgentDojo, ASB | whether an agent is attacked successfully while preserving utility | task success, security test cases, attack/defense outcomes | Auth-SafeInv measures unauthorized-effect FNR/FPR under tool-surface variation |
| Risk discovery | ToolEmu | whether a tool-use trajectory creates risk | LM-emulated tool outcomes and evaluator judgments | this paper studies monitor invariance for realized effect labels |
| Harmful-task benchmark | AgentHarm | whether the agent completes malicious tasks | harmful task completion across harm categories | this paper asks whether realized effects are authorized by the task |
| Causal attribution defense | AttriGuard, CausalArmor | why a privileged tool call occurs | counterfactual replay or ablation over context/untrusted spans | this paper asks what effect occurred and whether that effect is authorized |
| Boundary enforcement | ClawGuard | whether a call satisfies user-derived constraints before execution | pre-action policy / constraint checks | this paper uses execution or protocol evidence for realized effects |
| Provenance auditing | ARGUS | whether a decision is supported by trusted evidence | influence/provenance graph | this paper verifies effect occurrence and authorization, not only decision support |

## Paper-Writing Rule

Use this wording:

> We evaluate authorization-conditioned realized-effect consistency, not attack success, harmful-task completion, tool-call cause attribution, pre-action rule satisfaction, or provenance support.

Avoid this wording:

> We propose a new runtime defense for agent safety.

That wording invites direct comparison to ClawGuard, AttriGuard, CausalArmor, and ARGUS on their own terms.

## Sources Checked

- AgentDojo official/proceedings: https://agentdojo.spylab.ai/ and NeurIPS 2024 proceedings.
- ToolEmu OpenReview: https://openreview.net/forum?id=GEcwtMk1uA
- AgentHarm OpenReview: https://openreview.net/forum?id=AC5n7xHuR1
- ASB OpenReview: https://openreview.net/forum?id=V4y0CpX4hK
- AttriGuard arXiv: https://arxiv.org/abs/2603.10749
- CausalArmor arXiv: https://arxiv.org/abs/2602.07918
- ClawGuard arXiv: https://arxiv.org/abs/2604.11790
- ARGUS arXiv: https://arxiv.org/abs/2605.03378
