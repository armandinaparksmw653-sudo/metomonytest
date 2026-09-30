#!/usr/bin/env python3
"""Import FrameNet XML frames, FEs, lexical units, and valence patterns.

The FrameNet distribution is user-supplied because its download requires
accepting the upstream terms. Output is deterministic JSONL plus a manifest
that binds every projection to the exact XML tree hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET


SCHEMA = "framenet-context-1"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def children(element: ET.Element, name: str):
    return [child for child in element if local_name(child.tag) == name]


def descendants(element: ET.Element, name: str):
    return [child for child in element.iter() if local_name(child.tag) == name]


def source_digest(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix().encode()
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def parse_frame(path: Path, release: str) -> dict:
    root = ET.parse(path).getroot()
    frame_name = root.attrib["name"]
    frame_id = root.attrib["ID"]
    definition = next(
        (text(node) for node in children(root, "definition")),
        "",
    )
    frame_elements = []
    for element in children(root, "FE"):
        frame_elements.append(
            {
                "id": element.attrib.get("ID", ""),
                "name": element.attrib["name"],
                "abbrev": element.attrib.get("abbrev", ""),
                "core_type": element.attrib.get("coreType", ""),
                "semantic_type": element.attrib.get("semType", ""),
                "definition": next(
                    (text(node) for node in children(element, "definition")),
                    "",
                ),
            }
        )
    relations = []
    for relation in descendants(root, "frameRelation"):
        relations.append(
            {
                key: relation.attrib[key]
                for key in sorted(relation.attrib)
                if key
                in {
                    "type",
                    "superFrameName",
                    "subFrameName",
                    "relatedFrame",
                }
            }
        )
    return {
        "id": frame_id,
        "name": frame_name,
        "definition": definition,
        "frame_elements": sorted(
            frame_elements, key=lambda item: (item["name"], item["id"])
        ),
        "relations": sorted(
            relations,
            key=lambda item: json.dumps(item, sort_keys=True),
        ),
        "provenance": f"FrameNet-{release}:frame:{frame_id}",
    }


def annotation_valence_patterns(root: ET.Element) -> Counter[tuple]:
    patterns: Counter[tuple] = Counter()
    for annotation in descendants(root, "annotationSet"):
        layers = {
            layer.attrib.get("name"): layer
            for layer in children(annotation, "layer")
        }
        units: dict[tuple[str, str], dict[str, str]] = {}
        for layer_name in ("FE", "GF", "PT"):
            layer = layers.get(layer_name)
            if layer is None:
                continue
            for label in children(layer, "label"):
                if "start" not in label.attrib or "end" not in label.attrib:
                    continue
                span = (label.attrib["start"], label.attrib["end"])
                units.setdefault(span, {})[layer_name.lower()] = label.attrib.get(
                    "name", ""
                )
        normalized = tuple(
            tuple(sorted(unit.items()))
            for _, unit in sorted(units.items())
            if unit.get("fe")
        )
        if normalized:
            patterns[normalized] += 1
    return patterns


def explicit_valence_patterns(root: ET.Element) -> Counter[tuple]:
    patterns: Counter[tuple] = Counter()
    for pattern in descendants(root, "pattern"):
        units = []
        for unit in descendants(pattern, "valenceUnit"):
            normalized = tuple(
                sorted(
                    (key.casefold(), value)
                    for key, value in unit.attrib.items()
                    if key in {"FE", "GF", "PT"}
                )
            )
            if normalized:
                units.append(normalized)
        if units:
            count = int(pattern.attrib.get("total", "1") or "1")
            patterns[tuple(sorted(units))] += count
    return patterns


def parse_lexical_unit(path: Path, release: str) -> tuple[dict, list[dict]]:
    root = ET.parse(path).getroot()
    lu_id = root.attrib["ID"]
    frame_id = root.attrib.get("frameID", "")
    frame_name = root.attrib.get("frame", "")
    lexical_unit = {
        "id": lu_id,
        "name": root.attrib["name"],
        "pos": root.attrib.get("POS", ""),
        "frame_id": frame_id,
        "frame": frame_name,
        "status": root.attrib.get("status", ""),
        "definition": next(
            (text(node) for node in children(root, "definition")),
            "",
        ),
        "lexemes": sorted(
            [
                {
                    key: lexeme.attrib[key]
                    for key in sorted(lexeme.attrib)
                    if key in {"name", "POS", "breakBefore", "headword"}
                }
                for lexeme in children(root, "lexeme")
            ],
            key=lambda item: json.dumps(item, sort_keys=True),
        ),
        "provenance": f"FrameNet-{release}:lu:{lu_id}",
    }
    patterns = explicit_valence_patterns(root)
    if not patterns:
        patterns = annotation_valence_patterns(root)
    rendered = [
        {
            "lexical_unit_id": lu_id,
            "lexical_unit": lexical_unit["name"],
            "frame_id": frame_id,
            "frame": frame_name,
            "units": [dict(unit) for unit in units],
            "count": count,
            "provenance": f"FrameNet-{release}:lu:{lu_id}:valence",
        }
        for units, count in sorted(patterns.items())
    ]
    return lexical_unit, rendered


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framenet-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--release", default="1.7")
    arguments = parser.parse_args()
    root = arguments.framenet_dir
    frame_paths = sorted((root / "frame").glob("*.xml"))
    lu_paths = sorted((root / "lu").glob("*.xml"))
    if not frame_paths or not lu_paths:
        raise SystemExit("FrameNet frame/ and lu/ XML directories are required")

    frames = [parse_frame(path, arguments.release) for path in frame_paths]
    lexical_units, valence_patterns = [], []
    for path in lu_paths:
        lexical_unit, patterns = parse_lexical_unit(path, arguments.release)
        lexical_units.append(lexical_unit)
        valence_patterns.extend(patterns)
    output = arguments.output
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "frames.jsonl", sorted(frames, key=lambda row: row["id"]))
    write_jsonl(
        output / "lexical-units.jsonl",
        sorted(lexical_units, key=lambda row: row["id"]),
    )
    write_jsonl(
        output / "valence-patterns.jsonl",
        sorted(
            valence_patterns,
            key=lambda row: (
                row["lexical_unit_id"],
                json.dumps(row["units"], sort_keys=True),
            ),
        ),
    )
    paths = frame_paths + lu_paths
    manifest = {
        "schema_version": SCHEMA,
        "release": arguments.release,
        "source_sha256": source_digest(paths, root),
        "frames": len(frames),
        "frame_elements": sum(len(row["frame_elements"]) for row in frames),
        "lexical_units": len(lexical_units),
        "valence_patterns": len(valence_patterns),
        "redistributed": False,
        "source_policy": (
            "FrameNet XML is user-supplied and is not committed by this project"
        ),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
