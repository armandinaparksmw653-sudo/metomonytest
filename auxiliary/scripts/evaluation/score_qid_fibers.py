#!/usr/bin/env python3
"""Score set-valued QID fibers without exposing gold labels to inference."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def jsonl(path: Path):
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inference", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    predicted = {row["id"]: set(row.get("fiber", [])) for row in jsonl(args.inference)}
    inference_rows = {row["id"]: row for row in jsonl(args.inference)}
    gold_rows = list(jsonl(args.gold))
    if not gold_rows:
        raise SystemExit("gold file is empty")
    hits = 0
    positive_instances = 0
    negative_instances = 0
    empty_gold_exact = 0
    fully_contained = 0
    exact_matches = 0
    empty_fibers = 0
    intersection = 0
    total_gold = 0
    cardinalities = Counter()
    obstruction_distribution = Counter()
    eliminations = Counter()
    family_intersection = 0
    family_total = 0
    direction_totals = Counter()
    direction_exact = Counter()
    contraction_safety = Counter()
    covered_instances = 0
    abstentions = 0
    total_stages = 0
    verified_stages = 0
    preference_candidates = 0
    preference_matches = 0
    layer_counts = Counter()
    missing = []
    for row in gold_rows:
        identifier = row["id"]
        expected = set(row["gold_qids"])
        fiber = predicted.get(identifier, set())
        overlap = expected & fiber
        if expected:
            positive_instances += 1
            hits += bool(overlap)
        else:
            negative_instances += 1
            empty_gold_exact += not fiber
        fully_contained += expected <= fiber
        exact_matches += expected == fiber
        empty_fibers += not fiber
        intersection += len(overlap)
        total_gold += len(expected)
        cardinalities[len(fiber)] += 1
        if expected and not overlap:
            missing.append(identifier)
        inference = inference_rows.get(identifier, {})
        covered = inference.get("status") == "ok"
        covered_instances += covered
        abstentions += not covered
        layer_counts[len(inference.get("stages", []))] += 1
        direction = inference.get("direction", "expand")
        direction_totals[direction] += 1
        direction_exact[direction] += expected == fiber
        if inference.get("contraction_safety"):
            contraction_safety[inference["contraction_safety"]] += 1
        for stage in inference.get("stages", []):
            total_stages += 1
            verified_stages += bool(stage.get("agda_checked"))
            stage_name = stage.get("constraint", "unknown")
            input_count = (
                len(inference.get("stages", [])[stage["index"] - 1]["survivors"])
                if stage.get("index", 0) > 0
                else len(stage.get("survivors", []))
            )
            survived = len(stage.get("survivors", []))
            eliminations[stage_name] += max(0, input_count - survived)
            for obstruction in stage.get("obstructions", []):
                obstruction_distribution[obstruction.split(" ", 1)[0]] += 1
            if stage.get("preferred") or stage.get("preference_misses"):
                preference_candidates += len(stage.get("survivors", []))
                preference_matches += len(stage.get("preferred", []))
        expected_families = set(row.get("gold_families", []))
        predicted_families = set(inference.get("families", []))
        family_intersection += len(expected_families & predicted_families)
        family_total += len(expected_families)
    report = {
        "instances": len(gold_rows),
        "gold_in_fiber_hit_rate": {
            "numerator": hits,
            "denominator": positive_instances,
        },
        "empty_gold_exact_rate": {
            "numerator": empty_gold_exact,
            "denominator": negative_instances,
        },
        "gold_qid_micro_recall": {"numerator": intersection, "denominator": total_gold},
        "gold_fully_contained_rate": {
            "numerator": fully_contained,
            "denominator": len(gold_rows),
        },
        "fiber_exact_match_rate": {
            "numerator": exact_matches,
            "denominator": len(gold_rows),
        },
        "empty_fiber_rate": {
            "numerator": empty_fibers,
            "denominator": len(gold_rows),
        },
        "fiber_cardinality_histogram": dict(sorted(cardinalities.items())),
        "family_micro_recall": {
            "numerator": family_intersection,
            "denominator": family_total,
        },
        "eliminations_per_constraint": dict(sorted(eliminations.items())),
        "obstruction_distribution": dict(sorted(obstruction_distribution.items())),
        "exact_match_by_direction": {
            direction: {
                "numerator": direction_exact[direction],
                "denominator": total,
            }
            for direction, total in sorted(direction_totals.items())
        },
        "contraction_safety": dict(sorted(contraction_safety.items())),
        "gold_without_fiber_hit": missing,
        "coverage": {
            "numerator": covered_instances,
            "denominator": len(gold_rows),
        },
        "abstention_rate": {
            "numerator": abstentions,
            "denominator": len(gold_rows),
        },
        "formal_stage_verification_rate": {
            "numerator": verified_stages,
            "denominator": total_stages,
        },
        "preference_match_rate": {
            "numerator": preference_matches,
            "denominator": preference_candidates,
        },
        "layer_count_histogram": dict(sorted(layer_counts.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
