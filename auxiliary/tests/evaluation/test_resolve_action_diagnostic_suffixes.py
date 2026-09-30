"""Unit tests for resolve_action's two new safe diagnostic suffixes.

contextual-tower-evaluation.yml (unlike ci.yml, confirmed by reading its
own workflow file) installs real Stanza via
scripts/bootstrap_dependency_frontend.sh, so most real evaluation rows
actually go through resolve_action's dependency_hint ("direct-argument"/
"nested-modifier") path, not the no-hint positional fallback. After
batch 2 measurably (if modestly) reduced gf-parse-empty failures, the
real corpus evaluation's dominant remaining causes turned out to be
`unsupported-action-role` and `nested-modifier-unsupported` -- both
raised as a single undifferentiated string, giving no way to tell which
specific verb lemma or which specific UD relation actually dominates
without guessing.

Both new suffixes reuse content this project already treats as safe to
aggregate (the same risk class as the existing has_comma/has_digit
counts and exit2's QID-candidate-count bucketing):
- `nested-modifier-unsupported:<deprel>` -- a closed-vocabulary UD
  relation label from annotate_dependency_hints.py's own
  NESTED_MODIFIER_DEPRELS (e.g. "nmod:poss" for "Tolstoy's books"),
  never sentence text.
- `unsupported-action-role:<lemma>` -- a single common English verb
  lemma (or "<verb> <preposition>" for a reconstructed phrasal verb)
  already sitting in the dependency hint's own `governing_lemma` field,
  never sentence text. Only added on the dependency-hint path: the
  no-hint fallback searches every window in the sentence at once, so
  there is no single "the lemma that should have matched" to report.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from contextual_rule_compiler import ActionRole, resolve_action  # noqa: E402


class NestedModifierDeprelSuffixTests(unittest.TestCase):
    def test_nested_modifier_error_includes_the_deprel_when_known(self) -> None:
        hint = {
            "dep_status": "nested-modifier",
            "nested_modifier_deprel": "nmod:poss",
        }
        with self.assertRaises(ValueError) as raised:
            resolve_action("Anna reads Tolstoy's books", ["Tolstoy"], [], {}, dependency_hint=hint)
        self.assertEqual(str(raised.exception), "nested-modifier-unsupported:nmod:poss")

    def test_a_different_deprel_produces_a_different_suffix(self) -> None:
        hint = {
            "dep_status": "nested-modifier",
            "nested_modifier_deprel": "acl:relcl",
        }
        with self.assertRaises(ValueError) as raised:
            resolve_action("sentence", ["target"], [], {}, dependency_hint=hint)
        self.assertEqual(str(raised.exception), "nested-modifier-unsupported:acl:relcl")

    def test_falls_back_to_the_bare_string_when_no_deprel_is_present(self) -> None:
        # Backward compatible: an older-shaped hint dict (or one built by
        # hand without the new field) must not crash or silently produce
        # a malformed suffix.
        hint = {"dep_status": "nested-modifier"}
        with self.assertRaises(ValueError) as raised:
            resolve_action("sentence", ["target"], [], {}, dependency_hint=hint)
        self.assertEqual(str(raised.exception), "nested-modifier-unsupported")


class UnsupportedActionRoleSuffixTests(unittest.TestCase):
    def test_includes_the_governing_lemma_on_the_dependency_hint_path(self) -> None:
        # A direct-argument hint whose governing_lemma has no compiled
        # ActionRole at all (roles=[]) -- the exact "we know which verb,
        # we just don't have it in the vocabulary" case this suffix
        # exists to surface.
        sentence = "The company floreated its policy in Hitchin"
        hint = {
            "dep_status": "direct-argument",
            "hole_role": "Subject",
            "governing_lemma": "floreate",
            "governing_start": sentence.index("floreated"),
            "governing_end": sentence.index("floreated") + len("floreated"),
        }
        with self.assertRaises(ValueError) as raised:
            resolve_action(sentence, ["Hitchin"], [], {}, dependency_hint=hint)
        self.assertEqual(str(raised.exception), "unsupported-action-role:floreate")

    def test_no_hint_fallback_has_no_single_lemma_to_report(self) -> None:
        # No dependency hint at all -- the positional fallback searches
        # every window in the sentence, so there is no one governing
        # lemma to blame; must stay the bare, unsuffixed string.
        sentence = "Waterloo announces a programme"
        with self.assertRaises(ValueError) as raised:
            resolve_action(sentence, ["Waterloo"], [], {})
        self.assertEqual(str(raised.exception), "unsupported-action-role")

    def test_a_no_governing_verb_hint_also_has_no_lemma_to_report(self) -> None:
        # dep_status other than "direct-argument" (e.g. "no-governing-verb")
        # takes the same positional-fallback branch as no hint at all --
        # confirms the suffix is keyed on dep_status, not merely on
        # governing_lemma happening to be present in the hint dict.
        sentence = "Waterloo announces a programme"
        hint = {
            "dep_status": "no-governing-verb",
            "governing_lemma": "announce",
        }
        with self.assertRaises(ValueError) as raised:
            resolve_action(sentence, ["Waterloo"], [], {}, dependency_hint=hint)
        self.assertEqual(str(raised.exception), "unsupported-action-role")


if __name__ == "__main__":
    unittest.main()
