"""compile_gf_constraints must safely traverse trees built with three new
grammar/Metonymy.gf constructors added together after two consecutive
contextual-tower-evaluation.yml runs measured zero effect from earlier,
individually-verified additions (S-coordination+8 prepositions, then
VP-coordination). Local diagnosis on the real corpus sample found why:
79% of sentences containing "and"/"or" *also* contain a comma marking a
different, still-unaddressed construction -- grammar gaps overlap
heavily within the same sentences, so single-construction fixes rarely
flip any sentence from unparseable to parseable. This batch closes three
more gaps identified from the same sample, all verified against the
pinned gf-rgl commit's actual source and none needing a *new* `open`
(SyntaxEng/ExtraEng are already open from earlier work, and ExtraEng's
only two collisions were already found and qualified):

- PredCopNP : NP -> NP -> S -- copula predication ("Henry County is a
  county in ..."). Compl/PassCompl were the *only* VP-building rules
  before this, both requiring a V2, so a bare "NP is NP2" sentence had
  no derivation at all. Via Constructors.gf's mkCl : NP -> NP -> Cl.
- ModifyRelVP/ModifyRelCNVP : NP/CN -> VP -> NP/CN -- generalizes
  ModifyRel/ModifyRelCN (hardcoded to a V2+object pair) to an arbitrary
  VP, via mkRCl's own general RP -> VP -> RCl overload (the one
  ModifyRel already routes through internally) -- lets a relative clause
  use Compl, PassCompl, or any future VP-building rule uniformly.
- PossNP : NP -> CN -> NP -- possessive/genitive ("Tolstoy's works" as a
  live construction), via Extra.gf's GenNP : NP -> Quant combined with
  the already-confirmed mkNP : Quant -> CN -> NP.

These are pure Python tests against hand-built GF tree strings -- they do
not require a compiled grammar. They exercise the tree-walker's contract
("if the compiler ever produces a tree shaped like this, does the Python
side handle it"), not whether MetonymyEng.gf's new rules actually compile
or parse real English (that needs the GF toolchain, verified only in
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


class NewConstructorArityTests(unittest.TestCase):
    def test_pred_cop_np_takes_two_noun_phrases(self) -> None:
        self.assertEqual(ARITIES["PredCopNP"], 2)

    def test_modify_rel_vp_variants_take_a_head_and_a_verb_phrase(self) -> None:
        self.assertEqual(ARITIES["ModifyRelVP"], 2)
        self.assertEqual(ARITIES["ModifyRelCNVP"], 2)

    def test_poss_np_takes_a_possessor_and_a_common_noun(self) -> None:
        self.assertEqual(ARITIES["PossNP"], 2)


class CompileGfConstraintsCopulaTests(unittest.TestCase):
    def test_a_pure_copula_tree_is_a_safe_no_op_not_a_crash(self) -> None:
        # "Henry County is a county in Alabama" -- no Compl/PassCompl
        # anywhere in the tree at all, since PredCopNP builds an S
        # directly from two NPs. first_node must return None here, and
        # the surrounding code must degrade gracefully (no constraint),
        # not crash on a tree shape it has never seen before.
        proposal = base_proposal("Henry County is a county in Alabama")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'PredCopNP (OpenPN "Henry County") '
            '(DefCN (OpenIndefCN "county" "counties"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(constraints, [])

    def test_a_compl_elsewhere_in_a_larger_tree_is_still_found(self) -> None:
        # Sanity check that adding PredCopNP support didn't disturb the
        # existing Compl-finding path for trees that do have one.
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


class CompileGfConstraintsModifyRelVPTests(unittest.TestCase):
    def test_finds_a_compl_inside_modify_rel_vp(self) -> None:
        # "Waterloo captured the general who signed the treaty" -- the
        # outer Compl's object is a ModifyRelVP-wrapped NP. first_node
        # finds the *outer* Compl first (depth-first order reaches it
        # before descending into its own object), and lexical_head must
        # now unwrap ModifyRelVP the same way it already unwraps
        # ModifyRel/ModifyRelCN, to reach the underlying "general" head
        # noun rather than stopping at the ModifyRelVP node itself.
        proposal = base_proposal("Waterloo captured the general who signed the treaty")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Waterloo") '
            '(Compl Capture (ModifyRelVP '
            '(DefCN (OpenIndefCN "general" "generals")) '
            '(Compl Capture (OpenIndefCN "treaty" "treaties"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")

    def test_modify_rel_cn_vp_is_also_unwrapped_by_lexical_head(self) -> None:
        proposal = base_proposal("Waterloo captured the general who signed the treaty")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Waterloo") '
            '(Compl Capture (DefCN (ModifyRelCNVP '
            '(OpenIndefCN "general" "generals") '
            '(Compl Capture (OpenIndefCN "treaty" "treaties")))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0]["origin"]["constructor"], "FrameArgument")


class CompileGfConstraintsPossNPTests(unittest.TestCase):
    def test_a_possessive_object_does_not_crash_the_walker(self) -> None:
        # "Waterloo captured Napoleon's general" -- PossNP is a shape
        # _noun_lemma/gf_nouns don't resolve a lemma from (like AndNP),
        # so this is a safe no-op, not a crash.
        proposal = base_proposal("Waterloo captured Napoleon's general")
        proposal["role"] = "SubjectHole"
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Waterloo") '
            '(Compl Capture (PossNP (OpenPN "Napoleon") '
            '(OpenIndefCN "general" "generals")))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        self.assertEqual(constraints, [])


if __name__ == "__main__":
    unittest.main()
