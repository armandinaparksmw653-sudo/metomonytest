"""Data-integrity checks for data/contextual-language-rules.json.

compile_gf_constraints raises a hard ValueError if a composition_matrix
result_sort has no matching action_object_requirements entry for the
action in play (contextual_rule_compiler.py:626-628) -- turning "unknown
adjective+noun pair fails closed" into a crash instead. These tests run
the real committed JSON (not a hand-built fixture) through the actual
adjective-noun composition path for every newly-added sort, so a future
edit that adds a composition_matrix row without its action_object_requirements
counterpart is caught locally, not only by CI.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from contextual_rule_compiler import compile_gf_constraints  # noqa: E402

LANGUAGE_RULES = json.loads(
    (ROOT / "auxiliary/data/contextual-language-rules.json").read_text(encoding="utf-8")
)
WORDNET_RULES = json.loads(
    (ROOT / "auxiliary/data/wordnet-context-rules.json").read_text(encoding="utf-8")
)


def base_proposal(action: str, sentence: str) -> dict:
    return {
        "action": action,
        "sentence": sentence,
        "frames": [],
        "provenance": {"action": f"test:{action}"},
        "constraints": [
            {
                "origin": {
                    "constructor": "Verb",
                    "lemma": action,
                    "surface": action,
                    "start": 0,
                    "end": len(action),
                },
                "payload": {"requires": "HasSort Agent"},
                "provenance": f"test:{action}",
            }
        ],
    }


class CompositionMatrixCoverageTests(unittest.TestCase):
    def test_every_composition_matrix_result_sort_used_by_sign_or_announce_has_a_rule(
        self,
    ) -> None:
        sign_sorts = set(LANGUAGE_RULES["action_object_requirements"]["sign"])
        announce_sorts = set(LANGUAGE_RULES["action_object_requirements"]["announce"])
        for row in LANGUAGE_RULES["composition_matrix"]:
            result_sort = row["result_sort"]
            self.assertTrue(
                result_sort in sign_sorts or result_sort in announce_sorts,
                f"{result_sort} (from {row['modifier_sort']}×{row['noun_sort']}) has "
                "no action_object_requirements entry for sign or announce",
            )

    def _compose(self, action: str, adjective: str, noun: str) -> list[dict]:
        sentence = f"Waterloo {action}d a {adjective} {noun}"
        proposal = base_proposal(action, sentence)
        tree = (
            f'Pred (OpenPN "Waterloo") '
            f'(Compl {action.capitalize()} '
            f'(OpenAdjIndefCN "{adjective}" "{noun}" "{noun}s"))'
        )
        return compile_gf_constraints(
            proposal, tree, LANGUAGE_RULES, WORDNET_RULES, {}
        )

    # Each composition also produces a base FrameArgument constraint from
    # the bare noun's own WordNet sort (e.g. plain "agreement"), *ahead of*
    # the FrameComposition constraint the adjective+noun pair drives -- see
    # compile_gf_constraints: the top-level Compl object is analyzed before
    # walk() recurses into the same node. Both are legitimate, independent
    # constraints on the same candidate fiber; these tests check the
    # composed one specifically (constraints[-1]).

    def test_scientific_agreement_composes_without_raising(self) -> None:
        constraints = self._compose("sign", "scientific", "agreement")
        self.assertEqual(len(constraints), 2)
        self.assertEqual(
            constraints[-1]["payload"],
            {"requires": "AnyOf [HasSort Organization,HasSort Institution]"},
        )

    def test_educational_agreement_composes_without_raising(self) -> None:
        constraints = self._compose("announce", "educational", "agreement")
        self.assertEqual(len(constraints), 2)

    def test_political_programme_composes_without_raising(self) -> None:
        constraints = self._compose("sign", "political", "programme")
        self.assertEqual(len(constraints), 2)
        self.assertEqual(
            constraints[-1]["payload"],
            {"requires": "AnyOf [HasSort Government,HasSort PoliticalOrganization]"},
        )

    def test_commercial_programme_composes_without_raising(self) -> None:
        constraints = self._compose("announce", "commercial", "programme")
        self.assertEqual(len(constraints), 2)
        self.assertEqual(
            constraints[-1]["payload"], {"requires": "HasSort BusinessOrganization"}
        )

    def test_political_institution_still_resolves_to_the_shared_institution_rule(
        self,
    ) -> None:
        constraints = self._compose("sign", "political", "institution")
        self.assertEqual(len(constraints), 2)
        self.assertEqual(
            constraints[-1]["payload"],
            {"requires": "AnyOf [HasSort Organization,HasSort Institution]"},
        )


class ProvenanceHonestyTests(unittest.TestCase):
    """Every FrameNet-labeled provenance string must cite a real frame/FE."""

    REAL_FRAME_FE = {
        ("Sign_agreement", "Signatory"),
        ("Sign_agreement", "Co-participant"),
        ("Statement", "Speaker"),
        ("Reading_perception", "Reader"),
        ("Topic", "Topic"),
        ("Purpose", "Goal"),
    }

    def _check(self, provenance: str, label: str) -> None:
        if not provenance.startswith("FrameNet:"):
            return
        framenet_part = provenance.split("+", 1)[0]
        _, frame, fe, *rest = framenet_part.split(":")
        self.assertIn(
            (frame, fe),
            self.REAL_FRAME_FE,
            f"{label}: {frame}:{fe} is not a verified FrameNet frame/FE "
            "pair (see data/SOURCES.md)",
        )

    def test_every_action_object_requirement_cites_a_verified_frame_and_fe(
        self,
    ) -> None:
        for action, entries in LANGUAGE_RULES["action_object_requirements"].items():
            for result_sort, rule in entries.items():
                self._check(rule["provenance"], f"{action}.{result_sort}")

    def test_every_context_template_cites_a_verified_frame_and_fe(self) -> None:
        for index, template in enumerate(LANGUAGE_RULES["context_templates"]):
            self._check(
                template["provenance"],
                f"context_templates[{index}] ({template['construction']})",
            )

    def test_narrowed_sorts_are_explicitly_tagged_local(self) -> None:
        # Any requirement stricter than the base HasSort Agent/Organization
        # fallback must say so in its own provenance, not read as a bare
        # FrameNet citation for a fact FrameNet doesn't actually attest.
        for action, entries in LANGUAGE_RULES["action_object_requirements"].items():
            for result_sort, rule in entries.items():
                if "AnyOf [HasSort Government" in rule["candidate_requirement"] or (
                    rule["candidate_requirement"] == "HasSort BusinessOrganization"
                ):
                    self.assertIn(
                        "local:sort-narrowing",
                        rule["provenance"],
                        f"{action}.{result_sort} narrows beyond the base "
                        "FrameNet-attested requirement without saying so",
                    )


if __name__ == "__main__":
    unittest.main()
