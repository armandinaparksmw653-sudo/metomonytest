"""Unit tests for run_contextual_corpus.py's run_one line-scanning.

Only the new "tree-source=" parsing is covered here -- the rest of
run_one's line-scan (gf-tree=/graph_sha256=/stage=/survivors=/...) has
no prior dedicated test file at all (confirmed before adding this one);
scoping this file to the new field keeps it focused rather than
retroactively covering everything else in the same commit.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "evaluation"))

import run_contextual_corpus  # noqa: E402


def completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["python3", "scripts/run_automatic_contextual_pipeline.py"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


class RunOneTreeSourceTests(unittest.TestCase):
    def test_records_stanza_tree_source(self) -> None:
        stdout = (
            "gf-tree=Pred (OpenPN \"Waterloo\") (Compl Announce (OpenPN \"Henry\"))\n"
            "tree-source=stanza\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["tree_source"], "stanza")

    def test_records_gf_parser_tree_source(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=gf-parser\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["tree_source"], "gf-parser")

    def test_no_tree_source_line_means_no_field_at_all(self) -> None:
        # exit1/exit2 rows never reach tree-building, so no
        # "tree-source=" line is ever printed for them -- confirms the
        # field is absent (not defaulted to some placeholder), matching
        # row_tree_source's own "not-applicable" fallback in
        # score_contextual_detection.py.
        with patch(
            "subprocess.run",
            return_value=completed("", returncode=2),
        ):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertNotIn("tree_source", result)

    def test_records_decline_reason(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=gf-parser\n"
            "decline-reason=passive-agent-count\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["decline_reason"], "passive-agent-count")

    def test_records_an_empty_decline_reason_when_stanza_was_trusted(self) -> None:
        stdout = (
            "gf-tree=Pred (OpenPN \"Waterloo\") (Compl Announce (OpenPN \"Henry\"))\n"
            "tree-source=stanza\n"
            "decline-reason=\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["decline_reason"], "")

    def test_records_dep_status(self) -> None:
        stdout = (
            "gf-tree=Pred (OpenPN \"Waterloo\") (Compl Announce (OpenPN \"Henry\"))\n"
            "tree-source=stanza\n"
            "decline-reason=\n"
            "dep-status=direct-argument\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["dep_status"], "direct-argument")

    def test_no_dep_status_line_means_no_field_at_all(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=gf-parser\n"
            "decline-reason=no-ud-words\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertNotIn("dep_status", result)

    def test_records_all_decline_reasons(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=gf-parser\n"
            "decline-reason=common-noun-determiner-or-adjective-count\n"
            "all-decline-reasons=common-noun-determiner-or-adjective-count,nmod-preposition-unrecognized\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(
            result["all_decline_reasons"],
            ["common-noun-determiner-or-adjective-count", "nmod-preposition-unrecognized"],
        )

    def test_empty_all_decline_reasons_line_means_an_empty_list(self) -> None:
        stdout = (
            "gf-tree=Pred (OpenPN \"Waterloo\") (Compl Announce (OpenPN \"Henry\"))\n"
            "tree-source=stanza\n"
            "decline-reason=\n"
            "all-decline-reasons=\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["all_decline_reasons"], [])

    def test_no_all_decline_reasons_line_means_no_field_at_all(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=gf-parser\n"
            "decline-reason=no-ud-words\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertNotIn("all_decline_reasons", result)

    def test_records_llm_decline_reason(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=gf-parser\n"
            "decline-reason=no-ud-words\n"
            "llm-decline-reason=no-response\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertEqual(result["llm_decline_reason"], "no-response")

    def test_no_llm_decline_reason_line_means_no_field_at_all(self) -> None:
        stdout = (
            "gf-tree=DummyTree\n"
            "tree-source=stanza\n"
            "decline-reason=\n"
            "stage=0 constraint=graph-related\n"
            "  survivors=[Q1]\n"
        )
        with patch("subprocess.run", return_value=completed(stdout)):
            result = run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        self.assertNotIn("llm_decline_reason", result)


class RunOneLlmProposerFlagTests(unittest.TestCase):
    def test_llm_proposer_model_is_passed_through_to_the_subprocess_command(self) -> None:
        with patch("subprocess.run", return_value=completed("")) as mock_run:
            run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
                "llama3.2:3b-instruct",
                None,
            )
        command = mock_run.call_args[0][0]
        self.assertIn("--llm-proposer-model", command)
        self.assertEqual(
            command[command.index("--llm-proposer-model") + 1], "llama3.2:3b-instruct"
        )
        self.assertNotIn("--llm-proposer-endpoint", command)

    def test_llm_proposer_endpoint_is_passed_through_only_alongside_the_model(self) -> None:
        with patch("subprocess.run", return_value=completed("")) as mock_run:
            run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
                "llama3.2:3b-instruct",
                "http://localhost:11434/api/generate",
            )
        command = mock_run.call_args[0][0]
        self.assertIn("--llm-proposer-endpoint", command)
        self.assertEqual(
            command[command.index("--llm-proposer-endpoint") + 1],
            "http://localhost:11434/api/generate",
        )

    def test_no_llm_proposer_model_means_neither_flag_is_passed(self) -> None:
        with patch("subprocess.run", return_value=completed("")) as mock_run:
            run_contextual_corpus.run_one(
                Path("build/metonymy"),
                Path("data/wikidata-openalex-snapshot"),
                "full",
                {"id": "a", "sentence": "Waterloo announces Henry", "source": "Waterloo", "family": "x"},
                None,
            )
        command = mock_run.call_args[0][0]
        self.assertNotIn("--llm-proposer-model", command)
        self.assertNotIn("--llm-proposer-endpoint", command)


if __name__ == "__main__":
    unittest.main()
