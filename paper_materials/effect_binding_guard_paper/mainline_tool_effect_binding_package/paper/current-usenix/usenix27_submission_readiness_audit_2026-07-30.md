# USENIX Security '27 Submission Readiness Audit

Date: 2026-07-30

## Executive Decision

The manuscript is now internally complete as a bounded
representation-and-mediation paper. It compiles in the verified USENIX style,
the technical body occupies 13 pages, all admitted claims are traceable, and
the final capacity-matched, granularity-attribution, and fixed-transfer results
are integrated.

It is **not yet externally submission-ready** because the anonymous artifact
has not passed its release gates or received a stable anonymous URL. Scientific
acceptance risk also remains material: utility is low, executable authority
covers only 26/97 tasks, and the main runtime comparison uses one model.

## Venue Compliance

| Requirement | Status | Evidence / action |
|---|---|---|
| USENIX two-column letter format | Pass | `main.tex` uses the verified public `usenix.sty` |
| 13-page technical body | Pass | Conclusion ends on page 13; references start later on page 13 |
| References/appendices excluded from body | Pass | PDF totals 17 pages |
| Finished paper | Pass under bounded claims | No pending experiment is referenced as future main evidence |
| Open Science appendix | Partial | Appendix exists; anonymous URL is still missing |
| Anonymous artifact | Fail release gate | Evidence ledger passes; scrub, clean rerun, and URL remain |
| Citations and references | Pass | 34 cited keys, no missing or uncited entry |
| Cross-references/build | Pass | No undefined reference/citation, overfull box, or fatal build warning |
| Paper-source anonymity | Pass | No local path, username, credential, private label, or broken marker found |

## Scientific Claim Audit

| Claim | Evidence status | Judgment |
|---|---|---|
| Tool/call representations can merge authorization-inequivalent effects | Proved and instantiated by collision audits | Strong |
| A mixed joint effect--authority view forces unsafe allowance or withheld authorized work | Proved as a representation lower bound | Strong conditional result |
| Trusted evidence can refine authority ambiguity without granting new permission | Proved under projection-sound, authority-preserving refinement | Strong design obligation; implementation coverage remains partial |
| Counterfactual execution can falsify a candidate effect contract | E85 source-grounded interventions and controlled finite model | Strong bounded claim |
| Typed effect qualifiers remove observed collisions | 56-call finite domain plus pre-registered 32-context ToolSandbox check | Good finite evidence |
| Atom fields improve closed-loop behavior over whole-call mediation | 321-case hold-fixed applicability subset, 0/273 vs 3/273 ASR | Direct but narrow |
| Runtime reduces AgentDojo attack success | Capacity-matched Qwen3-32B, 54/627 vs 2/627 | Strong for this protocol |
| Runtime preserves useful task behavior | 33/97 benign and 207/627 attack-side utility | Weak; major tradeoff |
| Runtime transfers to long tasks | Fixed 303-case AgentLAB replay, 95/303 vs 0/303 ASR | Useful fixed-transfer evidence |
| Full independently bounded authority is available | 26/97 manifests compile | Not established broadly |
| Every executed guarded call is mediated in the sandboxes | 3,173/3,173 and 1,439/1,439 signature matches | Strong scoped audit |
| Production or open-domain safety | Explicitly excluded | Correct boundary |

## Evidence and Reproduction

- `reproduction/current_evidence.json` admits 360 fail-fast claim rows.
- `claim_to_source_map.md` maps every quantitative and formal claim to a result
  artifact and code/test entry.
- Final E78 reports all nine non-evaluable baseline trajectories and all-key
  bounds.
- Final E79 retains fixed-replay and utility-loss boundaries.
- `artifact/manifest.json` reports
  `paper_evidence_ready_artifact_release_pending`.

## Remaining Work

### Submission blockers

1. Assemble the curated anonymous artifact.
2. Reproduce tables in a clean environment.
3. Scan every packaged file for identity, credentials, host paths, and private
   metadata.
4. Freeze checksums and upload to an anonymous stable host.
5. Replace the Open Science URL placeholder.
6. Perform a final human author review of claims, references, ethics,
   acknowledgments, and anonymization.

### Highest-value scientific improvements

1. Improve authority/resolver coverage and rerun the fixed protocols to address
   the 33/97 and 87/303 utility results.
2. Add a second matched victim model.
3. Broaden the hold-fixed representation comparison and predeclare its
   applicability subset.
4. Add realistic coarser authority families and qualifier-deletion tests.
5. Optionally run adaptive AgentLAB generation; otherwise retain fixed-replay
   wording.

## Final Readiness Judgment

- **Theory:** sufficient and carefully bounded.
- **Problem evidence:** sufficient.
- **Representation validation:** strong but finite.
- **Runtime security:** strong under one matched protocol.
- **Runtime utility:** below a low-risk systems acceptance bar.
- **External validity:** improved by ToolSandbox and AgentLAB, but still
  single-model and fixed-replay.
- **Paper completeness:** complete under current claims.
- **Artifact readiness:** not ready for release.
- **Expected review posture:** borderline; approximately weak reject to weak
  accept depending on reviewer emphasis.

The paper can be submitted after artifact release work, but a low-risk USENIX
submission would benefit most from improved utility/authority coverage and one
second-model comparison. Adding more synthetic stress without addressing those
two points is unlikely to change the decision.
