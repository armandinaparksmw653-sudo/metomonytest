#!/usr/bin/env python3
"""Build an offline indexed Wikidata runtime and materialize finite snapshots."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import sqlite3
from collections import deque
from pathlib import Path
from typing import Iterator

PROPERTIES = (
    "P31", "P279", "P131", "P159", "P276", "P361", "P463",
    "P527", "P50", "P101", "P921", "P176", "P749", "P137",
    "P112", "P355", "P740", "P17",
)


def open_dump(path: Path):
    return bz2.open(path, "rt", encoding="utf-8") if path.suffix == ".bz2" else path.open(
        "rt", encoding="utf-8"
    )


def records(path: Path) -> Iterator[dict]:
    with open_dump(path) as source:
        first = source.read(1)
        while first and first.isspace():
            first = source.read(1)
        if first != "[":
            line = first + source.readline()
            if line.strip():
                yield json.loads(line)
            for line in source:
                if line.strip():
                    yield json.loads(line)
            return
        decoder, buffer = json.JSONDecoder(), ""
        while True:
            chunk = source.read(1024 * 1024)
            buffer += chunk
            while True:
                buffer = buffer.lstrip(" \t\r\n,")
                if buffer.startswith("]"):
                    return
                try:
                    value, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break
                yield value
                buffer = buffer[end:]
            if not chunk:
                raise ValueError("unterminated dump array")


def targets(record: dict, property_id: str) -> Iterator[str]:
    for statement in record.get("claims", {}).get(property_id, []):
        if statement.get("rank") == "deprecated":
            continue
        value = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        target = value.get("id") if isinstance(value, dict) else None
        if isinstance(target, str) and target.startswith("Q"):
            yield target


def aliases(record: dict, languages: set[str]) -> Iterator[tuple[str, int]]:
    labels = record.get("labels", {})
    alias_map = record.get("aliases", {})
    for language, value in labels.items() if isinstance(labels, dict) else []:
        if isinstance(value, dict) and isinstance(value.get("value"), str):
            if language in languages:
                yield value["value"], 0
    for language, values in alias_map.items() if isinstance(alias_map, dict) else []:
        for value in values if isinstance(values, list) else []:
            if isinstance(value, dict) and isinstance(value.get("value"), str):
                if language in languages:
                    yield value["value"], 1


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def initialise(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA temp_store=MEMORY;
        CREATE TABLE entities (qid TEXT PRIMARY KEY, label TEXT NOT NULL);
        CREATE TABLE aliases (
          alias TEXT NOT NULL,
          normalized TEXT NOT NULL,
          qid TEXT NOT NULL,
          rank INTEGER NOT NULL
        );
        CREATE TABLE claims (property TEXT NOT NULL, source TEXT NOT NULL, target TEXT NOT NULL);
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX aliases_normalized_idx ON aliases(normalized);
        CREATE INDEX aliases_qid_idx ON aliases(qid);
        CREATE INDEX claims_source_idx ON claims(source, property);
        CREATE INDEX claims_target_idx ON claims(target, property);
        """
    )


