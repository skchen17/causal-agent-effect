#!/usr/bin/env python3
"""Physically reorganize this workspace by paper role and experiment content.

The migration is intentionally compatibility-preserving: physical artifacts move
to their canonical content folders, while old paths become symlinks.  Top-level
legacy containers are then placed under shared/compatibility and exposed through
temporary root aliases so active jobs and historical commands continue to work.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from build_content_named_workspace_view import (
    EXPERIMENTS,
    EXPERIMENT_FAMILIES,
    iter_matching,
)


def discover_root() -> Path:
    for candidate in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        if (candidate / "paper").is_dir() and (candidate / "experiments").is_dir() and (candidate / "shared").is_dir():
            return candidate
    return Path(__file__).resolve().parents[1]


ROOT = discover_root()
MANIFEST_NAME = "physical_workspace_migration.json"


FAMILY_SLUGS = {
    "工具效果绑定失效与粒度瓶颈": "binding-failure-and-granularity",
    "预提交授权原型与审计": "precommit-authorization-and-audit",
    "独立合约真实轨迹与机制分解": "independent-contracts-and-realistic-traces",
    "效果合约生成与反事实注册": "counterfactual-descriptor-onboarding",
    "真实模型与发布检查点补强": "real-model-and-checkpoint-evidence",
    "任务意图绑定与运行时守卫": "intent-bound-runtime-guard",
    "统一强基线与代理安全评测": "unified-agent-security-baselines",
    "长任务跨环境迁移评测": "long-horizon-transfer",
    "安全模型消融自适应攻击与开销": "security-analysis-ablation-and-overhead",
    "人工权限审查与因果验证": "human-authority-and-causal-validation",
    "增强代理注入攻击数据集": "adaptive-injection-benchmark",
}


COMPONENT_SLUGS = {
    "跨方法工具效果绑定压力测试": "cross-method-binding-stress",
    "效果-资源元组绑定守卫": "effect-resource-tuple-guard",
    "学习式绑定校准器": "learned-binding-calibrator",
    "硬守卫鲁棒性与粒度瓶颈": "hard-guard-granularity-stress",
    "本地预提交授权原型": "local-precommit-authorizer",
    "决策路径与严格回放审计": "decision-path-replay-audit",
    "参考授权器与人工抽查验证": "reference-authorizer-validation",
    "独立规格留出授权合约": "independently-specified-heldout-contract",
    "效果合约注册原型": "effect-contract-onboarding-prototype",
    "真实格式代理轨迹回放": "realistic-agent-trace-replay",
    "抽取与授权机制分解": "extraction-authorization-decomposition",
    "本地语言模型效果合约生成": "local-llm-contract-proposer",
    "授权接口负担与上下文退化": "interface-burden-and-context-degradation",
    "迭代反事实合约修正": "iterative-counterfactual-refinement",
    "统一粒度基线比较": "granularity-baseline-suite",
    "真实语言模型安全裁决基线": "real-llm-decision-judge",
    "真实语言模型原子抽取": "real-llm-atom-extractor",
    "发布检查点适配基线": "released-checkpoint-baselines",
    "语言模型字段反事实敏感性": "llm-field-counterfactual-sensitivity",
    "反事实筛选原子描述": "counterfactually-selected-atom-descriptors",
    "反事实引导原子描述运行时守卫": "counterfactual-descriptor-runtime-guard",
    "原子字段必要性运行时验证": "atom-field-necessity-runtime",
    "任务权限包络运行时": "task-permission-envelope-runtime",
    "意图绑定与动态重规划": "intent-binding-and-replanning",
    "无守卫代理回放基线": "no-guard-agent-replay",
    "统一代理安全基线评测": "unified-agent-security-comparison",
    "语言模型描述符代理运行时": "llm-descriptor-agent-runtime",
    "效果差异运行时守卫": "effect-difference-runtime-guard",
    "强模型横向基线比较": "strong-model-baseline-comparison",
    "长任务跨环境迁移评测": "long-horizon-cross-environment-transfer",
    "条件性效果合约安全模型": "conditional-effect-contract-security-model",
    "运行时机制消融": "runtime-mechanism-ablation",
    "自适应攻击评测": "adaptive-attack-evaluation",
    "运行时开销测量": "runtime-overhead-measurement",
    "权限清单人工审查": "authority-manifest-human-review",
    "因果效果投影验证": "causal-effect-projection-validation",
    "增强代理注入攻击数据集": "agent-injection-benchmark-construction",
}


PAPER_MOVES = {
    "usenix27_candidate": "paper/current-usenix",
    "usenix27_candidate_compact": "paper/compact-usenix",
    "usenix27_candidate_flat": "paper/flat-usenix",
    "ndss_candidate_restructured_v2": "paper/archive/ndss-restructured-latest",
    "ndss_candidate_restructured": "paper/archive/ndss-restructured-early",
    "paper_drafts": "paper/archive/drafts",
    "paper_rewriting_output": "paper/writing-workspace",
    "method_materials": "paper/source-materials",
    "paper_figures": "paper/assets/paper-figures",
    "figures": "paper/assets/shared-figures",
    "tables": "paper/assets/shared-tables",
}


PAPER_DOCS = {
    "build_status.md",
    "MAINLINE_CLAIM_BOUNDARY.md",
    "MISSING_FILES.md",
    "PACKAGE_SUMMARY.md",
    "warnings.md",
    "WRITING_NEXT_STEPS.md",
}


LEGACY_CONTAINERS = (
    "analysis",
    "audit",
    "baselines",
    "code",
    "data",
    "evaluation",
    "logs",
    "manifests",
    "paper_tables",
    "reports",
    "reproduction",
    "results",
    "runs",
    "scripts",
    "tests",
)


@dataclass
class Move:
    source: str
    destination: str
    kind: str
    owner: str


def slug_name(name: str) -> str:
    stem, suffix = os.path.splitext(name)
    stem = re.sub(r"^(?:e\d+|b\d+)[_-]*", "", stem, flags=re.IGNORECASE)
    stem = stem.replace("_", "-").lower()
    stem = re.sub(r"[^a-z0-9.-]+", "-", stem).strip("-") or "artifact"
    return stem + suffix.lower()


def unique_destination(destination: Path, reserved: set[Path]) -> Path:
    candidate = destination
    index = 2
    while candidate in reserved or candidate.exists() or candidate.is_symlink():
        candidate = destination.with_name(f"{destination.stem}-{index}{destination.suffix}")
        index += 1
    reserved.add(candidate)
    return candidate


def subdirectory_for(path: Path) -> str:
    relative = path.relative_to(ROOT)
    head = relative.parts[0]
    if head == "runs":
        return "runs"
    if head == "scripts":
        return "scripts"
    if head == "tests":
        return "tests"
    if head in {"paper_tables", "tables"}:
        return "paper-tables"
    if head == "reports":
        return "reports"
    if head == "reproduction":
        return "reproduction"
    if head in {"analysis", "results"}:
        return "results"
    if head == "evaluation":
        return "evaluation"
    if head == "baselines":
        return "baselines"
    if head == "code":
        return "source"
    return "artifacts"


def build_experiment_moves() -> list[Move]:
    experiments = {experiment.folder: experiment for experiment in EXPERIMENTS}
    moves: list[Move] = []
    reserved: set[Path] = set()
    claimed: set[Path] = set()
    for family in EXPERIMENT_FAMILIES:
        family_slug = FAMILY_SLUGS[family.folder]
        for member_name in family.members:
            experiment = experiments[member_name]
            component_slug = COMPONENT_SLUGS[experiment.title]
            candidates: list[Path] = []
            for direct in experiment.direct_paths:
                source = ROOT / direct
                if source.exists() and not source.is_symlink():
                    candidates.append(source)
            candidates.extend(path for path in iter_matching(experiment) if not path.is_symlink())
            for source in candidates:
                identity = source.resolve()
                if identity in claimed:
                    continue
                claimed.add(identity)
                subdirectory = subdirectory_for(source)
                if source.is_dir() and subdirectory in {"source", "evaluation", "baselines"}:
                    destination = ROOT / "experiments" / family_slug / subdirectory / component_slug
                else:
                    destination = ROOT / "experiments" / family_slug / subdirectory / component_slug / slug_name(source.name)
                destination = unique_destination(destination, reserved)
                moves.append(Move(str(source.relative_to(ROOT)), str(destination.relative_to(ROOT)), "experiment", family_slug))
    return moves


def build_paper_moves(reserved: set[Path]) -> list[Move]:
    moves: list[Move] = []
    for old, new in PAPER_MOVES.items():
        source = ROOT / old
        if source.exists() and not source.is_symlink():
            destination = unique_destination(ROOT / new, reserved)
            moves.append(Move(old, str(destination.relative_to(ROOT)), "paper", "paper"))
    for name in PAPER_DOCS:
        source = ROOT / name
        if source.exists() and source.is_file():
            destination = unique_destination(ROOT / "paper" / "project-notes" / name, reserved)
            moves.append(Move(name, str(destination.relative_to(ROOT)), "paper-document", "paper"))
    return moves


def build_plan() -> list[Move]:
    experiment_moves = build_experiment_moves()
    reserved = {ROOT / move.destination for move in experiment_moves}
    return experiment_moves + build_paper_moves(reserved)


def relative_link(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=target.is_dir())


def execute_move(move: Move) -> None:
    source = ROOT / move.source
    destination = ROOT / move.destination
    if source.is_symlink():
        return
    if not source.exists():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    relative_link(destination, source)


def write_family_readmes() -> None:
    experiments = {experiment.folder: experiment for experiment in EXPERIMENTS}
    for family in EXPERIMENT_FAMILIES:
        folder = ROOT / "experiments" / FAMILY_SLUGS[family.folder]
        folder.mkdir(parents=True, exist_ok=True)
        components = "\n".join(
            f"- **{experiments[name].title}**：{experiments[name].purpose}"
            for name in family.members
        )
        (folder / "README.md").write_text(
            f"""# {family.folder}

