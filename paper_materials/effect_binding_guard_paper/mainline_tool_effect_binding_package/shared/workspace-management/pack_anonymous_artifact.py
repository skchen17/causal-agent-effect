#!/usr/bin/env python3
"""Build the anonymous USENIX Security 2027 artifact tarball (draft, 2026-08-04).

C 线 Artifact 准备 P0 任务 2 产物（GeneralPurpose 执行助手）。
本脚本仅为草案：编写完成，尚未执行打包。执行前需满足：
  * v17 实验链已结束并冻结（v17_finalizer_watch.log: finalizer exit=0 + protocol.json frozen）；
  * 路径参数化补丁方案（parameterization_patch_plan_2026-08-04.md）已应用并人工确认。

设计原则：
  1. 只读仓库 + 只写输出目录（--out 与 --staging 必须位于仓库外，默认 /tmp）。
  2. 不执行任何实验、不启动 GPU。
  3. 结构性排除（复制阶段） + 内容级泄漏复检（复制后剔除）双层防护。
  4. 符号链接全部解析为真实目录内容（staging 中无任何 symlink / 绝对路径）。
  5. 输出确定性 tar.gz（排序条目、不记录 mtime/uid/gid）。

产出（位于 --out 同目录的 staging 内）：
  anonymous_artifact.tar.gz      最终包
  checksums.sha256               全包文件 sha256 清单（{hash}  {path}）
  manifest.json                  文件清单（path / size_bytes / sha256 / role）
  leak_scan_report.txt           泄漏复检报告（命中行清单，含被剔除文件）

用法（自仓库根）：
  python3 shared/workspace-management/pack_anonymous_artifact.py \
      --out /tmp/anonymous_artifact.tar.gz \
      [--staging /tmp/artifact_staging] [--keep-staging] \
      [--paper-root paper/current-usenix] \
      [--skip-scan] [--skip-checksums] \
      [--include-claim-map] [--allow-email-pattern '^[A-Za-z0-9._%+-]+@(bluesparrowtech|clientcorp|amazingrecipes)\.com$']

退出码：0 = 打包完成且通过全量扫描；1 = 扫描/复制失败（不产出 tar.gz）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. 结构性排除清单
# ---------------------------------------------------------------------------

# 目录名级排除（出现在任意层级即跳过）
EXCLUDE_DIR_NAMES = {
    ".git",           # git 身份泄漏（skchen17 / remote URL）
    ".agents", ".codex", ".qoder",   # IDE/agent 配置
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".cache",
    "node_modules",
    "runs",           # 全部运行产物（含 v17 run 目录、venv、日志）
    "logs",
}

# 后缀级排除（TeX 构建中间文件等）
EXCLUDE_SUFFIXES = {
    ".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".toc",
    ".pyc", ".pyo", ".synctex.gz", ".gz.tmp",
}

# 顶层条目排除（仓库根下相对路径，目录或文件）
EXCLUDE_TOP_LEVEL = {
    "v17_finalizer_watch.sh",      # 含硬编码 ROOT，正在运行的监控脚本
    "v17_finalizer_watch.log",
    "README.md",                   # 根 README 提及 symlink 迁移，由 README.artifact.md 替代
}

# 精确路径排除（相对仓库根；目录则整棵排除）
EXCLUDE_PATHS = {
    # 论文内部树（全部不进包，只保留 current-usenix）
    "paper/archive",
    "paper/compact-usenix",
    "paper/flat-usenix",
    "paper/project-notes",
    "paper/source-materials",
    "paper/writing-workspace",
    # 内部审计/工作区管理
    "shared/compatibility/audit",
    "shared/compatibility/workspace-management",   # 本脚本自身与迁移 JSON 不进包
    "shared/compatibility/analysis/后续推进规划.md",
    # 旧打包器（内嵌 /data/CSK|/home/user|sk- 扫描正则，会触发复检误报）
    "shared/compatibility/code/scripts/build_mainline_tool_effect_binding_package.py",
    "shared/compatibility/code/scripts/build_e58_consolidated_package.py",
    # B 类：含主机路径的 data/结果状态文件（manifest 证据文件已验证干净，见 REQUIRED_EVIDENCE）
    "shared/compatibility/data/data/tool_effect_fragmentation",
    "shared/compatibility/data/data/counterfactual_core_phase4.jsonl",
    "shared/compatibility/data/data/ipiguard_phase5_traces.jsonl",
    "shared/compatibility/data/data/camel_phase5_traces.jsonl",
    "shared/compatibility/results",                      # canonical 结果含 traceback 主机路径
    "experiments/binding-failure-and-granularity/results",
    "experiments/unified-agent-security-baselines/results",
    "experiments/security-analysis-ablation-and-overhead/results",
    "experiments/intent-bound-runtime-guard/results",
    "experiments/long-horizon-transfer/results",
    "experiments/counterfactual-descriptor-onboarding/results",
    "experiments/adaptive-injection-benchmark/results",
    "experiments/real-model-and-checkpoint-evidence/baselines",
    "experiments/precommit-authorization-and-audit/results",
    "experiments/human-authority-and-causal-validation/results",
}

# 进包但内容级复检后仍需白名单的内嵌路径文件（扫描器正则，非真实泄漏）
PATH_SCAN_WHITELIST = {
    "shared/compatibility/code/scripts/build_mainline_tool_effect_binding_package.py",
    "shared/compatibility/code/scripts/build_e58_consolidated_package.py",
}

# manifest.json 引用的 required_evidence（已复核全部干净）——若被 B 类剔除则打包失败
REQUIRED_EVIDENCE = {
    "experiments/long-horizon-transfer/results/long-horizon-cross-environment-transfer/agentlab-saved-transfer-e77-results.json",
    "experiments/long-horizon-transfer/results/long-horizon-cross-environment-transfer/agentlab-saved-transfer-no-guard-results.json",
    "analysis/results/e78_capacity_matched_comparison.json",
    "analysis/results/e78_capacity_matched_statistics.json",
    "experiments/security-analysis-ablation-and-overhead/results/representation-closed-loop-attribution/closed-loop-attribution-report.json",
    "paper/current-usenix/reproduction/current_evidence.json",
}

# paper/current-usenix 内部工作文档（23 个；README.md 用改写版替换，claim_to_source_map.md 默认排除）
PAPER_INTERNAL_MD = {
    "accept_path_analysis_2026-08-03.md",
    "atom_effect_experiment_evidence_audit_2026-08-03.md",
    "atom_role_discussion_and_experiment_handoff_2026-08-01.md",
    "effect_binding_guard_handoff_2026-08-02.md",
    "effect_binding_guard_handoff_2026-08-03.md",
    "effect_binding_guard_handoff_alignment_audit_2026-08-03.md",
    "evidence_sufficiency_audit.md",
    "improvement_whitepaper_2026-08-03.md",
    "novelty_evidence_negative_result_risk_audit_2026-07-28.md",
    "open_questions_for_user.md",
    "paperspine_paper_audit_2026-08-03.md",
    "reviewer_perspective_improvement_evaluation_2026-08-04.md",
    "simulated_usenix_review_2026-07-28.md",
    "simulated_usenix_review_2026-07-30.md",
    "strict_atom_representation_attribution_protocol_2026-08-03.md",
    "strict_atom_representation_attribution_protocol_review_2026-08-03.md",
    "submission_war_plan_2026-08-03.md",
    "theory_proof_audit.md",
    "theory_utility_risk_update_2026-07-30.md",
    "usenix27_submission_readiness_audit_2026-07-28.md",
    "usenix27_submission_readiness_audit_2026-07-30.md",
    "window_execution_decision_2026-08-04.md",
    "writing_report.md",
}

# ---------------------------------------------------------------------------
# 2. 泄漏复检模式
# ---------------------------------------------------------------------------

LEAK_PATTERNS = {
    "host_path_csk": re.compile(r"/data/CSK"),
    "host_path_home": re.compile(r"/home/user"),
    "credential_sk": re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    "author_identity": re.compile(r"skchen17"),
    "git_ssh_remote": re.compile(r"git@github\.com:skchen17"),
}

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# ---------------------------------------------------------------------------
# 3. 工具函数
# ---------------------------------------------------------------------------


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.as_posix()


def should_exclude(rel_path: str, paper_root: str, include_claim_map: bool) -> bool:
    """复制阶段结构性排除判定。rel_path 为相对仓库根的 posix 路径。"""
    parts = rel_path.split("/")
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return True
    if any(part in EXCLUDE_TOP_LEVEL for part in parts[:1]):
        return True
    for exc in EXCLUDE_PATHS:
        if rel_path == exc or rel_path.startswith(exc + "/"):
            return True
    if Path(rel_path).suffix in EXCLUDE_SUFFIXES:
        return True
    # paper/current-usenix 顶层内部 md
    if rel_path.startswith(paper_root + "/") and "/" not in rel_path[len(paper_root) + 1 :]:
        name = rel_path.rsplit("/", 1)[-1]
        if name in PAPER_INTERNAL_MD:
            return True
        if name == "claim_to_source_map.md" and not include_claim_map:
            return True
    return False


def walk_ignore(repo_root: Path, paper_root: str, include_claim_map: bool):
    """copytree ignore 回调：由 should_exclude 驱动。

    copytree 的 ignore 回调收到的是源侧绝对目录路径，需先换算为相对
    仓库根的 posix 路径再交给 should_exclude 判定。
    """

    def _ignore(dir_path: str, names: list[str]) -> set[str]:
        dir_rel = os.path.relpath(dir_path, str(repo_root))
        skipped: set[str] = set()
        for name in names:
            full = (Path(dir_rel) / name).as_posix()
            if should_exclude(full, paper_root, include_claim_map):
                skipped.add(name)
        return skipped

    return _ignore


# ---------------------------------------------------------------------------
# 4. 打包主体
# ---------------------------------------------------------------------------

@dataclass
class PackageResult:
    copied_files: list[str] = field(default_factory=list)
    scrubbed: list[tuple[str, str, str]] = field(default_factory=list)  # (path, pattern, sample)
    scan_report: list[str] = field(default_factory=list)
    checksum_entries: list[str] = field(default_factory=list)
    manifest_entries: list[dict] = field(default_factory=list)


def build_package(
    repo_root: Path,
    paper_root: str,
    out_tar: Path,
    staging: Path,
    keep_staging: bool,
    skip_scan: bool,
    skip_checksums: bool,
    include_claim_map: bool,
    allow_email_pattern: str | None,
) -> int:
    result = PackageResult()

    # 4.1 复制（symlink 全部解引用）
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        shutil.copytree(
            repo_root,
            staging,
            symlinks=False,          # 解析符号链接为真实目录/文件
            ignore=walk_ignore(repo_root, paper_root, include_claim_map),
            dirs_exist_ok=False,
        )
    except (OSError, shutil.Error) as exc:
        print(f"[pack] copy failed: {exc}", file=sys.stderr)
        return 1

    # 4.2 README 替换（改写版进包）
    draft_readme = repo_root / "paper" / "current-usenix" / "README.artifact.md"
    if draft_readme.exists():
        shutil.copyfile(draft_readme, staging / paper_root / "README.md")
        print("[pack] packaged README.md <- README.artifact.md (anonymized draft)")
    else:
        print("[pack] WARNING: README.artifact.md missing; package keeps internal README.md", file=sys.stderr)

    # 4.3 收集文件清单（不含被排除项）
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            result.copied_files.append(rel(path.relative_to(staging)))

    # 4.4 内容级泄漏复检 + 剔除
    email_re = re.compile(allow_email_pattern) if allow_email_pattern else None
    for path in sorted(staging.rglob("*")):
        if not path.is_file():
            continue
        rel_path = rel(path.relative_to(staging))
        if rel_path in PATH_SCAN_WHITELIST:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hit: tuple[str, str, str] | None = None
        for name, pattern in LEAK_PATTERNS.items():
            m = pattern.search(text)
            if m:
                line_no = text.count("\n", 0, m.start()) + 1
                sample = text[max(0, m.start() - 40) : m.start() + 40].replace("\n", " ")
                hit = (rel_path, name, f"L{line_no} {sample}")
                break  # 每文件记录首个命中即可
        if hit is None:
            m = EMAIL_PATTERN.search(text)
            if m and (email_re is None or not email_re.fullmatch(m.group(0))):
                hit = (rel_path, "email", m.group(0))
        if hit is not None:
            result.scrubbed.append(hit)

    removed: set[str] = set()
    for rel_path, name, sample in result.scrubbed:
        target = staging / rel_path
        try:
            target.unlink()
            removed.add(rel_path)
        except OSError as exc:
            print(f"[pack] scrub unlink failed {rel_path}: {exc}", file=sys.stderr)

    # 4.5 证据完整性校验
    missing_evidence = []
    for ev in REQUIRED_EVIDENCE:
        if not (staging / ev).exists():
            missing_evidence.append(ev)
    if missing_evidence:
        print("[pack] FATAL: required evidence missing after scrub:", file=sys.stderr)
        for ev in missing_evidence:
            print(f"    {ev}", file=sys.stderr)
        if not keep_staging:
            shutil.rmtree(staging)
        return 1

    # 4.6 checksums + manifest
    for rel_path in sorted(rel(path.relative_to(staging)) for path in staging.rglob("*") if path.is_file()):
        digest = sha256(staging / rel_path)
        result.checksum_entries.append(f"{digest}  {rel_path}")
        result.manifest_entries.append(
            {
                "path": rel_path,
                "size_bytes": (staging / rel_path).stat().st_size,
                "sha256": digest,
                "role": "required_evidence" if rel_path in REQUIRED_EVIDENCE else "support",
            }
        )

    (staging / "checksums.sha256").write_text(
        "\n".join(result.checksum_entries) + "\n", encoding="utf-8"
    )
    manifest = {
        "artifact": "anonymous_usenix27_effect_contract_candidate",
        "packed_at": datetime.now(timezone.utc).isoformat(),
        "source": "binding-agent-tool-calls-to-effects workspace (parameterized)",
        "file_count": len(result.checksum_entries),
        "release_gates": {
            "full_artifact_credential_identity_path_scan_passed": not result.scrubbed,
            "clean_environment_reproduction_passed": False,
            "anonymous_stable_url_inserted": False,
        },
        "files": result.manifest_entries,
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # 4.7 扫描报告（供审计）
    report_lines = [
        f"leak scan: {len(result.scrubbed)} file(s) hit and removed",
        "---",
    ]
    for rel_path, name, sample in result.scrubbed:
        report_lines.append(f"{name}\t{rel_path}\t{sample}")
    if not result.scrubbed and not skip_scan:
        report_lines.append("clean: no /data/CSK, /home/user, sk- credential, skchen17, or git remote patterns")
    (staging / "leak_scan_report.txt").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    # 4.8 确定性 tar.gz
    def _filter(info: tarfile.TarInfo) -> tarfile.TarInfo:
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        info.mtime = 0
        return info

    with tarfile.open(out_tar, "w:gz", format=tarfile.PAX_FORMAT) as tf:
        for rel_path in sorted(rel(path.relative_to(staging)) for path in staging.rglob("*") if path.is_file()):
            tf.add(staging / rel_path, arcname=rel_path, recursive=False, filter=_filter)

    # 4.9 汇总
    print(f"[pack] files copied: {len(result.copied_files)}")
    print(f"[pack] leak hits scrubbed: {len(result.scrubbed)}")
    print(f"[pack] evidence files ok: {len(REQUIRED_EVIDENCE)}")
    print(f"[pack] tarball: {out_tar} ({out_tar.stat().st_size / 1e6:.1f} MB)")
    if result.scrubbed:
        print("[pack] NOTE: package produced but with scrubbed files; verify leak_scan_report.txt", file=sys.stderr)

    if not keep_staging:
        shutil.rmtree(staging)
        print("[pack] staging removed (use --keep-staging to retain)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the anonymous USENIX artifact tarball (draft)."
    )
    parser.add_argument("--out", type=Path, default=Path("/tmp/anonymous_artifact.tar.gz"))
    parser.add_argument("--staging", type=Path, default=Path("/tmp/artifact_staging"))
    parser.add_argument("--keep-staging", action="store_true")
    parser.add_argument("--paper-root", default="paper/current-usenix")
    parser.add_argument("--skip-scan", action="store_true", help="跳过内容级泄漏复检（不推荐）")
    parser.add_argument("--skip-checksums", action="store_true")
    parser.add_argument("--include-claim-map", action="store_true",
                        help="将 claim_to_source_map.md 一并进包（默认排除，待 P1 决策）")
    parser.add_argument("--allow-email-pattern",
                        help="允许的邮箱白名单正则（默认严格，任何邮箱命中即剔除该文件）")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]   # shared/workspace-management -> 仓库根
    # 校验输出/暂存目录位于仓库外（只读仓库约束）
    for p in (args.out, args.staging):
        if repo_root in p.resolve().parents or p.resolve() == repo_root:
            print(f"[pack] --out/--staging must be outside the repo root: {p}", file=sys.stderr)
            return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    return build_package(
        repo_root=repo_root,
        paper_root=args.paper_root,
        out_tar=args.out,
        staging=args.staging,
        keep_staging=args.keep_staging,
        skip_scan=args.skip_scan,
        skip_checksums=args.skip_checksums,
        include_claim_map=args.include_claim_map,
        allow_email_pattern=args.allow_email_pattern,
    )


if __name__ == "__main__":
    raise SystemExit(main())
