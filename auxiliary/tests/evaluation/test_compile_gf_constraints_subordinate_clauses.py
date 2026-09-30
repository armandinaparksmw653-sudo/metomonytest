"""compile_gf_constraints must safely traverse trees built with the two
newest grammar/Metonymy.gf additions, added directly in response to the
real, decisive text-free diagnostic in score_contextual_detection.py
(exit7_gf_sentence_signals): among the sentences still failing
gf-parse-empty after OpenPN2/OpenPN3, a comma is present in 87%/67% of
WiMCor/ConMeC's remaining rows -- far more than the 24%/3% that are still
a proper-noun-length issue OpenPN2/OpenPN3 don't cover. See
docs/contextual-tower.md's "Fronted/trailing subordinate clauses and
short comma appositives" section for the full reasoning, including why
an arbitrary-length comma-delimited appositive/parenthetical was
deliberately deferred (GF's String category matches exactly one token
during parsing -- the same confirmed limit that motivated OpenPN2/
OpenPN3 -- so a general free-text capture would need a fundamentally
different, higher-ambiguity-risk mechanism, not attempted here).

Two new constructor families:
- BecauseS/IfS/WhenS/AlthoughS (fronted: "because X, Y") and
  SBecauseS/SIfS/SWhenS/SAlthoughS (trailing: "Y, because X") -- built
  from RGL's closed Subj vocabulary (because_Subj/if_Subj/when_Subj/
  although_Subj) via SentenceEng's ExtAdvS/SSubjS, wrapping two full S
  values built from this grammar's own existing Pred/Compl/PredCopNP --
  no open-ended String parameter anywhere, so no PrepPP-class ambiguity
  risk.
- ApposCommaPN1/ApposCommaPN2 (short comma appositive, "Waterloo,
  Ontario, announces...") -- the same hand-rolled String-concatenation
  idiom OpenPN/OpenPN2/OpenPN3 already use, with a literal comma spliced
  into the NP's own string.

These are pure Python tests against hand-built GF tree strings -- they do
not require a compiled grammar. They exercise the tree-walker's contract,
not whether MetonymyEng.gf's new rules actually compile or parse real
English (verified only in CI/.cursor, and decisively by
tests/evaluation/test_gf_parse_diagnostic_matrix.py's real-sentence
regression cases).
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


class SubordinateClauseArityTests(unittest.TestCase):
    def test_fronted_subordinate_clause_constructors_take_two_sentences(self) -> None:
        for constructor in ("BecauseS", "IfS", "WhenS", "AlthoughS"):
            with self.subTest(constructor=constructor):
                self.assertEqual(ARITIES[constructor], 2)

    def test_trailing_subordinate_clause_constructors_take_two_sentences(self) -> None:
        for constructor in ("SBecauseS", "SIfS", "SWhenS", "SAlthoughS"):
            with self.subTest(constructor=constructor):
                self.assertEqual(ARITIES[constructor], 2)


class ApposCommaPNArityTests(unittest.TestCase):
    def test_apposcommapn1_takes_two_strings(self) -> None:
        self.assertEqual(ARITIES["ApposCommaPN1"], 2)

    def test_apposcommapn2_takes_three_strings(self) -> None:
        self.assertEqual(ARITIES["ApposCommaPN2"], 3)


class CompileGfConstraintsFrontedSubordinateClauseTests(unittest.TestCase):
    def test_finds_a_compl_node_in_the_main_clause_of_a_fronted_because_s(
        self,
    ) -> None:
        # "Because Napoleon approved it, Waterloo captured a general" --
        # first_node must recurse into BecauseS's own arguments (embedded
        # first, then main) to find the first Compl, exactly as it
        # already does for AndS/OrS.
        proposal = base_proposal("Because Napoleon approved it, Waterloo captured a general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'BecauseS '
            '(Pred (OpenPN "Napoleon") '
            '(Compl Capture (OpenIndefCN "general" "generals"))) '
            '(Pred (OpenPN "Waterloo") '
            '(Compl Capture (OpenIndefCN "general" "generals")))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")

    def test_if_when_although_all_walk_safely(self) -> None:
        for constructor in ("IfS", "WhenS", "AlthoughS"):
            with self.subTest(constructor=constructor):
                proposal = base_proposal("Waterloo captured a general")
                proposal["role"] = "SubjectHole"
                constraints = compile_gf_constraints(
                    proposal,
                    f'{constructor} '
                    '(Pred (OpenPN "Napoleon") '
                    '(Compl Capture (OpenIndefCN "general" "generals"))) '
                    '(Pred (OpenPN "Waterloo") '
                    '(Compl Capture (OpenIndefCN "general" "generals")))',
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                )
                self.assertEqual(len(constraints), 1)


class CompileGfConstraintsTrailingSubordinateClauseTests(unittest.TestCase):
    def test_finds_a_compl_node_in_the_main_clause_of_a_trailing_s_because_s(
        self,
    ) -> None:
        # "Waterloo captured a general, because Napoleon approved it" --
        # main clause is the *first* argument here (SBecauseS main
        # embedded), so first_node finds it without even needing to
        # recurse into the trailing embedded clause.
        proposal = base_proposal("Waterloo captured a general, because Napoleon approved it")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'SBecauseS '
            '(Pred (OpenPN "Waterloo") '
            '(Compl Capture (OpenIndefCN "general" "generals"))) '
            '(Pred (OpenPN "Napoleon") '
            '(Compl Capture (OpenIndefCN "plan" "plans")))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")

    def test_sif_swhen_salthough_all_walk_safely(self) -> None:
        for constructor in ("SIfS", "SWhenS", "SAlthoughS"):
            with self.subTest(constructor=constructor):
                proposal = base_proposal("Waterloo captured a general")
                proposal["role"] = "SubjectHole"
                constraints = compile_gf_constraints(
                    proposal,
                    f'{constructor} '
                    '(Pred (OpenPN "Waterloo") '
                    '(Compl Capture (OpenIndefCN "general" "generals"))) '
                    '(Pred (OpenPN "Napoleon") '
                    '(Compl Capture (OpenIndefCN "plan" "plans")))',
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                )
                self.assertEqual(len(constraints), 1)


class CompileGfConstraintsApposCommaPNTests(unittest.TestCase):
    def test_a_one_word_appositive_subject_does_not_crash_the_walker(self) -> None:
        # "Waterloo, Ontario, captured a general"
        proposal = base_proposal("Waterloo, Ontario, captured a general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (ApposCommaPN1 "Waterloo" "Ontario") '
            '(Compl Capture (OpenIndefCN "general" "generals"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")

    def test_a_two_word_appositive_subject_does_not_crash_the_walker(self) -> None:
        # "Waterloo, a small city, captured a general"
        proposal = base_proposal("Waterloo, a small city, captured a general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (ApposCommaPN2 "Waterloo" "small" "city") '
            '(Compl Capture (OpenIndefCN "general" "generals"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")


if __name__ == "__main__":
    unittest.main()
