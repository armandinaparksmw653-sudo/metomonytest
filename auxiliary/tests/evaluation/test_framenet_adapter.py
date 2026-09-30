import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "auxiliary/tests/evaluation/fixtures/framenet"


def jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


class FrameNetAdapterTests(unittest.TestCase):
    def test_imports_frames_fes_lus_and_valence_patterns_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            command = [
                "python3",
                str(ROOT / "auxiliary/scripts/import_framenet_context.py"),
                "--framenet-dir",
                str(FIXTURE),
            ]
            subprocess.run(command + ["--output", str(first)], check=True)
            subprocess.run(command + ["--output", str(second)], check=True)

            self.assertEqual(
                (first / "manifest.json").read_bytes(),
                (second / "manifest.json").read_bytes(),
            )
            manifest = json.loads((first / "manifest.json").read_text())
            self.assertEqual(manifest["frames"], 1)
            self.assertEqual(manifest["frame_elements"], 3)
            self.assertEqual(manifest["lexical_units"], 1)
            self.assertEqual(manifest["valence_patterns"], 1)
            self.assertFalse(manifest["redistributed"])

            frame = jsonl(first / "frames.jsonl")[0]
            self.assertEqual(frame["name"], "Statement")
            self.assertEqual(
                [element["name"] for element in frame["frame_elements"]],
                ["Message", "Speaker", "Topic"],
            )
            lexical_unit = jsonl(first / "lexical-units.jsonl")[0]
            self.assertEqual(lexical_unit["name"], "declare.v")
            pattern = jsonl(first / "valence-patterns.jsonl")[0]
            self.assertEqual(pattern["frame"], "Statement")
            self.assertEqual(
                {unit["fe"] for unit in pattern["units"]},
                {"Speaker", "Message"},
            )

    def test_generates_bounded_preference_only_frame_capabilities(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capabilities.json"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "auxiliary/scripts/generate_framenet_capabilities.py"),
                    "--output",
                    str(output),
                    "--limit",
                    "32",
                ],
                check=True,
                cwd=ROOT,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["projection_count"], 32)
            self.assertEqual(len(result["projections"]), 32)
            self.assertTrue(
                all(
                    projection["strength"] == "SelectionalPreference"
                    for projection in result["projections"]
                )
            )
            self.assertTrue(
                all(projection["evidence_count"] > 0 for projection in result["projections"])
            )

    def test_imported_snapshot_drives_proposer_frames_and_valence(self):
        with tempfile.TemporaryDirectory() as directory:
            imported = Path(directory) / "framenet"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "auxiliary/scripts/import_framenet_context.py"),
                    "--framenet-dir",
                    str(FIXTURE),
                    "--output",
                    str(imported),
                ],
                check=True,
            )
            completed = subprocess.run(
                [
                    "python3",
                    str(ROOT / "auxiliary/scripts/propose_contextual_scenario.py"),
                    "--snapshot",
                    str(ROOT / "auxiliary/data/wikidata-openalex-snapshot"),
                    "--sentence",
                    "Waterloo declared a program",
                    "--source",
                    "Waterloo",
                    "--framenet-snapshot",
                    str(imported),
                ],
                check=True,
                text=True,
                capture_output=True,
                cwd=ROOT,
            )
            proposal = json.loads(completed.stdout)
            self.assertEqual(
                {frame["frame"] for frame in proposal["frames"]},
                {"Statement"},
            )
            self.assertEqual(len(proposal["framenet_valence_patterns"]), 1)
            self.assertIn(
                "snapshot:",
                proposal["frames"][0]["provenance"],
            )


if __name__ == "__main__":
    unittest.main()
