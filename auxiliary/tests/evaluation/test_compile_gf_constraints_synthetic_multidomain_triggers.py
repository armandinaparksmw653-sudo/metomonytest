"""Synthetic multi-domain expansion of the (lemma, construction) ->
constraint context-trigger dictionary (data/contextual-context-
triggers.json), added after a full-corpus real-example search
(WiMCor test split, ConMeC) found the mechanism only has usable
material in the University domain, and never combines two
independent trigger signals in one real sentence -- every real
example this project has built (Valparaiso/Haifa/Pisa/UCLA/
Berklee/Padgate) is exactly "weak base action constraint + one
trigger" (2 stages), never a genuine 3+-stage "tower".

This file is honestly SYNTHETIC, not corpus-derived: every new
dictionary entry's provenance says so explicitly, and every
strength is "prefers" (never "requires") -- these constructed
sentences were never checked against a real corpus or live
Wikidata, unlike degree/doctorate/fraternity/diploma/certificate
above them in the same JSON file. The purpose is narrower than
raising real recall: (1) show the (construction, lemma) -> Sort
mechanism generalizes to many metonymy families using only the
47 Sort constants that already exist in engine/src/Metonymy/
Types.hs (zero Haskell/Agda risk), and (2) build explicit,
verified examples of a genuine multi-constraint tower -- two
INDEPENDENT trigger signals landing on the same target from
different tree positions, narrowing across two different Sorts
in one sentence, which real corpus search never turned up.

All lemmas reuse only the 12 already-stable, already-gf.exe-
verified V2s this session has built up (Announce/Read/Drink/Sign
plus the 8 data/predicates.tsv verbs) -- no new grammar, no new
hash-named CTX_*/WN_* lookups. Every distinct tree SHAPE below
(not every lemma -- substituting a different OpenIndefCN string
does not change grammaticality) was verified via local gf.exe
(`l -lang=GeneratedMetonymyEng`) before being written here, same
discipline as test_compile_gf_constraints_context_triggers.py.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from contextual_rule_compiler import compile_gf_constraints  # noqa: E402

LANGUAGE_RULES = {
    "schema_version": "test-1",
    "frame_argument_capabilities": [],
    "context_templates": [],
}

WORDNET_RULES = {
    # A non-empty lexical_sorts is required -- compile_gf_constraints
    # early-returns [] when it's empty (an unrelated existing guard,
    # not part of this mechanism); the entry itself is never looked up
    # by any test below.
    "lexical_sorts": {"county": {"requirement": "HasSort Place", "provenance": "test:wordnet"}},
    "adjective_sorts": {},
}

# Mirror of engine/src/Metonymy/Types.hs's Sort enum (47 constructors).
# Keep in sync by hand if that enum ever changes -- this list is what
# SortVocabularyCoverageTests checks every requirement string against.
KNOWN_SORTS = {
    "Entity",
    "Human",
    "Writer",
    "LiteraryWork",
    "Readable",
    "Container",
    "Drinkable",
    "Place",
    "Institution",
    "Agent",
    "Animate",
    "Organization",
    "Agreement",
    "MusicalWork",
    "Audible",
    "Film",
    "Watchable",
    "Food",
    "Edible",
    "Clothing",
    "Wearable",
    "Brand",
    "HumanGroup",
    "Event",
    "Artifact",
    "Product",
    "Producer",
    "Content",
    "Result",
    "Possessor",
    "LocatedEntity",
    "GenericReading",
    "University",
    "ResearchInstitution",
    "Programme",
    "ResearchProgramme",
    "ScientificDiscipline",
    "CommunicationContent",
    "Government",
    "PoliticalOrganization",
    "BusinessOrganization",
    "PoliticalAgreement",
    "CommercialAgreement",
    "Political",
    "Commercial",
}


def base_proposal(sentence: str, action: str = "announce") -> dict:
    return {
        "action": action,
        "sentence": sentence,
        "role": "ObjectHole",
        "frames": [],
        "provenance": {"action": "test:VerbNet:" + action},
        "constraints": [
            {
                "origin": {
                    "constructor": "Verb",
                    "lemma": action,
                    "surface": "announces",
                    "start": 0,
                    "end": len(sentence.split()[0]) + 1 + len(action) + 1,
                },
                "payload": {"prefers": "HasSort Entity"},
                "provenance": "test:VerbNet:" + action,
            }
        ],
    }


def _trigger_constraints(constraints: list, construction: str) -> list:
    return [
        c for c in constraints
        if c["origin"]["constructor"] == f"ContextTrigger:{construction}"
    ]


class SortVocabularyCoverageTests(unittest.TestCase):
    """Every requirement string in the real, shipped dictionary
    must parse as `HasSort <Sort>` with <Sort> a real Types.hs constructor
    -- catches a typo across all ~83 entries at once, since nothing on
    the Python side validates this at runtime (compile_gf_constraints
    copies the string through unexamined).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.triggers = json.loads(
            (ROOT / "auxiliary/data" / "contextual-context-triggers.json").read_text(
                encoding="utf-8"
            )
        )["triggers"]

    def test_every_requirement_is_a_known_sort(self) -> None:
        pattern = re.compile(r"^HasSort ([A-Za-z][A-Za-z0-9]*)$")
        for trigger in self.triggers:
            with self.subTest(construction=trigger["construction"], lemma=trigger["lemma"]):
                match = pattern.match(trigger["requirement"])
                self.assertIsNotNone(
                    match,
                    f"requirement {trigger['requirement']!r} does not match HasSort <Sort>",
                )
                self.assertIn(match.group(1), KNOWN_SORTS)


class TriggerDictionaryHygieneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.triggers = json.loads(
            (ROOT / "auxiliary/data" / "contextual-context-triggers.json").read_text(
                encoding="utf-8"
            )
        )["triggers"]

    def test_construction_and_strength_are_from_the_closed_vocabulary(self) -> None:
        known_constructions = {"ConjClauseObject", "ModifyNPObject", "RelativeClauseObject"}
        for trigger in self.triggers:
            with self.subTest(construction=trigger["construction"], lemma=trigger["lemma"]):
                self.assertIn(trigger["construction"], known_constructions)
                self.assertIn(trigger["strength"], {"requires", "prefers"})
                self.assertTrue(trigger["provenance"])

    def test_synthetic_entries_are_honestly_labeled_and_never_requires(self) -> None:
        for trigger in self.triggers:
            if "synthetic-curated" not in trigger["provenance"]:
                continue
            with self.subTest(construction=trigger["construction"], lemma=trigger["lemma"]):
                self.assertEqual(trigger["strength"], "prefers")


class UniversityFamilyTriggerTests(unittest.TestCase):
    """Synthetic university family -> HasSort University. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['scholarship', 'thesis', 'syllabus', 'semester', 'graduate', 'professorship', 'faculty']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort University",
                            "strength": "prefers",
                            "provenance": "test:synthetic:university",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort University"},
                )

    def test_modifynpobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['campus']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ModifyNPObject",
                            "lemma": lemma,
                            "requirement": "HasSort University",
                            "strength": "prefers",
                            "provenance": "test:synthetic:university",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'Pred (OpenPN "He") (Compl Announce (ModifyNP '
                    f'(OpenPN "Ashford") (FromPP (OpenIndefCN "{lemma}" "{lemma}s"))))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ModifyNPObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort University"},
                )


class ResearchInstitutionFamilyTriggerTests(unittest.TestCase):
    """Synthetic research-institution family -> HasSort ResearchInstitution. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['laboratory', 'grant', 'fellowship', 'symposium']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort ResearchInstitution",
                            "strength": "prefers",
                            "provenance": "test:synthetic:research-institution",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort ResearchInstitution"},
                )


