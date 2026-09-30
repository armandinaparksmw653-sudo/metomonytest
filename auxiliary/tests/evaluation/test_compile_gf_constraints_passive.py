"""compile_gf_constraints must recognize PassCompl nodes exactly like Compl.

These are pure Python tests against hand-built GF tree strings -- they do
not require a compiled grammar. They exercise the tree-walker's contract
("if the compiler ever produces a tree shaped like this, does the Python
side handle it"), not whether MetonymyEng.gf's new PassCompl rule actually
compiles or parses real English (that needs the GF toolchain, verified
only in CI/.cursor -- see docs/contextual-tower.md).
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


class PassComplArityTests(unittest.TestCase):
    def test_pass_compl_has_the_same_arity_as_compl(self) -> None:
        self.assertEqual(ARITIES["PassCompl"], 2)
        self.assertEqual(ARITIES["PassCompl"], ARITIES["Compl"])


class CompileGfConstraintsPassiveTests(unittest.TestCase):
    def test_pass_compl_agent_that_is_the_bare_target_is_a_safe_no_op(self) -> None:
        # role="SubjectHole": the target itself ("Napoleon") fills the
        # PassCompl agent slot. A bare proper noun never resolves through
        # _noun_lemma/gf_nouns, so this must produce no constraints at all
        # -- the same protection Compl already relies on when the target
        # is a bare-proper-noun grammatical object.
        proposal = base_proposal("The city was captured by Napoleon")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "city") (PassCompl Capture (OpenPN "Napoleon"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(constraints, [])

    def test_pass_compl_agent_with_a_recognized_common_noun_yields_a_constraint(
        self,
    ) -> None:
        # role="ObjectHole": the target is the passive *subject* (patient),
        # the PassCompl agent slot ("a general") is a separate argument --
        # its own WordNet sort should drive a FrameArgument constraint,
        # exactly like Compl's object slot does for an active sentence.
        proposal = base_proposal("The city was captured by a general")
        proposal["role"] = "ObjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "city") '
            '(PassCompl Capture (OpenIndefCN "general" "generals"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")
        self.assertEqual(constraints[0]["payload"], {"requires": "HasSort Place"})

    def test_first_node_still_finds_a_plain_compl_node_unchanged(self) -> None:
        proposal = base_proposal("Waterloo captured a general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Waterloo") '
            '(Compl Capture (OpenIndefCN "general" "generals"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")


if __name__ == "__main__":
    unittest.main()
