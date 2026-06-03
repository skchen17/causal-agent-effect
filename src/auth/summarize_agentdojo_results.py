"""Summarize AgentDojo T112-T114 experiment artifacts."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist
from typing import Any


OUTPUT_JSON = Path("analysis/results/agentdojo_experiment_summary_2026-06-01.json")
OUTPUT_MD = Path("analysis/results/agentdojo_experiment_summary_2026-06-01.md")


@dataclass
class AggregateRow:
    family: str
    attack: str
    method: str
    source: str
    n: int
    aur_count: int
    asr_count: int
    note: str

    @property
    def aur(self) -> float:
        return self.aur_count / self.n if self.n else math.nan

    @property
    def asr(self) -> float:
        return self.asr_count / self.n if self.n else math.nan

    def as_dict(self) -> dict[str, Any]:
        aur_ci = wilson(self.aur_count, self.n)
        asr_ci = wilson(self.asr_count, self.n)
        return {
            "family": self.family,
            "attack": self.attack,
            "method": self.method,
            "source": self.source,
            "n": self.n,
            "A_UR_count": f"{self.aur_count}/{self.n}",
            "ASR_count": f"{self.asr_count}/{self.n}",
            "A_UR": self.aur,
            "A_UR_wilson95": aur_ci,
            "ASR": self.asr,
            "ASR_wilson95": asr_ci,
            "note": self.note,
        }


def wilson(k: int, n: int, confidence: float = 0.95) -> list[float]:
    if n == 0:
        return [math.nan, math.nan]
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def count_from_rate(rate: float, n: int) -> int:
    return int(round(rate * n))


def aggregate_t112(path: str, attack: str, family: str, note: str) -> list[AggregateRow]:
    payload = load_json(path)
    by_defense: dict[str, dict[str, int]] = {}
    for row in payload["results"]:
        defense = row["defense"]
        bucket = by_defense.setdefault(defense, {"n": 0, "aur": 0, "asr": 0})
        n = int(row["n_attacked"])
        bucket["n"] += n
        bucket["aur"] += count_from_rate(float(row["utility_under_attack"]), n)
        bucket["asr"] += count_from_rate(float(row["attack_success_rate"]), n)
    out = []
    for defense, bucket in sorted(by_defense.items()):
        out.append(
            AggregateRow(
                family=family,
                attack=attack,
                method=f"AgentDojo {defense}",
                source=path,
                n=bucket["n"],
                aur_count=bucket["aur"],
                asr_count=bucket["asr"],
                note=note,
            )
        )
    return out


def parse_count(value: str) -> tuple[int, int]:
    left, right = value.split("/")
    return int(left), int(right)


def aggregate_t113(path: str, attack: str, family: str, note: str) -> list[AggregateRow]:
    payload = load_json(path)
    by_method: dict[str, dict[str, int]] = {}
    for row in payload["summary_by_suite"]:
        method = row["method"]
        bucket = by_method.setdefault(method, {"n": 0, "aur": 0, "asr": 0})
        aur, n1 = parse_count(row["A_UR_count"])
        asr, n2 = parse_count(row["ASR_count"])
        assert n1 == n2
        bucket["n"] += n1
        bucket["aur"] += aur
        bucket["asr"] += asr
    return [
        AggregateRow(
            family=family,
            attack=attack,
            method=method,
            source=path,
            n=bucket["n"],
            aur_count=bucket["aur"],
            asr_count=bucket["asr"],
            note=note,
        )
        for method, bucket in sorted(by_method.items())
    ]


def aggregate_t114(path: str, attack: str, family: str, note: str) -> list[AggregateRow]:
    payload = load_json(path)
    rows = []
    for row in payload["summary_by_method"]:
        aur, n1 = parse_count(row["proxy_A_UR_count"])
        asr, n2 = parse_count(row["proxy_ASR_count"])
        assert n1 == n2
        rows.append(
            AggregateRow(
                family=family,
                attack=attack,
                method=f"AuthGraph-style {row['method']}",
                source=path,
                n=n1,
                aur_count=aur,
                asr_count=asr,
                note=note,
            )
        )
    return rows


def build_rows() -> list[AggregateRow]:
    rows: list[AggregateRow] = []
    rows.extend(
        aggregate_t112(
            "analysis/results/agentdojo_real_scenario_eval_t112_deepseek_direct_5x3.json",
            "direct",
            "5x3 scaled",
            "DeepSeek direct no-defense baseline.",
        )
    )
    rows.extend(
        aggregate_t112(
            "analysis/results/agentdojo_real_scenario_eval_t112_deepseek_direct_5x3_builtin_defenses.json",
            "direct",
            "5x3 scaled",
            "AgentDojo built-in prompt defenses.",
        )
    )
    rows.extend(
        aggregate_t114(
            "analysis/results/agentdojo_authgraph_proxy_t114_deepseek_direct_5x3.json",
            "direct",
            "5x3 scaled",
            "Offline proxy over no-defense logs.",
        )
    )
    rows.extend(
        aggregate_t113(
            "analysis/results/agentdojo_guarded_eval_t113_replay_commit_deepseek_direct_5x3.json",
            "direct",
            "5x3 scaled",
            "Clean-shadow replay upper-bound method.",
        )
    )
    rows.extend(
        aggregate_t112(
            "analysis/results/agentdojo_real_scenario_eval_t112_deepseek_important_no_model_5x3.json",
            "important_instructions_no_model_name",
            "5x3 scaled",
            "No-defense baseline with AgentDojo stronger instruction attack variant.",
        )
    )
    rows.extend(
        aggregate_t114(
            "analysis/results/agentdojo_authgraph_proxy_t114_deepseek_important_no_model_5x3.json",
            "important_instructions_no_model_name",
            "5x3 scaled",
            "Offline proxy over stronger-attack no-defense logs.",
        )
    )
    rows.extend(
        aggregate_t113(
            "analysis/results/agentdojo_guarded_eval_t113_replay_commit_deepseek_important_no_model_5x3.json",
            "important_instructions_no_model_name",
            "5x3 scaled",
            "Clean-shadow replay upper-bound method under stronger attack.",
        )
    )
    rows.extend(
        aggregate_t113(
            "analysis/results/agentdojo_guarded_eval_t113_v1.json",
            "direct",
            "2x2 pilot",
            "Includes prefix-lock stress test and replay-commit smoke-scale method.",
        )
    )
    return rows


def write_markdown(rows: list[dict[str, Any]]) -> None:
    lines = [
        "# AgentDojo T112-T114 Experiment Summary",
        "",
        "## Scope",
        "",
        "- Model: `deepseek-v4-flash` through a DeepSeek OpenAI-compatible endpoint.",
        "- Benchmark: AgentDojo `v1.2.2` as installed in `causal-safety`.",
        "- Main scaled subset: 4 suites x 5 user tasks x 3 injection tasks = 60 attacked cases per method/attack.",
        "- `important_instructions_no_model_name` uses AgentDojo pipeline label `local` only for attack-string generation; the executed model remains DeepSeek.",
        "- T114 is an AuthGraph-style proxy, not the AuthGraph authors' implementation.",
        "- T113 replay-commit is a clean-shadow oracle upper bound, not a deployable compiler.",
        "",
        "## Aggregate Table",
        "",
        "| family | attack | method | n | A.UR | A.UR 95% CI | ASR | ASR 95% CI | counts |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['family']} | {row['attack']} | {row['method']} | {row['n']} | "
            f"{row['A_UR']:.4f} | [{row['A_UR_wilson95'][0]:.3f}, {row['A_UR_wilson95'][1]:.3f}] | "
            f"{row['ASR']:.4f} | [{row['ASR_wilson95'][0]:.3f}, {row['ASR_wilson95'][1]:.3f}] | "
            f"A.UR {row['A_UR_count']}; ASR {row['ASR_count']} |"
        )
    lines.extend(
        [
            "",
            "## Main Interpretation",
            "",
            "- Direct no-defense scaled baseline has ASR 9/60; the stronger instruction variant has ASR 8/60.",
            "- AgentDojo prompt defenses do not remove banking failures in the direct setting; aggregate direct ASR is 8/60 for repeat-user-prompt and 9/60 for spotlighting.",
            "- AuthGraph-style exact/provenance proxies drive ASR near or to zero but sharply reduce A.UR, indicating over-denial.",
            "- Shadow replay-commit has ASR 0/60 for both attacks and A.UR 48/60, better utility than the proxy baselines but still below no-defense/built-in utility in Slack due to replay fidelity errors.",
            "",
            "## Claim Boundary",
            "",
            "These results support a real-benchmark mechanism signal for future-constrained replay, not a deployable safety guarantee. The strongest current limitation is the clean-shadow oracle assumption and replay fidelity failures when injected environments change resources.",
        ]
    )
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows = [row.as_dict() for row in build_rows()]
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(rows)
    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_MD}")


if __name__ == "__main__":
    main()
