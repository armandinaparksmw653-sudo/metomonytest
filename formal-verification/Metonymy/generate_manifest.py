#!/usr/bin/env python3
"""Generate or verify the deterministic formal artifact manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST = HERE / "ARTIFACT_MANIFEST.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    toolchain = json.loads((ROOT / "toolchain.lock.json").read_text(encoding="utf-8"))
    modules = {
        path.name: digest(path)
        for path in sorted(HERE.glob("*.agda"))
    }
    return {
        "schema_version": "metonymy-formal-artifact-1",
        "entrypoint": "Metonymy.PublicationTheorems",
        "agda_include": "formal-verification",
        "agda_version": toolchain["system_packages"]["agda-bin"],
        "cubical": toolchain["cubical"],
        "modules": modules,
        "module_count": len(modules),
        "theorem_index": "THEOREMS.md",
    }


def canonical(value: dict) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = canonical(build_manifest())
    if args.check:
        if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != generated:
            raise SystemExit("formal artifact manifest is stale")
        print("formal artifact manifest verified")
    else:
        MANIFEST.write_text(generated, encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
