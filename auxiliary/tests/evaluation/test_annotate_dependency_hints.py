from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from annotate_dependency_hints import (  # noqa: E402
    annotate,
    classify_word,
    find_governing_structure,
    find_sentence_ud_words,
    serialize_sentence_words,
    validate_row,
)


class FakeToken:
    def __init__(self, start_char: int, end_char: int) -> None:
        self.start_char = start_char
        self.end_char = end_char


class FakeWord:
    def __init__(
        self,
        word_id: int,
        text: str,
        lemma: str,
        upos: str,
        deprel: str,
        head: int,
        start_char: int,
        end_char: int,
    ) -> None:
        self.id = word_id
        self.text = text
        self.lemma = lemma
        self.upos = upos
        self.deprel = deprel
        self.head = head
        self.parent = FakeToken(start_char, end_char)


class FakeSentence:
    def __init__(self, words: list[FakeWord]) -> None:
        self.words = words


class FakeDocument:
    def __init__(self, sentences: list[FakeSentence]) -> None:
        self.sentences = sentences


def moscow_signed_document() -> FakeDocument:
    # "Moscow signed the agreement"
    #  0     7      14  18
    words = [
        FakeWord(1, "Moscow", "Moscow", "PROPN", "nsubj", 2, 0, 6),
        FakeWord(2, "signed", "sign", "VERB", "root", 0, 7, 13),
        FakeWord(3, "the", "the", "DET", "det", 4, 14, 17),
        FakeWord(4, "agreement", "agreement", "NOUN", "obj", 2, 18, 27),
    ]
    return FakeDocument([FakeSentence(words)])


