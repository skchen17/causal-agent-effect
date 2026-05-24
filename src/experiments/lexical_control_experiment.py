#!/usr/bin/env python3
"""Lexical-control dataset generation and LOTO evaluation.

The paper's lexical-control claim should be reproducible from files, not from
manual text edits. This script has two modes:

  python lexical_control_experiment.py make-data
  python lexical_control_experiment.py evaluate qwen3-8b_scenarios_merged_lexical_control \
      --baseline qwen3-8b_scenarios_merged

`make-data` rewrites only the scenario text, preserving labels and tool names
for grouping. `evaluate` expects embeddings for both datasets to already exist
under embeddings/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import recall_score
from sklearn.model_selection import StratifiedKFold


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ANALYSIS = ROOT / "analysis"
EMBEDDINGS = ROOT / "embeddings"

DEFAULT_INPUT = DATA / "scenarios_merged.jsonl"
DEFAULT_OUTPUT = DATA / "scenarios_merged_lexical_control.jsonl"
DEFAULT_MANIFEST = ANALYSIS / "lexical_control_manifest.json"

URL_RE = re.compile(r"https?://[^\s)>\]\"']+")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:~/|/)[A-Za-z0-9._~+/@%-]+|"
    r"(?<![A-Za-z0-9_])[A-Za-z0-9._-]+\.(?:txt|json|jsonl|csv|md|py|sh|log|yaml|yml|toml|env)"
)

COMMAND_WORDS_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:awk|bash|cat|chmod|chown|cp|curl|find|git|grep|jq|ls|mkdir|mv|npm|pip|python3?|rm|sed|sh|tee|touch|wget)"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

TOOL_ALIASES = {
    "delete_file",
    "delete file",
    "read_file",
    "read file",
    "write_file",
    "write file",
    "send_message",
    "send message",
    "web_fetch",
    "web fetch",
    "web_search",
    "web search",
    "terminal",
    "shell",
    "command line",
    "delegate",
    "memory",
}
TOOL_ALIAS_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    + "|".join(re.escape(alias) for alias in sorted(TOOL_ALIASES, key=len, reverse=True))
    + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_text(
    text: str,
    *,
    replace_command_words: bool = False,
    replace_paths: bool = False,
) -> tuple[str, Counter[str]]:
    counts: Counter[str] = Counter()

    text, n = URL_RE.subn("[URL]", text)
    counts["url"] += n

    text, n = INLINE_CODE_RE.subn("[CMD]", text)
    counts["inline_code"] += n

    text, n = TOOL_ALIAS_RE.subn("[TOOL]", text)
    counts["tool_mention"] += n

    if replace_paths:
        text, n = PATH_RE.subn("[PATH]", text)
        counts["path"] += n

    if replace_command_words:
        text, n = COMMAND_WORDS_RE.subn("[CMD]", text)
        counts["command_word"] += n

    return text, counts


def make_data(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_path = Path(args.output)
    manifest_path = Path(args.manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    total_counts: Counter[str] = Counter()
    changed_rows = 0
    rows = 0
    context_counts: Counter[str] = Counter()
    tool_counts: Counter[str] = Counter()

    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            item = json.loads(line)
            rows += 1
            context_counts[item.get("context_type", "unknown")] += 1
            tool_counts[item.get("tool_name", "unknown")] += 1

            original = item.get("scenario_text", "")
            normalized, counts = normalize_text(
                original,
                replace_command_words=args.replace_command_words,
                replace_paths=args.replace_paths,
            )
            if normalized != original:
                changed_rows += 1
            total_counts.update(counts)
            item["scenario_text"] = normalized
            dst.write(json.dumps(item, ensure_ascii=False) + "\n")

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": str(input_path.relative_to(ROOT) if input_path.is_relative_to(ROOT) else input_path),
        "output": str(output_path.relative_to(ROOT) if output_path.is_relative_to(ROOT) else output_path),
        "input_sha256": sha256_file(input_path),
        "output_sha256": sha256_file(output_path),
        "rows": rows,
        "changed_rows": changed_rows,
        "normalization": {
            "url": "[URL]",
            "inline_backtick_code": "[CMD]",
            "tool_aliases": "[TOOL]",
            "replace_paths": bool(args.replace_paths),
            "replace_command_words": bool(args.replace_command_words),
        },
        "replacement_counts": dict(sorted(total_counts.items())),
        "context_counts": dict(sorted(context_counts.items())),
        "tool_counts": dict(sorted(tool_counts.items())),
        "next_steps": [
            "python extract_embeddings_llm.py Qwen/Qwen3-8B scenarios_merged_lexical_control.jsonl --batch-size 8",
            "python lexical_control_experiment.py evaluate qwen3-8b_scenarios_merged_lexical_control --baseline qwen3-8b_scenarios_merged",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output_path.relative_to(ROOT)}")
    print(f"Wrote {manifest_path.relative_to(ROOT)}")
    print(f"Rows changed: {changed_rows}/{rows}; replacements: {dict(sorted(total_counts.items()))}")


def load_embeddings(data_name: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any], list[str]]:
    emb_path = EMBEDDINGS / f"embeddings_{data_name}.npy"
    eff_path = EMBEDDINGS / f"effects_{data_name}.npy"
    meta_path = EMBEDDINGS / f"meta_{data_name}.json"
    texts_path = EMBEDDINGS / f"texts_{data_name}.jsonl"
    missing = [p for p in [emb_path, eff_path, meta_path, texts_path] if not p.exists()]
    if missing:
        names = ", ".join(str(p.relative_to(ROOT)) for p in missing)
        raise FileNotFoundError(f"Missing embedding artifacts for {data_name}: {names}")

    X = np.load(emb_path)
    Y = np.load(eff_path)
    with meta_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)
    with texts_path.open("r", encoding="utf-8") as f:
        tools = [json.loads(line).get("tool_name", "unknown") for line in f]
    return X, Y, meta, tools


def compute_loto_table(X: np.ndarray, Y: np.ndarray, meta: dict[str, Any], tools: list[str]) -> dict[str, Any]:
    tool_set = sorted(set(tools))
    loto_table: dict[str, Any] = {}

    for effect_idx, effect in enumerate(meta["effect_names"]):
        y = Y[:, effect_idx]
        effect_rows: dict[str, Any] = {}

        for heldout_tool in tool_set:
            pos_i = [i for i, tool in enumerate(tools) if tool == heldout_tool and y[i] == 1]
            neg_i = [i for i, tool in enumerate(tools) if tool == heldout_tool and y[i] == 0]
            n_pos, n_neg = len(pos_i), len(neg_i)
            if n_pos < 5 or n_neg < 5:
                continue

            all_idx = np.array(pos_i + neg_i)
            labels = np.array([1] * n_pos + [0] * n_neg)
            n_splits = min(3, n_pos, n_neg)
            within_fnrs = []
            skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            for train_fold, test_fold in skf.split(all_idx, labels):
                clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
                clf.fit(X[all_idx[train_fold]], labels[train_fold])
                pred = clf.predict(X[all_idx[test_fold]])
                within_fnrs.append(1.0 - recall_score(labels[test_fold], pred, zero_division=0))

            train_i = np.array([i for i, tool in enumerate(tools) if tool != heldout_tool])
            if len(np.unique(y[train_i])) < 2:
                continue
            clf_loto = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced")
            clf_loto.fit(X[train_i], y[train_i])
            pred_loto = clf_loto.predict(X[all_idx])
            heldout_fnr = 1.0 - recall_score(labels, pred_loto, zero_division=0)
            within_fnr = float(np.mean(within_fnrs))
            effect_rows[heldout_tool] = {
                "n_pos": n_pos,
                "n_neg": n_neg,
                "within_FNR": round(within_fnr, 4),
                "heldout_FNR": round(float(heldout_fnr), 4),
                "FNR_gap": round(float(heldout_fnr - within_fnr), 4),
            }

        if len(effect_rows) >= 2:
            loto_table[effect] = effect_rows

    return loto_table


def summarize_loto(loto_table: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    all_heldout = []
    all_gaps = []
    for effect, by_tool in loto_table.items():
        heldout = [row["heldout_FNR"] for row in by_tool.values()]
        gaps = [row["FNR_gap"] for row in by_tool.values()]
        all_heldout.extend(heldout)
        all_gaps.extend(gaps)
        summary[effect] = {
            "n_tools": len(by_tool),
            "mean_heldout_FNR": round(float(np.mean(heldout)), 4),
            "max_heldout_FNR": round(float(np.max(heldout)), 4),
            "mean_FNR_gap": round(float(np.mean(gaps)), 4),
            "max_FNR_gap": round(float(np.max(gaps)), 4),
        }
    summary["_overall"] = {
        "n_effect_tool_cells": len(all_heldout),
        "mean_heldout_FNR": round(float(np.mean(all_heldout)), 4) if all_heldout else None,
        "mean_FNR_gap": round(float(np.mean(all_gaps)), 4) if all_gaps else None,
    }
    return summary


def compare_loto(control: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    deltas: dict[str, Any] = {}
    heldout_deltas = []
    gap_deltas = []
    for effect in sorted(set(control) & set(baseline)):
        effect_rows = {}
        for tool in sorted(set(control[effect]) & set(baseline[effect])):
            c = control[effect][tool]
            b = baseline[effect][tool]
            row = {
                "baseline_heldout_FNR": b["heldout_FNR"],
                "control_heldout_FNR": c["heldout_FNR"],
                "delta_heldout_FNR": round(c["heldout_FNR"] - b["heldout_FNR"], 4),
                "baseline_FNR_gap": b["FNR_gap"],
                "control_FNR_gap": c["FNR_gap"],
                "delta_FNR_gap": round(c["FNR_gap"] - b["FNR_gap"], 4),
                "n_pos": c["n_pos"],
                "n_neg": c["n_neg"],
            }
            heldout_deltas.append(row["delta_heldout_FNR"])
            gap_deltas.append(row["delta_FNR_gap"])
            effect_rows[tool] = row
        if effect_rows:
            deltas[effect] = effect_rows
    return {
        "by_effect_tool": deltas,
        "summary": {
            "n_common_effect_tool_cells": len(heldout_deltas),
            "mean_delta_heldout_FNR": round(float(np.mean(heldout_deltas)), 4) if heldout_deltas else None,
            "mean_delta_FNR_gap": round(float(np.mean(gap_deltas)), 4) if gap_deltas else None,
            "max_delta_heldout_FNR": round(float(np.max(heldout_deltas)), 4) if heldout_deltas else None,
            "min_delta_heldout_FNR": round(float(np.min(heldout_deltas)), 4) if heldout_deltas else None,
        },
    }


def evaluate(args: argparse.Namespace) -> None:
    control_name = args.data_name
    baseline_name = args.baseline
    X_control, Y_control, meta_control, tools_control = load_embeddings(control_name)
    X_base, Y_base, meta_base, tools_base = load_embeddings(baseline_name)
    if meta_control["effect_names"] != meta_base["effect_names"]:
        raise ValueError("Control and baseline effect schemas differ.")

    control_loto = compute_loto_table(X_control, Y_control, meta_control, tools_control)
    baseline_loto = compute_loto_table(X_base, Y_base, meta_base, tools_base)
    result = {
        "control_data_name": control_name,
        "baseline_data_name": baseline_name,
        "control_loto_table": control_loto,
        "baseline_loto_table": baseline_loto,
        "control_summary": summarize_loto(control_loto),
        "baseline_summary": summarize_loto(baseline_loto),
        "comparison": compare_loto(control_loto, baseline_loto),
    }

    out = Path(args.analysis_out) if args.analysis_out else ANALYSIS / f"lexical_control_{control_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    print(f"Common cells: {result['comparison']['summary']['n_common_effect_tool_cells']}")
    print(f"Mean delta heldout FNR: {result['comparison']['summary']['mean_delta_heldout_FNR']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    make = sub.add_parser("make-data", help="Create lexical-control JSONL and manifest.")
    make.add_argument("--input", default=str(DEFAULT_INPUT))
    make.add_argument("--output", default=str(DEFAULT_OUTPUT))
    make.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    make.add_argument("--replace-paths", action="store_true", help="Also normalize file/path-looking tokens to [PATH].")
    make.add_argument(
        "--replace-command-words",
        action="store_true",
        help="Also normalize bare shell command words to [CMD]. Off by default to avoid over-editing prose.",
    )
    make.set_defaults(func=make_data)

    ev = sub.add_parser("evaluate", help="Evaluate lexical-control embeddings against a baseline dataset.")
    ev.add_argument("data_name", help="Control embedding data name, e.g. qwen3-8b_scenarios_merged_lexical_control.")
    ev.add_argument("--baseline", default="qwen3-8b_scenarios_merged")
    ev.add_argument("--analysis-out")
    ev.set_defaults(func=evaluate)
    return parser


def main() -> None:
    parser = build_parser()
    argv = sys.argv[1:] or ["make-data"]
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.error("choose a command: make-data or evaluate")
    args.func(args)


if __name__ == "__main__":
    main()
