"""Unit tests for resolve_action's "copula-argument" branch
(_resolve_copula_predicate) -- structurally separate from the rest of
resolve_action, since there is no VerbNet "action" for a copula at all;
the predicate noun's own lemma stands in for "action", and the
requirement comes directly from a wordnet_rules["lexical_sorts"] entry
instead of any ActionRole.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from contextual_rule_compiler import resolve_action  # noqa: E402

# "Waterloo is a county" -- copula word "is" only, not the whole
# predicate NP "a county".
SENTENCE = "Waterloo is a county"
COP_START = SENTENCE.index("is")
COP_END = COP_START + len("is")

WORDNET_RULES = {
    "lexical_sorts": {
        "county": {"requirement": "HasSort Place", "provenance": "test:wordnet:county"}
    }
}


def copula_hint(**overrides) -> dict:
    hint = {
        "dep_status": "copula-argument",
        "hole_role": "Subject",
        "governing_lemma": "county",
        "governing_start": COP_START,
        "governing_end": COP_END,
    }
    hint.update(overrides)
    return hint


class ResolveActionCopulaTests(unittest.TestCase):
    def test_predicate_noun_with_lexical_sorts_coverage_resolves(self) -> None:
        result = resolve_action(
            SENTENCE,
            ["Waterloo"],
            [],
            {},
            dependency_hint=copula_hint(),
            wordnet_rules=WORDNET_RULES,
        )
        self.assertEqual(result["lemma"], "county")
        self.assertEqual(result["surface"], "is")
        self.assertEqual(result["start"], COP_START)
        self.assertEqual(result["end"], COP_END)
        self.assertEqual(result["role"], "SubjectHole")
        self.assertEqual(result["requirement"], "HasSort Place")
        self.assertEqual(result["strength"], "hard")
        self.assertTrue(result["provenance"].startswith("compiled-copula-predicate:v1:hard:"))
        self.assertEqual(result["gf_form"], "is")
        self.assertEqual(result["voice"], "active")
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["evidence"][0]["identity"], "wordnet-lexical-sort:county")

    def test_hole_role_object_is_respected(self) -> None:
        # copula-argument only ever fires for a subject today (see
        # classify_word's own SUBJECT_DEPRELS-only scoping), but
        # resolve_action itself stays generic over hole_role rather
        # than hardcoding "Subject" -- confirmed here rather than
        # assumed.
        result = resolve_action(
            SENTENCE,
            ["Waterloo"],
            [],
            {},
            dependency_hint=copula_hint(hole_role="Object"),
            wordnet_rules=WORDNET_RULES,
        )
        self.assertEqual(result["role"], "ObjectHole")

    def test_predicate_noun_without_lexical_sorts_coverage_declines(self) -> None:
        # "museum" is deliberately absent from WORDNET_RULES -- the same
        # coverage ceiling already documented for adjective_sorts
        # elsewhere in this project, expected to fire for a real share
        # of "X is a Y" sentences.
        with self.assertRaises(ValueError) as raised:
            resolve_action(
                "Waterloo is a museum",
                ["Waterloo"],
                [],
                {},
                dependency_hint=copula_hint(governing_lemma="museum"),
                wordnet_rules=WORDNET_RULES,
            )
        self.assertEqual(str(raised.exception), "unsupported-copula-predicate:museum")

    def test_missing_wordnet_rules_declines_the_same_way(self) -> None:
        with self.assertRaises(ValueError) as raised:
            resolve_action(
                SENTENCE,
                ["Waterloo"],
                [],
                {},
                dependency_hint=copula_hint(),
                wordnet_rules=None,
            )
        self.assertEqual(str(raised.exception), "unsupported-copula-predicate:county")

    def test_missing_governing_span_is_a_defensive_decline(self) -> None:
        with self.assertRaises(ValueError) as raised:
            resolve_action(
                SENTENCE,
                ["Waterloo"],
                [],
                {},
                dependency_hint=copula_hint(governing_start=None),
                wordnet_rules=WORDNET_RULES,
            )
        self.assertEqual(str(raised.exception), "copula-predicate-unresolved")


if __name__ == "__main__":
    unittest.main()
