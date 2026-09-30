#!/usr/bin/env python3
"""Generate deterministic FrameNet role-capability projections from SemLink metadata.

VerbNet 3.4 carries FrameNet links on action senses.  This compiler joins
those links with executable Action×Role rows and emits the most evidenced
frame/hole/requirement projections.  They remain SelectionalPreference:
frequency and cross-resource agreement do not turn them into logical facts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


SCHEMA = "framenet-role-capabilities-1"


def rows(path: Path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--actions", type=Path, default=Path("auxiliary/data/verbnet-actions.tsv")
    )
    parser.add_argument(
        "--roles", type=Path, default=Path("auxiliary/data/verbnet-action-roles.tsv")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("auxiliary/data/framenet-role-capabilities.json"),
    )
    parser.add_argument("--limit", type=int, default=32)
    arguments = parser.parse_args()
    if not 20 <= arguments.limit <= 50:
        raise SystemExit("--limit must be between 20 and 50")

    actions = {row["action_id"]: row for row in rows(arguments.actions)}
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for role in rows(arguments.roles):
        if (
            role["mapping_status"] != "compiled"
            or role["hole_role"] not in {"SubjectHole", "ObjectHole"}
            or role["requirement"] in {"", "null"}
        ):
            continue
        action = actions.get(role["action_id"])
        if not action:
            continue
        frames = [
            frame
            for frame in json.loads(action["framenet_frames_json"])
            if frame and frame != "None"
        ]
        for frame in frames:
            grouped[(frame, role["hole_role"], role["requirement"])].append(
                {**role, "action_provenance": action["provenance"]}
            )

    ranked = sorted(
        grouped.items(),
        key=lambda item: (
            -len(item[1]),
            item[0][0],
            item[0][1],
            item[0][2],
        ),
    )[: arguments.limit]
    projections = []
    for (frame, hole, requirement), evidence in ranked:
        source_ids = sorted({row["action_id"] for row in evidence})
        digest = hashlib.sha256(
            "\n".join(source_ids).encode()
        ).hexdigest()[:16]
        projections.append(
            {
                "frame": frame,
                "hole_role": hole,
                "candidate_requirement": requirement,
                "strength": "SelectionalPreference",
                "mode": "role-compatibility",
                "evidence_count": len(evidence),
                "action_senses": len(source_ids),
                "example_lemmas": sorted(
                    {row["lemma"] for row in evidence}
                )[:12],
                "provenance": (
                    f"SemLink:VerbNet-3.4×FrameNet-1.7:"
                    f"{frame}:{hole}:{digest}"
                ),
            }
        )
    result = {
        "schema_version": SCHEMA,
        "selection_policy": (
            "top projections by executable Action×Role evidence count; "
            "deterministic lexical tie-break"
        ),
        "strength_policy": (
            "all imported projections remain SelectionalPreference"
        ),
        "projection_count": len(projections),
        "projections": projections,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema_version": SCHEMA,
                "projection_count": len(projections),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
