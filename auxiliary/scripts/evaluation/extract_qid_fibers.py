#!/usr/bin/env python3
"""Run the contextual CLI and emit gold-free set-valued inference JSONL."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

QID = re.compile(r"Q[0-9]+")


def parse_output(identifier: str, output: str, families: list[str] | None = None) -> dict:
    stages = []
    current = None
    graph_hash = None
    for line in output.splitlines():
        if line.startswith("graph_sha256="):
            graph_hash = line.split("=", 1)[1]
        elif line.startswith("stage="):
            match = re.match(r"stage=(\d+) constraint=(.*)", line)
            if not match:
                raise ValueError(f"malformed stage line: {line}")
            current = {
                "index": int(match.group(1)),
                "constraint": match.group(2),
                "survivors": [],
                "obstructions": [],
            }
            stages.append(current)
        elif line.strip().startswith("survivors=") and current is not None:
            current["survivors"] = QID.findall(line)
        elif line.strip().startswith("obstruction=") and current is not None:
            current["obstructions"].append(line.strip().split("=", 1)[1])
    if graph_hash is None or not stages:
        raise ValueError("contextual CLI did not return a tower")
    return {
        "id": identifier,
        "graph_sha256": graph_hash,
        "fiber": stages[-1]["survivors"],
        "families": families or [],
        "stages": stages,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    results = []
    with args.dataset.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            scenario = row["scenario"]
            completed = subprocess.run(
                [str(args.engine), "contextual-fiber", scenario],
                check=True,
                text=True,
                capture_output=True,
            )
            results.append(parse_output(row["id"], completed.stdout, row.get("families")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