class ClassifyWordTests(unittest.TestCase):
    def test_subject_of_a_verb_is_a_direct_argument(self) -> None:
        document = moscow_signed_document()
        sentence = document.sentences[0]
        target_word = sentence.words[0]
        self.assertEqual(
            classify_word(sentence, target_word),
            ("direct-argument", "Subject", "sign", 7, 13, "active", ""),
        )

    def test_object_of_a_verb_is_a_direct_argument(self) -> None:
        document = moscow_signed_document()
        sentence = document.sentences[0]
        target_word = sentence.words[3]
        self.assertEqual(
            classify_word(sentence, target_word),
            ("direct-argument", "Object", "sign", 7, 13, "active", ""),
        )

    def test_oblique_with_case_child_reconstructs_a_phrasal_verb_lemma(self) -> None:
        # "The teenager listened to Mozart"
        #  0   4        13       22 25
        words = [
            FakeWord(1, "The", "the", "DET", "det", 2, 0, 3),
            FakeWord(2, "teenager", "teenager", "NOUN", "nsubj", 3, 4, 12),
            FakeWord(3, "listened", "listen", "VERB", "root", 0, 13, 21),
            FakeWord(4, "to", "to", "ADP", "case", 5, 22, 24),
            FakeWord(5, "Mozart", "Mozart", "PROPN", "obl", 3, 25, 31),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[4]),
            ("direct-argument", "Object", "listen to", 13, 24, "active", ""),
        )

    def test_nested_possessive_modifier_is_not_a_direct_argument(self) -> None:
        # "Anna reads Tolstoy's books"
        words = [
            FakeWord(1, "Anna", "Anna", "PROPN", "nsubj", 2, 0, 4),
            FakeWord(2, "reads", "read", "VERB", "root", 0, 5, 10),
            FakeWord(3, "Tolstoy", "Tolstoy", "PROPN", "nmod:poss", 5, 11, 18),
            FakeWord(4, "'s", "'s", "PART", "case", 3, 18, 20),
            FakeWord(5, "books", "book", "NOUN", "obj", 2, 21, 26),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[2]),
            ("nested-modifier", "", "", None, None, "active", "nmod:poss"),
        )

    def test_an_unlisted_nmod_subtype_is_still_a_nested_modifier(self) -> None:
        # "the museum yesterday" (nmod:unmarked -- no "case" preposition
        # word at all) -- a real corpus run found this specific subtype
        # falling through to undifferentiated "no-governing-verb", even
        # though "nmod:unmarked" means the exact same "modifier nested
        # inside an NP" thing bare "nmod"/"nmod:poss" already do.
        words = [
            FakeWord(1, "Anna", "Anna", "PROPN", "nsubj", 2, 0, 4),
            FakeWord(2, "visited", "visit", "VERB", "root", 0, 5, 12),
            FakeWord(3, "the", "the", "DET", "det", 4, 13, 16),
            FakeWord(4, "museum", "museum", "NOUN", "obj", 2, 17, 23),
            FakeWord(5, "yesterday", "yesterday", "NOUN", "nmod:unmarked", 4, 24, 33),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[4]),
            ("nested-modifier", "", "", None, None, "active", "nmod:unmarked"),
        )

    def test_an_unlisted_obl_subtype_still_reconstructs_a_governing_structure(
        self,
    ) -> None:
        # "The teenager listened attentively" as an obl:agent stand-in --
        # a real corpus run found "obl:agent"/"obl:unmarked" falling
        # through to undifferentiated "no-governing-verb", even though
        # the underlying case-word/by-agent detection logic already
        # works identically regardless of the obl subtype.
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj:pass", 3, 0, 8),
            FakeWord(2, "was", "be", "AUX", "aux:pass", 3, 9, 12),
            FakeWord(3, "captured", "capture", "VERB", "root", 0, 13, 21),
            FakeWord(4, "by", "by", "ADP", "case", 5, 22, 24),
            FakeWord(5, "Napoleon", "Napoleon", "PROPN", "obl:agent", 3, 25, 33),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[4]),
            ("direct-argument", "Subject", "capture", 9, 21, "passive", ""),
        )

    def test_no_governing_verb_for_an_unhandled_relation(self) -> None:
        words = [
            FakeWord(1, "Yesterday", "yesterday", "ADV", "advmod", 2, 0, 9),
            FakeWord(2, "left", "leave", "VERB", "root", 0, 10, 14),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[0]),
            ("no-governing-verb:target-deprel-advmod", "", "", None, None, "active", ""),
        )

    def test_a_coordinated_subject_shares_the_first_conjuncts_role(self) -> None:
        # "Napoleon and Waterloo announced a treaty" -- target="Waterloo"
        # (deprel="conj", head=Napoleon) shares Napoleon's own "nsubj"
        # role, since UD coordination means both conjuncts fill the same
        # syntactic slot. A real corpus run found this ("target-deprel-
        # conj") the single dominant cause of "no-governing-verb"
        # (27/33 in WiMCor, ~82% of what remained after the nmod:*/
        # obl:* subtype fix).
        words = [
            FakeWord(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 3, 0, 8),
            FakeWord(2, "Waterloo", "Waterloo", "PROPN", "conj", 1, 13, 21),
            FakeWord(3, "announced", "announce", "VERB", "root", 0, 22, 31),
            FakeWord(4, "treaty", "treaty", "NOUN", "obj", 3, 34, 40),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[1]),
            ("direct-argument", "Subject", "announce", 22, 31, "active", ""),
        )

    def test_a_chained_three_way_coordinated_object_walks_to_the_true_first_conjunct(
        self,
    ) -> None:
        # "Napoleon praised Tolstoy, Waterloo, and Henry" -- target=
        # "Henry" chains through "Waterloo" (itself a "conj") to reach
        # "Tolstoy" (the real first conjunct, deprel="obj") -- UD may
        # attach every later conjunct directly to the first, or chain
        # them one to the next; this exercises the chained shape.
        words = [
            FakeWord(1, "Napoleon", "Napoleon", "PROPN", "nsubj", 2, 0, 8),
            FakeWord(2, "praised", "praise", "VERB", "root", 0, 9, 16),
            FakeWord(3, "Tolstoy", "Tolstoy", "PROPN", "obj", 2, 17, 24),
            FakeWord(4, "Waterloo", "Waterloo", "PROPN", "conj", 3, 26, 34),
            FakeWord(5, "Henry", "Henry", "PROPN", "conj", 4, 36, 41),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[4]),
            ("direct-argument", "Object", "praise", 9, 16, "active", ""),
        )

    def test_a_coordinated_nested_modifier_still_resolves_through_the_conj_chain(
        self,
    ) -> None:
        # Coordination isn't only ever a clause argument -- a conjunct
        # of a nested modifier must still correctly decline as
        # "nested-modifier" (propagating whatever the first conjunct's
        # own classification turns out to be, not just direct-argument).
        words = [
            FakeWord(1, "Anna", "Anna", "PROPN", "nsubj", 2, 0, 4),
            FakeWord(2, "reads", "read", "VERB", "root", 0, 5, 10),
            FakeWord(3, "Tolstoy", "Tolstoy", "PROPN", "nmod:poss", 5, 11, 18),
            FakeWord(4, "Turgenev", "Turgenev", "PROPN", "conj", 3, 20, 28),
            FakeWord(5, "books", "book", "NOUN", "obj", 2, 29, 34),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[3]),
            ("nested-modifier", "", "", None, None, "active", "nmod:poss"),
        )

    def test_a_broken_conj_chain_is_reported_distinctly(self) -> None:
        # Defensive only -- a well-formed UD graph never has a "conj"
        # word whose own head id doesn't exist.
        words = [FakeWord(1, "Waterloo", "Waterloo", "PROPN", "conj", 99, 0, 8)]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[0]),
            ("no-governing-verb:conj-chain-broken", "", "", None, None, "active", ""),
        )

    def test_passive_subject_is_the_object_hole_not_the_subject_hole(self) -> None:
        # "Waterloo was captured by Napoleon"
        #  0        11  15       26 29
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj:pass", 3, 0, 8),
            FakeWord(2, "was", "be", "AUX", "aux:pass", 3, 9, 12),
            FakeWord(3, "captured", "capture", "VERB", "root", 0, 13, 21),
            FakeWord(4, "by", "by", "ADP", "case", 5, 22, 24),
            FakeWord(5, "Napoleon", "Napoleon", "PROPN", "obl", 3, 25, 33),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[0]),
            ("direct-argument", "Object", "capture", 9, 21, "passive", ""),
        )

    def test_passive_by_agent_is_the_subject_hole(self) -> None:
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj:pass", 3, 0, 8),
            FakeWord(2, "was", "be", "AUX", "aux:pass", 3, 9, 12),
            FakeWord(3, "captured", "capture", "VERB", "root", 0, 13, 21),
            FakeWord(4, "by", "by", "ADP", "case", 5, 22, 24),
            FakeWord(5, "Napoleon", "Napoleon", "PROPN", "obl", 3, 25, 33),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[4]),
            ("direct-argument", "Subject", "capture", 9, 21, "passive", ""),
        )

    def test_oblique_by_phrase_without_aux_pass_is_not_treated_as_passive(
        self,
    ) -> None:
        # "The teenager listened by the radio" -- "by" oblique but the verb
        # is active (no aux:pass sibling), so this must NOT be misread as a
        # passive agent; it degrades to the ordinary phrasal-verb path.
        words = [
            FakeWord(1, "The", "the", "DET", "det", 2, 0, 3),
            FakeWord(2, "teenager", "teenager", "NOUN", "nsubj", 3, 4, 12),
            FakeWord(3, "listened", "listen", "VERB", "root", 0, 13, 21),
            FakeWord(4, "by", "by", "ADP", "case", 5, 22, 24),
            FakeWord(5, "radio", "radio", "NOUN", "obl", 3, 29, 34),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[4]),
            ("direct-argument", "Object", "listen by", 13, 24, "active", ""),
        )

    def test_oblique_with_a_verbal_head_but_no_case_word(self) -> None:
        # A bare temporal oblique ("obl:tmod") -- head is a good VERB,
        # but there is no preposition child at all, a genuinely different
        # reason than the head itself being wrong (_no_governing_verb's
        # own "head-upos-VERB" would be misleading here).
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0, 8),
            FakeWord(2, "left", "leave", "VERB", "root", 0, 9, 13),
            FakeWord(3, "yesterday", "yesterday", "NOUN", "obl", 2, 14, 23),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[2]),
            ("no-governing-verb:no-case-word", "", "", None, None, "active", ""),
        )

    def test_subject_with_no_head_at_all(self) -> None:
        # word.head points at an id that isn't in the sentence at all --
        # defensive, but a real "no-head" case _no_governing_verb's own
        # suffix vocabulary names distinctly from a *present* but
        # unusable head (see the two tests above/below).
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 99, 0, 8),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[0]),
            ("no-governing-verb:no-head", "", "", None, None, "active", ""),
        )

    def test_copula_subject_is_a_copula_argument(self) -> None:
        # "Waterloo is a county" -- nsubj attaches to the predicate NOUN
        # "county", not the AUX "is", so GOVERNING_UPOS never fires;
        # governing_lemma is the predicate noun's own lemma, and the
        # span covers only "is" itself, not the whole predicate NP.
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 3, 0, 8),
            FakeWord(2, "is", "be", "AUX", "cop", 3, 9, 11),
            FakeWord(3, "county", "county", "NOUN", "root", 0, 14, 20),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[0]),
            ("copula-argument", "Subject", "county", 9, 11, "active", ""),
        )

    def test_noun_headed_nsubj_without_a_cop_child_is_not_a_copula(self) -> None:
        # Not every NOUN-headed nsubj is a copula -- confirms the "cop"
        # child check is load-bearing, not just "head.upos == NOUN".
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 2, 0, 8),
            FakeWord(2, "county", "county", "NOUN", "root", 0, 9, 15),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[0]),
            ("no-governing-verb:head-upos-NOUN", "", "", None, None, "active", ""),
        )

    def test_adjectival_predicate_is_not_a_copula_argument(self) -> None:
        # "Waterloo is beautiful" -- head is ADJ, not NOUN;
        # grammar/Metonymy.gf has no AP category at all, so this stays
        # structurally out of scope regardless of classification here.
        words = [
            FakeWord(1, "Waterloo", "Waterloo", "PROPN", "nsubj", 3, 0, 8),
            FakeWord(2, "is", "be", "AUX", "cop", 3, 9, 11),
            FakeWord(3, "beautiful", "beautiful", "ADJ", "root", 0, 12, 21),
        ]
        sentence = FakeSentence(words)
        self.assertEqual(
            classify_word(sentence, words[0]),
            ("no-governing-verb:head-upos-ADJ", "", "", None, None, "active", ""),
        )


