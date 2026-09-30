"""Unit tests for llm_propose_clause_structure.py.

Business logic (propose_clause_structure) is tested with an INJECTED
query callable (a lambda), never a real or mocked Ollama HTTP call --
query_ollama's own network glue (scripts/ollama_client.py) stays
untested here, verified only by a real CI run, the same policy as
every Stanza-dependent test in this project.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from llm_propose_clause_structure import (  # noqa: E402
    build_prompt,
    propose_clause_structure,
    propose_clause_structure_with_reason,
)


class BuildPromptTests(unittest.TestCase):
    def test_prompt_includes_the_sentence_and_lemma(self) -> None:
        prompt = build_prompt("Waterloo announces Henry County", "announce")
        self.assertIn("Waterloo announces Henry County", prompt)
        self.assertIn("announce", prompt)
        self.assertIn('"voice"', prompt)
        self.assertIn("proper_noun", prompt)

    def test_prompt_forbids_a_non_null_voice_with_a_null_required_field(self) -> None:
        # A real corpus run showed the model producing exactly this
        # hybrid (e.g. {"voice": "active", "subject": ..., "object":
        # null}) far more than any other failure mode
        # (llm-active-missing-np/llm-passive-missing-np) -- the prompt
        # now spells out that this specific shape is never acceptable.
        # Worded concisely -- a follow-up run showed the first, more
        # verbose wording of this same rule nearly tripled the prompt's
        # length and, on a CPU-only CI runner, pushed most requests past
        # query_ollama's own timeout (see propose_clause_structure_with_
        # reason's docstring: "query-network-or-timeout").
        prompt = build_prompt("Waterloo announces Henry County", "announce")
        self.assertIn("never a non-null voice with a required NP left null", prompt)
        self.assertIn("complete abstention", prompt)

    def test_prompt_stays_reasonably_short(self) -> None:
        # A regression guard for the timeout regression above: the
        # prompt this module sends on every LLM-tier attempt should
        # stay in the same ballpark as it was before that regression
        # (roughly 1500-1600 characters), not silently creep back up.
        prompt = build_prompt("Waterloo announces Henry County", "announce")
        self.assertLess(len(prompt), 1900)


class ProposeClauseStructureTests(unittest.TestCase):
    def test_a_well_formed_response_is_returned_as_is(self) -> None:
        response = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {"kind": "proper_noun", "tokens": ["Henry"]},
            "agent": None,
        }
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertEqual(structure, response)

    def test_a_voice_null_abstention_becomes_none(self) -> None:
        # The model's own "not confident" signal (see the prompt's
        # explicit instruction) -- must never be treated as a usable
        # structure.
        response = {"voice": None, "subject": None, "object": None, "agent": None}
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertIsNone(structure)

    def test_a_query_exception_becomes_none(self) -> None:
        def failing_query(prompt: str) -> dict:
            raise RuntimeError("boom")

        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", failing_query
        )
        self.assertIsNone(structure)

    def test_a_non_dict_response_becomes_none(self) -> None:
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: "not a dict"
        )
        self.assertIsNone(structure)

    def test_a_missing_voice_key_becomes_none(self) -> None:
        structure = propose_clause_structure(
            "Waterloo announces Henry", "announce", lambda prompt: {"subject": {}}
        )
        self.assertIsNone(structure)


class ProposeClauseStructureWithReasonTests(unittest.TestCase):
    """Real corpus evaluation data showed propose_clause_structure's own
    None outcome dominating LLM-tier attempts, with no way to tell a
    technical failure apart from the model's own deliberate abstention.
    These mirror ProposeClauseStructureTests's five cases exactly, but
    additionally assert the specific reason code each one now carries.
    """

    def test_a_well_formed_response_has_no_decline_reason(self) -> None:
        response = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {"kind": "proper_noun", "tokens": ["Henry"]},
            "agent": None,
        }
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertEqual(structure, response)
        self.assertEqual(reason, "")

    def test_a_voice_null_abstention_is_not_a_technical_failure(self) -> None:
        response = {"voice": None, "subject": None, "object": None, "agent": None}
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: response
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "voice-null-abstention")

    def test_a_query_exception_is_reported_distinctly(self) -> None:
        def failing_query(prompt: str) -> dict:
            raise RuntimeError("boom")

        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", failing_query
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "query-exception")

    def test_a_network_or_timeout_error_is_reported_distinctly(self) -> None:
        # OSError covers urllib.error.URLError/HTTPError (both OSError
        # subclasses) and a raw socket timeout alike -- the request
        # never got a usable response at all, as opposed to getting one
        # that just wasn't valid JSON (the next test).
        def timing_out_query(prompt: str) -> dict:
            raise TimeoutError("timed out")

        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", timing_out_query
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "query-network-or-timeout")

    def test_a_malformed_json_response_is_reported_distinctly(self) -> None:
        # query_ollama's own json.loads (of either the HTTP body or the
        # model's inner "response" text) raising -- a reply came back,
        # just not one shaped like JSON.
        def malformed_json_query(prompt: str) -> dict:
            raise json.JSONDecodeError("bad json", "doc", 0)

        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", malformed_json_query
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "query-malformed-response")

    def test_a_non_dict_response_is_reported_distinctly(self) -> None:
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: "not a dict"
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "non-dict-response")

    def test_a_missing_voice_key_is_reported_distinctly_from_an_explicit_null(
        self,
    ) -> None:
        structure, reason = propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", lambda prompt: {"subject": {}}
        )
        self.assertIsNone(structure)
        self.assertEqual(reason, "missing-voice-key")

    def test_calls_query_exactly_once(self) -> None:
        calls: list[str] = []

        def counting_query(prompt: str) -> dict:
            calls.append(prompt)
            return {"voice": None, "subject": None, "object": None, "agent": None}

        propose_clause_structure_with_reason(
            "Waterloo announces Henry", "announce", counting_query
        )
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
