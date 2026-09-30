#!/usr/bin/env python3
"""Build a deterministic broad entity-link cache from an offline runtime index.

Inputs are unlabelled inference rows: source/target spans or any application
text fields. The cache is constructed from exact aliases in the frozen index;
it never reads a gold label or endpoint answer. Ambiguous aliases remain
ambiguous and are recorded rather than guessed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path


SCHEMA = "wikidata-linker-cache-1"


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def jsonl(path: Path):
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def metadata(connection: sqlite3.Connection, key: str) -> str:
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = ?", (key,)
    ).fetchone()
    if not row:
        raise ValueError(f"runtime index has no metadata key: {key}")
    return row[0]


def exact_matches(connection: sqlite3.Connection, alias: str, limit: int) -> list[dict]:
    return [
        {
            "id": qid,
            "label": label,
            "alias": stored_alias,
            "rank": rank,
        }
        for stored_alias, rank, qid, label in connection.execute(
            """
            SELECT aliases.alias, aliases.rank, aliases.qid, entities.label
            FROM aliases JOIN entities ON entities.qid = aliases.qid
            WHERE aliases.normalized = ?
            ORDER BY aliases.rank, aliases.qid
            LIMIT ?
            """,
            (normalized(alias), limit),
        )
    ]


def extract_surfaces(row: dict, fields: list[str]) -> list[str]:
    values = []
    for field in fields:
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--fields",
        default="source,target",
        help="comma-separated string fields extracted from each unlabelled row",
    )
    parser.add_argument("--limit", type=int, default=20)
    arguments = parser.parse_args()
    fields = [field for field in arguments.fields.split(",") if field]
    rows = list(jsonl(arguments.inputs))
    surfaces = sorted(
        {
            surface
            for row in rows
            for surface in extract_surfaces(row, fields)
        },
        key=normalized,
    )
    connection = sqlite3.connect(arguments.database)
    index_sha256 = metadata(connection, "source_sha256")
    resolved, ambiguous, unresolved = [], [], []
    for surface in surfaces:
        matches = exact_matches(connection, surface, arguments.limit)
        qids = {match["id"] for match in matches}
        record = {"surface": surface, "normalized": normalized(surface)}
        if len(qids) == 1:
            match = matches[0]
            resolved.append(
                {
                    **record,
                    "id": match["id"],
                    "label": match["label"],
                    "match": "exact-label" if match["rank"] == 0 else "exact-alias",
                    "provenance": (
                        f"wikidata-runtime-index:{index_sha256}:"
                        f"{match['match'] if 'match' in match else 'exact'}"
                    ),
                }
            )
        elif matches:
            ambiguous.append({**record, "candidates": matches})
        else:
            unresolved.append(record)
    connection.close()
    payload = {
        "schema_version": SCHEMA,
        "index_sha256": index_sha256,
        "input_sha256": hashlib.sha256(arguments.inputs.read_bytes()).hexdigest(),
        "fields": fields,
        "match_policy": "exact normalized label/alias only; ambiguity abstains",
        "resolved": sorted(resolved, key=lambda row: row["normalized"]),
        "ambiguous": sorted(ambiguous, key=lambda row: row["normalized"]),
        "unresolved": sorted(unresolved, key=lambda row: row["normalized"]),
        "counts": {
            "surfaces": len(surfaces),
            "resolved": len(resolved),
            "ambiguous": len(ambiguous),
            "unresolved": len(unresolved),
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
