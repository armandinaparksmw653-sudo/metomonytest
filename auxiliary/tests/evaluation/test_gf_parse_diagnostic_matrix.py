"""Decisive, non-corpus diagnostic for what actually blocks GF parsing.

Three consecutive contextual-tower-evaluation.yml runs against verified,
CI-compiled grammar additions (S-coordination+8 prepositions, then VP
coordination, then copula+generalized-relative-clauses+genitive) measured
*zero* effect on the real corpus sample -- byte-identical
literal_prediction_reasons every time. Guessing another construction to
add without direct evidence would just be a fourth blind round. This
file exists to stop guessing: every sentence below is *our own*, written
for this test, never corpus text -- so, unlike anything drawn from
WiMCor/ConMeC, it is safe to print in full in a CI log or a test failure
message. Each test isolates exactly one hypothesis and prints a plain
PASS/FAIL verdict, so a single failing test name in the CI log is
decisive, the same way `test_wordnet_cn_relative_clause_parses_in_gf`
was decisive for the which_RP collision -- no corpus-derived guessing
required.

Leading hypothesis this batch was built to confirm or refute: `OpenPN :
String -> NP` is the only way this grammar represents a proper noun, and
every *proven*-working example sentence anywhere in this project's tests
so far ("Waterloo announces...", "Moscow signs...", "Anna examines...")
uses a single-word subject. Most real WiMCor/ConMeC source mentions are
multi-word ("Henry County", "The Shipley School", "Vilas County"). If
GF's String-category parsing cannot cleanly span multiple tokens for an
OpenPN slot in this grammar, no amount of additional sentence-level
grammar (coordination, copula, relative clauses, genitive -- all already
added and all measuring zero effect) can matter, because the subject NP
itself never parses in the first place.

**Confirmed by this file's own first real CI run**: the single-word
baseline and single-word-subject copula test passed; all four multi-word
tests failed, each exactly at the second token ("The parser failed at
token 2: \"County\""). `OpenPN2`/`OpenPN3` (`grammar/Metonymy.gf`,
`grammar/MetonymyEng.gf`) were added directly in response -- additional
NP-building alternatives for a two- or three-token span, coexisting with
(not replacing) `OpenPN`. The tests below are unchanged in what they
assert (a multi-word name must parse); this file is now the regression
check that the fix actually closes the gap it found, plus two new
`OpenPN3` cases the original diagnostic round didn't need to reach.

**Verb tense correction from this file's own first CI run**: every
sentence below uses present tense, third person singular
("announces"/"is", never "announced"/"was"). The first version of this
file used past tense and every single test failed, including the
single-word baseline -- not evidence the grammar is broken, but a bug in
the test itself: `contextual_rule_compiler.py`'s `resolve_action` always
substitutes the active (non-passive) verb with `third_person(lemma)`
regardless of the original sentence's own tense, so present tense,
third-person-singular is the *only* active-Compl surface form the real
pipeline (and therefore this grammar's tense-unspecified default `mkS :
Cl -> S`) actually ever asks GF to parse -- confirmed directly from
`resolve_action`'s source, not guessed. Every prior "proven working"
example sentence cited above went through that same substitution before
reaching GF, so it was never literally parsed in the past-tense surface
form its own `--sentence` argument displayed either.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class GfParseDiagnosticMatrix(unittest.TestCase):
    engine: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = ROOT / "build" / "metonymy"
        if not cls.engine.exists():
            raise unittest.SkipTest("build/metonymy is not built")

    def parse(self, sentence: str) -> str:
        completed = subprocess.run(
            [str(self.engine), "parse", sentence],
            check=True,
            text=True,
            capture_output=True,
            cwd=ROOT,
        )
        return completed.stdout

    def linearize(self, tree: str) -> str:
        completed = subprocess.run(
            [str(self.engine), "linearize", tree],
            check=True,
            text=True,
            capture_output=True,
            cwd=ROOT,
        )
        return completed.stdout.strip()

    def assert_parses(self, sentence: str) -> str:
        output = self.parse(sentence)
        if output.startswith("The parser failed"):
            self.fail(
                f"expected a successful parse of {sentence!r}, "
                f"got: {output.strip()!r}"
            )
        return output

    def assert_fails(self, sentence: str) -> str:
        output = self.parse(sentence)
        self.assertTrue(
            output.startswith("The parser failed"),
            f"expected {sentence!r} to fail to parse (documenting a known "
            f"gap), but it parsed as: {output.strip()!r} -- if this is a "
            f"deliberate improvement, update this test's expectation, "
            f"don't just note the surprise",
        )
        return output

    # -- Baseline: known-working shape, single-word subject and object.
    # Present tense, third person singular ("announces", not "announced")
    # -- confirmed from contextual_rule_compiler.py's own resolve_action:
    # the active (non-passive) gf_form always defaults to
    # third_person(lemma), regardless of the original sentence's own
    # tense, so this is the *only* surface verb form the pipeline (and
    # therefore this grammar's default, tense-unspecified `mkS : Cl ->
    # S`) ever actually asks GF to parse for an active Compl. --

    def test_baseline_single_word_subject_and_object_parses(self) -> None:
        self.assert_parses("Waterloo announces a programme")

    # -- The core hypothesis: multi-word OpenPN --

    def test_two_word_proper_noun_subject(self) -> None:
        """"Henry County" as a subject -- the single most common real
        source-mention shape (place names, institution names) this
        project's live-API-snapshot corpus sample actually contains."""
        self.assert_parses("Henry County announces a programme")

    def test_two_word_proper_noun_object(self) -> None:
        """Same question, object position instead of subject, in case
        OpenPN's token-span behavior differs by grammatical position."""
        self.assert_parses("Waterloo announces Henry County")

    def test_three_word_proper_noun_subject(self) -> None:
        """A longer multi-word name ("Shipley School" is two words on
        its own; kept to two here to isolate word-count from any
        confound with a leading article-like word, which OpenDefCN/
        OpenIndefCN's own literal "the"/"a" prefixes could otherwise
        interact with)."""
        self.assert_parses("Shipley School announces a programme")

    # -- Combined with the newest additions, to see whether multi-word
    # subjects specifically break the *newest* constructions even if they
    # already work with the older Compl-only shape above. --

    def test_copula_with_single_word_subject(self) -> None:
        self.assert_parses("Waterloo is a programme")

    def test_copula_with_two_word_subject(self) -> None:
        self.assert_parses("Henry County is a programme")

    # -- OpenPN3: three-token span, both positions. Same rationale as the
    # two-word tests above, extended to the three-word case (e.g. "The
    # Shipley School") that OpenPN2 alone still cannot cover. --

    def test_three_word_proper_noun_object(self) -> None:
        self.assert_parses("Waterloo announces Shipley School programme")

    def test_copula_with_three_word_subject(self) -> None:
        self.assert_parses("Shipley School District is a programme")

    # -- BecauseS/IfS/WhenS/AlthoughS/SBecauseS/SIfS/SWhenS/SAlthoughS and
    # ApposCommaPN1/ApposCommaPN2: added directly in response to the real,
    # decisive text-free diagnostic in score_contextual_detection.py
    # (exit7_gf_sentence_signals) -- among sentences still failing
    # gf-parse-empty after OpenPN2/OpenPN3, a comma is present in 87%/67%
    # of the remaining WiMCor/ConMeC rows, far more than the 24%/3% that
    # are still a proper-noun-length issue OpenPN2/OpenPN3 don't cover.
    # See docs/contextual-tower.md's "Fronted/trailing subordinate
    # clauses and short comma appositives" section. Only a representative
    # subset is exercised here (one fronted, one different fronted
    # conjunction, one trailing, both appositive arities) rather than all
    # 8 subordinate-clause functions -- each shares the exact same
    # ExtAdvS/SSubjS + mkAdv + closed-Subj-constant mechanism, differing
    # only in which fixed, closed-vocabulary word is substituted in, so a
    # working representative gives strong (not just compiled-without-
    # error) evidence the whole family works. --

    def test_fronted_because_clause_parses(self) -> None:
        self.assert_parses(
            "Because Napoleon announces a programme, Waterloo announces a programme"
        )

    def test_fronted_when_clause_parses(self) -> None:
        self.assert_parses(
            "When Napoleon announces a programme, Waterloo announces a programme"
        )

    def test_trailing_because_clause_parses(self) -> None:
        self.assert_parses(
            "Waterloo announces a programme, because Napoleon announces a programme"
        )

    def test_linearize_command_round_trips_a_because_s_tree(self) -> None:
        """Smoke test for the `linearize` diagnostic command itself (see
        the comment block below) -- confirms it still runs and produces
        a string containing every word the tree should linearize to,
        without pinning the exact spacing GF's raw `l` output happens to
        use (that spacing is a debug-display detail, not something
        either this command or `parse` depends on -- see below)."""
        tree = (
            'BecauseS '
            '(Pred (OpenPN "Napoleon") (Compl Announce (OpenIndefCN "programme" "programmes"))) '
            '(Pred (OpenPN "Waterloo") (Compl Announce (OpenIndefCN "programme" "programmes")))'
        )
        surface = self.linearize(tree)
        for word in ("Because", "Napoleon", "announces", "Waterloo"):
            self.assertIn(word, surface)

    # -- The real bug, found decisively using a local gf.exe build (the
    # official Windows release of GF 3.12, plus the pinned gf-rgl commit
    # this project already targets) instead of guessing through more CI
    # rounds: GF's parser uses a whitespace-only tokenizer by default, so
    # "programme," (no space) is ONE indivisible token, not two -- and no
    # grammar-level device can retroactively split an already-fused
    # input token at parse time. This was confirmed directly: BIND and
    # SOFT_BIND (RGL's own `frontComma` mechanism) both leave "programme,
    # Waterloo" unparseable, identically to a bare `"," ++`, because none
    # of them change how the *input string* gets tokenized -- they only
    # affect linearization/display. `linearize`'s raw output legitimately
    # shows a space before the comma by default (`gf --run`'s `l` command
    # without `-bind`); that is expected GF debug-display behavior, not a
    # bug, and irrelevant to parsing either way.
    #
    # The actual fix lives in engine/src/Metonymy/GF.hs's parseEnglish:
    # a space is inserted before any comma that doesn't already have one,
    # right before the sentence reaches GF's parser -- so grammar/
    # MetonymyEng.gf's comma-using constructs (BecauseS/SBecauseS-family,
    # ApposCommaPN1/ApposCommaPN2) can all go back to a plain `","`
    # literal, no BIND/SOFT_BIND machinery, no `open Predef`. Verified
    # locally against all thirteen sentences in this file at once (every
    # existing case plus every comma-using one) before touching the
    # engine, then again after -- zero regressions. The parsing tests
    # above and below this comment are the real regression coverage; this
    # class's own `parse` helper goes through the compiled engine, so it
    # exercises `spaceBeforeCommas` exactly as production does. --

    def test_short_one_word_appositive_subject_parses(self) -> None:
        self.assert_parses("Waterloo, Ontario, announces a programme")

    def test_short_two_word_appositive_subject_parses(self) -> None:
        self.assert_parses("Waterloo, a village, announces a programme")

    # -- Batch 2: found by literally reading real WiMCor/ConMeC sample
    # sentences (locally reproduced, seed=0, the exact same sample this
    # project's real CI uses) and testing the resulting gf_sentence
    # values against a locally compiled grammar instead of guessing from
    # aggregate signals -- see docs/contextual-tower.md's "batch 2"
    # section. Each construct here was verified working against a real
    # gf.exe build before being added, so this is regression coverage,
    # not exploratory. --

    def test_of_preposition_modifier_parses(self) -> None:
        # "of" was missing from the twelve existing prepositions despite
        # being one of the most common in English NP-modification
        # ("President of X", "part of Y", "University of Z").
        self.assert_parses("Waterloo announces the president of Alabama")

    def test_chained_pp_modifiers_parse_with_no_new_grammar(self) -> None:
        # ModifyNP recursing on its own output ("a general in Hitchin of
        # Hertfordshire") was already valid with zero new code -- this
        # just locks in that it actually parses in the real grammar, not
        # only in the abstract syntax's own type signature.
        self.assert_parses(
            "Waterloo announces a general in Hitchin of Hertfordshire"
        )

    def test_fronted_on_date_clause_parses(self) -> None:
        self.assert_parses("On 18 May 2010, Waterloo announces a programme")

    def test_fronted_in_date_clause_parses(self) -> None:
        self.assert_parses("In 1805, Waterloo announces a programme")

    def test_fronted_from_date_clause_parses(self) -> None:
        self.assert_parses("From 1947, Waterloo announces a programme")

    def test_parenthetical_acronym_after_subject_parses(self) -> None:
        self.assert_parses("Waterloo announces the Foundation (HOLA)")

    def test_he_pronoun_subject_parses(self) -> None:
        self.assert_parses("He announces a programme")

    def test_she_pronoun_object_parses(self) -> None:
        self.assert_parses("Waterloo announces her")


if __name__ == "__main__":
    unittest.main()