## 目的

{family.purpose}

## 流程

{family.flow}

## 包含内容

{components}

## 结论边界

{family.claim_boundary}

目录名按实验内容命名。历史实验编号只保留在原始 artifact 内容和兼容路径中，不再作为目录名。
""",
            encoding="utf-8",
        )


def move_legacy_containers() -> list[Move]:
    moved: list[Move] = []
    compatibility = ROOT / "shared" / "compatibility"
    compatibility.mkdir(parents=True, exist_ok=True)
    for name in LEGACY_CONTAINERS:
        source = ROOT / name
        if not source.exists() or source.is_symlink():
            continue
        destination = compatibility / name
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        source.rename(destination)
        relative_link(destination, source)
        moved.append(Move(name, str(destination.relative_to(ROOT)), "compatibility-container", "shared"))
    return moved


def compatibility_location(old_path: str) -> Path:
    relative = Path(old_path)
    if relative.parts and relative.parts[0] in LEGACY_CONTAINERS:
        return ROOT / "shared" / "compatibility" / relative
    return ROOT / relative


def repair_moved_compatibility_links(moves: list[Move]) -> int:
    repaired = 0
    for move in moves:
        if move.kind in {"compatibility-container", "paper-document"}:
            continue
        link = compatibility_location(move.source)
        target = ROOT / move.destination
        if not target.exists():
            raise FileNotFoundError(target)
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            continue
        relative_link(target, link)
        repaired += 1
    return repaired


def move_root_readme() -> Move | None:
    source = ROOT / "README.md"
    if not source.exists() or source.is_symlink():
        return None
    destination = ROOT / "paper" / "project-notes" / "legacy-root-readme.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    source.rename(destination)
    return Move("README.md", str(destination.relative_to(ROOT)), "paper-document", "paper")


def remove_caches_and_old_view() -> list[str]:
    removed: list[str] = []
    for path in (ROOT / "整理后工作区", ROOT / ".pytest_cache", ROOT / ".ruff_cache"):
        if path.is_symlink() or path.is_file():
            path.unlink()
            removed.append(str(path.relative_to(ROOT)))
        elif path.exists():
            shutil.rmtree(path)
            removed.append(str(path.relative_to(ROOT)))
    for path in ROOT.rglob("__pycache__"):
        if "runs/e75_agentdojo_env" in str(path):
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
    return removed


def write_root_files(moves: list[Move], removed: list[str], active_compatibility: bool) -> None:
    manifest = {
        "status": "completed_with_temporary_compatibility_aliases" if active_compatibility else "completed",
        "physical_moves": [asdict(move) for move in moves],
        "removed_generated_or_cache_paths": removed,
        "canonical_roots": ["paper", "experiments", "shared"],
        "temporary_root_aliases": [name for name in LEGACY_CONTAINERS if (ROOT / name).is_symlink()],
    }
    manifest_path = ROOT / "shared" / "workspace-management" / MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "README.md").write_text(
        """# Tool-Effect Binding Research Workspace