class FindGoverningStructureTests(unittest.TestCase):
    def test_single_token_span_resolves_directly(self) -> None:
        document = moscow_signed_document()
        self.assertEqual(
            find_governing_structure(document, 0, 6),
            ("direct-argument", "Subject", "sign", 7, 13, "active", ""),
        )

    def test_multi_token_span_resolves_to_the_phrase_internal_root(self) -> None:
        # "Anna visited New York"
        #  0    5       14  18
        words = [
            FakeWord(1, "Anna", "Anna", "PROPN", "nsubj", 2, 0, 4),
            FakeWord(2, "visited", "visit", "VERB", "root", 0, 5, 12),
            FakeWord(3, "New", "New", "PROPN", "compound", 4, 13, 16),
            FakeWord(4, "York", "York", "PROPN", "obj", 2, 17, 21),
        ]
        document = FakeDocument([FakeSentence(words)])
        self.assertEqual(
            find_governing_structure(document, 13, 21),
            ("direct-argument", "Object", "visit", 5, 12, "active", ""),
        )

    def test_span_with_no_covering_token_is_a_parse_error(self) -> None:
        document = moscow_signed_document()
        self.assertEqual(
            find_governing_structure(document, 100, 110),
            ("parse-error", "", "", None, None, "active", ""),
        )


