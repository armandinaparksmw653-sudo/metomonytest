#!/usr/bin/env python3
"""Create and verify deterministic, finite QID snapshots from local dumps."""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
from itertools import chain
from pathlib import Path
from typing import Iterable, Iterator

SCHEMA = "wikidata-qid-snapshot-1"
VERSION = "qid-extractor-1"
PROPERTIES = {
    "P31", "P279", "P131", "P749", "P361", "P463", "P527",
    "P101", "P921", "P176", "P50", "P159"
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def open_dump(path: Path):
    return bz2.open(path, "rt", encoding="utf-8") if path.suffix == ".bz2" else path.open(
        "rt", encoding="utf-8"
    )


def records(path: Path) -> Iterator[dict]:
    """Decode JSONL or a top-level JSON array without network access."""
    with open_dump(path) as source:
        first = source.read(1)
        while first and first.isspace():
            first = source.read(1)
        if first != "[":
            first_line = first + source.readline()
            for line in chain([first_line], source):
                if line.strip():
                    yield json.loads(line)
            return
        decoder = json.JSONDecoder()
        buffer = ""
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk and not buffer.strip():
                return
            buffer += chunk
            while True:
                buffer = buffer.lstrip(" \t\r\n,")
                if buffer.startswith("]"):
                    return
                try:
                    value, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    if not chunk:
                        raise
                    break
                if not isinstance(value, dict):
                    raise ValueError("Wikidata top-level entries must be objects")
                yield value
                buffer = buffer[end:]
            if not chunk:
                raise ValueError("unterminated JSON array")


def entity_id(record: dict) -> str | None:
    return record.get("id") if isinstance(record.get("id"), str) else None


def targets(claims: dict, property_id: str) -> Iterable[str]:
    for statement in claims.get(property_id, []):
        if statement.get("rank") == "deprecated":
            continue
        value = (
            statement.get("mainsnak", {})
            .get("datavalue", {})
            .get("value", {})
        )
        target = value.get("id") if isinstance(value, dict) else None
        if isinstance(target, str) and target.startswith("Q"):
            yield target


def label_values(record: dict) -> list[str]:
    labels = record.get("labels", {})
    aliases = record.get("aliases", {})
    values = set()
    for item in labels.values() if isinstance(labels, dict) else []:
        if isinstance(item, dict) and isinstance(item.get("value"), str):
            values.add(item["value"])
    for entries in aliases.values() if isinstance(aliases, dict) else []:
        for item in entries if isinstance(entries, list) else []:
            if isinstance(item, dict) and isinstance(item.get("value"), str):
                values.add(item["value"])
    return sorted(values, key=lambda value: value.casefold())


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def extract(args: argparse.Namespace) -> None:
    dump = Path(args.dump)
    if sha256(dump) != args.expected_sha256:
        raise SystemExit("dump SHA-256 mismatch")
    allowlist = (
        {
            line.strip()
            for line in Path(args.allowlist).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        if args.allowlist
        else None
    )
    selected = [
        record
        for record in records(dump)
        if allowlist is None or entity_id(record) in allowlist
    ]
    selected.sort(key=lambda record: entity_id(record) or "")
    entities, aliases, claims = [], [], []
    for record in selected:
        qid = entity_id(record)
        assert qid is not None
        labels = label_values(record)
        entities.append({"id": qid, "labels": labels})
        aliases.extend({"alias": alias, "id": qid} for alias in labels)
        raw_claims = record.get("claims", {})
        for property_id in sorted(PROPERTIES):
            for target in sorted(targets(raw_claims, property_id)):
                claims.append({"property": property_id, "source": qid, "target": target})
    aliases.sort(key=lambda value: (value["alias"].casefold(), value["id"]))
    claims.sort(key=lambda value: (value["property"], value["source"], value["target"]))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    rules = json.loads(Path(args.rules).read_text(encoding="utf-8")) if args.rules else {"relations": []}
    payloads = {
        "entities.jsonl": entities,
        "aliases.jsonl": aliases,
        "claims.jsonl": claims,
        "rules.json": rules,
    }
    graph = hashlib.sha256()
    for name in ("entities.jsonl", "aliases.jsonl", "claims.jsonl", "rules.json"):
        rendered = (
            canonical(payloads[name])
            if name == "rules.json"
            else "".join(canonical(value) for value in payloads[name])
        )
        (output / name).write_text(rendered, encoding="utf-8", newline="\n")
        graph.update(name.encode("utf-8") + b"\0" + rendered.encode("utf-8"))
    manifest = {
        "schema_version": SCHEMA,
        "source": {
            "kind": "wikidata-json-dump",
            "compressed_sha256": args.expected_sha256,
            "size_bytes": dump.stat().st_size,
        },
        "extractor": {
            "version": VERSION,
            "config_sha256": sha256(Path(args.allowlist)) if args.allowlist else "all-entities",
        },
        "graph_sha256": graph.hexdigest(),
        "normalization": "nfkc-casefold-whitespace-v1",
        "license": {"spdx": "CC0-1.0"},
    }
    (output / "manifest.json").write_text(canonical(manifest), encoding="utf-8", newline="\n")


def verify(args: argparse.Namespace) -> None:
    snapshot = Path(args.snapshot)
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA:
        raise SystemExit("unsupported snapshot schema")
    graph = hashlib.sha256()
    names = ["entities.jsonl", "aliases.jsonl", "claims.jsonl", "rules.json"]
    if (snapshot / "evidence.jsonl").exists():
        names.append("evidence.jsonl")
    for name in names:
        contents = (snapshot / name).read_bytes()
        graph.update(name.encode("utf-8") + b"\0" + contents)
    if graph.hexdigest() != manifest.get("graph_sha256"):
        raise SystemExit("graph SHA-256 mismatch")
    print(manifest["graph_sha256"])


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)
    extract_parser = commands.add_parser("extract")
    extract_parser.add_argument("--dump", required=True)
    extract_parser.add_argument("--expected-sha256", required=True)
    extract_parser.add_argument("--allowlist")
    extract_parser.add_argument("--output", required=True)
    extract_parser.add_argument("--rules")
    extract_parser.set_defaults(handler=extract)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--snapshot", required=True)
    verify_parser.set_defaults(handler=verify)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
