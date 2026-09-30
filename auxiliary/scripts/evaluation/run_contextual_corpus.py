#!/usr/bin/env python3
"""Run a gold-free contextual corpus through GF and every Agda-checked layer."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

QID = re.compile(r"Q[0-9]+")


def precompute_dependency_hints(dataset: Path) -> dict[str, dict]:
    """Batch-parse the whole corpus once via annotate_dependency_hints.py.

    Must run before the per-row ThreadPoolExecutor loop below, not inside
    it -- one Stanza pipeline for the whole corpus, not one per parallel
    subprocess (that already caused a 5h50m CI timeout on the flat
    pipeline once; see scripts/annotate_dependency_hints.py's docstring).
    A failure here degrades to "no hints for anyone", never a hard error:
    resolve_action's dependency_hint=None path is identical to its
    pre-hint behaviour.
    """
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "dependency-hints.jsonl"
        completed = subprocess.run(
            [
                "python3",
                "auxiliary/scripts/annotate_dependency_hints.py",
                "--dataset",
                str(dataset),
                "--output",
                str(output),
                "--text-field",
                "sentence",
                "--target-field",
                "source",
                "--no-source-filter",
            ],
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0 or not output.exists():
            print(
                "run_contextual_corpus: dependency-hint precompute failed, "
                "continuing without hints: " + completed.stderr.strip(),
                file=sys.stderr,
            )
            return {}
        hints = {}
        with output.open(encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    hint = json.loads(line)
                    hints[hint["id"]] = hint
        return hints


def run_one(
    engine: Path,
    snapshot: Path,
    ablation: str,
    row: dict,
    dependency_hint: dict | None,
    llm_proposer_model: str | None = None,
    llm_proposer_endpoint: str | None = None,
) -> dict:
    command = [
        "python3",
        "auxiliary/scripts/run_automatic_contextual_pipeline.py",
        "--engine",
        str(engine),
        "--snapshot",
        str(snapshot),
        "--sentence",
        row["sentence"],
        "--source",
        row["source"],
        "--ablation",
        ablation,
    ]
    if row.get("direction") == "contract":
        command.extend(["--contract-target", row["contract_target"]])
    if dependency_hint is not None:
        command.extend(
            ["--dependency-hint", json.dumps(dependency_hint, sort_keys=True)]
        )
    if llm_proposer_model:
        command.extend(["--llm-proposer-model", llm_proposer_model])
        if llm_proposer_endpoint:
            command.extend(["--llm-proposer-endpoint", llm_proposer_endpoint])
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
    )
    combined = completed.stdout + completed.stderr
    expected_rejection = row.get("expected_status") == "rejected"
    rejected_by_safety = (
        completed.returncode != 0
        and "contextual contraction rejected" in combined
    )
    successful = rejected_by_safety if expected_rejection else completed.returncode == 0
    result = {
        "id": row["id"],
        "family": row["family"],
        "families": [row["family"]],
        "status": "ok" if successful else "failed",
        "exit_code": completed.returncode,
        "direction": row.get("direction", "expand"),
        "expected_status": row.get("expected_status", "accepted"),
        "ablation": ablation,
        "stages": [],
    }
    current = None
    for line in completed.stdout.splitlines():
        if line.startswith("gf-tree="):
            result["gf_tree"] = line.split("=", 1)[1]
        elif line.startswith("tree-source="):
            # "stanza" or "gf-parser" -- which of
            # run_automatic_contextual_pipeline.py's two tree sources
            # produced this row's tree, printed unconditionally once a
            # tree was successfully obtained (see that module's own
            # comment on its "tree-source=" print). Content-free: just
            # names one of two known code paths, never sentence text.
            result["tree_source"] = line.split("=", 1)[1]
        elif line.startswith("decline-reason="):
            # "" when a Stanza-built tree was trusted, else a closed-
            # vocabulary reason code (see
            # build_gf_tree_decline_reason's own docstring) -- printed
            # alongside "tree-source=" for the same reason.
            result["decline_reason"] = line.split("=", 1)[1]
        elif line.startswith("all-decline-reasons="):
            # Every reason this sentence's tree-building would hit in
            # turn, not just the first (see enumerate_gf_tree_blockers's
            # own docstring) -- comma-joined reason codes, safe to split
            # since the closed vocabulary never contains a comma; "" (no
            # commas at all) means zero blockers.
            value = line.split("=", 1)[1]
            result["all_decline_reasons"] = value.split(",") if value else []
        elif line.startswith("llm-decline-reason="):
            # Same idea, for the third (LLM) tier -- "not-attempted"
            # when it never ran at all (Stanza already succeeded, or no
            # --llm-proposer-model was configured).
            result["llm_decline_reason"] = line.split("=", 1)[1]
        elif line.startswith("dep-status="):
            # annotate_dependency_hints.py's own dep_status
            # ("direct-argument"/"copula-argument"/"nested-modifier"/
            # "no-governing-verb:<reason>"/"parse-error"/"no-hint") --
            # determines whether resolve_action got a real governing_start
            # at all (root-lemma-mismatch:no-governing-start's own root
            # cause), printed alongside tree-source/decline-reason for
            # the same reason.
            result["dep_status"] = line.split("=", 1)[1]
        elif line.startswith("graph_sha256="):
            result["graph_sha256"] = line.split("=", 1)[1]
        elif line.startswith("contract="):
            match = re.match(r"contract=(Q[0-9]+) -> (Q[0-9]+) safety=(.*)", line)
            if match:
                result["contracted_target"] = match.group(1)
                result["contracted_source"] = match.group(2)
                result["contraction_safety"] = match.group(3)
        elif line.startswith("stage="):
            match = re.match(r"stage=(\d+) constraint=(.*)", line)
            current = {
                "index": int(match.group(1)),
                "constraint": match.group(2),
                "survivors": [],
                "obstructions": [],
                "preferred": [],
                "preference_misses": [],
                "agda_checked": False,
            }
            result["stages"].append(current)
        elif current is not None and line.strip().startswith("survivors="):
            current["survivors"] = QID.findall(line)
        elif current is not None and line.strip() == "agda-layer-check=true":
            current["agda_checked"] = True
        elif current is not None and line.strip().startswith("obstruction="):
            current["obstructions"].append(line.strip().split("=", 1)[1])
        elif current is not None and line.strip().startswith("preferred="):
            current["preferred"] = QID.findall(line)
        elif current is not None and line.strip().startswith("preference-miss="):
            current["preference_misses"].append(line.strip().split("=", 1)[1])
    result["fiber"] = (
        [result["contracted_source"]]
        if "contracted_source" in result
        else (result["stages"][-1]["survivors"] if result["stages"] else [])
    )
    if completed.returncode != 0:
        result["failure"] = (completed.stdout + completed.stderr).strip()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--allow-failures", action="store_true")
    parser.add_argument(
        "--print-failures",
        action="store_true",
        help=(
            "print each failing row's id and failure text to stdout. "
            "Opt-in and off by default: this prints the row's own raw "
            "subprocess output, which can include sentence text -- only "
            "safe for datasets that are not license-restricted (e.g. "
            "this project's own checked-in evaluation/contextual-"
            "multidomain/*.jsonl fixtures, used by the Makefile's own "
            "contextual-corpus-test target). Never pass this for a real "
            "WiMCor/ConMeC corpus run -- contextual-tower-evaluation.yml "
            "never does."
        ),
    )
    parser.add_argument(
        "--ablation",
        choices=[
            "full",
            "no-wordnet",
            "no-framenet",
            "no-existential",
            "no-formal-filtering",
        ],
        default="full",
    )
    parser.add_argument(
        "--llm-proposer-model",
        help=(
            "third tree-source tier, passed through to each "
            "run_automatic_contextual_pipeline.py subprocess's own "
            "--llm-proposer-model -- unset (default) disables it entirely"
        ),
    )
    parser.add_argument("--llm-proposer-endpoint")
    args = parser.parse_args()
    inputs = [
        json.loads(line)
        for line in args.dataset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dependency_hints = precompute_dependency_hints(args.dataset)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(
            executor.map(
                lambda row: run_one(
                    args.engine,
                    args.snapshot,
                    args.ablation,
                    row,
                    dependency_hints.get(row["id"]),
                    args.llm_proposer_model,
                    args.llm_proposer_endpoint,
                ),
                inputs,
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )
    failures = sum(row["status"] != "ok" for row in results)
    print(f"instances={len(results)} failures={failures}")
    if failures and args.print_failures:
        for row in results:
            if row["status"] != "ok":
                print(f"failure id={row['id']}: {row.get('failure', '')}")
    if failures and not args.allow_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