class ScientificDisciplineFamilyTriggerTests(unittest.TestCase):
    """Synthetic scientific-discipline family -> HasSort ScientificDiscipline. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['theorem', 'hypothesis', 'formula', 'dissertation']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort ScientificDiscipline",
                            "strength": "prefers",
                            "provenance": "test:synthetic:scientific-discipline",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort ScientificDiscipline"},
                )


class GovernmentFamilyTriggerTests(unittest.TestCase):
    """Synthetic government family -> HasSort Government. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['parliament', 'cabinet', 'ministry', 'ballot']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Government",
                            "strength": "prefers",
                            "provenance": "test:synthetic:government",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Government"},
                )


class PoliticalOrganizationFamilyTriggerTests(unittest.TestCase):
    """Synthetic political-organization family -> HasSort PoliticalOrganization. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['manifesto', 'caucus', 'delegate', 'campaign']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort PoliticalOrganization",
                            "strength": "prefers",
                            "provenance": "test:synthetic:political-organization",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort PoliticalOrganization"},
                )


class BusinessOrganizationFamilyTriggerTests(unittest.TestCase):
    """Synthetic business-organization family -> HasSort BusinessOrganization. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['shareholder', 'merger', 'subsidiary', 'franchise']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort BusinessOrganization",
                            "strength": "prefers",
                            "provenance": "test:synthetic:business-organization",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort BusinessOrganization"},
                )

    def test_relativeclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['contract', 'tender']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "RelativeClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort BusinessOrganization",
                            "strength": "prefers",
                            "provenance": "test:synthetic:business-organization",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'Pred (OpenPN "He") (Compl Announce (ModifyRelAtVP '
                    '(OpenPN "Ashford") (OpenPN "He") '
                    f'(PassComplRetained Award (OpenIndefCN "{lemma}" "{lemma}s"))))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "RelativeClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort BusinessOrganization"},
                )


class LiteraryWorkFamilyTriggerTests(unittest.TestCase):
    """Synthetic literary-work family -> HasSort LiteraryWork. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['manuscript', 'chapter', 'preface', 'bibliography', 'glossary', 'foreword']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort LiteraryWork",
                            "strength": "prefers",
                            "provenance": "test:synthetic:literary-work",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort LiteraryWork"},
                )


class MusicalWorkFamilyTriggerTests(unittest.TestCase):
    """Synthetic musical-work family -> HasSort MusicalWork. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['record', 'chorus', 'verse', 'symphony', 'concerto']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort MusicalWork",
                            "strength": "prefers",
                            "provenance": "test:synthetic:musical-work",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort MusicalWork"},
                )


class FilmFamilyTriggerTests(unittest.TestCase):
    """Synthetic film family -> HasSort Film. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['screenplay', 'cast', 'premiere', 'sequel']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Film",
                            "strength": "prefers",
                            "provenance": "test:synthetic:film",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Film"},
                )


class BrandFamilyTriggerTests(unittest.TestCase):
    """Synthetic brand family -> HasSort Brand. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['trademark', 'logo', 'flagship', 'billboard']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Brand",
                            "strength": "prefers",
                            "provenance": "test:synthetic:brand",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Brand"},
                )


class ProducerFamilyTriggerTests(unittest.TestCase):
    """Synthetic producer family -> HasSort Producer. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['factory', 'conveyor', 'workshop']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Producer",
                            "strength": "prefers",
                            "provenance": "test:synthetic:producer",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Producer"},
                )


class ProductFamilyTriggerTests(unittest.TestCase):
    """Synthetic product family -> HasSort Product. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['prototype', 'patent']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Product",
                            "strength": "prefers",
                            "provenance": "test:synthetic:product",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Product"},
                )


