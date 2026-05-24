"""
Merge multiple scenario JSONL files into one unified dataset.
"""
from __future__ import annotations

import json
import random
from pathlib import Path


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data"
    files = [
        out_dir / "scenarios_counterfactual.jsonl",
        out_dir / "targeted_synthetic.jsonl",
    ]

    all_data = []
    for fp in files:
        if fp.exists():
            with open(fp) as f:
                items = [json.loads(line) for line in f]
            all_data.extend(items)
            print(f"  {fp.name}: {len(items)} rows")
        else:
            print(f"  {fp.name}: (not found, skipping)")

    # Shuffle
    random.Random(42).shuffle(all_data)

    out_path = out_dir / "scenarios_merged.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    if not all_data:
        print("No data to merge.")
        return
    # Stats
    EFFECTS = sorted(all_data[0]["effects"].keys())
    effect_counts = {e: 0 for e in EFFECTS}
    tool_counts = {}
    for d in all_data:
        for e, v in d["effects"].items():
            if v: effect_counts[e] += 1
        tool_counts[d["tool_name"]] = tool_counts.get(d["tool_name"], 0) + 1

    print(f"\nMerged: {len(all_data)} total → {out_path}")
    print(f"\nEffect distribution:")
    for e, c in sorted(effect_counts.items(), key=lambda x: -x[1]):
        pct = c / len(all_data) * 100
        print(f"  {e:25s}: {c:5d} ({pct:5.1f}%)")

    print(f"\nTool distribution:")
    for t, c in sorted(tool_counts.items()):
        print(f"  {t:15s}: {c:5d}")


if __name__ == "__main__":
    main()
