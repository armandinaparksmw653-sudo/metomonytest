"""Unit tests for build_gf_tree_from_dependencies's Phase 1 tree builder.

Words are plain dicts (id/head/deprel/upos/lemma/text/start_char/
end_char) -- the same flat shape annotate_dependency_hints.py's new
"ud_words" hint field carries after a JSON round-trip, deliberately not
a duck-typed Stanza-like object (build_gf_tree never sees a live Stanza
object, only its serialized form).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from build_gf_tree_from_dependencies import (  # noqa: E402
    build_gf_tree,
    build_gf_tree_decline_reason,
    build_gf_tree_from_llm_structure,
    build_gf_tree_from_llm_structure_decline_reason,
    enumerate_gf_tree_blockers,
    load_gf_function_by_lemma,
)

GF_FUNCTIONS = {"announce": "CTX_announce", "praise": "CTX_praise"}


def word(
    id_: int,
    text: str,
    lemma: str,
    upos: str,
    deprel: str,
    head: int,
    start_char: int,
) -> dict:
    return {
        "id": id_,
        "text": text,
        "lemma": lemma,
        "upos": upos,
        "deprel": deprel,
        "head": head,
        "start_char": start_char,
        "end_char": start_char + len(text),
    }


class SimpleTransitiveClauseTests(unittest.TestCase):
    def test_single_word_proper_noun_subject_and_object(self) -> None:
        # "Waterloo announces Henry"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree, 'Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Henry"))'
        )

    def test_two_word_compound_proper_noun_uses_openpn2(self) -> None:
        # "Henry County announces Waterloo"
        words = [
            word(1, "Henry", "Henry", "PROPN", "compound", 2, 0),
            word(2, "County", "County", "PROPN", "nsubj", 3, 6),
            word(3, "announces", "announce", "VERB", "root", 0, 13),
            word(4, "Waterloo", "Waterloo", "PROPN", "obj", 3, 23),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN2 "Henry" "County") (Compl CTX_announce (OpenPN "Waterloo"))',
        )

    def test_three_word_compound_proper_noun_uses_openpn3(self) -> None:
        # "Waterloo announces The Royal Shipley School"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Royal", "Royal", "PROPN", "compound", 5, 19),
            word(4, "Shipley", "Shipley", "PROPN", "compound", 5, 25),
            word(5, "School", "School", "PROPN", "obj", 2, 33),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenPN3 "Royal" "Shipley" "School"))',
        )

    def test_four_word_compound_proper_noun_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "A", "A", "PROPN", "compound", 6, 19),
            word(4, "B", "B", "PROPN", "compound", 6, 21),
            word(5, "C", "C", "PROPN", "compound", 6, 23),
            word(6, "D", "D", "PROPN", "obj", 2, 25),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_pronoun_subject(self) -> None:
        # "He praises Tolstoy"
        words = [
            word(1, "He", "he", "PRON", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 3),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 11),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
        self.assertEqual(tree, 'Pred HePN (Compl CTX_praise (OpenPN "Tolstoy"))')

    def test_pronoun_object(self) -> None:
        # "Tolstoy praises them"
        words = [
            word(1, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 8),
            word(3, "them", "they", "PRON", "obj", 2, 16),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
        self.assertEqual(tree, 'Pred (OpenPN "Tolstoy") (Compl CTX_praise TheyPN)')

    def test_all_four_pronoun_constructors(self) -> None:
        for pronoun_lemma, constructor in (
            ("he", "HePN"),
            ("she", "ShePN"),
            ("it", "ItPN"),
            ("they", "TheyPN"),
        ):
            with self.subTest(pronoun_lemma=pronoun_lemma):
                words = [
                    word(1, pronoun_lemma, pronoun_lemma, "PRON", "nsubj", 2, 0),
                    word(2, "praises", "praise", "VERB", "root", 0, 3),
                    word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 11),
                ]
                tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
                self.assertEqual(
                    tree, f'Pred {constructor} (Compl CTX_praise (OpenPN "Tolstoy"))'
                )


class BailsOutToNoneTests(unittest.TestCase):
    def test_a_pp_modifier_is_out_of_scope(self) -> None:
        # "Waterloo announces Henry in Ontario"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "in", "in", "ADP", "case", 6, 25),
            word(5, "Ontario", "Ontario", "PROPN", "obl", 2, 28),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_a_non_article_determiner_is_out_of_scope(self) -> None:
        # "a"/"an"/"the" are in scope (see CommonNounNpTests below) --
        # "every"/"this"/etc are not: OpenIndefCN/OpenDefCN only ever
        # produce "a"/"the", so this module isn't confident guessing a
        # shape for anything else.
        words = [
            word(1, "Every", "every", "DET", "det", 2, 0),
            word(2, "county", "county", "NOUN", "nsubj", 3, 6),
            word(3, "announces", "announce", "VERB", "root", 0, 13),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 23),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_coordination_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "and", "and", "CCONJ", "cc", 6, 25),
            word(5, "Tolstoy", "Tolstoy", "PROPN", "conj", 3, 29),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_a_common_noun_subject_is_out_of_scope(self) -> None:
        words = [
            word(1, "county", "county", "NOUN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 7),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 17),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_no_object_is_out_of_scope(self) -> None:
        # grammar/Metonymy.gf has no intransitive VP at all.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_more_than_one_root_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "announces", "announce", "VERB", "root", 0, 30),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_a_lemma_missing_from_the_gf_action_lexicon_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "floreates", "floreate", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertIsNone(build_gf_tree(words, "floreate", GF_FUNCTIONS))

    def test_an_auxiliary_root_with_no_matching_shape_is_out_of_scope(self) -> None:
        # "He is Tolstoy" -- AUX root but no matching action lemma; also
        # exercises the AUX branch of the root-upos check.
        words = [
            word(1, "He", "he", "PRON", "nsubj", 2, 0),
            word(2, "is", "be", "AUX", "root", 0, 3),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 6),
        ]
        self.assertIsNone(build_gf_tree(words, "be", GF_FUNCTIONS))

    def test_a_lemma_mismatched_with_uds_own_root_is_out_of_scope(self) -> None:
        # Guards the case resolve_action's positional fallback (used
        # whenever dependency_hint's dep_status isn't "direct-argument")
        # resolved a *different* word than UD's own root -- must not
        # silently build a tree around the wrong clause.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertIsNone(build_gf_tree(words, "sign", GF_FUNCTIONS))


class CommonNounNpTests(unittest.TestCase):
    def test_indefinite_common_noun_object(self) -> None:
        # "Waterloo announces a programme"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "a", "a", "DET", "det", 4, 19),
            word(4, "programme", "programme", "NOUN", "obj", 2, 21),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenIndefCN "programme" "programme"))',
        )

    def test_definite_common_noun_subject(self) -> None:
        # "The county announces Henry"
        words = [
            word(1, "The", "the", "DET", "det", 2, 0),
            word(2, "county", "county", "NOUN", "nsubj", 3, 4),
            word(3, "announces", "announce", "VERB", "root", 0, 11),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 21),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenDefCN "county" "county") '
            '(Compl CTX_announce (OpenPN "Henry"))',
        )

    def test_indefinite_common_noun_with_adjective(self) -> None:
        # "Waterloo announces a large county"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "a", "a", "DET", "det", 5, 19),
            word(4, "large", "large", "ADJ", "amod", 5, 21),
            word(5, "county", "county", "NOUN", "obj", 2, 27),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenAdjIndefCN "large" "county" "county"))',
        )

    def test_definite_common_noun_with_adjective(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 5, 19),
            word(4, "large", "large", "ADJ", "amod", 5, 23),
            word(5, "county", "county", "NOUN", "obj", 2, 29),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenAdjDefCN "large" "county" "county"))',
        )

    def test_a_common_noun_with_no_determiner_at_all_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "programmes", "programme", "NOUN", "obj", 2, 19),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))

    def test_two_adjectives_is_out_of_scope(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "a", "a", "DET", "det", 6, 19),
            word(4, "large", "large", "ADJ", "amod", 6, 21),
            word(5, "old", "old", "ADJ", "amod", 6, 27),
            word(6, "county", "county", "NOUN", "obj", 2, 31),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))


class PassiveClauseTests(unittest.TestCase):
    def test_passive_with_a_proper_noun_agent(self) -> None:
        # "Waterloo was announced by Henry"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 9),
            word(3, "announced", "announce", "VERB", "root", 0, 13),
            word(4, "by", "by", "ADP", "case", 5, 23),
            word(5, "Henry", "Henry", "PROPN", "obl", 3, 26),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(PassCompl CTX_announce (OpenPN "Henry"))',
        )

    def test_passive_without_a_by_agent_uses_the_bare_passive(self) -> None:
        # "Waterloo was announced" -- no "by"-agent at all. Used to be
        # out of scope entirely (grammar/Metonymy.gf's PassCompl always
        # needs an agent NP) -- a real corpus run found this the
        # dominant share of "passive-agent-count" (most real passives
        # never name an agent), so this round added PassCompl0 (V2 ->
        # VP, no agent slot), verified locally against gf.exe/pinned
        # gf-rgl: `l -lang=MetonymyEng (Pred (OpenPN "Henry") (PassCompl0
        # Announce))` -> "Henry is announced".
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 9),
            word(3, "announced", "announce", "VERB", "root", 0, 13),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(tree, 'Pred (OpenPN "Waterloo") (PassCompl0 CTX_announce)')


class RelativeClauseTests(unittest.TestCase):
    def test_relative_clause_on_the_object(self) -> None:
        # "Waterloo praises Tolstoy, (that) announces Henry" -- a
        # relativized *object* shape, the relativizer itself elided (as
        # real UD "acl:relcl" annotations correctly do when it's
        # dropped), since ModifyRelVP's own shape ("NP which VP") has no
        # room for a relative clause with its own separate subject word
        # (see test_relative_clause_with_its_own_subject_is_out_of_scope
        # below) -- ModifyRelVP's own linearization always says
        # "which"/"that" regardless of what the original relative
        # pronoun even was, so there's nothing to separately represent.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "announces", "announce", "VERB", "acl:relcl", 3, 26),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 36),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_praise (ModifyRelVP (OpenPN "Tolstoy") '
            '(Compl CTX_announce (OpenPN "Henry"))))',
        )

    def test_relative_clause_with_its_own_subject_is_out_of_scope(self) -> None:
        # ModifyRelVP's own shape ("NP which VP") has no room for the
        # relative clause's own separate subject.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "who", "who", "PRON", "nsubj", 5, 26),
            word(5, "announces", "announce", "VERB", "acl:relcl", 3, 30),
            word(6, "Henry", "Henry", "PROPN", "obj", 5, 40),
        ]
        self.assertIsNone(build_gf_tree(words, "praise", GF_FUNCTIONS))


class NmodModifierTests(unittest.TestCase):
    """A trailing UD "nmod"+"case" modifier on a noun ("the museum in
    Kent") -- a real corpus run found this a real share of what
    "leftover-words"/"embedded-leftover-words" were catching, since
    _np/_np_base never looked for one at all. Reuses grammar/Metonymy.gf's
    already-compiled ModifyNP + 13-preposition family (already used by
    the fronted-date path), and contextual_rule_compiler.py's own
    compile_gf_constraints already walks any ModifyNP node generically
    -- no changes needed there.
    """

    def test_object_side_nmod(self) -> None:
        # "Waterloo captured the museum in Kent"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "captured", "capture", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 18),
            word(4, "museum", "museum", "NOUN", "obj", 2, 22),
            word(5, "in", "in", "ADP", "case", 6, 29),
            word(6, "Kent", "Kent", "PROPN", "nmod", 4, 32),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        tree = build_gf_tree(words, "capture", functions)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") (Compl CTX_capture '
            '(ModifyNP (OpenDefCN "museum" "museum") (InPP (OpenPN "Kent"))))',
        )

    def test_subject_side_nmod(self) -> None:
        # "the president of France captured Waterloo"
        words = [
            word(1, "the", "the", "DET", "det", 2, 0),
            word(2, "president", "president", "NOUN", "nsubj", 5, 4),
            word(3, "of", "of", "ADP", "case", 4, 14),
            word(4, "France", "France", "PROPN", "nmod", 2, 17),
            word(5, "captured", "capture", "VERB", "root", 0, 24),
            word(6, "Waterloo", "Waterloo", "PROPN", "obj", 5, 33),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        tree = build_gf_tree(words, "capture", functions)
        self.assertEqual(
            tree,
            'Pred (ModifyNP (OpenDefCN "president" "president") '
            '(OfPP (OpenPN "France"))) (Compl CTX_capture (OpenPN "Waterloo"))',
        )

    def test_nmod_count(self) -> None:
        # Two nmod children on the same noun -- not confident which (if
        # either) is the "real" modifier, decline rather than guess.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "captured", "capture", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 18),
            word(4, "museum", "museum", "NOUN", "obj", 2, 22),
            word(5, "in", "in", "ADP", "case", 6, 29),
            word(6, "Kent", "Kent", "PROPN", "nmod", 4, 32),
            word(7, "near", "near", "ADP", "case", 8, 37),
            word(8, "Dover", "Dover", "PROPN", "nmod", 4, 42),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            build_gf_tree_decline_reason(words, "capture", functions),
            "nmod-count",
        )

    def test_nmod_case_count(self) -> None:
        # The nmod dependent has no "case" child at all (no recognizable
        # preposition word) -- e.g. an appositive-like nmod this module
        # doesn't otherwise model.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "captured", "capture", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 18),
            word(4, "museum", "museum", "NOUN", "obj", 2, 22),
            word(5, "Kent", "Kent", "PROPN", "nmod", 4, 29),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            build_gf_tree_decline_reason(words, "capture", functions),
            "nmod-case-count",
        )

    def test_nmod_preposition_unrecognized(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "captured", "capture", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 18),
            word(4, "museum", "museum", "NOUN", "obj", 2, 22),
            word(5, "despite", "despite", "ADP", "case", 6, 29),
            word(6, "Kent", "Kent", "PROPN", "nmod", 4, 37),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            build_gf_tree_decline_reason(words, "capture", functions),
            "nmod-preposition-unrecognized",
        )

    def test_nmod_and_relative_clause_is_out_of_scope(self) -> None:
        # Both a relative clause and an nmod on the same head noun --
        # not confident which modifier matters (or how they'd compose).
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "captured", "capture", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 18),
            word(4, "museum", "museum", "NOUN", "obj", 2, 22),
            word(5, "in", "in", "ADP", "case", 6, 29),
            word(6, "Kent", "Kent", "PROPN", "nmod", 4, 32),
            word(7, "that", "that", "SCONJ", "mark", 8, 38),
            word(8, "opened", "open", "VERB", "acl:relcl", 4, 43),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            build_gf_tree_decline_reason(words, "capture", functions),
            "nmod-and-relative-clause",
        )


class CopulaClauseTests(unittest.TestCase):
    """"Waterloo is a county" -- the sentence's own UD root is the
    predicate NOUN itself, never VERB/AUX (see
    annotate_dependency_hints.py's own "cop"-child check for why
    classify_word never classifies this as "direct-argument" at all).
    grammar/Metonymy.gf's PredCopNP : NP -> NP -> S already existed
    before this module ever produced one -- no new grammar needed.
    """

    def test_a_basic_copula_clause(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 0),
            word(2, "is", "be", "AUX", "cop", 4, 9),
            word(3, "a", "a", "DET", "det", 4, 12),
            word(4, "county", "county", "NOUN", "root", 0, 14),
        ]
        tree = build_gf_tree(words, "county", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'PredCopNP (OpenPN "Waterloo") (OpenIndefCN "county" "county")',
        )

    def test_predicate_np_gets_an_nmod_modifier_for_free(self) -> None:
        # "Waterloo is a county in Iowa" -- _copula_clause reuses _np
        # (not _np_base) for the predicate NP, so NmodModifierTests's
        # own feature applies here with zero extra code.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 0),
            word(2, "is", "be", "AUX", "cop", 4, 9),
            word(3, "a", "a", "DET", "det", 4, 12),
            word(4, "county", "county", "NOUN", "root", 0, 14),
            word(5, "in", "in", "ADP", "case", 6, 21),
            word(6, "Iowa", "Iowa", "PROPN", "nmod", 4, 24),
        ]
        tree = build_gf_tree(words, "county", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'PredCopNP (OpenPN "Waterloo") '
            '(ModifyNP (OpenIndefCN "county" "county") (InPP (OpenPN "Iowa")))',
        )

    def test_root_lemma_mismatch(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 0),
            word(2, "is", "be", "AUX", "cop", 4, 9),
            word(3, "a", "a", "DET", "det", 4, 12),
            word(4, "county", "county", "NOUN", "root", 0, 14),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "museum", GF_FUNCTIONS),
            "root-lemma-mismatch:no-governing-start",
        )

    def test_root_lemma_mismatch_with_a_governing_start(self) -> None:
        # copula-argument's own dependency_hint does carry a
        # governing_start (the "is"/"was" word's own start_char) --
        # _copula_clause's own branch never resolves/verifies it against
        # anything (see its own comment), so this only ever tells apart
        # "no UD grounding at all" from "the hint carried one".
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 0),
            word(2, "is", "be", "AUX", "cop", 4, 9),
            word(3, "a", "a", "DET", "det", 4, 12),
            word(4, "county", "county", "NOUN", "root", 0, 14),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(
                words, "museum", GF_FUNCTIONS, governing_start=9
            ),
            "root-lemma-mismatch:governing-start-present",
        )

    def test_copula_count(self) -> None:
        # No "cop" child at all reaches _copula_clause (dispatch already
        # requires one), but two would be a genuine, unexpected
        # ambiguity -- confirms the count is actually checked, not just
        # assumed.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 0),
            word(2, "is", "be", "AUX", "cop", 4, 9),
            word(3, "was", "be", "AUX", "cop", 4, 12),
            word(4, "county", "county", "NOUN", "root", 0, 17),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "county", GF_FUNCTIONS),
            "copula-count",
        )

    def test_subject_count(self) -> None:
        words = [
            word(1, "is", "be", "AUX", "cop", 3, 0),
            word(2, "a", "a", "DET", "det", 3, 3),
            word(3, "county", "county", "NOUN", "root", 0, 5),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "county", GF_FUNCTIONS),
            "subject-count:root",
        )


class FrontedDateClauseTests(unittest.TestCase):
    def test_on_fronted_date(self) -> None:
        # "On 2010, Waterloo announces Henry"
        words = [
            word(1, "On", "on", "ADP", "case", 2, 0),
            word(2, "2010", "2010", "PROPN", "obl", 4, 3),
            word(3, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 10),
            word(4, "announces", "announce", "VERB", "root", 0, 19),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 29),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'OnFrontedS (OpenPN "2010") '
            '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Henry")))',
        )

    def test_in_and_from_fronted_dates(self) -> None:
        for preposition, constructor in (("In", "InFrontedS"), ("From", "FromFrontedS")):
            with self.subTest(preposition=preposition):
                words = [
                    word(1, preposition, preposition.lower(), "ADP", "case", 2, 0),
                    word(2, "2010", "2010", "PROPN", "obl", 4, len(preposition) + 1),
                    word(
                        3, "Waterloo", "Waterloo", "PROPN", "nsubj", 4,
                        len(preposition) + 7,
                    ),
                    word(
                        4, "announces", "announce", "VERB", "root", 0,
                        len(preposition) + 16,
                    ),
                    word(
                        5, "Henry", "Henry", "PROPN", "obj", 4,
                        len(preposition) + 26,
                    ),
                ]
                tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
                self.assertEqual(
                    tree,
                    f'{constructor} (OpenPN "2010") '
                    '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Henry")))',
                )

    def test_a_trailing_non_fronted_date_oblique_is_out_of_scope(self) -> None:
        # The same "on"+obl shape, but positioned *after* the subject --
        # not fronted, so not this construction (and general trailing
        # oblique-PP attachment is out of scope entirely -- see the
        # module docstring).
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 4, 19),
            word(4, "on", "on", "ADP", "case", 6, 25),
            word(5, "2010", "2010", "PROPN", "obl", 2, 28),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))


class SubordinateClauseTests(unittest.TestCase):
    def test_fronted_because_clause(self) -> None:
        # "Because Tolstoy announces Henry, Waterloo announces Mary"
        words = [
            word(1, "Because", "because", "SCONJ", "mark", 3, 0),
            word(2, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 3, 8),
            word(3, "announces", "announce", "VERB", "advcl", 6, 16),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 26),
            word(5, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 34),
            word(6, "announces", "announce", "VERB", "root", 0, 43),
            word(7, "Mary", "Mary", "PROPN", "obj", 6, 53),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'BecauseS (Pred (OpenPN "Tolstoy") (Compl CTX_announce (OpenPN "Henry"))) '
            '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Mary")))',
        )

    def test_trailing_although_clause(self) -> None:
        # "Waterloo announces Mary, although Tolstoy announces Henry"
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Mary", "Mary", "PROPN", "obj", 2, 19),
            word(4, "although", "although", "SCONJ", "mark", 6, 25),
            word(5, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 6, 34),
            word(6, "announces", "announce", "VERB", "advcl", 2, 42),
            word(7, "Henry", "Henry", "PROPN", "obj", 6, 52),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'SAlthoughS (Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Mary"))) '
            '(Pred (OpenPN "Tolstoy") (Compl CTX_announce (OpenPN "Henry")))',
        )

    def test_if_and_when_both_map_correctly(self) -> None:
        for subordinator, fronted_constructor in (("if", "IfS"), ("when", "WhenS")):
            with self.subTest(subordinator=subordinator):
                words = [
                    word(1, subordinator.capitalize(), subordinator, "SCONJ", "mark", 3, 0),
                    word(2, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 3, len(subordinator) + 1),
                    word(
                        3, "announces", "announce", "VERB", "advcl", 6,
                        len(subordinator) + 9,
                    ),
                    word(4, "Henry", "Henry", "PROPN", "obj", 3, len(subordinator) + 19),
                    word(
                        5, "Waterloo", "Waterloo", "PROPN", "nsubj", 6,
                        len(subordinator) + 27,
                    ),
                    word(
                        6, "announces", "announce", "VERB", "root", 0,
                        len(subordinator) + 36,
                    ),
                    word(7, "Mary", "Mary", "PROPN", "obj", 6, len(subordinator) + 46),
                ]
                tree = build_gf_tree(words, "announce", GF_FUNCTIONS)
                self.assertEqual(
                    tree,
                    f'{fronted_constructor} '
                    '(Pred (OpenPN "Tolstoy") (Compl CTX_announce (OpenPN "Henry"))) '
                    '(Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Mary")))',
                )

    def test_an_unrecognized_subordinator_is_out_of_scope(self) -> None:
        words = [
            word(1, "Since", "since", "SCONJ", "mark", 2, 0),
            word(2, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 3, 6),
            word(3, "announces", "announce", "VERB", "advcl", 6, 14),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 24),
            word(5, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 32),
            word(6, "announces", "announce", "VERB", "root", 0, 41),
            word(7, "Mary", "Mary", "PROPN", "obj", 6, 51),
        ]
        self.assertIsNone(build_gf_tree(words, "announce", GF_FUNCTIONS))


class GoverningStartTests(unittest.TestCase):
    """A real corpus run found "root-lemma-mismatch" dominates Stanza-tier
    declines (35/92 WiMCor, 43/122 ConMeC): the target's own governing
    verb (whatever resolve_action actually resolved, per
    annotate_dependency_hints.py's own "governing_start" hint field) is
    very often embedded in a relative/subordinate/complement clause of a
    real, complex sentence -- not the sentence's own UD root. These
    build ONLY that local clause (reusing the exact same _clause/_np
    machinery the root-anchored path already uses), deliberately not
    representing whatever wraps it.
    """

    def test_target_inside_a_relative_clause_with_its_own_subject(self) -> None:
        # "Napoleon renamed the county that Waterloo announces Henry" --
        # target=Waterloo, governing verb="announces" (the relative
        # clause's OWN verb). Distinct from
        # RelativeClauseTests.test_relative_clause_with_its_own_subject_
        # is_out_of_scope above: that test is about a relative clause
        # attached as an NP MODIFIER elsewhere in the sentence
        # (ModifyRelVP, out of scope since it has no room for the
        # embedded verb's own subject); here the metonymy TARGET itself
        # sits inside the relative clause, so _relative_clause_vp/
        # ModifyRelVP is never entered at all -- this is a completely
        # different code path (the new governing_start branch).
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "renamed", "rename", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 17),
            word(4, "county", "county", "NOUN", "obj", 2, 21),
            word(5, "that", "that", "SCONJ", "mark", 6, 28),
            word(6, "announces", "announce", "VERB", "acl:relcl", 4, 33),
            word(7, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 43),
            word(8, "Henry", "Henry", "PROPN", "obj", 6, 52),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS, governing_start=33)
        self.assertEqual(
            tree, 'Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN "Henry"))'
        )

    def test_target_inside_an_advcl_subordinate_clause(self) -> None:
        # "Because Tolstoy announces Henry, Waterloo praises Mary" --
        # target=Tolstoy, governing verb="announces" (the advcl's own
        # verb). Confirms the "mark" word ("Because") is correctly
        # excluded from the embedded-leftover-words check -- without
        # that exclusion this fixture would incorrectly decline.
        words = [
            word(1, "Because", "because", "SCONJ", "mark", 3, 0),
            word(2, "Tolstoy", "Tolstoy", "PROPN", "nsubj", 3, 8),
            word(3, "announces", "announce", "VERB", "advcl", 6, 16),
            word(4, "Henry", "Henry", "PROPN", "obj", 3, 26),
            word(5, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 34),
            word(6, "praises", "praise", "VERB", "root", 0, 43),
            word(7, "Mary", "Mary", "PROPN", "obj", 6, 51),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS, governing_start=16)
        self.assertEqual(
            tree, 'Pred (OpenPN "Tolstoy") (Compl CTX_announce (OpenPN "Henry"))'
        )

    def test_omitting_governing_start_is_byte_for_byte_todays_behavior(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(
            build_gf_tree(words, "announce", GF_FUNCTIONS),
            build_gf_tree(words, "announce", GF_FUNCTIONS, governing_start=None),
        )

    def test_governing_start_pointing_at_a_passive_roots_own_aux_still_takes_the_root_path(
        self,
    ) -> None:
        # "Henry was announced by Waterloo" -- root is "announced" (the
        # content verb). annotate_dependency_hints.py's own
        # _passive_verb_span anchors governing_start to
        # min(content_verb.start, aux_pass.start), which for real English
        # word order ("was announced") is the AUXILIARY's own start_char,
        # not the root's -- this must still resolve (via the aux:pass ->
        # its head hop) to the sentence's own root, taking the unchanged
        # existing path (fronted-date/subordinate-clause enrichment +
        # strict whole-sentence leftover check), not the new embedded
        # branch.
        words = [
            word(1, "Henry", "Henry", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 6),
            word(3, "announced", "announce", "VERB", "root", 0, 10),
            word(4, "by", "by", "ADP", "case", 5, 20),
            word(5, "Waterloo", "Waterloo", "PROPN", "obl", 3, 23),
        ]
        tree = build_gf_tree(words, "announce", GF_FUNCTIONS, governing_start=6)
        self.assertEqual(
            tree,
            build_gf_tree(words, "announce", GF_FUNCTIONS),
        )
        self.assertEqual(
            tree,
            'Pred (OpenPN "Henry") (PassCompl CTX_announce (OpenPN "Waterloo"))',
        )

    def test_a_reported_speech_wrapper_with_an_intransitive_local_clause_still_declines(
        self,
    ) -> None:
        # "Napoleon announced Waterloo fell" -- target=Waterloo, governing
        # verb="fell" (a ccomp -- reported speech/complement clause, a
        # wrapper shape this session has never built support for, on
        # purpose). The local clause itself is intransitive
        # (grammar/Metonymy.gf has no intransitive VP at all -- an
        # existing, already-documented limitation of the whole grammar,
        # not new to this branch), so this must still decline, and for
        # the SAME existing reason code the main-clause path already
        # uses for any other intransitive clause -- not a new code, not a
        # crash. Confirms the fix never inspects the wrapper's own deprel
        # at all: ccomp is handled by the identical code path as
        # acl:relcl/advcl above, it just happens to hit an unrelated,
        # pre-existing limitation here.
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "announced", "announce", "VERB", "root", 0, 9),
            word(3, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 19),
            word(4, "fell", "fall", "VERB", "ccomp", 2, 28),
        ]
        functions = {**GF_FUNCTIONS, "fall": "CTX_fall"}
        self.assertEqual(
            build_gf_tree_decline_reason(words, "fall", functions, governing_start=28),
            "object-count:zero",
        )

    def test_a_reported_speech_wrapper_with_a_transitive_local_clause_succeeds(self) -> None:
        # Same ccomp wrapper as above, but the local clause is
        # transitive -- succeeds, demonstrating the fix is genuinely
        # wrapper-agnostic (identical outcome regardless of whether the
        # wrapper is acl:relcl, advcl, or ccomp).
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "announced", "announce", "VERB", "root", 0, 9),
            word(3, "Waterloo", "Waterloo", "PROPN", "nsubj", 4, 19),
            word(4, "praised", "praise", "VERB", "ccomp", 2, 28),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 37),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS, governing_start=28)
        self.assertEqual(
            tree, 'Pred (OpenPN "Waterloo") (Compl CTX_praise (OpenPN "Henry"))'
        )

    def test_shared_subject_from_the_first_conjunct(self) -> None:
        # "Napoleon announced Henry and praised Waterloo" -- target=
        # Waterloo, governing verb="praised" (a "conj" sibling of the
        # root "announced", sharing its subject "Napoleon" -- English
        # coordination shares the first conjunct's subject unless a
        # later conjunct states its own, a real syntactic fact UD's own
        # "conj" relation encodes, not a guess). Real corpus evaluation
        # data (after suffixing "subject-count" with the governing verb's
        # own deprel -- an earlier, different guess about this bucket's
        # cause, acl:relcl, had measured zero real effect) found "conj"
        # the single largest share of it.
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "announced", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "and", "and", "CCONJ", "cc", 5, 25),
            word(5, "praised", "praise", "VERB", "conj", 2, 29),
            word(6, "Waterloo", "Waterloo", "PROPN", "obj", 5, 37),
        ]
        tree = build_gf_tree(words, "praise", GF_FUNCTIONS, governing_start=29)
        self.assertEqual(
            tree, 'Pred (OpenPN "Napoleon") (Compl CTX_praise (OpenPN "Waterloo"))'
        )

    def test_conj_without_a_clean_first_conjunct_subject_still_declines(self) -> None:
        # Same shape as above, but the first conjunct ("announced") has
        # no subject of its own either (e.g. itself embedded some other
        # way not modeled here) -- _shared_subject_from_conjunct only
        # borrows a subject it can find with total confidence (exactly
        # one plain "nsubj" on the true first conjunct); with none to
        # borrow, this still declines, reporting the real UD deprel
        # (still "subject-count:conj", diagnostically honest) rather
        # than silently guessing at any other word in the sentence.
        words = [
            word(1, "announced", "announce", "VERB", "root", 0, 0),
            word(2, "Henry", "Henry", "PROPN", "obj", 1, 10),
            word(3, "and", "and", "CCONJ", "cc", 4, 16),
            word(4, "praised", "praise", "VERB", "conj", 1, 20),
            word(5, "Waterloo", "Waterloo", "PROPN", "obj", 4, 28),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "praise", GF_FUNCTIONS, governing_start=20),
            "subject-count:conj",
        )

    def test_shared_subject_walks_a_chained_three_way_conjunct(self) -> None:
        # "Napoleon announced Henry, praised Waterloo, and greeted Mary"
        # -- target=Mary, governing verb="greeted", UD-attached as "conj"
        # of "praised" (itself "conj" of the root "announced") rather
        # than directly of the root -- one real, valid way UD represents
        # a 3+-way coordinated list. Confirms the "walk up while conj"
        # loop keeps going past one hop to find the true first conjunct
        # ("announced") and its subject ("Napoleon"), not just its
        # immediate "conj" parent ("praised", which has no subject of
        # its own either). Also includes the real UD "cc" word ("and",
        # attached to the last conjunct it precedes) the simpler two-way
        # test above omitted -- catching a real bug the first version of
        # this fix had (embedded-leftover-words firing on "and" even
        # though the shared subject was found correctly).
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "announced", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "praised", "praise", "VERB", "conj", 2, 26),
            word(5, "Waterloo", "Waterloo", "PROPN", "obj", 4, 34),
            word(6, "and", "and", "CCONJ", "cc", 7, 44),
            word(7, "greeted", "greet", "VERB", "conj", 4, 48),
            word(8, "Mary", "Mary", "PROPN", "obj", 7, 56),
        ]
        functions = {**GF_FUNCTIONS, "greet": "CTX_greet"}
        tree = build_gf_tree(words, "greet", functions, governing_start=48)
        self.assertEqual(
            tree, 'Pred (OpenPN "Napoleon") (Compl CTX_greet (OpenPN "Mary"))'
        )

    def test_governing_start_not_found(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(
                words, "announce", GF_FUNCTIONS, governing_start=999
            ),
            "governing-start-not-found",
        )

    def test_governing_word_not_verb(self) -> None:
        # governing_start points at "county" (a NOUN), a data shape
        # classify_word's own GOVERNING_UPOS check should never actually
        # produce -- a defensive check, same category as root-not-verb.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "county", "county", "NOUN", "obj", 2, 19),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(
                words, "announce", GF_FUNCTIONS, governing_start=19
            ),
            "governing-word-not-verb",
        )

    def test_governing_lemma_mismatch(self) -> None:
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "renamed", "rename", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 17),
            word(4, "county", "county", "NOUN", "obj", 2, 21),
            word(5, "that", "that", "SCONJ", "mark", 6, 28),
            word(6, "announces", "announce", "VERB", "acl:relcl", 4, 33),
            word(7, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 43),
            word(8, "Henry", "Henry", "PROPN", "obj", 6, 52),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(
                words, "sign", GF_FUNCTIONS, governing_start=33
            ),
            "governing-lemma-mismatch",
        )

    def test_embedded_leftover_words(self) -> None:
        # Same relative-clause shape as the first test above, but with an
        # extra, unhandled adverbial modifier directly on the embedded
        # verb ("quickly") -- content this branch doesn't understand, so
        # it must decline rather than silently drop it.
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "renamed", "rename", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 17),
            word(4, "county", "county", "NOUN", "obj", 2, 21),
            word(5, "that", "that", "SCONJ", "mark", 6, 28),
            word(6, "announces", "announce", "VERB", "acl:relcl", 4, 33),
            word(7, "Waterloo", "Waterloo", "PROPN", "nsubj", 6, 43),
            word(8, "quickly", "quickly", "ADV", "advmod", 6, 52),
            word(9, "Henry", "Henry", "PROPN", "obj", 6, 60),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(
                words, "announce", GF_FUNCTIONS, governing_start=33
            ),
            "embedded-leftover-words:advmod",
        )

    def test_target_is_the_object_of_an_implicit_subject_relative_clause(self) -> None:
        # "Napoleon renamed the county that governs Henry" -- target=
        # Henry, governing verb="governs" (an acl:relcl on "county" with
        # NO own nsubj word at all -- the relativizer elided, mirroring
        # RelativeClauseTests.test_relative_clause_on_the_object's own
        # precedent -- "county" implicitly fills "governs"'s subject
        # role). A real corpus run found this dominates the new
        # "subject-count" bucket the governing_start branch itself
        # introduced: a bare _clause call has no notion of an implicit
        # subject, only ever looks for a literal "nsubj" child.
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "renamed", "rename", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 17),
            word(4, "county", "county", "NOUN", "obj", 2, 21),
            word(5, "governs", "govern", "VERB", "acl:relcl", 4, 28),
            word(6, "Henry", "Henry", "PROPN", "obj", 5, 36),
        ]
        functions = {**GF_FUNCTIONS, "govern": "CTX_govern"}
        tree = build_gf_tree(words, "govern", functions, governing_start=28)
        self.assertEqual(
            tree, 'Pred (OpenDefCN "county" "county") (Compl CTX_govern (OpenPN "Henry"))'
        )

    def test_implicit_subject_relative_clause_head_with_another_relative_clause(
        self,
    ) -> None:
        # Same shape as above, but "county" has a SECOND, different
        # relative clause attached too ("which Waterloo praised") -- that
        # second relative clause is outside governing_word's own subtree
        # entirely (it modifies the head noun, not a descendant of
        # "governs"), so the ordinary embedded-leftover-words check can't
        # catch it; this must decline explicitly rather than silently
        # drop it.
        words = [
            word(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0),
            word(2, "renamed", "rename", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 17),
            word(4, "county", "county", "NOUN", "obj", 2, 21),
            word(5, "governs", "govern", "VERB", "acl:relcl", 4, 28),
            word(6, "Henry", "Henry", "PROPN", "obj", 5, 36),
            word(7, "praised", "praise", "VERB", "acl:relcl", 4, 43),
            word(8, "Waterloo", "Waterloo", "PROPN", "nsubj", 7, 51),
        ]
        functions = {**GF_FUNCTIONS, "govern": "CTX_govern"}
        self.assertEqual(
            build_gf_tree_decline_reason(words, "govern", functions, governing_start=28),
            "governing-relcl-head-has-other-relative-clause",
        )


class BuildGfTreeDeclineReasonTests(unittest.TestCase):
    """A real corpus evaluation run measured zero successful uses of
    build_gf_tree across 300 real rows (tree_source_counts: 100%
    "gf-parser") -- every one of these reproduces one specific decline
    path from the tests above and confirms the reason code matches,
    proving the vocabulary this session's next real measurement will
    actually see.
    """

    def test_succeeds_when_build_gf_tree_would(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS), "")

    def test_root_count(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "announces", "announce", "VERB", "root", 0, 30),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS), "root-count"
        )

    def test_root_not_verb(self) -> None:
        # A NOUN root with no "cop" child at all -- not a copula clause
        # (see CopulaClauseTests for the "Waterloo is a county" shape,
        # which now succeeds), just some other NOUN-rooted UD shape this
        # module still doesn't model.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "county", "county", "NOUN", "root", 0, 9),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "county", GF_FUNCTIONS),
            "root-not-verb:NOUN",
        )

    def test_root_lemma_mismatch(self) -> None:
        # No governing_start passed at all -- the "no-governing-start"
        # suffix (see _main_clause's own docstring for the full
        # vocabulary, added after a real corpus run found this the
        # single largest terminal blocker in both corpora).
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "sign", GF_FUNCTIONS),
            "root-lemma-mismatch:no-governing-start",
        )

    def test_root_lemma_mismatch_with_governing_start_resolving_to_the_root(
        self,
    ) -> None:
        # governing_start resolves successfully, and to this very root --
        # yet the lemmas still disagree. A real, previously-unnamed third
        # case this suffix distinguishes from both "no-governing-start"
        # (no UD grounding at all) and the governing_start branch's own,
        # separate "governing-lemma-mismatch" (governing_start resolves
        # to a *different* word than root).
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(
                words, "sign", GF_FUNCTIONS, governing_start=9
            ),
            "root-lemma-mismatch:governing-start-is-root",
        )

    def test_verb_not_in_lexicon(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "floreates", "floreate", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "floreate", GF_FUNCTIONS),
            "verb-not-in-lexicon",
        )

    def test_subject_count(self) -> None:
        # Suffixed with the clause-building verb's own deprel ("root"
        # here) -- see GoverningStartTests for the embedded-verb case,
        # where the suffix is the real diagnostic payoff (e.g. "conj",
        # not always "root").
        words = [
            word(1, "announces", "announce", "VERB", "root", 0, 0),
            word(2, "Henry", "Henry", "PROPN", "obj", 1, 10),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "subject-count:root",
        )

    def test_object_count(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "object-count:zero",
        )

    def test_np_unsupported_upos(self) -> None:
        # A numeral subject -- _np only ever dispatches on PROPN/PRON/
        # NOUN, so NUM (or any other UPOS) hits this generic fallback
        # rather than one of the more specific per-shape reasons above.
        words = [
            word(1, "1805", "1805", "NUM", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 5),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 14),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "np-unsupported-upos:NUM",
        )

    def test_pronoun_unrecognized(self) -> None:
        words = [
            word(1, "who", "who", "PRON", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 4),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 14),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "pronoun-unrecognized",
        )

    def test_proper_noun_chain_too_long(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "A", "A", "PROPN", "compound", 6, 19),
            word(4, "B", "B", "PROPN", "compound", 6, 21),
            word(5, "C", "C", "PROPN", "compound", 6, 23),
            word(6, "D", "D", "PROPN", "obj", 2, 25),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "proper-noun-chain-too-long",
        )

    def test_common_noun_determiner_or_adjective_count(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "programmes", "programme", "NOUN", "obj", 2, 19),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "common-noun-determiner-or-adjective-count:zero-determiners",
        )

    def test_common_noun_unrecognized_determiner(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "every", "every", "DET", "det", 4, 19),
            word(4, "county", "county", "NOUN", "obj", 2, 25),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "common-noun-unrecognized-determiner:every",
        )

    def test_passive_aux_count(self) -> None:
        words = [
            word(1, "Henry", "Henry", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 6),
            word(3, "announced", "announce", "VERB", "root", 0, 10),
            word(4, "by", "by", "ADP", "case", 5, 20),
            word(5, "Waterloo", "Waterloo", "PROPN", "obl", 3, 23),
        ]
        # A second aux:pass child makes the count wrong.
        words.append(
            word(6, "being", "be", "AUX", "aux:pass", 3, 32)
        )
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "passive-aux-count",
        )

    def test_passive_agent_count(self) -> None:
        # Two distinct "by"-agents -- a genuine ambiguity (which one is
        # real?), unlike the zero-agent case (now a supported bare
        # passive via PassCompl0, see PassiveClauseTests).
        words = [
            word(1, "Henry", "Henry", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 6),
            word(3, "announced", "announce", "VERB", "root", 0, 10),
            word(4, "by", "by", "ADP", "case", 5, 20),
            word(5, "Waterloo", "Waterloo", "PROPN", "obl", 3, 23),
            word(6, "by", "by", "ADP", "case", 7, 32),
            word(7, "Napoleon", "Napoleon", "PROPN", "obl", 3, 35),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "passive-agent-count",
        )

    def test_relative_clause_count(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "announces", "announce", "VERB", "acl:relcl", 3, 26),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 36),
            word(6, "signs", "sign", "VERB", "acl:relcl", 3, 42),
            word(7, "Mary", "Mary", "PROPN", "obj", 6, 48),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "praise", GF_FUNCTIONS),
            "relative-clause-count",
        )

    def test_relative_clause_verb_not_verb(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "county", "county", "NOUN", "acl:relcl", 3, 26),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "praise", GF_FUNCTIONS),
            "relative-clause-verb-not-verb",
        )

    def test_relative_clause_has_own_subject(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "who", "who", "PRON", "nsubj", 5, 26),
            word(5, "announces", "announce", "VERB", "acl:relcl", 3, 30),
            word(6, "Henry", "Henry", "PROPN", "obj", 5, 40),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "praise", GF_FUNCTIONS),
            "relative-clause-has-own-subject",
        )

    def test_relative_clause_verb_not_in_lexicon(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "floreates", "floreate", "VERB", "acl:relcl", 3, 26),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 36),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "praise", GF_FUNCTIONS),
            "relative-clause-verb-not-in-lexicon",
        )

    def test_leftover_words(self) -> None:
        # A PP modifier neither consumed nor accounted for anywhere.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
            word(4, "in", "in", "ADP", "case", 6, 25),
            word(5, "Ontario", "Ontario", "PROPN", "obl", 2, 28),
        ]
        self.assertEqual(
            build_gf_tree_decline_reason(words, "announce", GF_FUNCTIONS),
            "leftover-words:case",
        )


class BuildGfTreeFromLlmStructureTests(unittest.TestCase):
    """The LLM-proposer tier's own renderer -- reuses the same low-level
    rendering primitives as the UD-tree builder above (_apply/_quote/
    _PROPER_NOUN_CONSTRUCTORS/_PRONOUN_CONSTRUCTORS), just fed an LLM-
    described structure instead of a UD graph. Every generated tree
    shape here was also verified directly against the local GF toolchain
    before being written into build_gf_tree_from_dependencies.py itself.
    """

    def test_active_with_proper_noun_subject_and_object(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {"kind": "proper_noun", "tokens": ["Henry", "County"]},
        }
        tree = build_gf_tree_from_llm_structure(structure, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") (Compl CTX_announce (OpenPN2 "Henry" "County"))',
        )

    def test_three_token_proper_noun(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {
                "kind": "proper_noun",
                "tokens": ["Royal", "Shipley", "School"],
            },
        }
        tree = build_gf_tree_from_llm_structure(structure, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenPN3 "Royal" "Shipley" "School"))',
        )

    def test_pronoun_subject_and_common_noun_object_with_adjective(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "he"},
            "object": {
                "kind": "common_noun",
                "determiner": "a",
                "noun": "programme",
                "adjective": "large",
            },
        }
        tree = build_gf_tree_from_llm_structure(structure, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred HePN (Compl CTX_announce '
            '(OpenAdjIndefCN "large" "programme" "programme"))',
        )

    def test_common_noun_without_adjective_definite(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {"kind": "common_noun", "determiner": "the", "noun": "county"},
        }
        tree = build_gf_tree_from_llm_structure(structure, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenDefCN "county" "county"))',
        )

    def test_an_determiner_is_indefinite_same_as_a(self) -> None:
        # A real corpus run showed "llm-common-noun-unrecognized-
        # determiner" firing whenever the model correctly copied "an"
        # (vowel-initial nouns) from the sentence -- the UD-based tier
        # already accepts both ("a", "an" in _INDEFINITE_DETERMINERS),
        # this tier didn't.
        structure = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "object": {"kind": "common_noun", "determiner": "an", "noun": "institution"},
        }
        tree = build_gf_tree_from_llm_structure(structure, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") '
            '(Compl CTX_announce (OpenIndefCN "institution" "institution"))',
        )

    def test_all_four_pronouns(self) -> None:
        for pronoun, constructor in (
            ("he", "HePN"), ("she", "ShePN"), ("it", "ItPN"), ("they", "TheyPN"),
        ):
            with self.subTest(pronoun=pronoun):
                structure = {
                    "voice": "active",
                    "subject": {"kind": "pronoun", "pronoun": pronoun},
                    "object": {"kind": "proper_noun", "tokens": ["Henry"]},
                }
                tree = build_gf_tree_from_llm_structure(
                    structure, "announce", GF_FUNCTIONS
                )
                self.assertEqual(
                    tree, f'Pred {constructor} (Compl CTX_announce (OpenPN "Henry"))'
                )

    def test_passive_with_agent(self) -> None:
        structure = {
            "voice": "passive",
            "subject": {"kind": "proper_noun", "tokens": ["Waterloo"]},
            "agent": {"kind": "proper_noun", "tokens": ["Henry"]},
        }
        tree = build_gf_tree_from_llm_structure(structure, "announce", GF_FUNCTIONS)
        self.assertEqual(
            tree,
            'Pred (OpenPN "Waterloo") (PassCompl CTX_announce (OpenPN "Henry"))',
        )

    def test_declines_when_lemma_missing_from_lexicon(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "he"},
            "object": {"kind": "pronoun", "pronoun": "it"},
        }
        self.assertIsNone(
            build_gf_tree_from_llm_structure(structure, "floreate", GF_FUNCTIONS)
        )


class BuildGfTreeFromLlmStructureDeclineReasonTests(unittest.TestCase):
    def test_succeeds_when_the_renderer_would(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "he"},
            "object": {"kind": "pronoun", "pronoun": "it"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "",
        )

    def test_structure_not_a_dict(self) -> None:
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                None, "announce", GF_FUNCTIONS
            ),
            "llm-structure-not-a-dict",
        )

    def test_verb_not_in_lexicon(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "he"},
            "object": {"kind": "pronoun", "pronoun": "it"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "floreate", GF_FUNCTIONS
            ),
            "verb-not-in-lexicon",
        )

    def test_voice_unrecognized(self) -> None:
        structure = {"voice": None, "subject": None, "object": None, "agent": None}
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-voice-unrecognized",
        )

    def test_active_missing_np(self) -> None:
        structure = {"voice": "active", "subject": {"kind": "pronoun", "pronoun": "he"}}
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-active-missing-np",
        )

    def test_passive_missing_np(self) -> None:
        structure = {
            "voice": "passive",
            "subject": {"kind": "pronoun", "pronoun": "he"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-passive-missing-np",
        )

    def test_np_not_a_dict(self) -> None:
        structure = {"voice": "active", "subject": "Waterloo", "object": {"kind": "pronoun", "pronoun": "it"}}
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-np-not-a-dict",
        )

    def test_np_unrecognized_kind(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "numeral", "text": "1805"},
            "object": {"kind": "pronoun", "pronoun": "it"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-np-unrecognized-kind",
        )

    def test_proper_noun_tokens_invalid(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": "Waterloo"},
            "object": {"kind": "pronoun", "pronoun": "it"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-proper-noun-tokens-invalid",
        )

    def test_proper_noun_chain_too_long(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "proper_noun", "tokens": ["A", "B", "C", "D"]},
            "object": {"kind": "pronoun", "pronoun": "it"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-proper-noun-chain-too-long",
        )

    def test_pronoun_unrecognized(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "who"},
            "object": {"kind": "pronoun", "pronoun": "it"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-pronoun-unrecognized",
        )

    def test_common_noun_missing_noun(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "he"},
            "object": {"kind": "common_noun", "determiner": "a", "noun": None},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-common-noun-missing-noun",
        )

    def test_common_noun_unrecognized_determiner(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "he"},
            "object": {"kind": "common_noun", "determiner": "every", "noun": "county"},
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-common-noun-unrecognized-determiner",
        )

    def test_common_noun_invalid_adjective(self) -> None:
        structure = {
            "voice": "active",
            "subject": {"kind": "pronoun", "pronoun": "he"},
            "object": {
                "kind": "common_noun",
                "determiner": "a",
                "noun": "county",
                "adjective": 5,
            },
        }
        self.assertEqual(
            build_gf_tree_from_llm_structure_decline_reason(
                structure, "announce", GF_FUNCTIONS
            ),
            "llm-common-noun-invalid-adjective",
        )


class LoadGfFunctionByLemmaTests(unittest.TestCase):
    def test_inverts_the_gf_function_to_lemma_direction(self) -> None:
        actions_json = {
            "actions": [
                {"gf_function": "CTX_abc123", "lemma": "abandon"},
                {"gf_function": "CTX_def456", "lemma": "announce"},
            ]
        }
        self.assertEqual(
            load_gf_function_by_lemma(actions_json),
            {"abandon": "CTX_abc123", "announce": "CTX_def456"},
        )


class EnumerateAllBlockersTests(unittest.TestCase):
    """enumerate_gf_tree_blockers -- unlike build_gf_tree_decline_reason,
    which only ever reports the *first* _Bail a sentence hits, this
    keeps going past each ablatable one to answer the compounding-
    blockers question a real corpus run raised directly: does a
    sentence that now passes an earlier check actually build, or does
    it just hit a different, still-unaddressed blocker next?
    """

    def test_zero_blockers_returns_an_empty_list(self) -> None:
        # Same fixture as SimpleTransitiveClauseTests's own -- already
        # builds on the first attempt, nothing to enumerate.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(enumerate_gf_tree_blockers(words, "announce", GF_FUNCTIONS), [])

    def test_a_terminal_blocker_with_no_known_ablation_stops_immediately(self) -> None:
        # No subject at all -- the ablatable "2+ nsubj" path has nothing
        # to dedupe (its own groups dict is empty), so this correctly
        # stays terminal rather than looping.
        words = [
            word(1, "captured", "capture", "VERB", "root", 0, 0),
            word(2, "the", "the", "DET", "det", 3, 10),
            word(3, "museum", "museum", "NOUN", "obj", 1, 14),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "capture", functions),
            ["subject-count:root"],
        )

    def test_two_blockers_compound_on_the_same_noun(self) -> None:
        # "Waterloo captured the big beautiful museum despite Kent" --
        # the object noun has both 2 adjectives (common-noun-determiner-
        # or-adjective-count) *and* an nmod with an unrecognized
        # preposition. _np_base's own adjective-count check runs first,
        # so that is the reason build_gf_tree_decline_reason alone would
        # report; this confirms the *second*, still-unaddressed nmod
        # problem on the very same noun is found right after the first
        # is ablated away -- the exact "fix one, hit the next" pattern a
        # real corpus run's growing decline_reason buckets predicted.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "captured", "capture", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 6, 18),
            word(4, "big", "big", "ADJ", "amod", 6, 22),
            word(5, "beautiful", "beautiful", "ADJ", "amod", 6, 26),
            word(6, "museum", "museum", "NOUN", "obj", 2, 36),
            word(7, "despite", "despite", "ADP", "case", 8, 43),
            word(8, "Kent", "Kent", "PROPN", "nmod", 6, 51),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            build_gf_tree_decline_reason(words, "capture", functions),
            "common-noun-determiner-or-adjective-count:multiple-adjectives",
        )
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "capture", functions),
            [
                "common-noun-determiner-or-adjective-count:multiple-adjectives",
                "nmod-preposition-unrecognized",
            ],
        )

    def test_subject_count_multiplicity_is_ablated(self) -> None:
        # Two literal "nsubj" arcs on the same verb -- an artificial UD
        # shape (like NmodModifierTests's own test_nmod_count fixture),
        # but a valid exercise of the "keep earliest, drop the rest"
        # ablation regardless of real-world naturalness.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 3, 0),
            word(2, "Napoleon", "Napoleon", "PROPN", "nsubj", 3, 13),
            word(3, "captured", "capture", "VERB", "root", 0, 23),
            word(4, "the", "the", "DET", "det", 5, 32),
            word(5, "museum", "museum", "NOUN", "obj", 3, 36),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "capture", functions),
            ["subject-count:root"],
        )

    def test_object_count_multiplicity_is_ablated(self) -> None:
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "captured", "capture", "VERB", "root", 0, 9),
            word(3, "the", "the", "DET", "det", 4, 18),
            word(4, "museum", "museum", "NOUN", "obj", 2, 22),
            word(5, "the", "the", "DET", "det", 6, 33),
            word(6, "palace", "palace", "NOUN", "obj", 2, 37),
        ]
        functions = {**GF_FUNCTIONS, "capture": "CTX_capture"}
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "capture", functions),
            ["object-count:multiple"],
        )

    def test_passive_agent_count_multiplicity_is_ablated(self) -> None:
        # Same fixture as BuildGfTreeDeclineReasonTests's own
        # test_passive_agent_count.
        words = [
            word(1, "Henry", "Henry", "PROPN", "nsubj:pass", 3, 0),
            word(2, "was", "be", "AUX", "aux:pass", 3, 6),
            word(3, "announced", "announce", "VERB", "root", 0, 10),
            word(4, "by", "by", "ADP", "case", 5, 20),
            word(5, "Waterloo", "Waterloo", "PROPN", "obl", 3, 23),
            word(6, "by", "by", "ADP", "case", 7, 32),
            word(7, "Napoleon", "Napoleon", "PROPN", "obl", 3, 35),
        ]
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "announce", GF_FUNCTIONS),
            ["passive-agent-count"],
        )

    def test_pronoun_unrecognized_is_ablated(self) -> None:
        words = [
            word(1, "Something", "something", "PRON", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 10),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 20),
        ]
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "announce", GF_FUNCTIONS),
            ["pronoun-unrecognized"],
        )

    def test_common_noun_unrecognized_determiner_is_ablated(self) -> None:
        # Same fixture as BuildGfTreeDeclineReasonTests's own
        # test_common_noun_unrecognized_determiner.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "every", "every", "DET", "det", 4, 19),
            word(4, "county", "county", "NOUN", "obj", 2, 25),
        ]
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "announce", GF_FUNCTIONS),
            ["common-noun-unrecognized-determiner:every"],
        )

    def test_proper_noun_chain_too_long_is_truncated(self) -> None:
        # Same fixture as BuildGfTreeDeclineReasonTests's own
        # test_proper_noun_chain_too_long -- "D" (start_char 25) is the
        # real head, last by real English compound-noun word order; the
        # ablation must drop the earliest-starting modifier ("A"), never
        # the head itself.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "announces", "announce", "VERB", "root", 0, 9),
            word(3, "A", "A", "PROPN", "compound", 6, 19),
            word(4, "B", "B", "PROPN", "compound", 6, 21),
            word(5, "C", "C", "PROPN", "compound", 6, 23),
            word(6, "D", "D", "PROPN", "obj", 2, 25),
        ]
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "announce", GF_FUNCTIONS),
            ["proper-noun-chain-too-long"],
        )

    def test_verb_not_in_lexicon_is_ablated(self) -> None:
        # Same fixture as BuildGfTreeDeclineReasonTests's own
        # test_verb_not_in_lexicon -- the injected placeholder lexicon
        # entry is never a real GF function name, only ever used inside
        # this diagnostic search, so this can safely keep going.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "floreates", "floreate", "VERB", "root", 0, 9),
            word(3, "Henry", "Henry", "PROPN", "obj", 2, 19),
        ]
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "floreate", GF_FUNCTIONS),
            ["verb-not-in-lexicon"],
        )

    def test_relative_clause_verb_not_in_lexicon_is_ablated(self) -> None:
        # Same fixture as BuildGfTreeDeclineReasonTests's own
        # test_relative_clause_verb_not_in_lexicon.
        words = [
            word(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0),
            word(2, "praises", "praise", "VERB", "root", 0, 9),
            word(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17),
            word(4, "floreates", "floreate", "VERB", "acl:relcl", 3, 26),
            word(5, "Henry", "Henry", "PROPN", "obj", 4, 36),
        ]
        self.assertEqual(
            enumerate_gf_tree_blockers(words, "praise", GF_FUNCTIONS),
            ["relative-clause-verb-not-in-lexicon"],
        )


if __name__ == "__main__":
    unittest.main()
