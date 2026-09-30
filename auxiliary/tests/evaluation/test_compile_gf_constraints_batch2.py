"""compile_gf_constraints must safely traverse trees built with this
batch's grammar/Metonymy.gf additions -- found by literally reading real
WiMCor/ConMeC sample sentences (locally reproduced, seed=0, matching this
project's real CI exactly) and testing them against a locally compiled
grammar instead of guessing from aggregate signals. See
docs/contextual-tower.md's "batch 2" section for the full reasoning.

- OfPP : NP -> PP -- the missing "of" preposition (President *of* X, part
  *of* Y, University *of* Z). Same closed idiom as the existing twelve.
- OnFrontedS/InFrontedS/FromFrontedS : NP -> S -> S -- fronted date/time
  adverbials ("On 18 May 2010, X announces...", "In 1805, ..."). Same
  hand-rolled capitalized-literal idiom BecauseS/IfS/WhenS/AlthoughS
  already use, for the identical reason: OnPP/InPP/FromPP's own
  preposition words are hardcoded lowercase, with no capitalized variant,
  and this is the first time any of them needs to be sentence-initial.
- ParenNP : NP -> String -> NP -- a parenthetical acronym/gloss right
  after an NP ("the Foundation (HOLA)"). Same hand-rolled
  string-splicing idiom as ApposCommaPN1/ApposCommaPN2, parentheses
  instead of commas -- needs the engine's spaceAroundParens for the same
  reason ApposCommaPN1/ApposCommaPN2 needed spaceBeforeCommas (confirmed
  directly: without it, an unrelated existing rule, OpenPN3, silently
  absorbs the fused "(HOLA)" token instead).
- HePN/ShePN/ItPN/TheyPN : NP -- plain pronoun subjects/objects, RGL's
  own closed Pron vocabulary (already reachable via the open Syntax
  interface) through mkNP's own Pron -> NP overload. Previously entirely
  unsupported -- every NP-building rule needed a proper noun, a common
  noun, or a coordination of those.

These are pure Python tests against hand-built GF tree strings -- they do
not require a compiled grammar. They exercise the tree-walker's contract,
not whether the grammar actually compiles and parses real English
(verified locally against a real gf.exe build for every construct in
this file, and decisively by
tests/evaluation/test_gf_parse_diagnostic_matrix.py's real-sentence
regression cases in CI).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from contextual_rule_compiler import ARITIES, compile_gf_constraints  # noqa: E402

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


class NewConstructorArityTests(unittest.TestCase):
    def test_of_pp_takes_one_noun_phrase(self) -> None:
        self.assertEqual(ARITIES["OfPP"], 1)
        self.assertEqual(ARITIES["OfPP"], ARITIES["InPP"])

    def test_fronted_date_constructors_take_a_noun_phrase_and_a_sentence(self) -> None:
        for constructor in ("OnFrontedS", "InFrontedS", "FromFrontedS"):
            with self.subTest(constructor=constructor):
                self.assertEqual(ARITIES[constructor], 2)

    def test_paren_np_takes_a_noun_phrase_and_a_string(self) -> None:
        self.assertEqual(ARITIES["ParenNP"], 2)


class CompileGfConstraintsOfPPTests(unittest.TestCase):
    def test_of_pp_modifier_does_not_crash_the_walker(self) -> None:
        # "Waterloo captured a general of Alabama"
        proposal = base_proposal("Waterloo captured a general of Alabama")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Waterloo") '
            '(Compl Capture (ModifyNP '
            '(OpenIndefCN "general" "generals") '
            '(OfPP (OpenPN "Alabama"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")

    def test_chained_pp_modifiers_do_not_crash_the_walker(self) -> None:
        # ModifyNP recursing on its own output ("area of Hitchin in
        # Hertfordshire") is already valid abstract syntax with zero new
        # code -- confirmed directly against a real compiled grammar,
        # this just locks in that the Python side tolerates it too.
        proposal = base_proposal("Waterloo captured a general of Hitchin in Hertfordshire")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Waterloo") '
            '(Compl Capture (ModifyNP (ModifyNP '
            '(OpenIndefCN "general" "generals") '
            '(OfPP (OpenPN "Hitchin"))) '
            '(InPP (OpenPN "Hertfordshire"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)


class CompileGfConstraintsFrontedDateTests(unittest.TestCase):
    def test_on_fronted_s_finds_the_compl_in_the_main_clause(self) -> None:
        proposal = base_proposal("On 18 May 2010, Waterloo captured a general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'OnFrontedS (OpenPN3 "18" "May" "2010") '
            '(Pred (OpenPN "Waterloo") '
            '(Compl Capture (OpenIndefCN "general" "generals")))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")

    def test_in_fronted_s_and_from_fronted_s_walk_safely(self) -> None:
        for constructor in ("InFrontedS", "FromFrontedS"):
            with self.subTest(constructor=constructor):
                proposal = base_proposal("Waterloo captured a general")
                proposal["role"] = "SubjectHole"
                constraints = compile_gf_constraints(
                    proposal,
                    f'{constructor} (OpenPN "1805") '
                    '(Pred (OpenPN "Waterloo") '
                    '(Compl Capture (OpenIndefCN "general" "generals")))',
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                )
                self.assertEqual(len(constraints), 1)


class CompileGfConstraintsParenNPTests(unittest.TestCase):
    def test_a_parenthetical_acronym_subject_does_not_crash_the_walker(self) -> None:
        # "Waterloo (WLO) captured a general"
        proposal = base_proposal("Waterloo (WLO) captured a general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (ParenNP (OpenPN "Waterloo") "WLO") '
            '(Compl Capture (OpenIndefCN "general" "generals"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")


class CompileGfConstraintsPronounTests(unittest.TestCase):
    def test_pronoun_subjects_walk_safely(self) -> None:
        for constructor in ("HePN", "ShePN", "ItPN", "TheyPN", "IPN", "WePN", "YouPN"):
            with self.subTest(constructor=constructor):
                proposal = base_proposal("He captured a general")
                proposal["role"] = "SubjectHole"
                constraints = compile_gf_constraints(
                    proposal,
                    f"Pred {constructor} "
                    '(Compl Capture (OpenIndefCN "general" "generals"))',
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                )
                self.assertEqual(len(constraints), 1)
                self.assertEqual(
                    constraints[0]["origin"]["constructor"], "FrameArgument"
                )

    def test_pronoun_objects_are_a_safe_no_op(self) -> None:
        # A bare pronoun object gives _noun_lemma/gf_nouns nothing to
        # resolve a lemma from -- must not crash; produces no
        # constraint, the same safe-degradation behavior a bare proper
        # noun object already gets.
        proposal = base_proposal("Waterloo captured her")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Waterloo") (Compl Capture ShePN)',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(constraints, [])


if __name__ == "__main__":
    unittest.main()