def build(args: argparse.Namespace) -> None:
    database = Path(args.database)
    if args.commit_every <= 0:
        raise SystemExit("--commit-every must be positive")
    if database.exists():
        database.unlink()
    connection = sqlite3.connect(database)
    initialise(connection)
    dump = Path(args.dump)
    languages = set(args.languages.split(","))
    digest = hashlib.sha256()
    with dump.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    connection.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [
            ("schema_version", "wikidata-runtime-index-2"),
            ("source_sha256", digest.hexdigest()),
            ("source_size_bytes", str(dump.stat().st_size)),
            ("languages", ",".join(sorted(languages))),
            ("properties", ",".join(PROPERTIES)),
        ],
    )
    count = 0
    for record in records(Path(args.dump)):
        qid = record.get("id")
        if not isinstance(qid, str) or not qid.startswith("Q"):
            continue
        names = sorted(set(aliases(record, languages)), key=lambda item: (item[1], item[0].casefold()))
        label = next((name for name, rank in names if rank == 0), qid)
        connection.execute("INSERT INTO entities VALUES (?, ?)", (qid, label))
        connection.executemany(
            "INSERT INTO aliases VALUES (?, ?, ?, ?)",
            [(name, normalized(name), qid, rank) for name, rank in names],
        )
        connection.executemany(
            "INSERT INTO claims VALUES (?, ?, ?)",
            [
                (property_id, qid, target)
                for property_id in PROPERTIES
                for target in targets(record, property_id)
            ],
        )
        count += 1
        if count % args.commit_every == 0:
            connection.commit()
    connection.commit()
    connection.execute("VACUUM")
    connection.close()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def metadata(connection: sqlite3.Connection, key: str) -> str:
    row = connection.execute(
        "SELECT value FROM metadata WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        raise ValueError(f"runtime index has no metadata key: {key}")
    return row[0]


def lookup(args: argparse.Namespace) -> None:
    connection = sqlite3.connect(args.database)
    query = normalized(args.alias)
    matches = [
        {
            "id": qid,
            "label": label,
            "alias": alias,
            "match": "exact-label" if rank == 0 else "exact-alias",
        }
        for alias, rank, qid, label in connection.execute(
            """
            SELECT aliases.alias, aliases.rank, aliases.qid, entities.label
            FROM aliases JOIN entities ON entities.qid = aliases.qid
            WHERE aliases.normalized = ?
            ORDER BY aliases.rank, aliases.qid
            LIMIT ?
            """,
            (query, args.limit),
        )
    ]
    connection.close()
    print(
        json.dumps(
            {
                "query": args.alias,
                "normalized": query,
                "matches": matches,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def materialize(args: argparse.Namespace) -> None:
    sources = sorted(set(args.source_qid))
    allowed = tuple(args.properties.split(","))
    connection = sqlite3.connect(args.database)
    missing = [
        source
        for source in sources
        if connection.execute(
            "SELECT 1 FROM entities WHERE qid = ?", (source,)
        ).fetchone()
        is None
    ]
    if missing:
        raise SystemExit("source QIDs absent from runtime index: " + ",".join(missing))
    visited, queue = set(sources), deque((source, 0) for source in sources)
    claims = set()
    while queue and len(visited) < args.max_entities:
        current, depth = queue.popleft()
        if depth >= args.depth:
            continue
        placeholders = ",".join("?" for _ in allowed)
        for property_id, left, right in connection.execute(
            f"SELECT property, source, target FROM claims WHERE source = ? AND property IN ({placeholders}) "
            f"UNION SELECT property, source, target FROM claims WHERE target = ? AND property IN ({placeholders})",
            (current, *allowed, current, *allowed),
        ):
            claims.add((property_id, left, right))
            other = right if left == current else left
            if other not in visited and len(visited) < args.max_entities:
                visited.add(other)
                queue.append((other, depth + 1))
    entities = [
        {"id": qid, "labels": [label]}
        for qid, label in connection.execute(
            f"SELECT qid, label FROM entities WHERE qid IN ({','.join('?' for _ in visited)}) ORDER BY qid",
            tuple(sorted(visited)),
        )
    ]
    aliases_rows = [
        {"alias": alias, "id": qid}
        for alias, qid in connection.execute(
            f"SELECT alias, qid FROM aliases WHERE qid IN ({','.join('?' for _ in visited)}) ORDER BY normalized, rank, qid",
            tuple(sorted(visited)),
        )
    ]
    index_sha256 = metadata(connection, "source_sha256")
    connection.close()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    payloads = {
        "entities.jsonl": entities,
        "aliases.jsonl": aliases_rows,
        "claims.jsonl": [
            {"property": property_id, "source": left, "target": right}
            for property_id, left, right in sorted(claims)
        ],
    }
    graph = hashlib.sha256()
    for name, rows in payloads.items():
        rendered = "".join(canonical(row) for row in rows)
        (output / name).write_text(rendered, encoding="utf-8", newline="\n")
        graph.update(name.encode() + b"\0" + rendered.encode())
    rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    rendered_rules = canonical(rules)
    (output / "rules.json").write_text(rendered_rules, encoding="utf-8", newline="\n")
    graph.update(b"rules.json\0" + rendered_rules.encode())
    manifest = {
        "schema_version": "wikidata-qid-snapshot-1",
        "source": {
            "kind": "offline-runtime-index",
            "source_qids": sources,
            "index_sha256": index_sha256,
        },
        "runtime_index": {
            "depth": args.depth,
            "max_entities": args.max_entities,
            "properties": list(allowed),
        },
        "graph_sha256": graph.hexdigest(),
    }
    (output / "manifest.json").write_text(canonical(manifest), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)
    build_parser = commands.add_parser("build")
    build_parser.add_argument("--dump", required=True)
    build_parser.add_argument("--database", required=True)
    build_parser.add_argument("--languages", default="en")
    build_parser.add_argument("--commit-every", type=int, default=10000)
    build_parser.set_defaults(handler=build)
    materialize_parser = commands.add_parser("materialize")
    materialize_parser.add_argument("--database", required=True)
    materialize_parser.add_argument("--source-qid", action="append", required=True)
    materialize_parser.add_argument("--properties", default=",".join(PROPERTIES))
    materialize_parser.add_argument("--depth", type=int, default=2)
    materialize_parser.add_argument("--max-entities", type=int, default=50000)
    materialize_parser.add_argument("--rules", required=True)
    materialize_parser.add_argument("--output", required=True)
    materialize_parser.set_defaults(handler=materialize)
    lookup_parser = commands.add_parser("lookup")
    lookup_parser.add_argument("--database", required=True)
    lookup_parser.add_argument("--alias", required=True)
    lookup_parser.add_argument("--limit", type=int, default=20)
    lookup_parser.set_defaults(handler=lookup)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
