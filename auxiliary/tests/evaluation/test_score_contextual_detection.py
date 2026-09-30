from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts" / "evaluation"))

import json  # noqa: E402

from score_contextual_detection import (  # noqa: E402
    empty_fiber_reason,
    exit1_suffixed_token,
    exit4_reason_bucket,
    exit4_suffixed_token,
    exit4_tree_source,
    exit7_gf_sentence_bucket,
    exit7_gf_sentence_signals,
    exit7_max_capitalized_run,
    fingerprint_failure_text,
    literal_reason,
    predict,
    row_all_decline_reasons,
    row_decline_reason,
    row_dep_status,
    row_llm_decline_reason,
    row_tree_really_built,
    row_tree_source,
    score,
)


def ok_row(id_: str, fiber: list[str]) -> dict:
    return {"id": id_, "status": "ok", "fiber": fiber, "stages": []}


def failed_row(id_: str, exit_code: int = 3) -> dict:
    return {"id": id_, "status": "failed", "exit_code": exit_code, "fiber": [], "stages": []}


class PredictTests(unittest.TestCase):
    def test_ok_with_nonempty_fiber_is_metonymic(self) -> None:
        self.assertEqual(predict(ok_row("a", ["Q1"])), "metonymic")

    def test_ok_with_empty_fiber_is_literal(self) -> None:
        self.assertEqual(predict(ok_row("a", [])), "literal")

    def test_failed_run_is_literal_regardless_of_fiber_field(self) -> None:
        self.assertEqual(predict(failed_row("a")), "literal")