class ClothingFamilyTriggerTests(unittest.TestCase):
    """Synthetic clothing family -> HasSort Clothing. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['collection', 'runway', 'tailor', 'silhouette']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Clothing",
                            "strength": "prefers",
                            "provenance": "test:synthetic:clothing",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Clothing"},
                )

    def test_modifynpobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['boutique']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ModifyNPObject",
                            "lemma": lemma,
                            "requirement": "HasSort Clothing",
                            "strength": "prefers",
                            "provenance": "test:synthetic:clothing",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'Pred (OpenPN "He") (Compl Announce (ModifyNP '
                    f'(OpenPN "Ashford") (FromPP (OpenIndefCN "{lemma}" "{lemma}s"))))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ModifyNPObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Clothing"},
                )

    def test_relativeclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['commission']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "RelativeClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Clothing",
                            "strength": "prefers",
                            "provenance": "test:synthetic:clothing",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'Pred (OpenPN "He") (Compl Announce (ModifyRelAtVP '
                    '(OpenPN "Ashford") (OpenPN "He") '
                    f'(PassComplRetained Award (OpenIndefCN "{lemma}" "{lemma}s"))))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "RelativeClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Clothing"},
                )


class FoodFamilyTriggerTests(unittest.TestCase):
    """Synthetic food family -> HasSort Food. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['recipe', 'menu', 'harvest', 'kitchen']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Food",
                            "strength": "prefers",
                            "provenance": "test:synthetic:food",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Food"},
                )


class DrinkableFamilyTriggerTests(unittest.TestCase):
    """Synthetic drinkable family -> HasSort Drinkable. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['vintage', 'vineyard', 'distillery', 'brewery', 'cellar']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Drinkable",
                            "strength": "prefers",
                            "provenance": "test:synthetic:drinkable",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Drinkable"},
                )

    def test_modifynpobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['vineyard']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ModifyNPObject",
                            "lemma": lemma,
                            "requirement": "HasSort Drinkable",
                            "strength": "prefers",
                            "provenance": "test:synthetic:drinkable",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'Pred (OpenPN "He") (Compl Announce (ModifyNP '
                    f'(OpenPN "Ashford") (FromPP (OpenIndefCN "{lemma}" "{lemma}s"))))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ModifyNPObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Drinkable"},
                )


class CommunicationFamilyTriggerTests(unittest.TestCase):
    """Synthetic communication family -> HasSort CommunicationContent. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['broadcast', 'bulletin', 'briefing', 'statement', 'headline']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort CommunicationContent",
                            "strength": "prefers",
                            "provenance": "test:synthetic:communication",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort CommunicationContent"},
                )

    def test_modifynpobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['broadcast']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ModifyNPObject",
                            "lemma": lemma,
                            "requirement": "HasSort CommunicationContent",
                            "strength": "prefers",
                            "provenance": "test:synthetic:communication",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'Pred (OpenPN "He") (Compl Announce (ModifyNP '
                    f'(OpenPN "Ashford") (FromPP (OpenIndefCN "{lemma}" "{lemma}s"))))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ModifyNPObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort CommunicationContent"},
                )


class ProgrammeFamilyTriggerTests(unittest.TestCase):
    """Synthetic programme family -> HasSort Programme. See
    data/contextual-context-triggers.json's synthetic-curated
    entries for this family's provenance strings."""

    def test_conjclauseobject_lemmas_produce_the_trigger_constraint(self) -> None:
        lemmas = ['segment', 'rundown']
        for lemma in lemmas:
            with self.subTest(lemma=lemma):
                context_triggers = {
                    "triggers": [
                        {
                            "construction": "ConjClauseObject",
                            "lemma": lemma,
                            "requirement": "HasSort Programme",
                            "strength": "prefers",
                            "provenance": "test:synthetic:programme",
                        }
                    ]
                }
                proposal = base_proposal(f"He announces Ashford and announces a {lemma}")
                tree = (
                    'PredConjVP (OpenPN "He") '
                    '(Compl Announce (OpenPN "Ashford")) '
                    f'(Compl Announce (OpenIndefCN "{lemma}" "{lemma}s"))'
                )
                constraints = compile_gf_constraints(
                    proposal,
                    tree,
                    LANGUAGE_RULES,
                    WORDNET_RULES,
                    {},
                    context_triggers=context_triggers,
                )
                trigger_constraints = _trigger_constraints(constraints, "ConjClauseObject")
                self.assertEqual(len(trigger_constraints), 1)
                self.assertEqual(
                    trigger_constraints[0]["payload"],
                    {"prefers": "HasSort Programme"},
                )


