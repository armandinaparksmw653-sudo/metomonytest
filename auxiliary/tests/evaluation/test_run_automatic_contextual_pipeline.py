"""Regression test for a real bug found via a live CI run: subprocess.run(...,
check=True) on the propose_contextual_scenario.py call silently discarded the
child's captured stdout/stderr when it failed. An uncaught CalledProcessError's
default traceback only prints "Command '...' returned non-zero exit status N"
-- never the child's own short, sentence-free error message (resolve_action's
target-occurrence-not-found/unsupported-action-role/nested-modifier-unsupported,
raised via `raise SystemExit(str(error))` and printed to *its own* stderr,
which capture_output=True redirects into an attribute nothing ever read).

This made every one of a real run's failures show up as
"failed:exit1:unrecognized" in score_contextual_detection.py's diagnostic --
technically correct (no sentence text leaked) but useless for telling apart
target-occurrence-not-found from unsupported-action-role from
nested-modifier-unsupported, exactly the distinction that diagnostic exists
to make. Fixed by checking the return code explicitly and printing the
child's combined output as a "detail" field, matching the same JSON-error
convention this script already uses for gf-parse-failed and
semantic-composition-failed.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

import run_automatic_contextual_pipeline  # noqa: E402


def failing_propose(returncode: int, stderr: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["python3", "scripts/propose_contextual_scenario.py"],
        returncode=returncode,
        stdout="",
        stderr=stderr,
    )


class ProposeScenarioFailureSurfacingTests(unittest.TestCase):
    def _run_main_with(self, completed: subprocess.CompletedProcess) -> str:
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Waterloo confabulates a treaty",
            "--source",
            "Waterloo",
        ]
        stdout = io.StringIO()
        with patch("subprocess.run", return_value=completed):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        self.assertEqual(raised.exception.code, 1)
        return stdout.getvalue()

    def test_the_childs_actual_error_message_is_surfaced_not_swallowed(self) -> None:
        printed = self._run_main_with(
            failing_propose(1, "unsupported-action-role\n")
        )
        payload = json.loads(printed)
        self.assertEqual(payload["status"], "propose-scenario-failed")
        self.assertIn("unsupported-action-role", payload["detail"])

    def test_distinguishes_each_known_resolve_action_error(self) -> None:
        for token in (
            "target-occurrence-not-found",
            "unsupported-action-role",
            "nested-modifier-unsupported",
        ):
            with self.subTest(token=token):
                printed = self._run_main_with(failing_propose(1, token + "\n"))
                payload = json.loads(printed)
                self.assertIn(token, payload["detail"])

    def test_zero_candidates_is_still_source_qid_unresolved(self) -> None:
        # The pre-existing "no candidate resolved at all" case (formerly
        # len(candidates) != 1, now len(candidates) == 0) must still exit 2
        # with the same status string, unaffected by the new multi-
        # candidate disambiguation loop below.
        ready_proposal = json.dumps(
            {
                "status": "ready",
                "source_surface": "Southern Cal",
                "source_qid_candidates": [],
            }
        )
        completed = subprocess.CompletedProcess(
            args=["python3", "scripts/propose_contextual_scenario.py"],
            returncode=0,
            stdout=ready_proposal,
            stderr="",
        )
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Southern Cal confabulates a treaty",
            "--source",
            "Southern Cal",
        ]
        stdout = io.StringIO()
        with patch("subprocess.run", return_value=completed):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        self.assertEqual(raised.exception.code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "source-qid-unresolved")

    def test_successful_propose_is_unaffected(self) -> None:
        # A returncode of 0 must still flow into the normal ready/not-ready
        # handling below, not the new failure branch.
        ready_proposal = json.dumps(
            {
                "status": "source-qid-unresolved",
                "source_surface": "Waterloo",
            }
        )
        completed = subprocess.CompletedProcess(
            args=["python3", "scripts/propose_contextual_scenario.py"],
            returncode=0,
            stdout=ready_proposal,
            stderr="",
        )
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Waterloo confabulates a treaty",
            "--source",
            "Waterloo",
        ]
        stdout = io.StringIO()
        with patch("subprocess.run", return_value=completed):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        # The *old* status-not-ready path (exit 2), not the new exit-1
        # propose-scenario-failed path.
        self.assertEqual(raised.exception.code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "source-qid-unresolved")


def propose_proposal(candidates: list[str]) -> subprocess.CompletedProcess:
    payload = {
        "status": "ready",
        "gf_sentence": "Liverpool announced a new programme",
        "action": "announce",
        "role": "SubjectHole",
        "max_depth": 1,
        "bridge_relations": ["InstitutionOf"],
        "constraints": [],
        "source_qid_candidates": candidates,
        "source_surface": "Liverpool",
    }
    return subprocess.CompletedProcess(
        args=["python3", "scripts/propose_contextual_scenario.py"],
        returncode=0,
        stdout=json.dumps(payload),
        stderr="",
    )


def gf_parse_result() -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["build/metonymy", "parse", "Liverpool announced a new programme"],
        returncode=0,
        # A single 0-arity, unparenthesized token is already a complete,
        # parseable GF tree (contextual_rule_compiler.parse_gf_tree) --
        # --ablation no-wordnet (used throughout this test class) makes
        # compile_gf_constraints return immediately after parsing it, so
        # its actual shape past being parseable is never inspected.
        stdout="DummyTree\n",
        stderr="",
    )


def engine_trace(final_survivors: list[str]) -> str:
    return "\n".join(
        [
            "graph_sha256=deadbeef",
            "source=Q0 action=announce role=SubjectHole",
            "stage=0 constraint=graph-related",
            "  survivors=[Q0]",
            "  agda-layer-check=true",
            "stage=1 constraint=Requires (HasSort Organization)@announce",
            "  survivors=[" + ",".join(final_survivors) + "]",
            "  agda-layer-check=true",
        ]
    ) + "\n"


def engine_result(
    returncode: int, stdout: str, stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["build/metonymy", "contextual-fiber", "..."],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def make_fake_run(candidates: list[str], engine_results_by_qid: dict):
    def fake_run(command, **kwargs):
        if command[0] == "python3":
            return propose_proposal(candidates)
        if command[1] == "parse":
            return gf_parse_result()
        # A per-candidate engine invocation: [engine, "contextual-fiber",
        # scenario_name, "--snapshot", ..., "--scenarios", ...] where
        # scenario_name is f"{qid.lower()}-{action}" (see run_engine in
        # run_automatic_contextual_pipeline.py).
        scenario_name = command[2]
        qid = scenario_name.split("-", 1)[0].upper()
        return engine_results_by_qid[qid]

    return fake_run


class SourceDisambiguationTests(unittest.TestCase):
    """The candidate list this class exercises is exactly the "Liverpool"
    situation found by locally reproducing the real contextual-tower-
    evaluation.yml sample: many exact-alias Wikidata matches for one
    surface, only some of which bridge to anything satisfying the
    sentence's own constraints once the tower's existing per-layer
    narrowing actually runs against each of them.
    """

    def _run_main(self, candidates: list[str], engine_results_by_qid: dict) -> tuple[str, int]:
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Liverpool announced a new programme",
            "--source",
            "Liverpool",
            "--ablation",
            "no-wordnet",
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("subprocess.run", side_effect=make_fake_run(candidates, engine_results_by_qid)):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        return stdout.getvalue() + stderr.getvalue(), raised.exception.code

    def test_exactly_one_surviving_candidate_is_the_answer(self) -> None:
        printed, code = self._run_main(
            ["Q24826", "Q2252369"],
            {
                "Q24826": engine_result(0, engine_trace(["Q145"])),
                "Q2252369": engine_result(0, engine_trace([])),
            },
        )
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        # No --dependency-hint flag at all in this class's own argv --
        # dep_status must default to "no-hint", distinct from any status
        # annotate_dependency_hints.py's classify_word itself produces.
        self.assertIn("dep-status=no-hint", printed)

    def test_zero_surviving_candidates_is_a_literal_prediction_not_a_failure(
        self,
    ) -> None:
        printed, code = self._run_main(
            ["Q24826", "Q2252369"],
            {
                "Q24826": engine_result(0, engine_trace([])),
                "Q2252369": engine_result(0, engine_trace([])),
            },
        )
        self.assertEqual(code, 0)
        self.assertIn("survivors=[]", printed)

    def test_two_surviving_candidates_is_reported_as_ambiguous_not_guessed(
        self,
    ) -> None:
        printed, code = self._run_main(
            ["Q24826", "Q1189030"],
            {
                "Q24826": engine_result(0, engine_trace(["Q145"])),
                "Q1189030": engine_result(0, engine_trace(["Q999"])),
            },
        )
        self.assertEqual(code, 6)
        # printed also carries the earlier "gf-tree=..." progress line
        # (main() prints it before the candidate loop runs); the ambiguity
        # report is the JSON object after it.
        payload = json.loads(printed[printed.index("{") :])
        self.assertEqual(payload["status"], "source-disambiguation-ambiguous")
        self.assertEqual(
            payload["confirmed_source_qid_candidates"], ["Q1189030", "Q24826"]
        )

    def test_a_genuine_engine_rejection_among_zero_survivors_still_surfaces(
        self,
    ) -> None:
        # If every candidate's own engine run failed outright (not just an
        # empty fiber), that is a real error and must not be silently
        # treated as a clean "no metonymic reading" result. The engine's
        # own `die` (engine/app/Main.hs) writes to stderr, not stdout.
        printed, code = self._run_main(
            ["Q24826"],
            {
                "Q24826": engine_result(
                    1, "", "contextual fiber failed: bad snapshot\n"
                )
            },
        )
        self.assertEqual(code, 1)
        self.assertIn("bad snapshot", printed)

    def test_contract_target_keeps_requiring_exactly_one_candidate(self) -> None:
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "The university announced a new programme",
            "--source",
            "Liverpool",
            "--contract-target",
            "the university",
        ]
        stdout = io.StringIO()
        with patch(
            "subprocess.run",
            return_value=propose_proposal(["Q24826", "Q2252369"]),
        ):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        self.assertEqual(raised.exception.code, 2)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "source-qid-unresolved")


class GfParseEmptyTests(unittest.TestCase):
    """Regression test for a real bug found via a real
    contextual-tower-evaluation.yml run: the "no lexicalized trees"
    branch used a bare `raise SystemExit("some string")`, which prints
    that string and exits 1 without the JSON-"status" convention every
    sibling failure in this function follows. That made it invisible to
    score_contextual_detection.py's exit-1 token search -- two full CI
    rounds of guessing new KNOWN_FAILURE_TOKENS/GENERIC_RUNTIME_CRASH_TOKENS
    entries found nothing, because the actual message was never among
    them, until fingerprint_failure_text's safe hashing (no content, just
    a SHA-256 prefix and a length) matched a locally-reproduced
    fingerprint of this exact 32-character string. Fixed by giving it its
    own exit code (7), JSON-wrapped like gf-parse-failed/
    semantic-composition-failed/contract-target-qid-unresolved.
    """

    def test_gf_parse_producing_no_trees_gets_its_own_exit_code(self) -> None:
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Liverpool announced a new programme",
            "--source",
            "Liverpool",
        ]

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "parse":
                return subprocess.CompletedProcess(
                    args=command, returncode=0, stdout="", stderr=""
                )
            raise AssertionError(f"unexpected command: {command}")

        stdout = io.StringIO()
        with patch("subprocess.run", side_effect=fake_run):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        self.assertEqual(raised.exception.code, 7)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "gf-parse-empty")

    def test_a_parser_failed_message_also_counts_as_no_trees(self) -> None:
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Liverpool announced a new programme",
            "--source",
            "Liverpool",
        ]

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "parse":
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="The parser failed at token 3\n",
                    stderr="",
                )
            raise AssertionError(f"unexpected command: {command}")

        stdout = io.StringIO()
        with patch("subprocess.run", side_effect=fake_run):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        self.assertEqual(raised.exception.code, 7)


def liverpool_announces_henry_ud_words() -> list[dict]:
    # "Liverpool announces Henry" -- deliberately independent of
    # propose_proposal's own "gf_sentence" text (that field is only used
    # by the legacy `engine parse`-on-raw-text path, never read at all
    # once the Stanza-built tree validates).
    return [
        {
            "id": 1, "head": 2, "deprel": "nsubj", "upos": "PROPN",
            "lemma": "Liverpool", "text": "Liverpool",
            "start_char": 0, "end_char": 9,
        },
        {
            "id": 2, "head": 0, "deprel": "root", "upos": "VERB",
            "lemma": "announce", "text": "announces",
            "start_char": 10, "end_char": 19,
        },
        {
            "id": 3, "head": 2, "deprel": "obj", "upos": "PROPN",
            "lemma": "Henry", "text": "Henry",
            "start_char": 20, "end_char": 25,
        },
    ]


class StanzaTreeFirstTests(unittest.TestCase):
    """Phase 1 of the "Stanza instead of GF-as-parser" transition (see
    scripts/build_gf_tree_from_dependencies.py and
    docs/contextual-tower.md): build_gf_tree is tried before `engine
    parse` on raw text, using --dependency-hint's "ud_words". Uses the
    real, on-disk data/contextual-gf-actions.json (only subprocess.run is
    mocked here, not file reads) -- "announce" maps to the real "Announce"
    V2 already in grammar/Metonymy.gf, confirmed by grep.
    """

    def _run_main_with_hint(
        self, ud_words: list[dict] | None, fake_run, governing_start: int | None = None
    ) -> tuple[str, int]:
        hint = {"dep_status": "direct-argument", "ud_words": ud_words}
        if governing_start is not None:
            hint["governing_start"] = governing_start
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Liverpool announces Henry",
            "--source",
            "Liverpool",
            "--ablation",
            "no-wordnet",
            "--dependency-hint",
            json.dumps(hint),
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("subprocess.run", side_effect=fake_run):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        return stdout.getvalue() + stderr.getvalue(), raised.exception.code

    def test_a_validated_stanza_built_tree_skips_engine_parse_entirely(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            calls.append(list(command))
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="Liverpool announces Henry\n",
                    stderr="",
                )
            if command[1] == "parse":
                raise AssertionError(
                    "engine parse must never run once the Stanza-built "
                    "tree already validated"
                )
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_hint(
            liverpool_announces_henry_ud_words(), fake_run
        )
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("tree-source=stanza", printed)
        # Empty decline_reason -- the Stanza-built tree was trusted, so
        # there's nothing to report a reason for.
        self.assertIn("decline-reason=\n", printed)
        # enumerate_gf_tree_blockers is still computed unconditionally
        # alongside decline_reason -- an already-successful build has no
        # blockers to enumerate at all.
        self.assertIn("all-decline-reasons=\n", printed)
        # The fixture's own hint carries dep_status="direct-argument" --
        # surfaced unconditionally, the same way tree_source/decline_reason
        # already are.
        self.assertIn("dep-status=direct-argument", printed)
        engine_calls = [call for call in calls if call[0] != "python3"]
        self.assertTrue(any(call[1] == "linearize" for call in engine_calls))
        self.assertFalse(any(call[1] == "parse" for call in engine_calls))

    def test_governing_start_builds_a_tree_around_an_embedded_verb(self) -> None:
        # "Because Liverpool announces Henry, Manchester praises Mary" --
        # target=Liverpool, whose governing verb ("announces") is embedded
        # in an advcl, not the sentence's own root ("praises"). Confirms
        # --dependency-hint's own "governing_start" field is threaded all
        # the way from main() into build_gf_tree, and that this still
        # takes the Stanza tree-source path (never falling through to
        # engine parse), even though the target's own governing verb
        # isn't the UD root.
        ud_words = [
            {
                "id": 1, "head": 3, "deprel": "mark", "upos": "SCONJ",
                "lemma": "because", "text": "Because",
                "start_char": 0, "end_char": 7,
            },
            {
                "id": 2, "head": 3, "deprel": "nsubj", "upos": "PROPN",
                "lemma": "Liverpool", "text": "Liverpool",
                "start_char": 8, "end_char": 17,
            },
            {
                "id": 3, "head": 6, "deprel": "advcl", "upos": "VERB",
                "lemma": "announce", "text": "announces",
                "start_char": 18, "end_char": 27,
            },
            {
                "id": 4, "head": 3, "deprel": "obj", "upos": "PROPN",
                "lemma": "Henry", "text": "Henry",
                "start_char": 28, "end_char": 33,
            },
            {
                "id": 5, "head": 6, "deprel": "nsubj", "upos": "PROPN",
                "lemma": "Manchester", "text": "Manchester",
                "start_char": 35, "end_char": 45,
            },
            {
                "id": 6, "head": 0, "deprel": "root", "upos": "VERB",
                "lemma": "praise", "text": "praises",
                "start_char": 46, "end_char": 53,
            },
            {
                "id": 7, "head": 6, "deprel": "obj", "upos": "PROPN",
                "lemma": "Mary", "text": "Mary",
                "start_char": 54, "end_char": 58,
            },
        ]

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                return subprocess.CompletedProcess(
                    args=command, returncode=0,
                    stdout="Liverpool announces Henry\n", stderr="",
                )
            if command[1] == "parse":
                raise AssertionError(
                    "engine parse must never run once the Stanza-built "
                    "tree (around the embedded governing verb) validated"
                )
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_hint(
            ud_words, fake_run, governing_start=18
        )
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("tree-source=stanza", printed)
        self.assertIn("decline-reason=\n", printed)

    def test_falls_back_to_engine_parse_when_build_gf_tree_declines(self) -> None:
        # A passive clause with two distinct "by"-agents -- a genuine
        # ambiguity (which one is real?), still outside scope even after
        # this round's PassCompl0 addition (which only covers the ZERO-
        # agent case -- see scripts/build_gf_tree_from_dependencies.py's
        # _clause) -- build_gf_tree returns None, so this must fall back
        # to asking GF's own parser to read raw text, unchanged.
        passive_ud_words = [
            {
                "id": 1, "head": 3, "deprel": "nsubj:pass", "upos": "PROPN",
                "lemma": "Henry", "text": "Henry", "start_char": 0, "end_char": 5,
            },
            {
                "id": 2, "head": 3, "deprel": "aux:pass", "upos": "AUX",
                "lemma": "be", "text": "was", "start_char": 6, "end_char": 9,
            },
            {
                "id": 3, "head": 0, "deprel": "root", "upos": "VERB",
                "lemma": "announce", "text": "announced",
                "start_char": 10, "end_char": 19,
            },
            {
                "id": 4, "head": 5, "deprel": "case", "upos": "ADP",
                "lemma": "by", "text": "by", "start_char": 20, "end_char": 22,
            },
            {
                "id": 5, "head": 3, "deprel": "obl", "upos": "PROPN",
                "lemma": "Waterloo", "text": "Waterloo",
                "start_char": 23, "end_char": 31,
            },
            {
                "id": 6, "head": 8, "deprel": "case", "upos": "ADP",
                "lemma": "by", "text": "by", "start_char": 36, "end_char": 38,
            },
            {
                "id": 7, "head": 3, "deprel": "cc", "upos": "CCONJ",
                "lemma": "and", "text": "and", "start_char": 32, "end_char": 35,
            },
            {
                "id": 8, "head": 3, "deprel": "obl", "upos": "PROPN",
                "lemma": "Napoleon", "text": "Napoleon",
                "start_char": 39, "end_char": 47,
            },
        ]

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                raise AssertionError(
                    "linearize must never run when build_gf_tree returned None"
                )
            if command[1] == "parse":
                return gf_parse_result()
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_hint(passive_ud_words, fake_run)
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("tree-source=gf-parser", printed)
        # Two "by"-agents in this fixture -- build_gf_tree's own passive
        # handling declines specifically because of that genuine
        # ambiguity (not the zero-agent case, which now succeeds).
        self.assertIn("decline-reason=passive-agent-count", printed)
        # enumerate_gf_tree_blockers keeps going past that first _Bail:
        # once the extra "by"-agent is ablated away, the fixture's own
        # "and" (cc) word -- never accounted for by the passive branch,
        # which only ever consumes the subject/aux/verb/single agent --
        # surfaces as a second, genuinely different blocker. A real,
        # useful finding this diagnostic exists to surface, not a test
        # artifact to hide.
        self.assertIn(
            "all-decline-reasons=passive-agent-count,leftover-words", printed
        )

    def test_falls_back_to_engine_parse_when_linearize_validation_fails(self) -> None:
        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=1,
                    stdout="",
                    stderr="malformed or incomplete GF tree",
                )
            if command[1] == "parse":
                return gf_parse_result()
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_hint(
            liverpool_announces_henry_ud_words(), fake_run
        )
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("decline-reason=linearize-validation-failed", printed)

    def test_falls_back_to_engine_parse_when_there_are_no_ud_words_at_all(self) -> None:
        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                raise AssertionError("linearize must never run with no ud_words hint")
            if command[1] == "parse":
                return gf_parse_result()
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_hint(None, fake_run)
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("decline-reason=no-ud-words", printed)
        # No --llm-proposer-model was passed -- the LLM tier must never
        # even be attempted, let alone call out to query_ollama.
        self.assertIn("llm-decline-reason=not-attempted", printed)
        # dep_status is read straight off the hint dict, independent of
        # whether ud_words itself was present -- this fixture's own hint
        # (see _run_main_with_hint) still carries "direct-argument".
        self.assertIn("dep-status=direct-argument", printed)


class LlmProposerTierTests(unittest.TestCase):
    """The third tree-source tier, tried only when Stanza-UD declined
    and --llm-proposer-model was actually passed. query_ollama is
    patched at run_automatic_contextual_pipeline's own import binding
    (never a real network call) -- the business logic
    (propose_clause_structure/build_gf_tree_from_llm_structure) runs
    for real, only the HTTP glue is faked, the same division already
    used by tests/evaluation/test_llm_propose_clause_structure.py.
    """

    def _run_main_with_llm(
        self,
        ud_words: list[dict] | None,
        ollama_response,
        fake_run,
        query_side_effect=None,
    ) -> tuple[str, int]:
        hint = {"dep_status": "direct-argument", "ud_words": ud_words}
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Liverpool announces Henry",
            "--source",
            "Liverpool",
            "--ablation",
            "no-wordnet",
            "--dependency-hint",
            json.dumps(hint),
            "--llm-proposer-model",
            "llama3.2:3b-instruct",
        ]
        stdout = io.StringIO()
        stderr = io.StringIO()
        query_kwargs = (
            {"side_effect": query_side_effect}
            if query_side_effect is not None
            else {"return_value": ollama_response}
        )
        with patch(
            "run_automatic_contextual_pipeline.query_ollama",
            **query_kwargs,
        ):
            with patch("subprocess.run", side_effect=fake_run):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        run_automatic_contextual_pipeline.main()
        return stdout.getvalue() + stderr.getvalue(), raised.exception.code

    def test_llm_tier_succeeds_when_stanza_declined(self) -> None:
        response = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Liverpool"]},
            "object": {"kind": "proper_noun", "tokens": ["Henry"]},
            "agent": None,
        }
        calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            calls.append(list(command))
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                return subprocess.CompletedProcess(
                    args=command, returncode=0, stdout="Liverpool announces Henry\n", stderr="",
                )
            if command[1] == "parse":
                raise AssertionError(
                    "engine parse must never run once the LLM-built tree validated"
                )
            return engine_result(0, engine_trace(["Q145"]))

        # No ud_words at all -- Stanza tier is guaranteed to decline
        # ("no-ud-words"), so this exercises the LLM tier in isolation.
        printed, code = self._run_main_with_llm(None, response, fake_run)
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("tree-source=llm", printed)
        self.assertIn("llm-decline-reason=\n", printed)
        engine_calls = [call for call in calls if call[0] != "python3"]
        self.assertTrue(any(call[1] == "linearize" for call in engine_calls))
        self.assertFalse(any(call[1] == "parse" for call in engine_calls))

    def test_falls_back_to_engine_parse_when_the_llm_also_declines(self) -> None:
        # "voice": null -- the model's own "not confident" abstention.
        response = {"voice": None, "subject": None, "object": None, "agent": None}

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                raise AssertionError(
                    "linearize must never run when the LLM tier had no structure"
                )
            if command[1] == "parse":
                return gf_parse_result()
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_llm(None, response, fake_run)
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("tree-source=gf-parser", printed)
        self.assertIn("llm-decline-reason=voice-null-abstention", printed)

    def test_falls_back_to_engine_parse_when_the_query_itself_times_out(self) -> None:
        # A network/timeout failure inside query_ollama -- distinct from
        # the model's own "voice": null abstention above; a real corpus
        # run showed this whole bucket (then flattened into one generic
        # "no-response") dominating LLM-tier attempts, with no way to
        # tell which of the two this was.
        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                raise AssertionError(
                    "linearize must never run when the LLM tier had no structure"
                )
            if command[1] == "parse":
                return gf_parse_result()
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_llm(
            None, None, fake_run, query_side_effect=TimeoutError("boom")
        )
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("tree-source=gf-parser", printed)
        self.assertIn("llm-decline-reason=query-network-or-timeout", printed)

    def test_falls_back_to_engine_parse_when_the_llm_tree_fails_validation(self) -> None:
        response = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Liverpool"]},
            "object": {"kind": "proper_noun", "tokens": ["Henry"]},
            "agent": None,
        }

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=1,
                    stdout="",
                    stderr="malformed or incomplete GF tree",
                )
            if command[1] == "parse":
                return gf_parse_result()
            return engine_result(0, engine_trace(["Q145"]))

        printed, code = self._run_main_with_llm(None, response, fake_run)
        self.assertEqual(code, 0)
        self.assertIn("survivors=[Q145]", printed)
        self.assertIn("tree-source=gf-parser", printed)
        self.assertIn("llm-decline-reason=linearize-validation-failed", printed)

    def test_stanza_is_preferred_when_it_succeeds_llm_never_called(self) -> None:
        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "linearize":
                return subprocess.CompletedProcess(
                    args=command, returncode=0, stdout="Liverpool announces Henry\n", stderr="",
                )
            if command[1] == "parse":
                raise AssertionError("engine parse must never run")
            return engine_result(0, engine_trace(["Q145"]))

        with patch("run_automatic_contextual_pipeline.query_ollama") as mock_query:
            printed, code = self._run_main_with_llm(
                liverpool_announces_henry_ud_words(), {}, fake_run
            )
            mock_query.assert_not_called()
        self.assertEqual(code, 0)
        self.assertIn("tree-source=stanza", printed)
        self.assertIn("llm-decline-reason=not-attempted", printed)


class Exit4TreeSourceTaggingTests(unittest.TestCase):
    """A live corpus evaluation run surfaced a real mystery in exit4's
    breakdown: bare, unquoted capitalized words (e.g. "Albright", "The")
    showing up as "unrecognized constructor(s)" -- neither this
    module's own tree-builder (which always quotes its own string
    arguments and is validated through `engine linearize` before it is
    ever trusted) nor any known gf_actions entry can explain that. These
    tests confirm the exit-4 JSON payload's new "tree_source" field
    correctly distinguishes which of the two tree sources actually
    produced trees[0] for that row, so a future real corpus run can
    isolate which one the mystery is actually coming from.
    """

    def test_tags_stanza_when_the_stanza_built_tree_was_used(self) -> None:
        # "programme" has real data/wordnet-context-rules.json lexical_
        # sorts coverage (unmocked here, read for real, since this test
        # deliberately does not use --ablation no-wordnet), so
        # compile_gf_constraints's FrameArgument derivation reaches
        # _cumulative_origin's own token search -- which fails, because
        # the mocked payload's own "sentence" field (deliberately
        # distinct from the tree's actual object noun) never contains
        # the word "programme" at all, raising "GF lexical token is
        # absent from source: programme". A real exit-4 trigger reachable
        # through a well-formed, linearize-validated Stanza-built tree,
        # and (unlike an unsupported adjective+noun pair, which
        # compile_gf_constraints now skips rather than treats as fatal --
        # see contextual_rule_compiler.py's own "unsupported GF
        # adjective-noun semantics" handling) still a hard failure.
        words = [
            {"id": 1, "head": 2, "deprel": "nsubj", "upos": "PROPN", "lemma": "Waterloo", "text": "Waterloo", "start_char": 0, "end_char": 8},
            {"id": 2, "head": 0, "deprel": "root", "upos": "VERB", "lemma": "announce", "text": "announces", "start_char": 9, "end_char": 18},
            {"id": 3, "head": 4, "deprel": "det", "upos": "DET", "lemma": "a", "text": "a", "start_char": 19, "end_char": 20},
            {"id": 4, "head": 2, "deprel": "obj", "upos": "NOUN", "lemma": "programme", "text": "programme", "start_char": 21, "end_char": 30},
        ]
        hint = {"dep_status": "direct-argument", "ud_words": words}
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Waterloo announces a programme",
            "--source",
            "Waterloo",
            "--dependency-hint",
            json.dumps(hint),
        ]

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                # Not propose_proposal (its fixed "constraints": [] would
                # make compile_gf_constraints's own
                # proposal["constraints"][0] lookup crash before ever
                # reaching the wordnet-based check this test needs --
                # every other test in this file uses --ablation
                # no-wordnet, which returns before that lookup; this one
                # deliberately doesn't). "sentence" is deliberately absent
                # "programme" -- the whole point of this fixture.
                payload = {
                    "status": "ready",
                    "gf_sentence": "Waterloo announces a programme",
                    "sentence": "Waterloo announces a florbnorbish quzzleblat",
                    "action": "announce",
                    "role": "SubjectHole",
                    "provenance": {"action": "test:VerbNet:announce"},
                    "max_depth": 1,
                    "bridge_relations": ["InstitutionOf"],
                    "constraints": [
                        {
                            "origin": {
                                "constructor": "Verb",
                                "lemma": "announce",
                                "surface": "announces",
                                "start": 9,
                                "end": 18,
                            },
                            "payload": {"requires": "HasSort Entity"},
                            "provenance": "test",
                        }
                    ],
                    "source_qid_candidates": ["Q24826"],
                    "source_surface": "Waterloo",
                }
                return subprocess.CompletedProcess(
                    args=["python3", "scripts/propose_contextual_scenario.py"],
                    returncode=0,
                    stdout=json.dumps(payload),
                    stderr="",
                )
            if command[1] == "linearize":
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="Waterloo announces a programme\n",
                    stderr="",
                )
            raise AssertionError(f"unexpected command: {command}")

        stdout = io.StringIO()
        with patch("subprocess.run", side_effect=fake_run):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        self.assertEqual(raised.exception.code, 4)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "semantic-composition-failed")
        self.assertEqual(payload["tree_source"], "stanza")

    def test_tags_gf_parser_when_the_legacy_path_was_used(self) -> None:
        sys.argv = [
            "run_automatic_contextual_pipeline.py",
            "--engine",
            "build/metonymy",
            "--snapshot",
            "auxiliary/data/wikidata-openalex-snapshot",
            "--sentence",
            "Liverpool announced a new programme",
            "--source",
            "Liverpool",
            "--ablation",
            "no-wordnet",
        ]

        def fake_run(command, **kwargs):
            if command[0] == "python3":
                return propose_proposal(["Q24826"])
            if command[1] == "parse":
                # Two top-level tokens left unconsumed -- a genuinely
                # malformed tree, triggering exit4 even under
                # --ablation no-wordnet (parse_gf_tree runs before
                # compile_gf_constraints's own wordnet short-circuit).
                return subprocess.CompletedProcess(
                    args=command, returncode=0, stdout="DummyTree DummyTree2\n", stderr="",
                )
            raise AssertionError(f"unexpected command: {command}")

        stdout = io.StringIO()
        with patch("subprocess.run", side_effect=fake_run):
            with redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    run_automatic_contextual_pipeline.main()
        self.assertEqual(raised.exception.code, 4)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "semantic-composition-failed")
        self.assertEqual(payload["tree_source"], "gf-parser")


if __name__ == "__main__":
    unittest.main()