class LiteralReasonTests(unittest.TestCase):
    def test_failed_row_reports_its_exit_code(self) -> None:
        self.assertEqual(literal_reason(failed_row("a", exit_code=5)), "failed:exit5")

    def test_ok_row_with_empty_fiber_is_tagged_distinctly(self) -> None:
        self.assertEqual(literal_reason(ok_row("a", [])), "ok:empty-fiber")

    def test_carries_no_sentence_text(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 3,
            "failure": "some sentence text and a traceback",
        }
        self.assertNotIn("sentence", literal_reason(row))
        self.assertNotIn("traceback", literal_reason(row))

    def test_exit1_extracts_the_specific_error_token_from_the_failure_text(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": (
                "Traceback (most recent call last):\n"
                "ValueError: unsupported-action-role"
            ),
        }
        self.assertEqual(literal_reason(row), "failed:exit1:unsupported-action-role")

    def test_exit1_distinguishes_different_known_tokens(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "ValueError: nested-modifier-unsupported",
        }
        self.assertEqual(literal_reason(row), "failed:exit1:nested-modifier-unsupported")

    def test_exit1_recognizes_an_engine_die_message_from_the_disambiguation_loop(
        self,
    ) -> None:
        # When every candidate in run_automatic_contextual_pipeline.py's
        # multi-candidate loop fails its own engine invocation outright,
        # the pipeline propagates that candidate's raw exit code (always 1
        # -- System.Exit.die) with the engine's own stderr message, never
        # JSON-wrapped: "contextual fiber failed: <reason>" from
        # Metonymy.Contextual/Metonymy.ContextualChecked.
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "contextual fiber failed: snapshot-hash-mismatch",
        }
        self.assertEqual(literal_reason(row), "failed:exit1:snapshot-hash-mismatch")

    def test_exit1_recognizes_an_agda_cross_check_disagreement_ignoring_the_stage_number(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "contextual fiber failed: agda-rejected-survivor-at-stage-2",
        }
        self.assertEqual(
            literal_reason(row), "failed:exit1:agda-rejected-survivor-at-stage-"
        )

    def test_exit1_recognizes_a_scenario_tsv_parse_failure(self) -> None:
        # loadContextScenarios (Metonymy.ContextSpec) runs unconditionally
        # at the very start of every engine invocation, before any command
        # dispatch -- its own `fail` (not `die`) is a genuinely different
        # message shape (GHC's default top-level handler, not
        # System.Exit.die's "contextual fiber failed: " convention) but
        # still exits 1.
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": (
                "metonymy: user error (/tmp/x/scenarios.tsv:2: "
                "malformed contextual constraint: Verb|announce)"
            ),
        }
        self.assertEqual(
            literal_reason(row), "failed:exit1:malformed contextual constraint:"
        )

    def test_exit1_recognizes_an_unknown_scenario_lookup_failure(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "metonymy: unknown contextual scenario: q24826-announce",
        }
        self.assertEqual(
            literal_reason(row), "failed:exit1:unknown contextual scenario:"
        )

    def test_exit1_recognizes_a_generic_prelude_partial_function_crash(
        self,
    ) -> None:
        # A separate, broader pass from KNOWN_FAILURE_TOKENS -- see
        # GENERIC_RUNTIME_CRASH_TOKENS's own comment. GHC's own crash
        # message for a partial function applied outside its domain (e.g.
        # `head` on an empty list), not something this codebase raises on
        # purpose the way the other exit-1 tokens are.
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "metonymy: Prelude.head: empty list",
        }
        self.assertEqual(literal_reason(row), "failed:exit1:Prelude.")

    def test_known_failure_tokens_are_checked_before_generic_crash_tokens(
        self,
    ) -> None:
        # A precise, this-codebase token must win even if the surrounding
        # text also happens to contain a generic crash signature.
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "unsupported-action-role near Prelude.head",
        }
        self.assertEqual(literal_reason(row), "failed:exit1:unsupported-action-role")

    def test_exit1_with_no_known_token_is_unrecognized_not_a_crash(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "some completely different, unanticipated crash",
        }
        self.assertEqual(literal_reason(row), "failed:exit1:unrecognized")

    def test_exit1_with_no_failure_field_at_all_is_unrecognized_not_a_crash(
        self,
    ) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 1}
        self.assertEqual(literal_reason(row), "failed:exit1:unrecognized")

    def test_exit1_token_extraction_never_leaks_the_surrounding_traceback_text(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": (
                'gf_sentence="Waterloo confabulates a treaty"\n'
                "ValueError: unsupported-action-role"
            ),
        }
        reason = literal_reason(row)
        self.assertEqual(reason, "failed:exit1:unsupported-action-role")
        self.assertNotIn("Waterloo", reason)
        self.assertNotIn("confabulates", reason)
        self.assertNotIn("treaty", reason)

    def test_exit2_with_zero_candidates_is_tagged_distinctly(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 2,
            "failure": json.dumps(
                {"status": "source-qid-unresolved", "source_qid_candidates": []}
            ),
        }
        self.assertEqual(literal_reason(row), "failed:exit2:zero-candidates")

    def test_exit2_with_multiple_candidates_is_tagged_ambiguous(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 2,
            "failure": json.dumps(
                {
                    "status": "source-qid-unresolved",
                    "source_qid_candidates": ["Q1", "Q2"],
                }
            ),
        }
        self.assertEqual(literal_reason(row), "failed:exit2:ambiguous-candidates")

    def test_exit2_with_unparseable_failure_text_is_unrecognized_not_a_crash(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 2,
            "failure": "not valid json at all",
        }
        self.assertEqual(literal_reason(row), "failed:exit2:unrecognized")

    def test_exit2_with_no_failure_field_at_all_is_unrecognized_not_a_crash(
        self,
    ) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 2}
        self.assertEqual(literal_reason(row), "failed:exit2:unrecognized")

    def test_exit2_extraction_never_leaks_qid_candidates_or_sentence_text(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 2,
            "failure": json.dumps(
                {
                    "sentence": "The Kremlin announced a new policy",
                    "status": "source-qid-unresolved",
                    "source_qid_candidates": ["Q1234", "Q5678"],
                }
            ),
        }
        reason = literal_reason(row)
        self.assertEqual(reason, "failed:exit2:ambiguous-candidates")
        self.assertNotIn("Kremlin", reason)
        self.assertNotIn("Q1234", reason)
        self.assertNotIn("Q5678", reason)

    def test_exit1_nested_modifier_unsupported_includes_the_deprel_suffix(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": (
                "Traceback (most recent call last):\n"
                "ValueError: nested-modifier-unsupported:nmod:poss"
            ),
        }
        self.assertEqual(
            literal_reason(row), "failed:exit1:nested-modifier-unsupported:nmod:poss"
        )

    def test_exit1_unsupported_action_role_includes_the_lemma_suffix(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "ValueError: unsupported-action-role:floreate",
        }
        self.assertEqual(
            literal_reason(row), "failed:exit1:unsupported-action-role:floreate"
        )

    def test_exit1_unsupported_copula_predicate_includes_the_lemma_suffix(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "ValueError: unsupported-copula-predicate:museum",
        }
        self.assertEqual(
            literal_reason(row), "failed:exit1:unsupported-copula-predicate:museum"
        )

    def test_exit1_suffixed_token_falls_back_to_bare_token_with_no_colon(
        self,
    ) -> None:
        # The backward-compatible bare raise (no deprel/lemma known) --
        # resolve_action's own fallback when hint_governing_lemma/deprel
        # is empty.
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": "ValueError: unsupported-action-role",
        }
        self.assertEqual(literal_reason(row), "failed:exit1:unsupported-action-role")

    def test_exit1_suffix_never_leaks_the_surrounding_traceback_text(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": (
                'gf_sentence="Waterloo confabulates a treaty"\n'
                "ValueError: unsupported-action-role:confabulate\n"
                "some other traceback line"
            ),
        }
        reason = literal_reason(row)
        self.assertEqual(reason, "failed:exit1:unsupported-action-role:confabulate")
        self.assertNotIn("Waterloo", reason)
        self.assertNotIn("treaty", reason)
        self.assertNotIn("some other traceback line", reason)

    def test_exit1_suffix_from_the_real_json_wrapped_propose_scenario_failure(
        self,
    ) -> None:
        # Regression test for a real bug a live contextual-tower-evaluation.yml
        # run actually caught: run_automatic_contextual_pipeline.py's
        # "propose-scenario-failed" exit-1 branch JSON-wraps
        # propose_contextual_scenario.py's `raise SystemExit(str(error))`
        # message into {"status": ..., "sentence": ..., "detail": <bare
        # message>}, pretty-printed with json.dumps(indent=2) -- NOT a raw
        # Python traceback, as this function's first version wrongly
        # assumed. That version's naive "capture to end of line" regex
        # matched the JSON string value's own closing quote as part of
        # the suffix, producing literal_prediction_reasons entries like
        # "nested-modifier-unsupported:appos\"" in real CI output.
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": json.dumps(
                {
                    "status": "propose-scenario-failed",
                    "sentence": "Tolstoy's books were published widely",
                    "detail": "nested-modifier-unsupported:appos",
                },
                indent=2,
            ),
        }
        self.assertEqual(
            literal_reason(row), "failed:exit1:nested-modifier-unsupported:appos"
        )

    def test_exit1_suffix_from_json_wrapped_failure_never_includes_a_stray_quote(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 1,
            "failure": json.dumps(
                {
                    "status": "propose-scenario-failed",
                    "sentence": "The company floreated its policy",
                    "detail": "unsupported-action-role:floreate",
                },
                indent=2,
            ),
        }
        reason = literal_reason(row)
        self.assertEqual(reason, "failed:exit1:unsupported-action-role:floreate")
        self.assertNotIn('"', reason)

    def test_exit4_recognizes_each_known_composition_failure(self) -> None:
        cases = {
            "malformed GF tree near Because": "malformed GF tree near ",
            "malformed or incomplete GF tree": "malformed or incomplete GF tree",
            "GF lexical token is absent from source: announce": (
                "GF lexical token is absent from source: "
            ),
            "malformed adjective-noun GF node": "malformed adjective-noun GF node",
            "unsupported GF adjective-noun semantics: large county": (
                "unsupported GF adjective-noun semantics: "
            ),
            "ambiguous noun sort for GF composition: county": (
                "ambiguous noun sort for GF composition: "
            ),
            "no semantic composition for Place×Human": "no semantic composition for ",
            "action announce has no role rule for Place": " has no role rule for ",
            "context modifier QID is not unique: Hertfordshire": (
                "context modifier QID is not unique: "
            ),
        }
        for detail, expected_token in cases.items():
            with self.subTest(detail=detail):
                row = {
                    "id": "a",
                    "status": "failed",
                    "exit_code": 4,
                    "failure": json.dumps(
                        {
                            "status": "semantic-composition-failed",
                            "gf_tree": "PredCopNP (OpenPN \"Waterloo\") x",
                            "detail": detail,
                        }
                    ),
                }
                self.assertEqual(
                    literal_reason(row), f"failed:exit4:{expected_token.strip()}"
                )

    def test_exit4_with_unparseable_failure_text_is_unrecognized_not_a_crash(
        self,
    ) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 4, "failure": "not json"}
        self.assertEqual(literal_reason(row), "failed:exit4:unrecognized")

    def test_exit4_with_unrecognized_detail_falls_back_gracefully(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "a completely new, unanticipated failure",
                }
            ),
        }
        self.assertEqual(literal_reason(row), "failed:exit4:unrecognized")

    def test_exit4_never_leaks_the_gf_tree_or_interpolated_detail_content(
        self,
    ) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": (
                        'PredCopNP (OpenPN "Waterloo") '
                        '(OpenIndefCN countyCN (InPP (OpenPN "Hertfordshire")))'
                    ),
                    "detail": (
                        "ambiguous noun sort for GF composition: Hertfordshire"
                    ),
                }
            ),
        }
        reason = literal_reason(row)
        self.assertEqual(reason, "failed:exit4:ambiguous noun sort for GF composition:")
        self.assertNotIn("Waterloo", reason)
        self.assertNotIn("Hertfordshire", reason)


