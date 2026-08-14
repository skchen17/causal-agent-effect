# Known Artifact Limitations

- The same-checkpoint five-method Qwen3-32B comparison was still running when
  this snapshot was prepared. Its protocol and code are included; partial model
  rows are not published as final evidence.
- Full AgentDojo and ToolSandbox source reruns require their public third-party
  packages. The repository includes frozen source-execution contexts and result
  artifacts so the representation and policy analyses can be rerun without model
  inference.
- Source replay can update timestamp-bearing output files. The release manifest
  binds the exact frozen files used by the manuscript; run source replay in a
  clean checkout when byte-for-byte artifact preservation matters.
- The AgentDojo runtime monitor instantiates provenance-origin confinement over
  registered fields and effect labels. It is not the same as the concrete typed
  ToolSandbox authorizer and does not implement general ACLs or delegation.
- The manuscript snapshot contains negative utility and mechanism-attribution
  results. They are intentionally retained.

