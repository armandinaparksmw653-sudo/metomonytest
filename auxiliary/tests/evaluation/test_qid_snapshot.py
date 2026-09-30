import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXTRACTOR = ROOT / "auxiliary/scripts" / "extract_wikidata_snapshot.py"
RUNTIME_INDEX = ROOT / "auxiliary/scripts" / "build_wikidata_runtime_index.py"
DUMP = ROOT / "auxiliary" / "evaluation" / "qid-fiber" / "waterloo-mini-dump.jsonl"
SEEDS = ROOT / "auxiliary" / "evaluation" / "qid-fiber" / "source-seeds.tsv"
RULES = ROOT / "auxiliary" / "evaluation" / "qid-fiber" / "rules.json"


class QidSnapshotTests(unittest.TestCase):
    def test_committed_wordnet_projection_has_expected_lexemes(self):
        rules = json.loads(
            (ROOT / "auxiliary/data/wordnet-context-rules.json").read_text(encoding="utf-8")
        )
        self.assertIn("Readable", rules["lexical_sorts"]["book"]["requirement"])
        self.assertIn("Clothing", rules["lexical_sorts"]["clothing"]["requirement"])

    def test_openalex_enriched_snapshot_verifies(self):
        subprocess.run(
            [
                "python3",
                str(EXTRACTOR),
                "verify",
                "--snapshot",
                str(ROOT / "auxiliary/data/wikidata-openalex-snapshot"),
            ],
            check=True,
        )

    def test_fixture_extraction_is_deterministic(self):
        digest = hashlib.sha256(DUMP.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            permuted_dump = Path(directory) / "permuted.jsonl"
            permuted_dump.write_text(
                "".join(reversed(DUMP.read_text(encoding="utf-8").splitlines(keepends=True))),
                encoding="utf-8",
            )
            command = [
                "python3",
                str(EXTRACTOR),
                "extract",
                "--dump",
                str(DUMP),
                "--expected-sha256",
                digest,
                "--allowlist",
                str(SEEDS),
                "--rules",
                str(RULES),
            ]
            subprocess.run(command + ["--output", str(first)], check=True)
            permuted_command = command.copy()
            permuted_command[permuted_command.index(str(DUMP))] = str(permuted_dump)
            permuted_command[permuted_command.index(digest)] = hashlib.sha256(
                permuted_dump.read_bytes()
            ).hexdigest()
            subprocess.run(permuted_command + ["--output", str(second)], check=True)
            self.assertEqual(
                sorted(path.relative_to(first) for path in first.iterdir()),
                sorted(path.relative_to(second) for path in second.iterdir()),
            )
            for path in first.iterdir():
                if path.name != "manifest.json":
                    self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
            self.assertEqual(
                json.loads((first / "manifest.json").read_text())["graph_sha256"],
                json.loads((second / "manifest.json").read_text())["graph_sha256"],
            )
            subprocess.run(
                ["python3", str(EXTRACTOR), "verify", "--snapshot", str(first)],
                check=True,
            )

    def test_wrong_dump_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "extract",
                    "--dump",
                    str(DUMP),
                    "--expected-sha256",
                    "0" * 64,
                    "--allowlist",
                    str(SEEDS),
                    "--output",
                    directory,
                ],
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dump SHA-256 mismatch", result.stderr)

    def test_offline_index_materializes_a_finite_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "runtime.sqlite"
            snapshot = Path(directory) / "snapshot"
            subprocess.run(
                ["python3", str(RUNTIME_INDEX), "build", "--dump", str(DUMP), "--database", str(database)],
                check=True,
            )
            subprocess.run(
                [
                    "python3", str(RUNTIME_INDEX), "materialize",
                    "--database", str(database), "--source-qid", "Q639408",
                    "--depth", "1", "--rules", str(RULES), "--output", str(snapshot),
                ],
                check=True,
            )
            subprocess.run(
                ["python3", str(EXTRACTOR), "verify", "--snapshot", str(snapshot)],
                check=True,
            )

    def test_offline_index_resolves_exact_aliases_and_builds_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "runtime.sqlite"
            linker_input = Path(directory) / "inputs.jsonl"
            linker_output = Path(directory) / "linker.json"
            subprocess.run(
                [
                    "python3",
                    str(RUNTIME_INDEX),
                    "build",
                    "--dump",
                    str(DUMP),
                    "--database",
                    str(database),
                ],
                check=True,
            )
            lookup = subprocess.run(
                [
                    "python3",
                    str(RUNTIME_INDEX),
                    "lookup",
                    "--database",
                    str(database),
                    "--alias",
                    "Waterloo",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertEqual(
                json.loads(lookup.stdout)["matches"][0]["id"], "Q639408"
            )
            linker_input.write_text(
                json.dumps({"source": "Waterloo", "target": "physics"}) + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "auxiliary/scripts/build_wikidata_linker_cache.py"),
                    "--database",
                    str(database),
                    "--inputs",
                    str(linker_input),
                    "--output",
                    str(linker_output),
                ],
                check=True,
            )
            cache = json.loads(linker_output.read_text(encoding="utf-8"))
            self.assertGreaterEqual(cache["counts"]["resolved"], 1)
            self.assertEqual(
                next(
                    row["id"]
                    for row in cache["resolved"]
                    if row["surface"] == "Waterloo"
                ),
                "Q639408",
            )

    def test_runtime_rules_materialize_extended_projected_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "runtime.sqlite"
            snapshot = Path(directory) / "snapshot"
            subprocess.run(
                [
                    "python3",
                    str(RUNTIME_INDEX),
                    "build",
                    "--dump",
                    str(DUMP),
                    "--database",
                    str(database),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "python3",
                    str(RUNTIME_INDEX),
                    "materialize",
                    "--database",
                    str(database),
                    "--source-qid",
                    "Q639408",
                    "--depth",
                    "1",
                    "--rules",
                    str(ROOT / "auxiliary/data/wikidata-runtime-rules.json"),
                    "--output",
                    str(snapshot),
                ],
                check=True,
            )
            manifest = json.loads((snapshot / "manifest.json").read_text())
            self.assertEqual(manifest["source"]["source_qids"], ["Q639408"])
            self.assertIn("index_sha256", manifest["source"])
            subprocess.run(
                ["python3", str(EXTRACTOR), "verify", "--snapshot", str(snapshot)],
                check=True,
            )


if __name__ == "__main__":
    unittest.main()