class SerializeSentenceWordsTests(unittest.TestCase):
    def test_flattens_every_word_in_sentence_order(self) -> None:
        document = moscow_signed_document()
        self.assertEqual(
            serialize_sentence_words(document.sentences[0]),
            [
                {
                    "id": 1, "head": 2, "deprel": "nsubj", "upos": "PROPN",
                    "lemma": "Moscow", "text": "Moscow",
                    "start_char": 0, "end_char": 6,
                },
                {
                    "id": 2, "head": 0, "deprel": "root", "upos": "VERB",
                    "lemma": "sign", "text": "signed",
                    "start_char": 7, "end_char": 13,
                },
                {
                    "id": 3, "head": 4, "deprel": "det", "upos": "DET",
                    "lemma": "the", "text": "the",
                    "start_char": 14, "end_char": 17,
                },
                {
                    "id": 4, "head": 2, "deprel": "obj", "upos": "NOUN",
                    "lemma": "agreement", "text": "agreement",
                    "start_char": 18, "end_char": 27,
                },
            ],
        )


class FindSentenceUdWordsTests(unittest.TestCase):
    def test_returns_every_word_of_the_sentence_containing_the_span(self) -> None:
        document = moscow_signed_document()
        words = find_sentence_ud_words(document, 0, 6)
        self.assertEqual(len(words), 4)
        self.assertEqual(words[1]["deprel"], "root")
        self.assertEqual(words[1]["lemma"], "sign")

    def test_returns_none_when_no_sentence_covers_the_span(self) -> None:
        document = moscow_signed_document()
        self.assertIsNone(find_sentence_ud_words(document, 100, 110))

    def test_agrees_with_find_governing_structure_on_which_sentence(self) -> None:
        # Both are built on the same shared sentence lookup -- confirms
        # they never disagree about which sentence "the" target's
        # sentence is.
        words = [
            FakeWord(1, "Anna", "Anna", "PROPN", "nsubj", 2, 0, 4),
            FakeWord(2, "visited", "visit", "VERB", "root", 0, 5, 12),
            FakeWord(3, "New", "New", "PROPN", "compound", 4, 13, 16),
            FakeWord(4, "York", "York", "PROPN", "obj", 2, 17, 21),
        ]
        document = FakeDocument([FakeSentence(words)])
        ud_words = find_sentence_ud_words(document, 13, 21)
        self.assertEqual([word["text"] for word in ud_words], ["Anna", "visited", "New", "York"])


