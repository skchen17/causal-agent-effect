# Tool-Effect Binding Research Workspace

Current handoff and status:

- PROJECT_HANDOFF_2026-08-14.md: project goal, evidence, active runs, paper map, risks, and takeover order.
- `PROJECT_FILE_CONTENT_MAP.csv`: locally generated, searchable per-file inventory of the physical workspace. It is omitted from Git because it indexes runtime and cache files that are not part of the reproducible source package.

The workspace is physically organized into three canonical roots:

- `paper/`: current manuscript, archived drafts, figures, tables, and writing materials.
- `experiments/`: experiment families named by research content. Every family has a Chinese README and physically contains its source, evaluation data, results, scripts, tests, or runs.
- `shared/`: common data, compatibility aliases, reusable infrastructure, and workspace-management manifests.

Some legacy root paths are temporary symlinks because a full AgentDojo run was active during migration. They preserve old imports and artifact paths but are not canonical storage locations. Remove them only after the active run finishes and path-rewrite tests pass.
