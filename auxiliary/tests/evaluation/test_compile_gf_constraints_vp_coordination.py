"""compile_gf_constraints must safely traverse trees built with
grammar/Metonymy.gf's PredConjVP/PredOrConjVP -- Phase 1 of the grammar-
expansion plan (see docs/contextual-tower.md and the plan file's
"Расширение GF-грамматики" section).

AndS/OrS (already shipped) only join two *full* clauses, each with its
own subject repeated in the surface text ("X did A and X did B") -- but
real "and" in corpus text is overwhelmingly VP coordination with a
*shared* subject ("X did A and did B", subject not repeated), which is
exactly why adding AndS/OrS plus eight new prepositions measured zero
effect on a real contextual-tower-evaluation.yml run: the sentences that
actually contain "and" mostly needed this shape, not sentence-level
coordination. PredConjVP/PredOrConjVP cover it via RGL's Extra.gf VPS/
MkVPS/ConjVPS/PredVPS machinery (verified against the pinned gf-rgl
commit's actual source, not guessed), using Constructors.gf's
presentTense/simultaneousAnt/positivePol/mkTemp convenience constants
(already reachable via the existing `open SyntaxEng` -- only ExtraEng
needed adding for VPS itself).

Getting ExtraEng compiling cleanly took two rounds: opening it made two
pre-existing unqualified calls ambiguous, since Extra.gf independently
redeclares both PassAgentVPSlash (already used from Extend/ExtendEng for
the passive-voice work) and which_RP (already used from
Constructors/SyntaxEng for ModifyRel/ModifyRelCN) with identical
signatures/types. Both are now explicitly qualified
(ExtendEng.PassAgentVPSlash, SyntaxEng.which_RP) -- see the comments at
each call site in MetonymyEng.gf, and the real CI compiler's own
ambiguity warnings ("conflict ExtraEng.X, OriginalModule.X") that
confirmed both, rather than guessing.

These are pure Python tests against hand-built GF tree strings -- they do
not require a compiled grammar. They exercise the tree-walker's contract
("if the compiler ever produces a tree shaped like this, does the Python
side handle it"), not whether MetonymyEng.gf's new rule actually compiles
or parses real English (that needs the GF toolchain, verified only in
CI/.cursor).
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


class PredConjVPArityTests(unittest.TestCase):
    def test_pred_conj_vp_takes_a_subject_and_two_verb_phrases(self) -> None:
        self.assertEqual(ARITIES["PredConjVP"], 3)

    def test_pred_or_conj_vp_takes_a_subject_and_two_verb_phrases(self) -> None:
        self.assertEqual(ARITIES["PredOrConjVP"], 3)


class CompileGfConstraintsVpCoordinationTests(unittest.TestCase):
    def test_finds_a_compl_in_the_first_verb_phrase(self) -> None:
        # "Waterloo captured a general and signed a treaty" -- shared
        # subject, exactly the shape AndS could not represent.
        proposal = base_proposal("Waterloo captured a general and signed a treaty")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Waterloo") '
            '(Compl Capture (OpenIndefCN "general" "generals")) '
            '(Compl Capture (OpenIndefCN "treaty" "treaties"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")

    def test_pred_or_conj_vp_does_not_crash_the_walker(self) -> None:
        proposal = base_proposal("Waterloo captured a general or signed a treaty")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'PredOrConjVP (OpenPN "Waterloo") '
            '(Compl Capture (OpenIndefCN "general" "generals")) '
            '(Compl Capture (OpenIndefCN "treaty" "treaties"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)


if __name__ == "__main__":
    unittest.main()