class Exit1SuffixedTokenTests(unittest.TestCase):
    def test_recovers_a_ud_deprel_suffix(self) -> None:
        self.assertEqual(
            exit1_suffixed_token(
                "nested-modifier-unsupported",
                "ValueError: nested-modifier-unsupported:acl:relcl",
            ),
            "nested-modifier-unsupported:acl:relcl",
        )

    def test_recovers_a_phrasal_verb_lemma_suffix_containing_a_space(self) -> None:
        self.assertEqual(
            exit1_suffixed_token(
                "unsupported-action-role",
                "ValueError: unsupported-action-role:listen to",
            ),
            "unsupported-action-role:listen to",
        )

    def test_falls_back_to_the_bare_token_when_there_is_no_colon(self) -> None:
        self.assertEqual(
            exit1_suffixed_token(
                "unsupported-action-role", "ValueError: unsupported-action-role"
            ),
            "unsupported-action-role",
        )

    def test_stops_at_the_end_of_the_traceback_line(self) -> None:
        self.assertEqual(
            exit1_suffixed_token(
                "unsupported-action-role",
                "ValueError: unsupported-action-role:announce\nmore traceback below",
            ),
            "unsupported-action-role:announce",
        )

    def test_recovers_the_suffix_from_the_real_json_wrapped_failure_shape(
        self,
    ) -> None:
        failure_text = json.dumps(
            {
                "status": "propose-scenario-failed",
                "sentence": "Tolstoy's books were published widely",
                "detail": "nested-modifier-unsupported:nmod:poss",
            },
            indent=2,
        )
        self.assertEqual(
            exit1_suffixed_token("nested-modifier-unsupported", failure_text),
            "nested-modifier-unsupported:nmod:poss",
        )


class Exit4ReasonBucketTests(unittest.TestCase):
    def test_unparseable_failure_text_is_unrecognized_not_a_crash(self) -> None:
        self.assertEqual(exit4_reason_bucket("not valid json"), "unrecognized")

    def test_missing_detail_key_is_unrecognized_not_a_crash(self) -> None:
        self.assertEqual(
            exit4_reason_bucket(
                json.dumps({"status": "semantic-composition-failed", "gf_tree": "x"})
            ),
            "unrecognized",
        )

    def test_matches_a_middle_interpolated_message(self) -> None:
        # "action <lemma> has no role rule for <sort>" interpolates a
        # value in the middle, not just at the end -- confirms substring
        # matching (not prefix matching) is what makes this one matchable
        # at all.
        failure = json.dumps(
            {
                "status": "semantic-composition-failed",
                "gf_tree": "x",
                "detail": "action confabulate has no role rule for Place",
            }
        )
        self.assertEqual(exit4_reason_bucket(failure), "has no role rule for")

    def test_malformed_tree_with_an_unrecognized_constructor_includes_it(
        self,
    ) -> None:
        failure = json.dumps(
            {
                "status": "semantic-composition-failed",
                "gf_tree": "x",
                "detail": (
                    "malformed or incomplete GF tree; unrecognized "
                    "constructor(s): GlorbNode"
                ),
            }
        )
        self.assertEqual(
            exit4_reason_bucket(failure),
            "malformed or incomplete GF tree:GlorbNode",
        )

    def test_malformed_tree_with_no_identifiable_constructor_stays_bare(
        self,
    ) -> None:
        failure = json.dumps(
            {
                "status": "semantic-composition-failed",
                "gf_tree": "x",
                "detail": "malformed or incomplete GF tree",
            }
        )
        self.assertEqual(exit4_reason_bucket(failure), "malformed or incomplete GF tree")


class Exit4SuffixedTokenTests(unittest.TestCase):
    def test_recovers_a_single_unrecognized_constructor(self) -> None:
        self.assertEqual(
            exit4_suffixed_token(
                "malformed or incomplete GF tree",
                "malformed or incomplete GF tree; unrecognized constructor(s): GlorbNode",
            ),
            "malformed or incomplete GF tree:GlorbNode",
        )

    def test_recovers_multiple_comma_joined_constructors(self) -> None:
        self.assertEqual(
            exit4_suffixed_token(
                "malformed or incomplete GF tree",
                (
                    "malformed or incomplete GF tree; unrecognized "
                    "constructor(s): FooBar,BazQux"
                ),
            ),
            "malformed or incomplete GF tree:FooBar,BazQux",
        )

    def test_falls_back_to_the_bare_token_when_the_marker_is_absent(self) -> None:
        self.assertEqual(
            exit4_suffixed_token(
                "malformed or incomplete GF tree", "malformed or incomplete GF tree"
            ),
            "malformed or incomplete GF tree",
        )


class Exit4TreeSourceTests(unittest.TestCase):
    def test_reads_stanza(self) -> None:
        failure = json.dumps(
            {
                "status": "semantic-composition-failed",
                "gf_tree": "x",
                "detail": "y",
                "tree_source": "stanza",
            }
        )
        self.assertEqual(exit4_tree_source(failure), "stanza")

    def test_reads_gf_parser(self) -> None:
        failure = json.dumps(
            {
                "status": "semantic-composition-failed",
                "gf_tree": "x",
                "detail": "y",
                "tree_source": "gf-parser",
            }
        )
        self.assertEqual(exit4_tree_source(failure), "gf-parser")

    def test_missing_field_is_unrecognized_not_a_crash(self) -> None:
        failure = json.dumps(
            {"status": "semantic-composition-failed", "gf_tree": "x", "detail": "y"}
        )
        self.assertEqual(exit4_tree_source(failure), "unrecognized")

    def test_unparseable_failure_text_is_unrecognized_not_a_crash(self) -> None:
        self.assertEqual(exit4_tree_source("not json"), "unrecognized")