class ValidateRowTests(unittest.TestCase):
    def test_valid_row_returns_text_and_span(self) -> None:
        row = {
            "id": "wimcor:test:0",
            "text": "Moscow signed the agreement",
            "target": "Moscow",
            "target_span": [0, 6],
        }
        self.assertEqual(validate_row(row), ("Moscow signed the agreement", 0, 6))

    def test_span_not_matching_target_text_is_invalid(self) -> None:
        row = {
            "id": "wimcor:test:1",
            "text": "Moscow signed the agreement",
            "target": "Moscow",
            "target_span": [7, 13],  # actually covers "signed", not "Moscow"
        }
        self.assertIsNone(validate_row(row))

    def test_missing_text_or_span_is_invalid(self) -> None:
        self.assertIsNone(
            validate_row({"id": "x", "text": "", "target": "Moscow", "target_span": [0, 1]})
        )
        # No target_span at all, and "Moscow" is genuinely absent from the
        # text -- the word-boundary fallback must not match anything.
        self.assertIsNone(
            validate_row({"id": "x", "text": "Anna reads Tolstoy", "target": "Moscow"})
        )

    def test_missing_span_falls_back_to_word_boundary_match(self) -> None:
        # The contextual-tower corpus format (evaluation/contextual-multidomain/)
        # supplies only a plain mention string, no character span --
        # mirrors scripts/contextual_rule_compiler.py's _mention_span.
        row = {
            "id": "ctx:0",
            "text": "Waterloo announced a new research programme",
            "target": "Waterloo",
        }
        self.assertEqual(
            validate_row(row),
            ("Waterloo announced a new research programme", 0, 8),
        )

    def test_fallback_match_is_case_insensitive_and_word_bounded(self) -> None:
        row = {"id": "ctx:1", "text": "the waterloo team won", "target": "Waterloo"}
        self.assertEqual(validate_row(row), ("the waterloo team won", 4, 12))
        # "Water" must not match inside "Waterloo" (word-boundary required).
        row_partial = {"id": "ctx:2", "text": "the waterloo team won", "target": "Water"}
        self.assertIsNone(validate_row(row_partial))

    def test_alternate_field_names(self) -> None:
        row = {
            "id": "ctx:3",
            "sentence": "Waterloo announced a new research programme",
            "source": "Waterloo",
        }
        self.assertEqual(
            validate_row(row, text_field="sentence", target_field="source"),
            ("Waterloo announced a new research programme", 0, 8),
        )
        # Default field names do not see these rows at all.
        self.assertIsNone(validate_row(row))


