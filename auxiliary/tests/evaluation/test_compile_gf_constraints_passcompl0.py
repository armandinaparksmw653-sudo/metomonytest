"""compile_gf_constraints must safely traverse a tree built with this
round's new grammar/Metonymy.gf constructor, PassCompl0 : V2 -> VP -- a
bare/agentless passive ("Henry is announced"), added alongside the
governing_start tree-builder's own new PassCompl0-building branch in
scripts/build_gf_tree_from_dependencies.py's _clause. Verified locally
against gf.exe/pinned gf-rgl before this file was written:
`l -lang=MetonymyEng (Pred (OpenPN "Henry") (PassCompl0 Announce))` ->
"Henry is announced"; the existing agent-present
`(PassCompl Announce (OpenPN "Waterloo"))` re-checked unaffected ->
"Henry is announced by Waterloo".

Deliberately not added to first_node's {"Compl", "PassCompl"} set (see
contextual_rule_compiler.py's own ARITIES/first_node) -- PassCompl0 has
no agent NP to derive a FrameArgument constraint from anyway, so a tree
built purely from it is a safe no-op, the same "degrade gracefully on
an unrecognized/incomplete node shape" behavior PredCopNP's own tests
already established for a differently-shaped VP-less tree.
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


def base_proposal(sentence: str, action: str = "announce") -> dict:
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
                    "surface": "announced",
                    "start": 0,
                    "end": 8,
                },
                "payload": {"requires": "HasSort Entity"},
                "provenance": "test:VerbNet:" + action,
            }
        ],
    }


class NewConstructorArityTests(unittest.TestCase):
    def test_pass_compl0_takes_one_verb(self) -> None:
        self.assertEqual(ARITIES["PassCompl0"], 1)


class CompileGfConstraintsPassCompl0Tests(unittest.TestCase):
    def test_an_agentless_passive_tree_is_a_safe_no_op_not_a_crash(self) -> None:
        proposal = base_proposal("Henry is announced")
        proposal["role"] = "ObjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Henry") (PassCompl0 Announce)',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(constraints, [])

    def test_an_agent_present_passive_elsewhere_is_still_found(self) -> None:
        # Sanity check that adding PassCompl0 didn't disturb the
        # existing agent-present PassCompl-finding path. A common-noun
        # agent (not a bare proper noun -- _noun_lemma only resolves a
        # lemma from OpenIndefCN/OpenDefCN/OpenAdjDefCN/OpenAdjIndefCN,
        # the same reason test_compile_gf_constraints_batch2.py's own
        # test_pronoun_objects_are_a_safe_no_op gives 0 constraints for
        # a bare pronoun object -- confirmed directly, not assumed,
        # before writing this assertion).
        proposal = base_proposal("Henry was announced by a general")
        proposal["role"] = "ObjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Henry") '
            '(PassCompl Announce (OpenIndefCN "general" "generals"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)


if __name__ == "__main__":
    unittest.main()