class RowTreeSourceTests(unittest.TestCase):
    def test_reads_the_top_level_field_for_a_successful_row(self) -> None:
        row = {"id": "a", "status": "ok", "fiber": ["Q1"], "tree_source": "stanza"}
        self.assertEqual(row_tree_source(row), "stanza")

    def test_reads_the_top_level_field_for_an_ambiguous_exit6_row(self) -> None:
        row = {
            "id": "a", "status": "failed", "exit_code": 6, "tree_source": "gf-parser",
        }
        self.assertEqual(row_tree_source(row), "gf-parser")

    def test_falls_back_to_parsing_the_failure_json_for_exit4(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "stanza",
                }
            ),
        }
        self.assertEqual(row_tree_source(row), "stanza")

    def test_falls_back_to_parsing_the_failure_json_for_exit3_and_exit7(self) -> None:
        for exit_code, status in ((3, "gf-parse-failed"), (7, "gf-parse-empty")):
            with self.subTest(exit_code=exit_code):
                row = {
                    "id": "a",
                    "status": "failed",
                    "exit_code": exit_code,
                    "failure": json.dumps({"status": status, "tree_source": "gf-parser"}),
                }
                self.assertEqual(row_tree_source(row), "gf-parser")

    def test_exit1_and_exit2_are_not_applicable(self) -> None:
        for exit_code in (1, 2):
            with self.subTest(exit_code=exit_code):
                row = {"id": "a", "status": "failed", "exit_code": exit_code}
                self.assertEqual(row_tree_source(row), "not-applicable")

    def test_an_unexpected_shape_is_unrecognized_not_a_crash(self) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 99}
        self.assertEqual(row_tree_source(row), "unrecognized")


class RowDeclineReasonTests(unittest.TestCase):
    def test_reads_the_top_level_field_for_a_successful_row(self) -> None:
        row = {"id": "a", "status": "ok", "fiber": ["Q1"], "decline_reason": ""}
        self.assertEqual(row_decline_reason(row), "")

    def test_reads_the_top_level_field_for_a_fallback_success(self) -> None:
        row = {
            "id": "a", "status": "ok", "fiber": [], "decline_reason": "subject-count",
        }
        self.assertEqual(row_decline_reason(row), "subject-count")

    def test_falls_back_to_parsing_the_failure_json_for_exit4(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                    "decline_reason": "object-count",
                }
            ),
        }
        self.assertEqual(row_decline_reason(row), "object-count")

    def test_falls_back_to_parsing_the_failure_json_for_exit3_and_exit7(self) -> None:
        for exit_code, status in ((3, "gf-parse-failed"), (7, "gf-parse-empty")):
            with self.subTest(exit_code=exit_code):
                row = {
                    "id": "a",
                    "status": "failed",
                    "exit_code": exit_code,
                    "failure": json.dumps(
                        {
                            "status": status,
                            "tree_source": "gf-parser",
                            "decline_reason": "no-ud-words",
                        }
                    ),
                }
                self.assertEqual(row_decline_reason(row), "no-ud-words")

    def test_exit1_and_exit2_are_not_applicable(self) -> None:
        for exit_code in (1, 2):
            with self.subTest(exit_code=exit_code):
                row = {"id": "a", "status": "failed", "exit_code": exit_code}
                self.assertEqual(row_decline_reason(row), "not-applicable")

    def test_an_unexpected_shape_is_unrecognized_not_a_crash(self) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 99}
        self.assertEqual(row_decline_reason(row), "unrecognized")


class RowAllDeclineReasonsTests(unittest.TestCase):
    """Mirrors RowDeclineReasonTests exactly, for the "all_decline_reasons"
    list field enumerate_gf_tree_blockers populates instead of the
    single "decline_reason" string.
    """

    def test_reads_the_top_level_field_for_a_successful_row(self) -> None:
        row = {"id": "a", "status": "ok", "fiber": ["Q1"], "all_decline_reasons": []}
        self.assertEqual(row_all_decline_reasons(row), [])

    def test_reads_the_top_level_field_for_a_fallback_success(self) -> None:
        row = {
            "id": "a",
            "status": "ok",
            "fiber": [],
            "all_decline_reasons": ["subject-count:advcl"],
        }
        self.assertEqual(row_all_decline_reasons(row), ["subject-count:advcl"])

    def test_falls_back_to_parsing_the_failure_json_for_exit4(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                    "decline_reason": "object-count",
                    "all_decline_reasons": ["object-count", "leftover-words"],
                }
            ),
        }
        self.assertEqual(
            row_all_decline_reasons(row), ["object-count", "leftover-words"]
        )

    def test_falls_back_to_parsing_the_failure_json_for_exit3_and_exit7(self) -> None:
        for exit_code, status in ((3, "gf-parse-failed"), (7, "gf-parse-empty")):
            with self.subTest(exit_code=exit_code):
                row = {
                    "id": "a",
                    "status": "failed",
                    "exit_code": exit_code,
                    "failure": json.dumps(
                        {
                            "status": status,
                            "tree_source": "gf-parser",
                            "decline_reason": "no-ud-words",
                            "all_decline_reasons": [],
                        }
                    ),
                }
                self.assertEqual(row_all_decline_reasons(row), [])

    def test_exit1_and_exit2_are_empty_not_not_applicable(self) -> None:
        # Unlike row_decline_reason's own "not-applicable" sentinel (a
        # string value), this returns [] for the same "tree-building
        # never even attempted" case -- row_tree_source/row_decline_reason
        # on the very same row already carry that distinction, so this
        # field doesn't need its own separate not-applicable marker.
        for exit_code in (1, 2):
            with self.subTest(exit_code=exit_code):
                row = {"id": "a", "status": "failed", "exit_code": exit_code}
                self.assertEqual(row_all_decline_reasons(row), [])

    def test_an_unexpected_shape_is_unrecognized_not_a_crash(self) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 99}
        self.assertEqual(row_all_decline_reasons(row), ["unrecognized"])

    def test_a_non_list_field_inside_the_failure_json_is_unrecognized(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps({"all_decline_reasons": "not-a-list"}),
        }
        self.assertEqual(row_all_decline_reasons(row), ["unrecognized"])


