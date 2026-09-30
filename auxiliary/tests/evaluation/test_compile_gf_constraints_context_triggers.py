"""compile_gf_constraints's automatic (lemma, tree-relation) -> constraint
mechanism (data/contextual-context-triggers.json), added so a content word
like "degree" can narrow the fiber without a human hand-writing a TSV
scenario row for it (see evaluation/pilot-decode-wimcor/README.md's
Valparaiso/Haifa degree-context result, which was built by hand before
this).

Deliberately keyed on (lemma, construction) together, never a bare lemma
lookup -- a flat word->requirement table would wrongly attach "degree" to
an unrelated target whenever the word happens to occur anywhere else in
the tree (e.g. "He interviewed the dean, who had a degree from Yale,
about Valparaiso's admissions policy" -- "degree" there is about the dean
and Yale, not Valparaiso). The negative test below is exactly this case.

Two construction types, both pure tree-shape checks, no new GF grammar
needed (both tree fixtures below were verified against the local GF
toolchain's `l -lang=MetonymyEng` before being written here, matching
this project's usual discipline for hand-built tree text):
- "ConjClauseObject": the object of a SECOND Compl/PassCompl reached
  through PredConjVP/AndS coordination -- "shares the target's subject"
  is a given of PredConjVP's own shape (one NP argument shared by both
  VPs), nothing else to verify.
- "ModifyNPObject": the object of a ModifyNP+<prep> modifier when that
  object is a common noun (not the proper-noun/entity case the existing
  FrameModifier code already handles via context_templates).

These are pure Python tests against hand-built GF tree strings -- no GF/
Haskell toolchain required to run them (same pattern as every other
tests/evaluation/test_compile_gf_constraints_*.py file).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from contextual_rule_compiler import ARITIES, compile_gf_constraints  # noqa: E402

WORDNET_RULES = {
    "lexical_sorts": {
        "county": {"requirement": "HasSort Place", "provenance": "test:wordnet"},
    },
    "adjective_sorts": {},
}

LANGUAGE_RULES = {
    "schema_version": "test-1",
    "frame_argument_capabilities": [],
    "context_templates": [],
}

CONTEXT_TRIGGERS = {
    "schema_version": "test-1",
    "triggers": [
        {
            "construction": "ConjClauseObject",
            "lemma": "degree",
            "requirement": "HasSort University",
            "strength": "requires",
            "provenance": "test:context-trigger:degree-implies-university",
        },
        {
            "construction": "ModifyNPObject",
            "lemma": "degree",
            "requirement": "HasSort University",
            "strength": "prefers",
            "provenance": "test:context-trigger:degree-modifier",
        },
        {
            "construction": "ConjClauseObject",
            "lemma": "diploma",
            "requirement": "HasSort University",
            "strength": "prefers",
            "provenance": "test:context-trigger:diploma-implies-university",
        },
        {
            "construction": "RelativeClauseObject",
            "lemma": "certificate",
            "requirement": "HasSort University",
            "strength": "prefers",
            "provenance": "test:context-trigger:certificate-implies-university",
        },
    ],
}


def base_proposal(sentence: str, action: str = "attend") -> dict:
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
                    "surface": "attended",
                    "start": 0,
                    "end": len(sentence.split()[0]) + 1 + len(action) + 1,
                },
                "payload": {"prefers": "HasSort Entity"},
                "provenance": "test:VerbNet:" + action,
            }
        ],
    }


class PassComplRetainedArityTests(unittest.TestCase):
    def test_pass_compl_retained_takes_a_verb_and_a_retained_object(self) -> None:
        self.assertEqual(ARITIES["PassComplRetained"], 2)


class ConjClauseObjectTests(unittest.TestCase):
    def test_second_conj_object_produces_a_trigger_constraint(self) -> None:
        # Verified via local gf.exe: linearizes to
        # "Farina announces Valparaiso and reads a degree".
        proposal = base_proposal("Farina attended Valparaiso and received a degree")
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Farina") '
            '(Compl Announce (OpenPN "Valparaiso")) '
            '(Compl Read (OpenIndefCN "degree" "degrees"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c for c in constraints if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"requires": "HasSort University"}
        )
        self.assertEqual(
            trigger_constraints[0]["provenance"],
            "test:context-trigger:degree-implies-university",
        )

    def test_absent_context_triggers_produces_no_trigger_constraint(self) -> None:
        # Backward compatibility: context_triggers defaults to None, and
        # the mechanism must be a strict no-op then (matches every other
        # optional keyword this function already has).
        proposal = base_proposal("Farina attended Valparaiso and received a degree")
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Farina") '
            '(Compl Announce (OpenPN "Valparaiso")) '
            '(Compl Read (OpenIndefCN "degree" "degrees"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])

    def test_unmatched_lemma_produces_no_trigger_constraint(self) -> None:
        # "treaty" is not in CONTEXT_TRIGGERS -- must not raise or
        # fabricate a constraint for it.
        proposal = base_proposal("Farina attended Valparaiso and signed a treaty")
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Farina") '
            '(Compl Announce (OpenPN "Valparaiso")) '
            '(Compl Sign (OpenIndefCN "treaty" "treaties"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])

    def test_modified_object_never_matches_even_a_known_lemma(self) -> None:
        # Real WiMCor finding: "He attended Gettysburg and received a
        # Bachelor of Science degree AT the University of Maryland" --
        # the degree is explicitly from a DIFFERENT institution. Verified
        # via local gf.exe: linearizes to "Farina announces Valparaiso
        # and reads a degree at University Maryland". lexical_head is
        # deliberately NOT used for this relation (see the code comment)
        # -- ANY modifier on the object, benign or institution-
        # redirecting, must decline rather than risk misattribution.
        proposal = base_proposal(
            "Farina attended Valparaiso and received a degree at University Maryland"
        )
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Farina") '
            '(Compl Announce (OpenPN "Valparaiso")) '
            '(Compl Read (ModifyNP (OpenIndefCN "degree" "degrees") '
            '(AtPP (OpenPN2 "University" "Maryland"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])

    def test_compl_oblique_object_produces_a_trigger_constraint(self) -> None:
        # ComplOblique (grammar/Metonymy.gf), added for a real WiMCor
        # shape ("graduated WITH a diploma") that Compl cannot represent
        # -- "diploma" is a verb-level oblique, not a direct object.
        # Verified via local gf.exe: linearizes to "Farina announces
        # Valparaiso and graduates with a diploma".
        proposal = base_proposal(
            "Farina attended Valparaiso and graduated with a diploma"
        )
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Farina") '
            '(Compl Announce (OpenPN "Valparaiso")) '
            '(ComplOblique Graduate (WithPP (OpenIndefCN "diploma" "diplomas")))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_compl_oblique_modified_object_never_matches(self) -> None:
        # Same safety guarantee as test_modified_object_never_matches_
        # even_a_known_lemma, one level deeper (inside the PP): a
        # "diploma FROM Harvard" must decline just as readily as a
        # "degree AT the University of Maryland" does for Compl. Verified
        # via local gf.exe: linearizes to "Farina announces Valparaiso
        # and graduates with a diploma from Harvard".
        proposal = base_proposal(
            "Farina attended Valparaiso and graduated with a diploma from Harvard"
        )
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Farina") '
            '(Compl Announce (OpenPN "Valparaiso")) '
            '(ComplOblique Graduate (WithPP (ModifyNP '
            '(OpenIndefCN "diploma" "diplomas") (FromPP (OpenPN "Harvard")))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])

    def test_first_complement_is_never_treated_as_extra(self) -> None:
        # If the PRIMARY target's own object happens to be a trigger
        # lemma, it must still be handled only by the existing
        # FrameArgument path (first_node), not double-counted as a
        # ConjClauseObject match on itself.
        proposal = base_proposal("Farina received a degree and announced Valparaiso")
        constraints = compile_gf_constraints(
            proposal,
            'PredConjVP (OpenPN "Farina") '
            '(Compl Read (OpenIndefCN "degree" "degrees")) '
            '(Compl Announce (OpenPN "Valparaiso"))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        # "degree" is now the FIRST Compl's object (first_node's own
        # match), so the ConjClauseObject loop's only remaining candidate
        # is the second Compl's object ("Valparaiso", a bare proper noun
        # -- _noun_lemma resolves None for it, no trigger lookup at all).
        self.assertEqual(trigger_constraints, [])


class ModifyRelAtVpArityTests(unittest.TestCase):
    def test_modify_rel_at_vp_takes_target_subject_and_embedded_vp(self) -> None:
        self.assertEqual(ARITIES["ModifyRelAtVP"], 3)


class RelativeClauseObjectTests(unittest.TestCase):
    def test_embedded_vp_object_produces_a_trigger_constraint(self) -> None:
        # "Padgate, at which he was awarded a certificate" -- ModifyRelAtVP
        # (grammar/Metonymy.gf) modifies the TARGET's own NP directly
        # (distinct from ConjClauseObject's coordinated-sibling relation).
        # Verified via local gf.exe: linearizes to "He announces Padgate ,
        # at which He is awarded a certificate".
        proposal = base_proposal("He studied at Padgate, where he was awarded a certificate")
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "He") (Compl Announce (ModifyRelAtVP '
            '(OpenPN "Padgate") (OpenPN "He") '
            '(PassComplRetained Award (OpenIndefCN "certificate" "certificates"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:RelativeClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_modified_embedded_object_never_matches(self) -> None:
        # Same safety guarantee as the ConjClauseObject/ComplOblique
        # cases, one relation deeper: "a certificate FROM Cambridge"
        # inside the relative clause must decline just as readily.
        # Verified via local gf.exe: linearizes to "He announces Padgate ,
        # at which He is awarded a certificate from Cambridge".
        proposal = base_proposal(
            "He studied at Padgate, where he was awarded a certificate from Cambridge"
        )
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "He") (Compl Announce (ModifyRelAtVP '
            '(OpenPN "Padgate") (OpenPN "He") '
            '(PassComplRetained Award (ModifyNP '
            '(OpenIndefCN "certificate" "certificates") (FromPP (OpenPN "Cambridge"))))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])

    def test_unrelated_modify_rel_vp_is_unaffected(self) -> None:
        # Regression guard: the existing subject-relative ModifyRelVP
        # (a DIFFERENT constructor, "which was awarded...") is untouched
        # -- only ModifyRelAtVP is checked for RelativeClauseObject.
        proposal = base_proposal("Anna announces the dean who had a certificate")
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Anna") (Compl Announce (ModifyRelVP '
            '(OpenIndefCN "dean" "deans") '
            '(Compl Read (OpenIndefCN "certificate" "certificates"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])


class ModifyNpObjectTests(unittest.TestCase):
    def test_common_noun_pp_modifier_produces_a_trigger_constraint(self) -> None:
        # Verified via local gf.exe: linearizes to
        # "Anna announces Valparaiso with a degree".
        proposal = base_proposal("Anna attended Valparaiso with a degree")
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Anna") (Compl Announce (ModifyNP '
            '(OpenPN "Valparaiso") (WithPP (OpenIndefCN "degree" "degrees"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ModifyNPObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_proper_noun_pp_modifier_is_unaffected_by_the_new_mechanism(self) -> None:
        # Regression guard: the existing entity-QID ModifyNP+PP path
        # (context_templates) is untouched -- a proper-noun modifier
        # object must never be looked up in the new trigger table (its
        # own _noun_lemma is None for a proper noun, by construction).
        proposal = base_proposal("Anna attended the county in Kent")
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Anna") (Compl Announce (ModifyNP '
            '(OpenIndefCN "county" "counties") (InPP (OpenPN "Kent"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {"kent": ["Q1234567"]},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])


class RealDataFileCorpusExamplesTests(unittest.TestCase):
    """Runs hand-built trees for real WiMCor sentences (not synthetic
    fixtures) through compile_gf_constraints against the SHIPPED
    data/contextual-context-triggers.json and data/wordnet-context-
    rules.json -- confirms the actual dictionary works end to end, not
    just a local test double. Each sentence's structure was verified via
    local Stanza before being hand-built here; each tree was verified via
    local gf.exe.

    Corpus provenance (found via build/local-curation/wimcor-test.combined.jsonl,
    not committed -- WiMCor CC BY-SA 3.0, see evaluation/pilot-decode-wimcor/README.md
    for the licensing/attribution convention this project already follows):
    "In 1697, he studied at Pisa and obtained his doctorate of law in 1719."
    -- one of several real "attended/studied at X and
    received/earned/obtained a <degree-like noun>" sentences found by
    corpus search; several others (Gettysburg/Webster/Oklahoma City/Yale/
    Deep Springs/Kingston) were REJECTED because the degree-like noun
    names a DIFFERENT institution than the metonymy target ("received a
    degree AT the University of Maryland", "earned his MBA FROM San Diego
    State University", etc.) -- exactly the risk
    test_modified_object_never_matches_even_a_known_lemma guards against.
    """

    @classmethod
    def setUpClass(cls) -> None:
        data_root = ROOT / "auxiliary/data"
        cls.language_rules = json.loads(
            (data_root / "contextual-language-rules.json").read_text(
                encoding="utf-8"
            )
        )
        cls.wordnet_rules = json.loads(
            (data_root / "wordnet-context-rules.json").read_text(encoding="utf-8")
        )
        cls.context_triggers = json.loads(
            (data_root / "contextual-context-triggers.json").read_text(
                encoding="utf-8"
            )
        )

    def test_pisa_doctorate_is_derived_automatically(self) -> None:
        sentence = (
            "In 1697, he studied at Pisa and obtained his doctorate of "
            "law in 1719."
        )
        action_start = sentence.index("studied at")
        action_end = action_start + len("studied at")
        proposal = {
            "action": "study at",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:study_at"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "study at",
                        "surface": "studied at",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:study_at",
                }
            ],
        }
        # The real "of law" nmod on "doctorate" is deliberately dropped
        # (bare OpenIndefCN, same simplification the Valparaiso "with a
        # double major..." example already relies on) -- it's benign
        # (doesn't name a competing institution), unlike the rejected
        # Gettysburg/Webster/etc. sentences above.
        tree = (
            'PredConjVP (OpenPN "He") '
            '(Compl Announce (OpenPN "Pisa")) '
            '(Compl Read (OpenIndefCN "doctorate" "doctorates"))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )
        self.assertEqual(
            trigger_constraints[0]["origin"]["surface"],
            "studied at Pisa and obtained his doctorate",
        )

    def test_ucla_fraternity_is_derived_automatically(self) -> None:
        sentence = "He enrolled at UCLA and joined the Delta Sigma Phi fraternity."
        action_start = sentence.index("enrolled at")
        action_end = action_start + len("enrolled at")
        proposal = {
            "action": "enroll at",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:enroll_at"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "enroll at",
                        "surface": "enrolled at",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:enroll_at",
                }
            ],
        }
        # "Delta Sigma Phi" is a UD compound modifier on "fraternity", not
        # a PP -- dropped the same way OpenPN2/OpenPN3 chains are used
        # elsewhere for multi-word proper-noun-like content; a bare
        # OpenIndefCN is the honest simplification (no ModifyNP wrapper,
        # so the safety fix above still applies if this were ever a real
        # competing-institution PP instead).
        tree = (
            'PredConjVP (OpenPN "He") '
            '(Compl Announce (OpenPN "UCLA")) '
            '(Compl Read (OpenIndefCN "fraternity" "fraternities"))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_ankara_retained_object_passive_is_derived_automatically(self) -> None:
        # Real WiMCor sentence using PassComplRetained (grammar/Metonymy.gf),
        # a new constructor added specifically because this shape --
        # "X was awarded Y", a ditransitive retained-object passive with
        # no agent -- could not be represented by Compl (needs active
        # voice), PassCompl (whose NP is a "by"-agent, not this retained
        # theme), or PassCompl0 (no further NP at all). Verified via
        # local gf.exe: linearizes to "He announces Ankara and is
        # awarded a degree", and the pre-existing OpenPN2 "a X" parse
        # ambiguity this exposed on round-trip parsing was confirmed to
        # already exist for ANY OpenIndefCN object before this change
        # (tested directly: "Anna announces a degree" shows the same
        # ambiguity) -- not something this addition introduced.
        sentence = "He attended Ankara and was awarded a PhD degree in Pharmacy."
        action_start = sentence.index("attended")
        action_end = action_start + len("attended")
        proposal = {
            "action": "attend",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:attend"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "attend",
                        "surface": "attended",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:attend",
                }
            ],
        }
        # "PhD" (compound) and "in Pharmacy" (nmod) on "degree" are
        # dropped -- the same safe simplification as Pisa's "of law" and
        # Valparaiso's "with a double major..."; neither names a
        # competing institution.
        tree = (
            'PredConjVP (OpenPN "He") '
            '(Compl Announce (OpenPN "Ankara")) '
            '(PassComplRetained Award (OpenIndefCN "degree" "degrees"))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"requires": "HasSort University"}
        )

    def test_berklee_diploma_is_derived_automatically(self) -> None:
        # Real WiMCor sentence using ComplOblique (grammar/Metonymy.gf):
        # "with a diploma" is a verb-level oblique of "graduated", not a
        # direct object, which is exactly why Compl could not represent
        # this shape before this addition.
        sentence = (
            "He later attended Berklee and graduated with a diploma in "
            "arranging and composition in 1966."
        )
        action_start = sentence.index("attended")
        action_end = action_start + len("attended")
        proposal = {
            "action": "attend",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:attend"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "attend",
                        "surface": "attended",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:attend",
                }
            ],
        }
        # "in arranging and composition" (nmod on "diploma") is dropped --
        # the same safe simplification as every other real example above;
        # it names a field of study, not a competing institution.
        tree = (
            'PredConjVP (OpenPN "He") '
            '(Compl Announce (OpenPN "Berklee")) '
            '(ComplOblique Graduate (WithPP (OpenIndefCN "diploma" "diplomas")))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_padgate_certificate_is_derived_automatically(self) -> None:
        # Real WiMCor sentence using ModifyRelAtVP (grammar/Metonymy.gf):
        # "where he was awarded a Certificate" modifies the target's own
        # NP directly, via "at which" (RGL has no locative "where" RP in
        # this pinned commit -- see the grammar file's own comment).
        sentence = (
            "He studied at Padgate Training College, Warrington, where "
            "he was awarded a Certificate in Education in 1977."
        )
        action_start = sentence.index("studied at")
        action_end = action_start + len("studied at")
        proposal = {
            "action": "study at",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:study_at"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "study at",
                        "surface": "studied at",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:study_at",
                }
            ],
        }
        # "Warrington" (appositive) and "in Education"/"in 1977" (on the
        # target and the certificate respectively) are dropped -- the
        # same safe simplification as every other real example above.
        tree = (
            'Pred (OpenPN "He") (Compl Announce (ModifyRelAtVP '
            '(OpenPN "Padgate") (OpenPN "He") '
            '(PassComplRetained Award (OpenIndefCN "certificate" "certificates"))))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:RelativeClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_winchester_fellow_is_derived_automatically(self) -> None:
        # Real WiMCor sentence: "professions/writers" family, found this
        # session by searching the real target_span's own tail for the
        # "TARGET and VERB2 a/an NOUN" coordination shape (the same
        # methodology that originally found doctorate/fraternity/diploma/
        # certificate). "fellow of the Royal Historical Society" is a
        # DIFFERENT class of signal than "degree": a degree is conferred
        # BY its institution (direct entailment); a fellowship is a
        # correlated fact about the person, not a consequence of the
        # target -- kept at prefers even though the specific institution
        # WAS individually verified against live Wikidata this round
        # (University of Winchester, Q3551690: P31->Q62078547 "public
        # research university", P131->Q172157, the exact QID of the
        # surface "Winchester"). See data/contextual-context-triggers.json's
        # own provenance string and docs/contextual-tower.md.
        sentence = (
            "She is currently emeritus professor of early Medieval "
            "history at Winchester, and is a fellow of the Royal "
            "Historical Society."
        )
        action_start = sentence.index("is currently")
        action_end = action_start + len("is currently")
        proposal = {
            "action": "be",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:be"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "be",
                        "surface": "is",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:be",
                }
            ],
        }
        # "emeritus professor of early Medieval history at" simplified to
        # Announce, and "is a fellow of X" simplified to a bare Compl
        # object (dropping "of the Royal Historical Society", the same
        # safe simplification already used for "diploma"/"certificate"'s
        # own PP modifiers) -- verified via local gf.exe.
        tree = (
            'PredConjVP (OpenPN "He") '
            '(Compl Announce (OpenPN "Winchester")) '
            '(Compl Read (OpenIndefCN "fellow" "fellows"))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_phoenix_member_is_derived_automatically(self) -> None:
        # Real WiMCor sentence, same search as Winchester above. The
        # specific institution (University of Phoenix, Q1889100) was
        # identified via Wikidata search but NOT individually confirmed
        # via live P31/P131 claims this round -- a Wikidata API rate
        # limit (HTTP 403) was hit mid-session, honestly recorded in
        # data/contextual-context-triggers.json's own provenance string
        # rather than silently skipped or claimed as done.
        sentence = (
            "Smith holds a Doctor of Management degree in organizational "
            "leadership from Phoenix and is a member of the Delta Mu "
            "Delta International Business Honor Society."
        )
        action_start = sentence.index("holds")
        action_end = action_start + len("holds")
        proposal = {
            "action": "hold",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:hold"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "hold",
                        "surface": "holds",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:hold",
                }
            ],
        }
        # "Doctor of Management degree in organizational leadership" and
        # "of the Delta Mu Delta International Business Honor Society"
        # both dropped -- same safe simplification as every other real
        # example above. Verified via local gf.exe.
        tree = (
            'PredConjVP (OpenPN "He") '
            '(Compl Announce (OpenPN "Phoenix")) '
            '(Compl Read (OpenIndefCN "member" "members"))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )

    def test_loughborough_editor_in_chief_is_derived_automatically(self) -> None:
        # Real WiMCor sentence, same search and same unfinished-
        # verification honesty as Phoenix above (Loughborough University,
        # Q1434547, identified via search but not claims-confirmed this
        # round).
        sentence = (
            "Geoffrey Martin Hodgson is a Professor in Management at the "
            "London campus of Loughborough, and also the editor-in-chief "
            "of the Journal of Institutional Economics."
        )
        action_start = sentence.index("is a Professor")
        action_end = action_start + len("is")
        proposal = {
            "action": "be",
            "sentence": sentence,
            "role": "ObjectHole",
            "frames": [],
            "provenance": {"action": "test:VerbNet:be"},
            "constraints": [
                {
                    "origin": {
                        "constructor": "Verb",
                        "lemma": "be",
                        "surface": "is",
                        "start": action_start,
                        "end": action_end,
                    },
                    "payload": {"prefers": "HasSort Entity"},
                    "provenance": "test:VerbNet:be",
                }
            ],
        }
        # "of the Journal of Institutional Economics" dropped -- same
        # safe simplification as every other real example above. Also
        # note: OpenIndefCN always emits "a" (never "an"), a pre-existing,
        # documented grammar characteristic (see docs/contextual-tower.md's
        # synthetic multi-domain section) -- "editor-in-chief" is vowel-
        # initial, so the real linearization here is "a editor-in-chief",
        # not "an editor-in-chief"; harmless for constraint derivation,
        # which never linearizes the tree. Verified via local gf.exe.
        tree = (
            'PredConjVP (OpenPN "He") '
            '(Compl Announce (OpenPN "Loughborough")) '
            '(Compl Read (OpenIndefCN "editor-in-chief" "editor-in-chiefs"))'
        )
        constraints = compile_gf_constraints(
            proposal,
            tree,
            self.language_rules,
            self.wordnet_rules,
            {},
            context_triggers=self.context_triggers,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"] == "ContextTrigger:ConjClauseObject"
        ]
        self.assertEqual(len(trigger_constraints), 1)
        self.assertEqual(
            trigger_constraints[0]["payload"], {"prefers": "HasSort University"}
        )


class NegativeUnrelatedClauseTests(unittest.TestCase):
    def test_trigger_word_inside_an_unrelated_relative_clause_is_ignored(self) -> None:
        # The exact risk the (lemma, construction) keying exists to rule
        # out: "degree" reachable in the tree, but through neither
        # ConjClauseObject nor ModifyNPObject (here: a ModifyRelVP
        # relative-clause modifying a DIFFERENT NP than the target's own
        # clause) -- must not fire.
        proposal = base_proposal("Anna interviewed the dean who had a degree")
        constraints = compile_gf_constraints(
            proposal,
            'Pred (OpenPN "Anna") (Compl Announce (ModifyRelVP '
            '(OpenIndefCN "dean" "deans") (Compl Read (OpenIndefCN "degree" "degrees"))))',
            LANGUAGE_RULES,
            WORDNET_RULES,
            {},
            context_triggers=CONTEXT_TRIGGERS,
        )
        trigger_constraints = [
            c
            for c in constraints
            if c["origin"]["constructor"].startswith("ContextTrigger:")
        ]
        self.assertEqual(trigger_constraints, [])


if __name__ == "__main__":
    unittest.main()
