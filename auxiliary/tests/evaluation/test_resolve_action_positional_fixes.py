"""Unit tests for two real resolve_action bugs found by locally
reproducing the exact WiMCor/ConMeC sample this project's real
CI/evaluation workflow uses (seed=0) and parsing the resulting
gf_sentence values against a locally compiled grammar -- not guessed
from aggregate counts. Both bugs only ever manifest on the no-hint
fallback path: run_contextual_corpus.py's own dependency-hint
precompute fails in this project's actual CI too (Stanza is
unavailable there, confirmed from a real CI log: "ModuleNotFoundError:
No module named 'stanza'"), so this fallback path is not a rare corner
case -- it's what every real evaluation row currently goes through.

1. A word *inside* the target's own mention span could itself happen to
   match some unrelated ActionRole's inflected form (e.g. the real
   source "High Point" contains "Point", which is also a verb lemma in
   VerbNet) -- and since it sits at distance ~0 from the target's own
   start, it could outrank the real governing verb elsewhere in the
   sentence purely on proximity, corrupting the source's own text in
   gf_sentence ("raised in High points" instead of "raised in High
   Point").
2. Without a dependency hint, voice was always assumed active, silently
   replacing an already-correct passive surface ("is based") with a
   freshly reconjugated active one ("is bases"). The matched surface
   text already carries the answer: if what matched is the participle
   form used for passive (not the bare lemma) and it's immediately
   preceded by a form of "be", the sentence was already passive.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from contextual_rule_compiler import ActionRole, resolve_action  # noqa: E402


class TargetOverlapExclusionTests(unittest.TestCase):
    def test_a_word_inside_the_targets_own_mention_is_never_selected_as_the_action(
        self,
    ) -> None:
        # "Point" (inside the target "High Point") sits only 5 characters
        # from target_span[0]; "raised" (the real governing verb) sits 10
        # characters away. Without excluding target-overlapping
        # candidates, the closer-but-wrong "point" match would win.
        sentence = "Barrino was raised in High Point"
        roles = [
            ActionRole(
                lemma="raise",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:raise:object",
            ),
            ActionRole(
                lemma="point",
                hole_role="SubjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:point:subject",
            ),
        ]
        result = resolve_action(sentence, ["High Point"], roles, {})
        self.assertEqual(result["lemma"], "raise")
        self.assertEqual(result["surface"], "raised")

    def test_a_closer_unrelated_verb_outside_the_target_span_still_wins_normally(
        self,
    ) -> None:
        # Sanity check that the exclusion is scoped to the target's own
        # span, not proximity-based matching in general: a genuinely
        # separate, closer candidate should still be preferred over a
        # farther one, same as before this fix.
        sentence = "Waterloo announces a programme and later signs a treaty"
        roles = [
            ActionRole(
                lemma="announce",
                hole_role="SubjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:announce:subject",
            ),
            ActionRole(
                lemma="sign",
                hole_role="SubjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:sign:subject",
            ),
        ]
        result = resolve_action(sentence, ["Waterloo"], roles, {})
        self.assertEqual(result["lemma"], "announce")


class PassiveVoiceHeuristicTests(unittest.TestCase):
    def test_a_participle_preceded_by_a_be_verb_is_detected_as_already_passive(
        self,
    ) -> None:
        sentence = "The trust is based in Hitchin"
        roles = [
            ActionRole(
                lemma="base",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:base:object",
            )
        ]
        result = resolve_action(sentence, ["Hitchin"], roles, {})
        self.assertEqual(result["voice"], "passive")
        # No leading "is " added onto gf_form -- the "is" already sitting
        # untouched immediately before the substitution point in the
        # unedited sentence prefix is the only one that should appear.
        self.assertEqual(result["gf_form"], "based")

    def test_various_be_forms_all_trigger_the_heuristic(self) -> None:
        roles = [
            ActionRole(
                lemma="base",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:base:object",
            )
        ]
        for be_form in ("is", "was", "are", "were", "been", "being"):
            with self.subTest(be_form=be_form):
                sentence = f"The trust {be_form} based in Hitchin"
                result = resolve_action(sentence, ["Hitchin"], roles, {})
                self.assertEqual(result["voice"], "passive")

    def test_without_a_preceding_be_verb_stays_active(self) -> None:
        # "based" is also the regular past-tense *active* form of
        # "base" -- the heuristic must not fire just because the
        # matched surface happens to look participle-shaped; it also
        # needs the immediately preceding word to be a form of "be".
        sentence = "They based the office in Hitchin"
        roles = [
            ActionRole(
                lemma="base",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:base:object",
            )
        ]
        result = resolve_action(sentence, ["Hitchin"], roles, {})
        self.assertEqual(result["voice"], "active")
        self.assertEqual(result["gf_form"], "bases")

    def test_an_explicit_dependency_hint_voice_is_never_overridden_by_the_heuristic(
        self,
    ) -> None:
        sentence = "The trust is based in Hitchin"
        roles = [
            ActionRole(
                lemma="base",
                hole_role="ObjectHole",
                requirement="HasSort Place",
                strength="HardRequirement",
                provenance="test",
                identity="test:base:object",
            )
        ]
        dependency_hint = {
            "dep_status": "direct-argument",
            "hole_role": "Object",
            "governing_lemma": "base",
            "governing_start": sentence.index("based"),
            "governing_end": sentence.index("based") + len("based"),
            "voice": "active",
        }
        result = resolve_action(
            sentence, ["Hitchin"], roles, {}, dependency_hint=dependency_hint
        )
        self.assertEqual(result["voice"], "active")


if __name__ == "__main__":
    unittest.main()