class RowLlmDeclineReasonTests(unittest.TestCase):
    def test_reads_the_top_level_field_for_a_successful_row(self) -> None:
        row = {"id": "a", "status": "ok", "fiber": ["Q1"], "llm_decline_reason": ""}
        self.assertEqual(row_llm_decline_reason(row), "")

    def test_reads_the_top_level_field_when_the_tier_never_ran(self) -> None:
        row = {
            "id": "a", "status": "ok", "fiber": ["Q1"], "llm_decline_reason": "not-attempted",
        }
        self.assertEqual(row_llm_decline_reason(row), "not-attempted")

    def test_falls_back_to_parsing_the_failure_json_for_exit4(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                    "decline_reason": "no-ud-words",
                    "llm_decline_reason": "query-exception",
                }
            ),
        }
        self.assertEqual(row_llm_decline_reason(row), "query-exception")

    def test_falls_back_to_parsing_the_failure_json_for_exit3_and_exit7(self) -> None:
        for exit_code, status in ((3, "gf-parse-failed"), (7, "gf-parse-empty")):
            with self.subTest(exit_code=exit_code):
                row = {
                    "id": "a",
                    "status": "failed",
                    "exit_code": exit_code,
                    "failure": json.dumps(
                        {
                            "status": status,
                            "tree_source": "gf-parser",
                            "decline_reason": "no-ud-words",
                            "llm_decline_reason": "linearize-validation-failed",
                        }
                    ),
                }
                self.assertEqual(
                    row_llm_decline_reason(row), "linearize-validation-failed"
                )

    def test_exit1_and_exit2_are_not_applicable(self) -> None:
        for exit_code in (1, 2):
            with self.subTest(exit_code=exit_code):
                row = {"id": "a", "status": "failed", "exit_code": exit_code}
                self.assertEqual(row_llm_decline_reason(row), "not-applicable")

    def test_an_unexpected_shape_is_unrecognized_not_a_crash(self) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 99}
        self.assertEqual(row_llm_decline_reason(row), "unrecognized")


class RowDepStatusTests(unittest.TestCase):
    """Mirrors RowLlmDeclineReasonTests exactly, for the "dep_status"
    field -- the piece that was missing until now to make root-lemma-
    mismatch:no-governing-start's own real cause visible in a report.
    """

    def test_reads_the_top_level_field_for_a_successful_row(self) -> None:
        row = {
            "id": "a", "status": "ok", "fiber": ["Q1"], "dep_status": "direct-argument",
        }
        self.assertEqual(row_dep_status(row), "direct-argument")

    def test_reads_the_top_level_field_when_no_hint_was_passed(self) -> None:
        row = {"id": "a", "status": "ok", "fiber": ["Q1"], "dep_status": "no-hint"}
        self.assertEqual(row_dep_status(row), "no-hint")

    def test_falls_back_to_parsing_the_failure_json_for_exit4(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                    "decline_reason": "no-ud-words",
                    "dep_status": "no-governing-verb:target-deprel-conj",
                }
            ),
        }
        self.assertEqual(row_dep_status(row), "no-governing-verb:target-deprel-conj")

    def test_falls_back_to_parsing_the_failure_json_for_exit3_and_exit7(self) -> None:
        for exit_code, status in ((3, "gf-parse-failed"), (7, "gf-parse-empty")):
            with self.subTest(exit_code=exit_code):
                row = {
                    "id": "a",
                    "status": "failed",
                    "exit_code": exit_code,
                    "failure": json.dumps(
                        {
                            "status": status,
                            "tree_source": "gf-parser",
                            "decline_reason": "no-ud-words",
                            "dep_status": "parse-error",
                        }
                    ),
                }
                self.assertEqual(row_dep_status(row), "parse-error")

    def test_exit1_and_exit2_are_not_applicable(self) -> None:
        for exit_code in (1, 2):
            with self.subTest(exit_code=exit_code):
                row = {"id": "a", "status": "failed", "exit_code": exit_code}
                self.assertEqual(row_dep_status(row), "not-applicable")

    def test_an_unexpected_shape_is_unrecognized_not_a_crash(self) -> None:
        row = {"id": "a", "status": "failed", "exit_code": 99}
        self.assertEqual(row_dep_status(row), "unrecognized")


class FingerprintFailureTextTests(unittest.TestCase):
    def test_same_text_gives_same_fingerprint(self) -> None:
        a = fingerprint_failure_text("metonymy: Prelude.head: empty list")
        b = fingerprint_failure_text("metonymy: Prelude.head: empty list")
        self.assertEqual(a, b)

    def test_different_text_gives_different_fingerprint(self) -> None:
        a = fingerprint_failure_text("metonymy: Prelude.head: empty list")
        b = fingerprint_failure_text("metonymy: something else entirely")
        self.assertNotEqual(a["sha256_prefix"], b["sha256_prefix"])

    def test_fingerprint_never_contains_the_original_text(self) -> None:
        text = "Waterloo confabulates a treaty near the Kremlin"
        fingerprint = fingerprint_failure_text(text)
        self.assertNotIn("Waterloo", str(fingerprint))
        self.assertNotIn("Kremlin", str(fingerprint))
        self.assertNotIn(text, str(fingerprint))
        self.assertEqual(fingerprint["length"], len(text))


class Exit7MaxCapitalizedRunTests(unittest.TestCase):
    def test_single_word_proper_noun_gives_a_run_of_one(self) -> None:
        self.assertEqual(
            exit7_max_capitalized_run("Waterloo announces a programme"), 1
        )

    def test_two_word_proper_noun_gives_a_run_of_two(self) -> None:
        self.assertEqual(
            exit7_max_capitalized_run("Henry County announces a programme"), 2
        )

    def test_four_word_proper_noun_gives_a_run_of_four(self) -> None:
        self.assertEqual(
            exit7_max_capitalized_run(
                "The Royal Shipley School announces a programme"
            ),
            4,
        )

    def test_no_capitalized_token_gives_a_run_of_zero(self) -> None:
        self.assertEqual(exit7_max_capitalized_run("a programme is announced"), 0)

    def test_longest_run_wins_even_when_it_is_not_the_first(self) -> None:
        self.assertEqual(
            exit7_max_capitalized_run(
                "Waterloo announces the Henry County School programme"
            ),
            3,
        )


