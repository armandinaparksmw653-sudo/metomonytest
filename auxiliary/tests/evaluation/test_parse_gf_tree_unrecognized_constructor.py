"""Unit tests for parse_gf_tree's unrecognized-constructor diagnostic.

A live contextual-tower-evaluation.yml run showed ConMeC's exit4
(semantic-composition-failed) is dominated by "malformed or incomplete
GF tree" (23 of 25 rows) -- but that bare message alone doesn't say
*why* parse_gf_tree left tokens unconsumed. The most likely real cause:
a GF constructor missing from ARITIES entirely, silently treated as
0-ary by ARITIES.get(token, 0), leaving its actual arguments dangling as
unexpected top-level tokens. These tests cover the fix: when any
constructor-shaped token in the tree isn't in ARITIES (and isn't one of
the confirmed-0-ary pronoun constants), name it in the raised message --
the constructor name itself is this grammar's own closed vocabulary
(grammar/Metonymy.gf's `fun` declarations), never sentence text, the
same safety class already used for EXIT4_KNOWN_FAILURE_TOKENS.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from contextual_rule_compiler import parse_gf_tree  # noqa: E402


class UnrecognizedConstructorDiagnosticTests(unittest.TestCase):
    def test_names_a_single_unknown_constructor(self) -> None:
        with self.assertRaises(ValueError) as raised:
            parse_gf_tree('GlorbNode "extra"')
        self.assertEqual(
            str(raised.exception),
            "malformed or incomplete GF tree; unrecognized constructor(s): GlorbNode",
        )

    def test_names_multiple_unknown_constructors_in_order_deduplicated(
        self,
    ) -> None:
        with self.assertRaises(ValueError) as raised:
            parse_gf_tree('FooBar "x" BazQux "y" FooBar')
        self.assertEqual(
            str(raised.exception),
            "malformed or incomplete GF tree; unrecognized constructor(s): FooBar,BazQux",
        )

    def test_falls_back_to_the_bare_message_when_every_token_is_recognized(
        self,
    ) -> None:
        # OpenPN is a real, known (arity-1) constructor -- a malformed
        # tree using only known constructors (too many top-level args
        # here, not an unknown token) must not fabricate a constructor
        # name that isn't actually the problem.
        with self.assertRaises(ValueError) as raised:
            parse_gf_tree('OpenPN "a" "b"')
        self.assertEqual(str(raised.exception), "malformed or incomplete GF tree")

    def test_known_zero_arity_pronoun_constructors_are_never_misflagged(
        self,
    ) -> None:
        with self.assertRaises(ValueError) as raised:
            parse_gf_tree("FooBar (HePN)")
        self.assertEqual(
            str(raised.exception),
            "malformed or incomplete GF tree; unrecognized constructor(s): FooBar",
        )

    def test_a_well_formed_tree_with_an_unknown_leaf_constructor_still_parses(
        self,
    ) -> None:
        # A single top-level 0-arity token, known or not, is already a
        # complete tree -- no error, this diagnostic only ever fires on
        # the existing failure path, never a new one.
        tree = parse_gf_tree("DummyTree")
        self.assertEqual(tree.constructor, "DummyTree")


if __name__ == "__main__":
    unittest.main()
