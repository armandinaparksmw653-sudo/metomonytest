"""Regression test for a real bug found via a real contextual-tower-
evaluation.yml run and a local reproduction of the exact same corpus
sample: WiMCor/ConMeC's "sentence" field is a discourse-level excerpt,
often several sentences long (a real sample from the corpus went up to
21), kept that way on purpose since propose_contextual_scenario.py's own
lexical_evidence deliberately scans the whole excerpt for context clues.
But Metonymy.gf's abstract syntax has exactly one clause-level category
(no coordination, no cross-sentence structure at all), so feeding the
*entire* excerpt to `engine parse` -- which run_automatic_contextual_pipeline.py
always did before this fix -- asked a single-sentence grammar to parse a
whole paragraph. This was found not by guessing but by fingerprinting
score_contextual_detection.py's "unrecognized" exit-1 failures down to a
single 32-character message, confirming a bare `raise
SystemExit("GF returned no lexicalized trees")` as the sole cause,
locally reproducing the real corpus-driven sample, and inspecting the
actual gf_sentence strings this script produced -- every one was the
full multi-sentence excerpt, verb substituted in place, up to 1966
characters long.

sentence_span_containing narrows gf_sentence to just the sentence
containing the action's own span, without touching action["start"]/
["end"], proposal["sentence"], or anything compile_gf_constraints later
searches within -- those stay relative to the full excerpt on purpose.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from propose_contextual_scenario import sentence_span_containing  # noqa: E402


class SentenceSpanContainingTests(unittest.TestCase):
    def test_single_sentence_text_returns_the_whole_text(self) -> None:
        text = "Liverpool announced a new programme in physics."
        start, end = sentence_span_containing(text, 0, len("Liverpool"))
        self.assertEqual((start, end), (0, len(text)))

    def test_narrows_to_the_sentence_containing_the_span(self) -> None:
        text = (
            "Barrino was born in High Point. "
            "She began singing at the age of five. "
            "Her uncles were a 1970s R&B band."
        )
        action_start = text.index("born")
        action_end = action_start + len("born")
        start, end = sentence_span_containing(text, action_start, action_end)
        self.assertEqual(text[start:end], "Barrino was born in High Point. ")

    def test_narrows_to_a_later_sentence_when_the_action_is_there(self) -> None:
        text = (
            "Barrino was born in High Point. "
            "She began singing at the age of five. "
            "Her uncles were a 1970s R&B band."
        )
        action_start = text.index("singing")
        action_end = action_start + len("singing")
        start, end = sentence_span_containing(text, action_start, action_end)
        self.assertEqual(
            text[start:end], "She began singing at the age of five. "
        )

    def test_does_not_split_on_a_common_abbreviation(self) -> None:
        text = "Dr. Smith announced a new programme. He later signed it."
        action_start = text.index("announced")
        action_end = action_start + len("announced")
        start, end = sentence_span_containing(text, action_start, action_end)
        self.assertEqual(text[start:end], "Dr. Smith announced a new programme. ")

    def test_returns_the_whole_text_when_the_span_is_out_of_range(self) -> None:
        text = "One sentence. Another sentence."
        start, end = sentence_span_containing(text, 1000, 1010)
        self.assertEqual((start, end), (0, len(text)))

    def test_dramatically_shortens_a_real_multi_sentence_excerpt(self) -> None:
        # A real shape from locally reproducing the corpus sample --
        # dozens of unrelated trailing sentences after the relevant one.
        text = "Short relevant sentence here. " + "Filler sentence. " * 40
        action_start = text.index("relevant")
        action_end = action_start + len("relevant")
        start, end = sentence_span_containing(text, action_start, action_end)
        self.assertEqual(text[start:end], "Short relevant sentence here. ")
        self.assertLess(end - start, 50)


if __name__ == "__main__":
    unittest.main()
