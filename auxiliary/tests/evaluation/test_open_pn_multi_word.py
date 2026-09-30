"""OpenPN2/OpenPN3 -- the fix for the root cause found by
test_gf_parse_diagnostic_matrix.py's first real CI run: OpenPN's single
`String` slot matches exactly one token when parsing, so a two- or
three-word proper noun ("Henry County", "The Shipley School") never
completed a GF derivation at all, regardless of any sentence-level
grammar construction added elsewhere. This is very likely why three
consecutive contextual-tower-evaluation.yml runs each measured zero
effect from otherwise-correct, CI-verified grammar additions
(S-coordination+8 prepositions, then VP coordination, then
copula+generalized-relative-clauses+genitive): none of them can matter
if the subject/object NP itself can never parse.

Two things need to know about the new tree shapes:
- contextual_rule_compiler.py's ARITIES table (parse_gf_tree's own
  contract, covered by the arity tests below).
- _proper_lemma, which ModifyNP's PP-modifier composition-matrix path
  uses to look up a PP target's alias -- extended here the same way
  lexical_head was already extended for ModifyRelVP/ModifyRelCNVP, so a
  multi-word PP target ("a programme in New York") resolves its full,
  space-joined name instead of silently stopping at OpenPN alone.

These are pure Python tests against hand-built GF tree strings/direct
calls -- they do not require a compiled grammar. Whether the grammar
itself actually compiles and parses real multi-word names is verified
only in CI (this file's whole reason for existing is a real CI run that
already found the underlying bug, not a guess).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from contextual_rule_compiler import (  # noqa: E402
    ARITIES,
    GFNode,
    _proper_lemma,
    compile_gf_constraints,
)

WORDNET_RULES = {
    "lexical_sorts": {
        "general": {"requirement": "HasSort Military", "provenance": "test:wordnet"}
    },
    "adjective_sorts": {},
}

LANGUAGE_RULES = {
    "schema_version": "test-1",
    "frame_argument_capabilities": [],
}


def base_proposal(sentence: str, action: str = "capture") -> dict:
    return {
        "action": action,
        "sentence": sentence,
        "frames": [],
        "provenance": {"action": "test:VerbNet:" + action},
        "constraints": [
            {
                "origin": {
                    "constructor": "Verb",
                    "lemma": action,
                    "surface": "captured",
                    "start": 0,
                    "end": 8,
                },
                "payload": {"requires": "HasSort Place"},
                "provenance": "test:VerbNet:" + action,
            }
        ],
    }


class OpenPNMultiWordArityTests(unittest.TestCase):
    def test_open_pn2_takes_two_strings(self) -> None:
        self.assertEqual(ARITIES["OpenPN2"], 2)

    def test_open_pn3_takes_three_strings(self) -> None:
        self.assertEqual(ARITIES["OpenPN3"], 3)


class ProperLemmaMultiWordTests(unittest.TestCase):
    def test_open_pn_still_returns_its_single_word(self) -> None:
        self.assertEqual(_proper_lemma(GFNode("OpenPN", ("Waterloo",))), "Waterloo")

    def test_open_pn2_joins_both_words_with_a_space(self) -> None:
        self.assertEqual(
            _proper_lemma(GFNode("OpenPN2", ("Henry", "County"))), "Henry County"
        )

    def test_open_pn3_joins_all_three_words_with_a_space(self) -> None:
        self.assertEqual(
            _proper_lemma(GFNode("OpenPN3", ("The", "Shipley", "School"))),
            "The Shipley School",
        )

    def test_a_non_proper_noun_node_is_a_safe_none_not_a_crash(self) -> None:
        self.assertIsNone(_proper_lemma(GFNode("OpenIndefCN", ("county", "counties"))))


class CompileGfConstraintsMultiWordSubjectTests(unittest.TestCase):
    def test_a_two_word_open_pn_subject_does_not_crash_the_walker(self) -> None:
        # "Henry County captured a general" -- OpenPN2 as the Pred
        # subject rather than the Compl object; first_node's search for
        # Compl/PassCompl doesn't even look at the subject slot, so this
        # is mainly confirming the walker tolerates the new node shape
        # anywhere in the tree, subject position included.
        proposal = base_proposal("Henry County captured a general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN2 "Henry" "County") '
            '(Compl Capture (OpenIndefCN "general" "generals"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")


if __name__ == "__main__":
    unittest.main()