class AnnotateTests(unittest.TestCase):
    """``annotate`` batches every distinct valid sentence text through one
    (or a few) calls to a batch-callable pipeline, per Stanza's own
    guidance that calling the pipeline once per short text is very slow --
    see the module docstring. These tests use a batch-callable
    ``pipeline_batch(texts: list[str]) -> list[FakeDocument]`` mock rather
    than a real Stanza pipeline.
    """

    def test_span_not_matching_target_is_a_parse_error_without_parsing(self) -> None:
        calls: list[list[str]] = []

        def pipeline_batch(texts: list[str]) -> list[FakeDocument]:
            calls.append(list(texts))
            return [moscow_signed_document() for _ in texts]

        row = {
            "id": "wimcor:test:0",
            "text": "Moscow signed the agreement",
            "target": "Moscow",
            "target_span": [7, 13],
        }
        hints = list(annotate(pipeline_batch, [row]))
        self.assertEqual(
            hints,
            [
                {
                    "id": "wimcor:test:0",
                    "dep_status": "parse-error",
                    "hole_role": "",
                    "governing_lemma": "",
                    "governing_start": None,
                    "governing_end": None,
                    "voice": "active",
                    "nested_modifier_deprel": "",
                    "ud_words": None,
                }
            ],
        )
        self.assertEqual(calls, [])  # nothing valid to parse, pipeline never called

    def test_valid_row_resolves_through_the_pipeline(self) -> None:
        def pipeline_batch(texts: list[str]) -> list[FakeDocument]:
            return [moscow_signed_document() for _ in texts]

        row = {
            "id": "wimcor:test:1",
            "text": "Moscow signed the agreement",
            "target": "Moscow",
            "target_span": [0, 6],
        }
        hints = list(annotate(pipeline_batch, [row]))
        self.assertEqual(
            hints,
            [
                {
                    "id": "wimcor:test:1",
                    "dep_status": "direct-argument",
                    "hole_role": "Subject",
                    "governing_lemma": "sign",
                    "governing_start": 7,
                    "governing_end": 13,
                    "voice": "active",
                    "nested_modifier_deprel": "",
                    "ud_words": [
                        {
                            "id": 1, "head": 2, "deprel": "nsubj", "upos": "PROPN",
                            "lemma": "Moscow", "text": "Moscow",
                            "start_char": 0, "end_char": 6,
                        },
                        {
                            "id": 2, "head": 0, "deprel": "root", "upos": "VERB",
                            "lemma": "sign", "text": "signed",
                            "start_char": 7, "end_char": 13,
                        },
                        {
                            "id": 3, "head": 4, "deprel": "det", "upos": "DET",
                            "lemma": "the", "text": "the",
                            "start_char": 14, "end_char": 17,
                        },
                        {
                            "id": 4, "head": 2, "deprel": "obj", "upos": "NOUN",
                            "lemma": "agreement", "text": "agreement",
                            "start_char": 18, "end_char": 27,
                        },
                    ],
                }
            ],
        )

    def test_nested_modifier_deprel_reaches_the_full_annotate_output(self) -> None:
        # "Anna reads Tolstoy's books" -- the target ("Tolstoy") is an
        # nmod:poss modifier, not a clause argument. Confirms the
        # specific closed-vocabulary deprel makes it all the way through
        # annotate()'s own output dict, not just classify_word's direct
        # return value.
        def pipeline_batch(texts: list[str]) -> list[FakeDocument]:
            words = [
                FakeWord(1, "Anna", "Anna", "PROPN", "nsubj", 2, 0, 4),
                FakeWord(2, "reads", "read", "VERB", "root", 0, 5, 10),
                FakeWord(3, "Tolstoy", "Tolstoy", "PROPN", "nmod:poss", 5, 11, 18),
                FakeWord(4, "'s", "'s", "PART", "case", 3, 18, 20),
                FakeWord(5, "books", "book", "NOUN", "obj", 2, 21, 26),
            ]
            return [FakeDocument([FakeSentence(words)]) for _ in texts]

        row = {
            "id": "wimcor:test:3",
            "text": "Anna reads Tolstoy's books",
            "target": "Tolstoy",
            "target_span": [11, 18],
        }
        hints = list(annotate(pipeline_batch, [row]))
        self.assertEqual(
            hints,
            [
                {
                    "id": "wimcor:test:3",
                    "dep_status": "nested-modifier",
                    "hole_role": "",
                    "governing_lemma": "",
                    "governing_start": None,
                    "governing_end": None,
                    "voice": "active",
                    "nested_modifier_deprel": "nmod:poss",
                    "ud_words": [
                        {
                            "id": 1, "head": 2, "deprel": "nsubj", "upos": "PROPN",
                            "lemma": "Anna", "text": "Anna",
                            "start_char": 0, "end_char": 4,
                        },
                        {
                            "id": 2, "head": 0, "deprel": "root", "upos": "VERB",
                            "lemma": "read", "text": "reads",
                            "start_char": 5, "end_char": 10,
                        },
                        {
                            "id": 3, "head": 5, "deprel": "nmod:poss", "upos": "PROPN",
                            "lemma": "Tolstoy", "text": "Tolstoy",
                            "start_char": 11, "end_char": 18,
                        },
                        {
                            "id": 4, "head": 3, "deprel": "case", "upos": "PART",
                            "lemma": "'s", "text": "'s",
                            "start_char": 18, "end_char": 20,
                        },
                        {
                            "id": 5, "head": 2, "deprel": "obj", "upos": "NOUN",
                            "lemma": "book", "text": "books",
                            "start_char": 21, "end_char": 26,
                        },
                    ],
                }
            ],
        )

    def test_batch_pipeline_exception_degrades_that_batch_to_parse_error(self) -> None:
        def failing_pipeline(texts: list[str]) -> list[FakeDocument]:
            raise RuntimeError("boom")

        row = {
            "id": "wimcor:test:2",
            "text": "Moscow signed the agreement",
            "target": "Moscow",
            "target_span": [0, 6],
        }
        hints = list(annotate(failing_pipeline, [row]))
        self.assertEqual(hints[0]["dep_status"], "parse-error")

    def test_identical_sentence_text_is_parsed_only_once(self) -> None:
        calls: list[list[str]] = []

        def pipeline_batch(texts: list[str]) -> list[FakeDocument]:
            calls.append(list(texts))
            return [moscow_signed_document() for _ in texts]

        rows = [
            {
                "id": "wimcor:test:0",
                "text": "Moscow signed the agreement",
                "target": "Moscow",
                "target_span": [0, 6],
            },
            {
                "id": "wimcor:test:1",
                "text": "Moscow signed the agreement",
                "target": "agreement",
                "target_span": [18, 27],
            },
        ]
        hints = list(annotate(pipeline_batch, rows))
        self.assertEqual(len(hints), 2)
        self.assertEqual(calls, [["Moscow signed the agreement"]])
        self.assertEqual(hints[0]["hole_role"], "Subject")
        self.assertEqual(hints[1]["hole_role"], "Object")

    def test_batch_size_chunks_distinct_texts(self) -> None:
        calls: list[list[str]] = []

        def pipeline_batch(texts: list[str]) -> list[FakeDocument]:
            calls.append(list(texts))
            return [moscow_signed_document() for _ in texts]

        rows = [
            {
                "id": f"wimcor:test:{index}",
                "text": f"Moscow signed the agreement {index}",
                "target": "Moscow",
                "target_span": [0, 6],
            }
            for index in range(3)
        ]
        list(annotate(pipeline_batch, rows, batch_size=2))
        self.assertEqual([len(chunk) for chunk in calls], [2, 1])

    def test_progress_callback_receives_batch_counts(self) -> None:
        progress: list[tuple[int, int]] = []

        def pipeline_batch(texts: list[str]) -> list[FakeDocument]:
            return [moscow_signed_document() for _ in texts]

        rows = [
            {
                "id": f"wimcor:test:{index}",
                "text": f"Moscow signed the agreement {index}",
                "target": "Moscow",
                "target_span": [0, 6],
            }
            for index in range(3)
        ]
        list(
            annotate(
                pipeline_batch,
                rows,
                batch_size=2,
                on_progress=lambda done, total: progress.append((done, total)),
            )
        )
        self.assertEqual(progress, [(1, 2), (2, 2)])

    def test_alternate_field_names_reach_the_pipeline(self) -> None:
        # The contextual-tower corpus shape: {"sentence", "source"}, no span.
        def pipeline_batch(texts: list[str]) -> list[FakeDocument]:
            return [moscow_signed_document() for _ in texts]

        row = {
            "id": "ctx:0",
            "sentence": "Moscow signed the agreement",
            "source": "Moscow",
        }
        hints = list(
            annotate(
                pipeline_batch, [row], text_field="sentence", target_field="source"
            )
        )
        self.assertEqual(hints[0]["dep_status"], "direct-argument")
        self.assertEqual(hints[0]["hole_role"], "Subject")
        self.assertEqual(hints[0]["governing_lemma"], "sign")


if __name__ == "__main__":
    unittest.main()
