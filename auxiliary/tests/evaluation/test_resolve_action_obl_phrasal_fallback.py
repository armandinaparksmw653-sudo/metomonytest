"""Unit tests for resolve_action's "obl"+"case" phrasal-lemma fallback.

A live contextual-tower-evaluation.yml run showed WiMCor's
unsupported-action-role failures are, without a single exception, a
"<verb> <preposition>" phrasal reconstruction (e.g. "arrive from",
"raise in") -- annotate_dependency_hints.py's classify_word builds that
string for any "obl"+"case" dependency shape. Confirmed by reading the
source, not guessed: data/predicates.tsv and data/verbnet-action-roles.tsv
(the only two files load_action_roles reads) contain zero lemmas with a
space, so a phrasal governing_lemma can never match resolve_action's
by_form index, no matter how well-covered the bare verb itself already
is. These tests cover the fix: when the phrasal key misses, retry with
just the bare verb (the first word of governing_lemma), narrowing the
matched span to the verb's own token so the later gf_sentence
substitution (which replaces exactly [start:end] with gf_form) doesn't
delete the case-marking preposition from the sentence.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from contextual_rule_compiler import ActionRole, resolve_action  # noqa: E402


class ObliqueBareVerbFallbackTests(unittest.TestCase):
    def test_falls_back_to_the_bare_verb_when_the_phrasal_key_misses(self) -> None:
        sentence = "The museum is based in Hertfordshire"
        verb_start = sentence.index("based")
        verb_end = verb_start + len("based")
        prep_start = sentence.index("in", verb_end)
        prep_end = prep_start + len("in")
        hint = {
            "dep_status": "direct-argument",
            "hole_role": "Object",
            "governing_lemma": "base in",
            "governing_start": verb_start,
            "governing_end": prep_end,
        }
        roles = [
            ActionRole(
                lemma="base",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:base:object",
            ),
        ]
        result = resolve_action(
            sentence, ["Hertfordshire"], roles, {}, dependency_hint=hint
        )
        self.assertEqual(result["role"], "ObjectHole")
        self.assertEqual(result["lemma"], "base")

    def test_the_matched_span_excludes_the_preposition_not_just_the_lemma(
        self,
    ) -> None:
        # The regression this fix exists for: propose_contextual_scenario.py
        # replaces exactly sentence[action["start"]:action["end"]] with
        # action["gf_form"]. If start/end still spanned the whole
        # "based in" phrase (governing_start/governing_end, as reported
        # by annotate_dependency_hints.py for this deprel shape), the
        # substitution would delete "in" from the sentence entirely.
        sentence = "The museum is based in Hertfordshire"
        verb_start = sentence.index("based")
        verb_end = verb_start + len("based")
        prep_start = sentence.index("in", verb_end)
        prep_end = prep_start + len("in")
        hint = {
            "dep_status": "direct-argument",
            "hole_role": "Object",
            "governing_lemma": "base in",
            "governing_start": verb_start,
            "governing_end": prep_end,
        }
        roles = [
            ActionRole(
                lemma="base",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:base:object",
            ),
        ]
        result = resolve_action(
            sentence, ["Hertfordshire"], roles, {}, dependency_hint=hint
        )
        self.assertEqual(result["start"], verb_start)
        self.assertEqual(result["end"], verb_end)
        self.assertEqual(result["surface"], "based")
        substituted = (
            sentence[:result["start"]] + result["gf_form"] + sentence[result["end"]:]
        )
        self.assertIn(" in Hertfordshire", substituted)

    def test_finds_the_verb_even_with_an_adverb_between_it_and_the_preposition(
        self,
    ) -> None:
        sentence = "The company argued strongly against the decision"
        verb_start = sentence.index("argued")
        verb_end = verb_start + len("argued")
        prep_start = sentence.index("against")
        prep_end = prep_start + len("against")
        hint = {
            "dep_status": "direct-argument",
            "hole_role": "Object",
            "governing_lemma": "argue against",
            "governing_start": verb_start,
            "governing_end": prep_end,
        }
        roles = [
            ActionRole(
                lemma="argue",
                hole_role="ObjectHole",
                requirement="HasSort Entity",
                strength="HardRequirement",
                provenance="test",
                identity="test:argue:object",
            ),
        ]
        result = resolve_action(
            sentence, ["decision"], roles, {}, dependency_hint=hint
        )
        self.assertEqual(result["lemma"], "argue")
        self.assertEqual(result["start"], verb_start)
        self.assertEqual(result["end"], verb_end)

    def test_still_raises_with_the_original_phrasal_lemma_when_the_bare_verb_also_has_no_role(
        self,
    ) -> None:
        sentence = "The museum is based in Hertfordshire"
        verb_start = sentence.index("based")
        prep_end = sentence.index("in", verb_start) + len("in")
        hint = {
            "dep_status": "direct-argument",
            "hole_role": "Object",
            "governing_lemma": "base in",
            "governing_start": verb_start,
            "governing_end": prep_end,
        }
        with self.assertRaises(ValueError) as raised:
            resolve_action(sentence, ["Hertfordshire"], [], {}, dependency_hint=hint)
        # Reports the full phrase that was actually looked up (both the
        # exact phrasal key and the bare-verb retry failed), not just the
        # bare verb -- more informative for the next round of diagnosis.
        self.assertEqual(str(raised.exception), "unsupported-action-role:base in")

    def test_an_exact_phrasal_match_is_still_preferred_when_one_exists(self) -> None:
        # Hypothetical: if the action-role vocabulary ever does gain a
        # genuine phrasal entry, an exact match must win outright and the
        # bare-verb fallback must never even run -- confirmed by using
        # the *full* phrasal span here (a bare-verb-only substitution
        # would be wrong if the matched role's own gf_form is the full
        # two-word phrase).
        sentence = "The museum is based in Hertfordshire"
        verb_start = sentence.index("based")
        prep_end = sentence.index("in", verb_start) + len("in")
        hint = {
            "dep_status": "direct-argument",
            "hole_role": "Object",
            "governing_lemma": "base in",
            "governing_start": verb_start,
            "governing_end": prep_end,
        }
        roles = [
            ActionRole(
                lemma="base in",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:base-in:object",
            ),
        ]
        result = resolve_action(
            sentence, ["Hertfordshire"], roles, {}, dependency_hint=hint
        )
        self.assertEqual(result["lemma"], "base in")
        self.assertEqual(result["start"], verb_start)
        self.assertEqual(result["end"], prep_end)

    def test_a_single_word_governing_lemma_is_unaffected(self) -> None:
        # No space at all -- the ordinary direct-argument path, must not
        # trigger the fallback branch (there is nothing to split).
        sentence = "Tolstoy praised the critics"
        verb_start = sentence.index("praised")
        verb_end = verb_start + len("praised")
        hint = {
            "dep_status": "direct-argument",
            "hole_role": "Subject",
            "governing_lemma": "praise",
            "governing_start": verb_start,
            "governing_end": verb_end,
        }
        roles = [
            ActionRole(
                lemma="praise",
                hole_role="SubjectHole",
                requirement="HasSort Person",
                strength="HardRequirement",
                provenance="test",
                identity="test:praise:subject",
            ),
        ]
        result = resolve_action(
            sentence, ["Tolstoy"], roles, {}, dependency_hint=hint
        )
        self.assertEqual(result["role"], "SubjectHole")
        self.assertEqual(result["start"], verb_start)
        self.assertEqual(result["end"], verb_end)


if __name__ == "__main__":
    unittest.main()