class Exit7GfSentenceBucketTests(unittest.TestCase):
    def test_run_of_one_is_tagged_run_1(self) -> None:
        failure = json.dumps(
            {"status": "gf-parse-empty", "gf_sentence": "Waterloo announces a programme"}
        )
        self.assertEqual(exit7_gf_sentence_bucket(failure), "run-1")

    def test_run_of_three_is_tagged_run_3(self) -> None:
        failure = json.dumps(
            {
                "status": "gf-parse-empty",
                "gf_sentence": "The Shipley School announces a programme",
            }
        )
        self.assertEqual(exit7_gf_sentence_bucket(failure), "run-3")

    def test_run_of_four_or_more_is_bucketed_together(self) -> None:
        failure = json.dumps(
            {
                "status": "gf-parse-empty",
                "gf_sentence": "The Royal Shipley School District announces a programme",
            }
        )
        self.assertEqual(exit7_gf_sentence_bucket(failure), "run-4-or-more")

    def test_unparseable_failure_text_is_unrecognized_not_a_crash(self) -> None:
        self.assertEqual(exit7_gf_sentence_bucket("not valid json"), "unrecognized")

    def test_missing_gf_sentence_key_is_unrecognized_not_a_crash(self) -> None:
        self.assertEqual(
            exit7_gf_sentence_bucket(json.dumps({"status": "gf-parse-empty"})),
            "unrecognized",
        )

    def test_never_leaks_the_gf_sentence_itself(self) -> None:
        failure = json.dumps(
            {
                "status": "gf-parse-empty",
                "gf_sentence": "The Kremlin announces Henry County programme",
            }
        )
        bucket = exit7_gf_sentence_bucket(failure)
        self.assertNotIn("Kremlin", bucket)
        self.assertNotIn("Henry", bucket)


class Exit7GfSentenceSignalsTests(unittest.TestCase):
    def test_detects_comma_digit_and_apostrophe(self) -> None:
        failure = json.dumps(
            {
                "status": "gf-parse-empty",
                "gf_sentence": "Waterloo, Ontario's 1873 programme announces itself",
            }
        )
        self.assertEqual(
            exit7_gf_sentence_signals(failure),
            {"has_comma": True, "has_digit": True, "has_apostrophe": True},
        )

    def test_plain_sentence_has_no_signals(self) -> None:
        failure = json.dumps(
            {"status": "gf-parse-empty", "gf_sentence": "Waterloo announces a programme"}
        )
        self.assertEqual(
            exit7_gf_sentence_signals(failure),
            {"has_comma": False, "has_digit": False, "has_apostrophe": False},
        )

    def test_unparseable_failure_text_returns_none_not_a_crash(self) -> None:
        self.assertIsNone(exit7_gf_sentence_signals("not valid json"))


class EmptyFiberReasonTests(unittest.TestCase):
    def test_names_the_first_stage_whose_survivors_are_already_empty(self) -> None:
        row = {
            "status": "ok",
            "fiber": [],
            "stages": [
                {"index": 0, "constraint": "Requires (HasSort Human)@announce", "survivors": ["Q1"]},
                {"index": 1, "constraint": "Requires (HasSort Writer)@announce", "survivors": []},
                {"index": 2, "constraint": "Requires (HasSort Agent)@announce", "survivors": []},
            ],
        }
        self.assertEqual(
            empty_fiber_reason(row), "Requires (HasSort Writer)@announce"
        )

    def test_no_stages_at_all_is_no_constraints_derived(self) -> None:
        row = {"status": "ok", "fiber": [], "stages": []}
        self.assertEqual(empty_fiber_reason(row), "no-constraints-derived")

    def test_missing_stages_key_is_no_constraints_derived(self) -> None:
        row = {"status": "ok", "fiber": []}
        self.assertEqual(empty_fiber_reason(row), "no-constraints-derived")

    def test_every_stage_non_empty_is_unrecognized_not_a_crash(self) -> None:
        # Defensive only -- shouldn't happen in practice (an empty final
        # fiber with every recorded stage showing survivors).
        row = {
            "status": "ok",
            "fiber": [],
            "stages": [{"index": 0, "constraint": "Requires (HasSort Human)@x", "survivors": ["Q1"]}],
        }
        self.assertEqual(empty_fiber_reason(row), "unrecognized")