class MultiConstraintTowerTests(unittest.TestCase):
    """Flagship examples: two INDEPENDENT context-trigger signals
    landing on the same target from two different tree positions in one
    sentence, narrowing across two different Sorts. Real corpus search
    (this session, WiMCor test split + ConMeC, full sets) never found a
    single sentence combining two independent trigger signals -- every
    real example is exactly one base constraint + one trigger. These are
    the counter-demonstration: the MECHANISM already supports it (see
    scripts/contextual_rule_compiler.py's ConjClauseObject/ModifyNPObject/
    RelativeClauseObject -- none of the three gate on hole role, and
    ModifyNPObject's walk() is fully recursive, independent of
    ConjClauseObject's coordinated-sibling-only loop), just never needed
    on real data so far. Every tree verified via local gf.exe.
    """

    def test_tower_university_research(self) -> None:
        # 'He announces Ashford on a campus and announces a grant'
        context_triggers = {
            "triggers": [
                {
                    "construction": "ModifyNPObject",
                    "lemma": "campus",
                    "requirement": "HasSort University",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-university-research",
                },
                {
                    "construction": "ConjClauseObject",
                    "lemma": "grant",
                    "requirement": "HasSort ResearchInstitution",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-university-research",
                },
            ]
        }
        proposal = base_proposal('He announces Ashford on a campus and announces a grant')
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "He") (Compl Announce (ModifyNP (OpenPN "Ashford") (OnPP (OpenIndefCN "campus" "campuses")))) (Compl Announce (OpenIndefCN "grant" "grants"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(len(trigger_constraints), 2)
        payloads = {
            frozenset(c["payload"].items()) for c in trigger_constraints
        }
        self.assertEqual(len(payloads), 2)
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ModifyNPObject" and c["payload"] == {"prefers": "HasSort University"} for c in trigger_constraints))
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject" and c["payload"] == {"prefers": "HasSort ResearchInstitution"} for c in trigger_constraints))

    def test_tower_clothing_brand(self) -> None:
        # 'He announces Ashford from a boutique and announces a trademark'
        context_triggers = {
            "triggers": [
                {
                    "construction": "ModifyNPObject",
                    "lemma": "boutique",
                    "requirement": "HasSort Clothing",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-clothing-brand",
                },
                {
                    "construction": "ConjClauseObject",
                    "lemma": "trademark",
                    "requirement": "HasSort Brand",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-clothing-brand",
                },
            ]
        }
        proposal = base_proposal('He announces Ashford from a boutique and announces a trademark')
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "He") (Compl Announce (ModifyNP (OpenPN "Ashford") (FromPP (OpenIndefCN "boutique" "boutiques")))) (Compl Announce (OpenIndefCN "trademark" "trademarks"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(len(trigger_constraints), 2)
        payloads = {
            frozenset(c["payload"].items()) for c in trigger_constraints
        }
        self.assertEqual(len(payloads), 2)
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ModifyNPObject" and c["payload"] == {"prefers": "HasSort Clothing"} for c in trigger_constraints))
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject" and c["payload"] == {"prefers": "HasSort Brand"} for c in trigger_constraints))

    def test_tower_business_research(self) -> None:
        # 'He announces Ashford, at which He is awarded a contract, and announces a fellowship'
        context_triggers = {
            "triggers": [
                {
                    "construction": "RelativeClauseObject",
                    "lemma": "contract",
                    "requirement": "HasSort BusinessOrganization",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-business-research",
                },
                {
                    "construction": "ConjClauseObject",
                    "lemma": "fellowship",
                    "requirement": "HasSort ResearchInstitution",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-business-research",
                },
            ]
        }
        proposal = base_proposal('He announces Ashford, at which He is awarded a contract, and announces a fellowship')
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "He") (Compl Announce (ModifyRelAtVP (OpenPN "Ashford") (OpenPN "He") (PassComplRetained Award (OpenIndefCN "contract" "contracts")))) (Compl Announce (OpenIndefCN "fellowship" "fellowships"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(len(trigger_constraints), 2)
        payloads = {
            frozenset(c["payload"].items()) for c in trigger_constraints
        }
        self.assertEqual(len(payloads), 2)
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:RelativeClauseObject" and c["payload"] == {"prefers": "HasSort BusinessOrganization"} for c in trigger_constraints))
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject" and c["payload"] == {"prefers": "HasSort ResearchInstitution"} for c in trigger_constraints))

    def test_tower_drink_food(self) -> None:
        # 'He announces Ashford from a vineyard and announces a menu'
        context_triggers = {
            "triggers": [
                {
                    "construction": "ModifyNPObject",
                    "lemma": "vineyard",
                    "requirement": "HasSort Drinkable",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-drink-food",
                },
                {
                    "construction": "ConjClauseObject",
                    "lemma": "menu",
                    "requirement": "HasSort Food",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-drink-food",
                },
            ]
        }
        proposal = base_proposal('He announces Ashford from a vineyard and announces a menu')
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "He") (Compl Announce (ModifyNP (OpenPN "Ashford") (FromPP (OpenIndefCN "vineyard" "vineyards")))) (Compl Announce (OpenIndefCN "menu" "menus"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(len(trigger_constraints), 2)
        payloads = {
            frozenset(c["payload"].items()) for c in trigger_constraints
        }
        self.assertEqual(len(payloads), 2)
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ModifyNPObject" and c["payload"] == {"prefers": "HasSort Drinkable"} for c in trigger_constraints))
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject" and c["payload"] == {"prefers": "HasSort Food"} for c in trigger_constraints))

    def test_tower_communication_programme(self) -> None:
        # 'He announces Ashford from a broadcast and announces a segment'
        context_triggers = {
            "triggers": [
                {
                    "construction": "ModifyNPObject",
                    "lemma": "broadcast",
                    "requirement": "HasSort CommunicationContent",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-communication-programme",
                },
                {
                    "construction": "ConjClauseObject",
                    "lemma": "segment",
                    "requirement": "HasSort Programme",
                    "strength": "prefers",
                    "provenance": "test:synthetic:tower-communication-programme",
                },
            ]
        }
        proposal = base_proposal('He announces Ashford from a broadcast and announces a segment')
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "He") (Compl Announce (ModifyNP (OpenPN "Ashford") (FromPP (OpenIndefCN "broadcast" "broadcasts")))) (Compl Announce (OpenIndefCN "segment" "segments"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(len(trigger_constraints), 2)
        payloads = {
            frozenset(c["payload"].items()) for c in trigger_constraints
        }
        self.assertEqual(len(payloads), 2)
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ModifyNPObject" and c["payload"] == {"prefers": "HasSort CommunicationContent"} for c in trigger_constraints))
        self.assertTrue(any(c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject" and c["payload"] == {"prefers": "HasSort Programme"} for c in trigger_constraints))


class NegativeUnrelatedClauseSyntheticTests(unittest.TestCase):
    def test_synthetic_lemma_inside_an_unrelated_relative_clause_is_ignored(self) -> None:
        # Same guard as the University-domain suite's own negative test,
        # repeated for two new-family lemmas to confirm the (lemma,
        # construction) keying generalizes, not just for "degree".
        context_triggers = {
            "triggers": [
                {
                    "construction": "ConjClauseObject",
                    "lemma": "grant",
                    "requirement": "HasSort ResearchInstitution",
                    "strength": "prefers",
                    "provenance": "test:synthetic:negative",
                },
                {
                    "construction": "ConjClauseObject",
                    "lemma": "trademark",
                    "requirement": "HasSort Brand",
                    "strength": "prefers",
                    "provenance": "test:synthetic:negative",
                },
            ]
        }
        proposal = base_proposal("He interviewed the founder who had a grant")
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "He") (Compl Announce (ModifyRelVP '
            '(OpenIndefCN "founder" "founders") (Compl Announce (OpenIndefCN "grant" "grants"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])


if __name__ == "__main__":
    unittest.main()
