"""Regression test for a real bug found while extending
data/wikidata-openalex-snapshot with a new non-University "Cupertino ->
Apple" example this session: a real CI run failed
"audited-contract-cupertino-commercial" with
"target-occurrence-not-found" for the sentence "Apple Inc. signed the
commercial agreement" -- "Apple Inc." is a real alias verbatim from the
production snapshot's own aliases.jsonl, not an invented test string.

Root cause: contextual_rule_compiler.py's _mention_span matched a target
surface with `\\b<surface>\\b`. `\\b` requires a word/non-word transition
on *both* sides -- and fails whenever the surface itself ends in
punctuation immediately followed by whitespace, since neither side of
that boundary is a word character ("." and " " are both non-word).
Every surface this mechanism had been exercised against before
("Chanel", "Cupertino", "Valparaiso", "Rumi", ...) happened to be
word-ending, so this was never caught until a real alias with a
trailing "." was tried. Fixed by replacing both `\\b`s with
`(?<!\\w)`/`(?!\\w)` lookarounds -- identical behavior on every
word-ending surface, correct for punctuation-ending ones too.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from contextual_rule_compiler import (  # noqa: E402
    ActionRole,
    _mention_span,
    resolve_action,
)


class MentionSpanPunctuationTests(unittest.TestCase):
    def test_a_surface_ending_in_punctuation_is_still_found(self) -> None:
        sentence = "Apple Inc. signed the commercial agreement"
        span = _mention_span(sentence, ["Cupertino", "Apple Inc."])
        self.assertIsNotNone(span)
        self.assertEqual(sentence[span[0] : span[1]], "Apple Inc.")

    def test_word_ending_surfaces_behave_exactly_as_before(self) -> None:
        # Every surface this mechanism was previously exercised against
        # in this project -- none of these should change span.
        cases = [
            ("Chanel signed the commercial agreement", "Chanel", (0, 6)),
            ("Cupertino signed the commercial agreement", "Cupertino", (0, 9)),
            (
                "He attended Valparaiso and received a degree",
                "Valparaiso",
                (12, 22),
            ),
            ("Anna reads Rumi", "Rumi", (11, 15)),
        ]
        for sentence, surface, expected in cases:
            with self.subTest(surface=surface):
                self.assertEqual(_mention_span(sentence, [surface]), expected)

    def test_resolve_action_no_longer_raises_for_a_punctuation_ending_target(
        self,
    ) -> None:
        sentence = "Apple Inc. signed the commercial agreement"
        roles = [
            ActionRole(
                lemma="sign",
                hole_role="SubjectHole",
                requirement="HasSort Agent",
                strength="HardRequirement",
                provenance="test",
                identity="test:sign:subject",
            )
        ]
        result = resolve_action(sentence, ["Cupertino", "Apple Inc."], roles, {})
        self.assertEqual(result["lemma"], "sign")


if __name__ == "__main__":
    unittest.main()