The workspace is physically organized into three canonical roots:

- `paper/`: current manuscript, archived drafts, figures, tables, and writing materials.
- `experiments/`: experiment families named by research content. Every family has a Chinese README and physically contains its source, evaluation data, results, scripts, tests, or runs.
- `shared/`: common data, compatibility aliases, reusable infrastructure, and workspace-management manifests.

Some legacy root paths are temporary symlinks because a full AgentDojo run was active during migration. They preserve old imports and artifact paths but are not canonical storage locations. Remove them only after the active run finishes and path-rewrite tests pass.
""",
        encoding="utf-8",
    )


def validate_plan(moves: list[Move]) -> dict[str, object]:
    sources = [move.source for move in moves]
    destinations = [move.destination for move in moves]
    missing = [source for source in sources if not (ROOT / source).exists()]
    duplicate_sources = sorted({source for source in sources if sources.count(source) > 1})
    duplicate_destinations = sorted({destination for destination in destinations if destinations.count(destination) > 1})
    nested_sources = []
    source_paths = [Path(source) for source in sources]
    for source in source_paths:
        for other in source_paths:
            if source != other and source in other.parents:
                nested_sources.append((str(source), str(other)))
    return {
        "moves": len(moves),
        "missing_sources": missing,
        "duplicate_sources": duplicate_sources,
        "duplicate_destinations": duplicate_destinations,
        "nested_sources": nested_sources,
        "valid": not (missing or duplicate_sources or duplicate_destinations or nested_sources),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    plan = build_plan()
    validation = validate_plan(plan)
    if not args.execute:
        print(json.dumps({"validation": validation, "sample": [asdict(move) for move in plan[:20]]}, ensure_ascii=False, indent=2))
        return
    if not validation["valid"]:
        raise SystemExit(json.dumps(validation, ensure_ascii=False, indent=2))
    removed = remove_caches_and_old_view()
    completed: list[Move] = []
    for move in plan:
        execute_move(move)
        completed.append(move)
    write_family_readmes()
    root_readme_move = move_root_readme()
    if root_readme_move:
        completed.append(root_readme_move)
    completed.extend(move_legacy_containers())
    repair_moved_compatibility_links(completed)
    write_root_files(completed, removed, active_compatibility=True)
    print(json.dumps({
        "status": "completed_with_temporary_compatibility_aliases",
        "moves": len(completed),
        "removed": removed,
        "root": str(ROOT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