class ScoreTests(unittest.TestCase):
    def test_true_positive_true_negative_false_positive_false_negative(self) -> None:
        inference = [
            ok_row("tp", ["Q1"]),
            ok_row("tn", []),
            ok_row("fp", ["Q2"]),
            failed_row("fn"),
        ]
        gold = [
            {"id": "tp", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "tn", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "fp", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "fn", "gold_label": "metonymic", "gold_bridge_family": "x"},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["confusion"],
            {
                "true_positive": 1,
                "false_positive": 1,
                "true_negative": 1,
                "false_negative": 1,
            },
        )
        self.assertEqual(report["precision"], 0.5)
        self.assertEqual(report["recall"], 0.5)
        self.assertEqual(report["f1"], 0.5)

    def test_tree_available_metric_is_restricted_to_rows_with_a_built_tree(
        self,
    ) -> None:
        # Same confusion-matrix shape as the plain "every row" test above,
        # but this checks the *separate*, tree_source-gated metric: "a"
        # and "b" are both true positives overall, but only "a" (tree_
        # source="stanza") counts toward tree_available_* -- "b" (tree_
        # source="not-applicable", resolve_action declined before tree-
        # building was ever attempted) never exercised the tower at all,
        # so it must not inflate this restricted metric.
        tp_tree_available = ok_row("a", ["Q1"])
        tp_tree_available["tree_source"] = "stanza"
        tp_no_tree = ok_row("b", ["Q1"])
        tp_no_tree["tree_source"] = "not-applicable"
        tn_tree_available = ok_row("c", [])
        tn_tree_available["tree_source"] = "gf-parser"
        # exit_code=4 (semantic-composition-failed), not failed_row's own
        # default of 3 -- a real tree DID reach compile_gf_constraints
        # here, unlike exit 3/7 (see row_tree_really_built's own comment
        # for why those two exit codes must NOT count as tree-available
        # despite also carrying a "gf-parser" tree_source label).
        fn_tree_available = failed_row("d", exit_code=4)
        fn_tree_available["tree_source"] = "llm"
        inference = [tp_tree_available, tp_no_tree, tn_tree_available, fn_tree_available]
        gold = [
            {"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "b", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "d", "gold_label": "metonymic", "gold_bridge_family": "x"},
        ]
        report = score(inference, gold)
        # The overall metric still counts every row, unaffected.
        self.assertEqual(
            report["confusion"],
            {
                "true_positive": 2,
                "false_positive": 0,
                "true_negative": 1,
                "false_negative": 1,
            },
        )
        self.assertEqual(report["tree_available_instances"], 3)
        self.assertEqual(
            report["tree_available_confusion"],
            {
                "true_positive": 1,
                "false_positive": 0,
                "true_negative": 1,
                "false_negative": 1,
            },
        )
        self.assertEqual(report["tree_available_precision"], 1.0)
        self.assertEqual(report["tree_available_recall"], 0.5)
        self.assertAlmostEqual(report["tree_available_f1"], 2 / 3)

    def test_missing_inference_row_is_counted_not_silently_dropped(self) -> None:
        gold = [{"id": "missing", "gold_label": "metonymic", "gold_bridge_family": "x"}]
        report = score([], gold)
        self.assertEqual(report["missing_inference_rows"], 1)
        self.assertEqual(
            report["confusion"],
            {
                "true_positive": 0,
                "false_positive": 0,
                "true_negative": 0,
                "false_negative": 0,
            },
        )


    def test_perfect_score_has_no_undefined_precision_or_recall(self) -> None:
        inference = [ok_row("a", ["Q1"]), ok_row("b", [])]
        gold = [
            {"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(report["precision"], 1.0)
        self.assertEqual(report["recall"], 1.0)
        self.assertEqual(report["f1"], 1.0)

    def test_zero_positive_predictions_gives_none_precision_not_a_crash(self) -> None:
        inference = [ok_row("a", [])]
        gold = [{"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"}]
        report = score(inference, gold)
        self.assertIsNone(report["precision"])
        self.assertEqual(report["recall"], 0.0)
        self.assertIsNone(report["f1"])

    def test_literal_prediction_reasons_are_tallied_by_status_and_exit_code(
        self,
    ) -> None:
        inference = [
            failed_row("a", exit_code=3),
            failed_row("b", exit_code=3),
            failed_row("d", exit_code=4),
            ok_row("c", []),
        ]
        gold = [
            {"id": "a", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "b", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "d", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["literal_prediction_reasons"],
            # exit_code=4 now goes through exit4_reason_bucket -- a
            # failed_row with no "failure" field at all falls back to
            # "unrecognized", the same degrade-gracefully policy as
            # exit2/exit7's own bucket functions.
            {"failed:exit3": 2, "failed:exit4:unrecognized": 1, "ok:empty-fiber": 1},
        )

    def test_unrecognized_rows_get_no_fingerprint_bucket_when_none_are_unrecognized(
        self,
    ) -> None:
        inference = [failed_row("a", exit_code=3)]
        gold = [{"id": "a", "gold_label": "literal", "gold_bridge_family": None}]
        report = score(inference, gold)
        self.assertEqual(report["unrecognized_fingerprints"], [])

    def test_exit7_rows_are_bucketed_by_capitalized_run_in_literal_prediction_reasons(
        self,
    ) -> None:
        def exit7_row(id_: str, gf_sentence: str) -> dict:
            return {
                "id": id_,
                "status": "failed",
                "exit_code": 7,
                "failure": json.dumps(
                    {"status": "gf-parse-empty", "gf_sentence": gf_sentence}
                ),
                "fiber": [],
                "stages": [],
            }

        inference = [
            exit7_row("a", "Waterloo announces a programme"),
            exit7_row("b", "The Royal Shipley School announces a programme"),
        ]
        gold = [
            {"id": "a", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["literal_prediction_reasons"],
            {"failed:exit7:run-1": 1, "failed:exit7:run-4-or-more": 1},
        )

    def test_exit7_signal_counts_aggregate_across_rows_without_leaking_text(
        self,
    ) -> None:
        def exit7_row(id_: str, gf_sentence: str) -> dict:
            return {
                "id": id_,
                "status": "failed",
                "exit_code": 7,
                "failure": json.dumps(
                    {"status": "gf-parse-empty", "gf_sentence": gf_sentence}
                ),
                "fiber": [],
                "stages": [],
            }

        inference = [
            exit7_row("a", "Waterloo, Ontario announces a programme"),
            exit7_row("b", "Waterloo's programme announces itself"),
            exit7_row("c", "Waterloo announces a programme"),
        ]
        gold = [
            {"id": "a", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(report["exit7_rows_seen"], 3)
        self.assertEqual(
            report["exit7_signal_counts"],
            {"has_apostrophe": 1, "has_comma": 1, "has_digit": 0},
        )
        self.assertNotIn("Waterloo", json.dumps(report))
        self.assertNotIn("Ontario", json.dumps(report))

    def test_exit4_tree_source_counts_aggregate_across_rows(self) -> None:
        def exit4_row(id_: str, tree_source: str) -> dict:
            return {
                "id": id_,
                "status": "failed",
                "exit_code": 4,
                "failure": json.dumps(
                    {
                        "status": "semantic-composition-failed",
                        "gf_tree": "x",
                        "detail": "malformed or incomplete GF tree",
                        "tree_source": tree_source,
                    }
                ),
                "fiber": [],
                "stages": [],
            }

        inference = [
            exit4_row("a", "stanza"),
            exit4_row("b", "gf-parser"),
            exit4_row("c", "gf-parser"),
        ]
        gold = [
            {"id": "a", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["exit4_tree_source_counts"], {"gf-parser": 2, "stanza": 1}
        )

    def test_empty_fiber_reason_counts_aggregate_across_ok_empty_fiber_rows(
        self,
    ) -> None:
        def empty_fiber_row(id_: str, stages: list[dict]) -> dict:
            row = ok_row(id_, [])
            row["stages"] = stages
            return row

        inference = [
            empty_fiber_row(
                "a",
                [{"index": 0, "constraint": "Requires (HasSort Human)@x", "survivors": []}],
            ),
            empty_fiber_row(
                "b",
                [{"index": 0, "constraint": "Requires (HasSort Human)@x", "survivors": []}],
            ),
            empty_fiber_row("c", []),
            # A non-empty-fiber row (true positive) must not contribute.
            ok_row("d", ["Q1"]),
        ]
        gold = [
            {"id": "a", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "d", "gold_label": "metonymic", "gold_bridge_family": "x"},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["empty_fiber_reason_counts"],
            {"Requires (HasSort Human)@x": 2, "no-constraints-derived": 1},
        )

    def test_tree_source_counts_aggregate_across_every_outcome_not_just_exit4(
        self,
    ) -> None:
        successful = ok_row("a", ["Q1"])
        successful["tree_source"] = "stanza"
        exit1_row = failed_row("b", exit_code=1)
        exit4_row = {
            "id": "c",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                }
            ),
            "fiber": [],
            "stages": [],
        }
        inference = [successful, exit1_row, exit4_row]
        gold = [
            {"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["tree_source_counts"],
            {"gf-parser": 1, "not-applicable": 1, "stanza": 1},
        )

    def test_decline_reason_counts_aggregate_across_every_outcome(self) -> None:
        stanza_success = ok_row("a", ["Q1"])
        stanza_success["decline_reason"] = ""
        fallback_success = ok_row("b", [])
        fallback_success["decline_reason"] = "subject-count"
        exit1_row = failed_row("c", exit_code=1)
        exit4_row = {
            "id": "d",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                    "decline_reason": "subject-count",
                }
            ),
            "fiber": [],
            "stages": [],
        }
        inference = [stanza_success, fallback_success, exit1_row, exit4_row]
        gold = [
            {"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "d", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["decline_reason_counts"],
            {"": 1, "not-applicable": 1, "subject-count": 2},
        )

    def test_blockers_per_sentence_histogram_and_co_occurring_pairs(self) -> None:
        zero_blockers = ok_row("a", ["Q1"])
        zero_blockers["all_decline_reasons"] = []
        one_blocker = ok_row("b", [])
        one_blocker["all_decline_reasons"] = ["subject-count:advcl"]
        two_blockers = ok_row("c", [])
        two_blockers["all_decline_reasons"] = [
            "common-noun-determiner-or-adjective-count",
            "nmod-preposition-unrecognized",
        ]
        another_two_blockers = ok_row("d", [])
        another_two_blockers["all_decline_reasons"] = [
            "common-noun-determiner-or-adjective-count",
            "nmod-preposition-unrecognized",
        ]
        inference = [zero_blockers, one_blocker, two_blockers, another_two_blockers]
        gold = [
            {"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "d", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["blockers_per_sentence_histogram"], {"0": 1, "1": 1, "2": 2}
        )
        self.assertEqual(
            report["co_occurring_blocker_pairs"],
            {
                "common-noun-determiner-or-adjective-count + "
                "nmod-preposition-unrecognized": 2
            },
        )

    def test_llm_decline_reason_counts_aggregate_across_every_outcome(self) -> None:
        stanza_success = ok_row("a", ["Q1"])
        stanza_success["llm_decline_reason"] = "not-attempted"
        llm_success = ok_row("b", [])
        llm_success["llm_decline_reason"] = ""
        exit1_row = failed_row("c", exit_code=1)
        exit4_row = {
            "id": "d",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                    "decline_reason": "subject-count",
                    "llm_decline_reason": "query-exception",
                }
            ),
            "fiber": [],
            "stages": [],
        }
        inference = [stanza_success, llm_success, exit1_row, exit4_row]
        gold = [
            {"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "b", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "d", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["llm_decline_reason_counts"],
            {"": 1, "not-applicable": 1, "not-attempted": 1, "query-exception": 1},
        )

    def test_dep_status_counts_aggregate_across_every_outcome(self) -> None:
        direct_argument = ok_row("a", ["Q1"])
        direct_argument["dep_status"] = "direct-argument"
        no_hint = ok_row("b", [])
        no_hint["dep_status"] = "no-hint"
        exit1_row = failed_row("c", exit_code=1)
        exit4_row = {
            "id": "d",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                    "decline_reason": "root-lemma-mismatch:no-governing-start",
                    "dep_status": "no-governing-verb:target-deprel-conj",
                }
            ),
            "fiber": [],
            "stages": [],
        }
        inference = [direct_argument, no_hint, exit1_row, exit4_row]
        gold = [
            {"id": "a", "gold_label": "metonymic", "gold_bridge_family": "x"},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "d", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        self.assertEqual(
            report["dep_status_counts"],
            {
                "direct-argument": 1,
                "no-governing-verb:target-deprel-conj": 1,
                "no-hint": 1,
                "not-applicable": 1,
            },
        )

    def test_repeated_unrecognized_failure_text_groups_into_one_fingerprint(
        self,
    ) -> None:
        def unrecognized_row(id_: str, failure_text: str) -> dict:
            return {
                "id": id_,
                "status": "failed",
                "exit_code": 1,
                "failure": failure_text,
                "fiber": [],
                "stages": [],
            }

        inference = [
            unrecognized_row("a", "metonymy: something odd happened"),
            unrecognized_row("b", "metonymy: something odd happened"),
            unrecognized_row("c", "metonymy: a totally different crash"),
        ]
        gold = [
            {"id": "a", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "b", "gold_label": "literal", "gold_bridge_family": None},
            {"id": "c", "gold_label": "literal", "gold_bridge_family": None},
        ]
        report = score(inference, gold)
        counts = sorted(entry["count"] for entry in report["unrecognized_fingerprints"])
        self.assertEqual(counts, [1, 2])
        # ranked highest-count first
        self.assertEqual(report["unrecognized_fingerprints"][0]["count"], 2)
        self.assertEqual(
            len({entry["sha256_prefix"] for entry in report["unrecognized_fingerprints"]}),
            2,
        )


class RowTreeReallyBuiltTests(unittest.TestCase):
    """run_automatic_contextual_pipeline.py's own "tree_source" variable
    is set (to "gf-parser", unconditionally) *before* it decides whether
    to even attempt the legacy engine-parse fallback -- so exit 3
    ("gf-parse-failed") and exit 7 ("gf-parse-empty") both still carry a
    "gf-parser" tree_source in their JSON payload despite no tree ever
    having been produced. row_tree_source alone can't tell this apart
    from a real gf-parser success; row_tree_really_built can.
    """

    def test_a_real_success_with_a_tree_is_true(self) -> None:
        row = ok_row("a", ["Q1"])
        row["tree_source"] = "gf-parser"
        self.assertTrue(row_tree_really_built(row))

    def test_exit4_with_a_tree_is_true(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 4,
            "failure": json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": "x",
                    "detail": "y",
                    "tree_source": "gf-parser",
                }
            ),
        }
        self.assertTrue(row_tree_really_built(row))

    def test_exit3_despite_a_gf_parser_tree_source_label_is_false(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 3,
            "failure": json.dumps(
                {"status": "gf-parse-failed", "tree_source": "gf-parser"}
            ),
        }
        self.assertFalse(row_tree_really_built(row))

    def test_exit7_despite_a_gf_parser_tree_source_label_is_false(self) -> None:
        row = {
            "id": "a",
            "status": "failed",
            "exit_code": 7,
            "failure": json.dumps(
                {"status": "gf-parse-empty", "tree_source": "gf-parser"}
            ),
        }
        self.assertFalse(row_tree_really_built(row))

    def test_exit1_and_exit2_are_false(self) -> None:
        for exit_code in (1, 2):
            with self.subTest(exit_code=exit_code):
                row = {"id": "a", "status": "failed", "exit_code": exit_code}
                self.assertFalse(row_tree_really_built(row))

    def test_not_applicable_tree_source_is_false(self) -> None:
        row = ok_row("a", ["Q1"])
        row["tree_source"] = "not-applicable"
        self.assertFalse(row_tree_really_built(row))


if __name__ == "__main__":
    unittest.main()
