#!/usr/bin/env python3
"""Score the contextual tower's metonymic-vs-literal detection.

WiMCor/ConMeC gold only ever says metonymic-vs-literal plus a bridge-
family type; neither annotates a specific correct Wikidata entity, so
score_qid_fibers.py's exact-QID-in-fiber metric cannot be computed for
them at all -- there is no gold_qids field to compare against. This
scores the weaker claim these corpora actually support: for a
gold-metonymic mention, did the tower successfully run and produce a
non-empty final fiber (some bridged reading survived every stage); for a
gold-literal mention, did it correctly produce none.

This mapping is a design choice, not a re-derivation of something the
engine already reports as a "detected" flag -- the tower has no native
metonymic/literal output, only a per-run status and a final fiber (see
scripts/evaluation/run_contextual_corpus.py's run_one). "status == ok and
fiber non-empty" is treated as a positive prediction; every kind of
failure (GF parse failure, unsupported action role, semantic-composition
failure, or a successful run that filters the fiber down to nothing) is
treated as a negative one, mirroring how the flat pipeline's own
emitted/abstain split already works. Verify this mapping is what the
paper wants before citing raw precision/recall/F1 from it.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path


def jsonl(path: Path):
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def predict(inference_row: dict) -> str:
    if inference_row.get("status") == "ok" and inference_row.get("fiber"):
        return "metonymic"
    return "literal"


# Every short, fixed error token that can show up in an exit-1 row's
# "failure" text. Three distinct sources feed this same exit code:
# resolve_action/propose_contextual_scenario.py's own ValueErrors
# (contextual_rule_compiler.py, propose_contextual_scenario.py); the
# compiled engine's own `die` messages (System.Exit.die always exits 1),
# built as "contextual fiber failed: <reason>" from Metonymy.Contextual's
# validateContext/contextualFiber (empty-snapshot-hash/empty-action/
# tree-without-lexical-leaves/empty-constraint-provenance/unknown-
# constraint-provenance/invalid-lexical-span/snapshot-hash-mismatch/
# invalid-max-depth) and Metonymy.ContextualChecked's own per-stage Agda
# cross-check (agda-rejected-survivor-at-stage-/agda-accepted-
# obstruction-at-stage-/agda-rejected-preference-at-stage-/agda-accepted-
# preference-miss-at-stage-, each followed by a stage number this
# deliberately does not capture); and -- an easy one to miss, since it
# fires before any command dispatch, let alone the fiber computation
# above -- Metonymy.ContextSpec.loadContextScenarios's own scenario-TSV
# parsing, which runs unconditionally at the very start of every engine
# invocation and raises via plain `fail`, not `die`, so GHC's default
# top-level handler (not System.Exit.die's convention) formats the
# message, still exiting 1 either way (unknown contextual scenario:/
# empty contextual scenario file:/unexpected contextual scenario header:/
# expected seven tab-separated fields/malformed contextual constraint:/
# unknown symbolic value:). run_automatic_contextual_pipeline.py's
# multi-candidate disambiguation loop (see its own module docstring)
# reaches all of this by propagating a representative candidate's own
# exit code when *no* candidate's engine run succeeds. All of these are
# the *names* of failure conditions, never sentence text, so matching one
# out of a subprocess's combined stdout+stderr and reporting only the
# matched token, never the surrounding text, stays safe to upload even
# though the untruncated text (which does echo sentence text -- e.g.
# propose_contextual_scenario.py prints the offending gf_sentence/gf_tree
# on some failures, and a malformed-constraint message echoes the
# offending encoded constraint, which can include a source word) is not.
KNOWN_FAILURE_TOKENS = (
    "target-occurrence-not-found",
    "unsupported-action-role",
    "nested-modifier-unsupported",
    "unsupported-copula-predicate",
    "source-qid-unresolved",
    "contract-target-qid-unresolved",
    "unsupported-linker-cache-schema",
    "empty-snapshot-hash",
    "empty-action",
    "tree-without-lexical-leaves",
    "empty-constraint-provenance",
    "unknown-constraint-provenance",
    "invalid-lexical-span",
    "snapshot-hash-mismatch",
    "invalid-max-depth",
    "agda-rejected-survivor-at-stage-",
    "agda-accepted-obstruction-at-stage-",
    "agda-rejected-preference-at-stage-",
    "agda-accepted-preference-miss-at-stage-",
    "unknown contextual scenario:",
    "empty contextual scenario file:",
    "unexpected contextual scenario header:",
    "expected seven tab-separated fields",
    "malformed contextual constraint:",
    "unknown symbolic value:",
    # Confirmed (not guessed) the actual, sole cause of every real
    # "unrecognized" row seen so far -- see literal_reason's own
    # docstring. Now fixed at the source to its own exit code (7); kept
    # here only for any already-produced data that predates that fix.
    "GF returned no lexicalized trees",
)

# Generic GHC/Prelude runtime-crash signatures -- a different *kind* of
# token from KNOWN_FAILURE_TOKENS above: those are precise, this-codebase-
# specific named failure conditions (an explicit `Left "reason"` or `fail
# "reason"` this project's own code chose to raise); these are the
# standard library's own well-known partial-function/pattern-match/
# arithmetic crash message prefixes, which any GHC program can hit
# whenever such a function is applied outside its domain (e.g. `head` on
# an empty list) -- something this codebase does not raise on purpose.
# Motivation: two rounds of adding KNOWN_FAILURE_TOKENS entries (both
# guessed from reading Metonymy.Contextual/ContextualChecked/ContextSpec's
# own explicit Left/fail sites) changed nothing -- a real
# contextual-tower-evaluation.yml run produced byte-identical
# "unrecognized" counts before and after both additions, meaning neither
# round's tokens matched anything. `Checker.hs` (compiled from Agda,
# Metonymy.ContextualChecked's `verifyContextLayerWithAgda` calls into it)
# produced real GHC compiler warnings during this project's own build
# about exactly this class of partial function ("throws an error on empty
# lists... consider... Data.List.NonEmpty") -- and the live-API-built
# snapshot's own sparser entities (a same-named-place candidate with zero
# claims at all, confirmed by locally reproducing the real sample) are
# exactly the kind of edge case a curated, hand-picked snapshot would
# never have exercised. Deliberately broad rather than an exact function
# name, since GHC's own message varies by which partial function actually
# ran out of domain and this project cannot predict that in advance; still
# safe to match on since these are fixed standard-library message
# prefixes, never sentence text.
GENERIC_RUNTIME_CRASH_TOKENS = (
    "Prelude.",
    "Non-exhaustive patterns",
    "divide by zero",
)

# Three of KNOWN_FAILURE_TOKENS above now carry an optional ":<suffix>" --
# resolve_action (contextual_rule_compiler.py) appends a closed-vocabulary
# UD deprel to "nested-modifier-unsupported", a single governing verb
# lemma to "unsupported-action-role", and (_resolve_copula_predicate) a
# single predicate-noun lemma to "unsupported-copula-predicate" (see each
# raise site's own comment for why that's safe to surface: a UD relation
# label from a fixed 8-entry vocabulary, or one common English lemma /
# "<verb> <preposition>" phrasal reconstruction / predicate-noun lemma --
# never sentence text). Listed here so literal_reason knows which of the
# many KNOWN_FAILURE_TOKENS entries to look for a suffix on, rather than
# trying (and failing) to parse one off every token indiscriminately.
SUFFIXED_FAILURE_TOKENS = (
    "nested-modifier-unsupported",
    "unsupported-action-role",
    "unsupported-copula-predicate",
)

# Every fixed message compile_gf_constraints/_origin/_cumulative_origin
# (scripts/contextual_rule_compiler.py) can raise as a ValueError, reaching
# run_automatic_contextual_pipeline.py's exit-4 branch, which JSON-wraps it
# as {"status": "semantic-composition-failed", "gf_tree": ..., "detail":
# str(error)}. "gf_tree" echoes real sentence content (the GF tree's own
# String leaves are the sentence's proper nouns/lemmas) and must never be
# read here; "detail" is a fixed English sentence with, in most cases, one
# interpolated word or sort name spliced in (e.g. "ambiguous noun sort for
# GF composition: county") -- the same risk class already accepted for
# unsupported-action-role's governing_lemma above, but exit4_reason_bucket
# deliberately reports only the fixed substring match below, never the
# full "detail" text, so the interpolated word never leaves this function.
# A substring match (not a prefix match) is used because two of these
# messages interpolate a value in the *middle*, not at the end (e.g.
# f"action {proposal['action']} has no role rule for {sort}") -- the same
# style KNOWN_FAILURE_TOKENS already uses for the same reason.
EXIT4_KNOWN_FAILURE_TOKENS = (
    "malformed GF tree near ",
    "malformed or incomplete GF tree",
    "GF lexical token is absent from source: ",
    "malformed adjective-noun GF node",
    "unsupported GF adjective-noun semantics: ",
    "ambiguous noun sort for GF composition: ",
    "no semantic composition for ",
    " has no role rule for ",
    "context modifier QID is not unique: ",
)


# "malformed or incomplete GF tree" can now carry its own
# "; unrecognized constructor(s): <Name>,<Name>" suffix
# (contextual_rule_compiler.parse_gf_tree) -- the specific GF constructor
# name(s) missing from ARITIES that most likely caused the tree to be
# left unconsumed. A constructor name is this grammar's own closed
# vocabulary (grammar/Metonymy.gf's `fun` declarations), never sentence
# text, so exit4_suffixed_token below reports it the same way
# exit1_suffixed_token reports a UD deprel or verb lemma.
EXIT4_SUFFIXED_TOKENS = ("malformed or incomplete GF tree",)


def exit4_tree_source(failure_text: str) -> str:
    """Which of the three tree sources produced this exit-4 row's tree
    -- "stanza" (scripts/build_gf_tree_from_dependencies.py's UD-based
    build_gf_tree), "llm" (the same module's
    build_gf_tree_from_llm_structure, fed by
    scripts/llm_propose_clause_structure.py), or "gf-parser" (GF's own
    `engine parse` on raw text) -- or "unrecognized" if the field can't
    be read at all.

    A live corpus evaluation run of Phase 1's tree-builder surfaced a
    real mystery: bare, unquoted capitalized words (e.g. "Albright",
    "The") appearing as exit4_reason_bucket's own "unrecognized
    constructor(s)" -- something neither the tree-builder (which always
    quotes its own string arguments, and is validated through `engine
    linearize` before ever being trusted) nor any known gf_actions entry
    explains. run_automatic_contextual_pipeline.py tags every exit-4 row
    with exactly which source actually produced trees[0] for it, purely
    so a future real corpus run can isolate which source the mystery is
    actually coming from -- itself telling neither sentence text nor
    anything content-derived, just which of two known code paths ran.
    """
    try:
        return json.loads(failure_text).get("tree_source", "unrecognized")
    except (json.JSONDecodeError, TypeError):
        return "unrecognized"


# exit codes reached *before* run_automatic_contextual_pipeline.py ever
# attempts tree-building at all (propose_contextual_scenario.py itself
# failed, or no source QID resolved) -- "tree_source" is meaningless for
# these, not merely missing.
_EXIT_CODES_BEFORE_TREE_BUILDING = {1, 2}

# exit codes where run_automatic_contextual_pipeline.py's own
# "tree_source" variable is set to a real value ("gf-parser", always --
# see below) despite there being *no actual tree*: it computes
# tree_source once, unconditionally, right before deciding whether to
# fall back to the legacy `engine parse` on raw text at all -- so exit 3
# ("gf-parse-failed", GF's own parser errored) and exit 7 ("gf-parse-
# empty", GF's own parser found zero trees) both still carry
# tree_source="gf-parser" in their JSON payload, even though the whole
# reason they exited there is that no tree was ever produced. (Reaching
# either of these two exit codes at all requires both the Stanza and LLM
# tiers to have already declined, which is exactly why tree_source is
# always "gf-parser" -- never "stanza"/"llm" -- for both; neither of
# those two sources' own counts is affected by this.) row_tree_source
# alone cannot tell "gf-parser really built a tree" apart from "gf-
# parser was about to be tried and immediately failed" -- see
# row_tree_really_built, which can.
_EXIT_CODES_WITHOUT_A_REAL_TREE = {1, 2, 3, 7}


def row_tree_source(inference_row: dict) -> str:
    """Which of the three tree sources ("stanza"/"llm"/"gf-parser")
    produced this row's tree, across *every* outcome -- not just exit4
    failures.

    run_automatic_contextual_pipeline.py records "tree_source" two
    different ways depending on how the row ended: a top-level
    "tree-source=" stdout line (picked up directly onto the row by
    run_contextual_corpus.py's own line-scan) for every row that
    successfully obtained a tree (a full success, exit 5, or exit 6);
    a "tree_source" key inside the row's own JSON-encoded "failure"
    text for exit 3/4/7 (the three ways tree-building or the semantic-
    composition step that follows it can fail). This unifies both into
    one lookup so score()'s own aggregate doesn't need to special-case
    "did this row succeed or fail" first. Answers "not-applicable" for
    exit 1/2 (tree-building was never attempted at all for those), and
    "unrecognized" if a row that should have the field doesn't (a
    genuinely unexpected shape, degrading gracefully rather than
    crashing the scorer).
    """
    if "tree_source" in inference_row:
        return inference_row["tree_source"]
    exit_code = inference_row.get("exit_code")
    if exit_code in _EXIT_CODES_BEFORE_TREE_BUILDING:
        return "not-applicable"
    if exit_code in (3, 4, 7):
        return exit4_tree_source(inference_row.get("failure", ""))
    return "unrecognized"


_TREE_BUILT_SOURCES = {"stanza", "llm", "gf-parser"}


def row_tree_really_built(inference_row: dict) -> bool:
    """True only if a real GF tree actually reached compile_gf_constraints
    for this row -- unlike checking ``row_tree_source(...) in
    _TREE_BUILT_SOURCES`` alone, this correctly excludes exit 3 ("gf-
    parse-failed") and exit 7 ("gf-parse-empty"): see
    _EXIT_CODES_WITHOUT_A_REAL_TREE's own comment for why row_tree_source
    still (misleadingly) reports "gf-parser" for both of those, even
    though the whole reason they exited there is that no tree was ever
    produced.
    """
    if inference_row.get("exit_code") in _EXIT_CODES_WITHOUT_A_REAL_TREE:
        return False
    return row_tree_source(inference_row) in _TREE_BUILT_SOURCES


def row_decline_reason(inference_row: dict) -> str:
    """Which reason build_gf_tree (or the two extra checks around it --
    "no-ud-words"/"linearize-validation-failed") declined for this row,
    across every outcome -- mirrors row_tree_source exactly, just for
    "decline_reason" instead of "tree_source".

    A real corpus evaluation measured zero successful Stanza-tree uses
    across 300 real rows with no way to tell why (tree_source_counts:
    100% "gf-parser") -- this is what answers that, aggregated by
    score() into a "decline_reason_counts" report field. "" means a
    Stanza-built tree was actually trusted (nothing to explain, even if
    the row later failed for an unrelated reason downstream);
    "not-applicable" for exit 1/2 (tree-building was never attempted);
    "unrecognized" if a row that should have the field doesn't.
    """
    if "decline_reason" in inference_row:
        return inference_row["decline_reason"]
    exit_code = inference_row.get("exit_code")
    if exit_code in _EXIT_CODES_BEFORE_TREE_BUILDING:
        return "not-applicable"
    if exit_code in (3, 4, 7):
        try:
            return json.loads(inference_row.get("failure", "")).get(
                "decline_reason", "unrecognized"
            )
        except (json.JSONDecodeError, TypeError):
            return "unrecognized"
    return "unrecognized"


def row_all_decline_reasons(inference_row: dict) -> list[str]:
    """Every reason enumerate_gf_tree_blockers found for this row, in
    order -- not just the first one row_decline_reason reports. Mirrors
    row_decline_reason exactly, just for the "all_decline_reasons" list
    field instead of the single "decline_reason" string.

    A real corpus evaluation round found several decline_reason buckets
    grow even as others shrank after a real fix -- exactly what "a
    sentence that now passes an earlier check just hits a different,
    still-unaddressed one next" predicts, but decline_reason_counts
    alone (only ever the *first* blocker) can't confirm it. This is what
    score() aggregates into "blockers_per_sentence_histogram" and
    "co_occurring_blocker_pairs" to answer that directly. [] means
    either zero blockers (the row's own tree actually built) or
    "not-applicable" (exit 1/2, tree-building never attempted) --
    row_tree_source/row_decline_reason already distinguish those two for
    the same row, so this doesn't need its own separate sentinel for it.
    ["unrecognized"] if a row that should carry the field doesn't.
    """
    if "all_decline_reasons" in inference_row:
        return inference_row["all_decline_reasons"]
    exit_code = inference_row.get("exit_code")
    if exit_code in _EXIT_CODES_BEFORE_TREE_BUILDING:
        return []
    if exit_code in (3, 4, 7):
        try:
            reasons = json.loads(inference_row.get("failure", "")).get(
                "all_decline_reasons"
            )
            return reasons if isinstance(reasons, list) else ["unrecognized"]
        except (json.JSONDecodeError, TypeError):
            return ["unrecognized"]
    return ["unrecognized"]


def row_llm_decline_reason(inference_row: dict) -> str:
    """Which reason the third (LLM) tier declined for this row, across
    every outcome -- mirrors row_decline_reason exactly, just for
    "llm_decline_reason" instead of "decline_reason".

    "not-attempted" means the LLM tier never ran at all (either a
    Stanza-built tree was already trusted, or no --llm-proposer-model
    was configured for this run); "" means the LLM tier's own tree was
    trusted; "not-applicable" for exit 1/2 (tree-building was never
    attempted); "unrecognized" if a row that should have the field
    doesn't.
    """
    if "llm_decline_reason" in inference_row:
        return inference_row["llm_decline_reason"]
    exit_code = inference_row.get("exit_code")
    if exit_code in _EXIT_CODES_BEFORE_TREE_BUILDING:
        return "not-applicable"
    if exit_code in (3, 4, 7):
        try:
            return json.loads(inference_row.get("failure", "")).get(
                "llm_decline_reason", "unrecognized"
            )
        except (json.JSONDecodeError, TypeError):
            return "unrecognized"
    return "unrecognized"


def row_dep_status(inference_row: dict) -> str:
    """annotate_dependency_hints.py's own dep_status
    ("direct-argument"/"copula-argument"/"nested-modifier"/
    "no-governing-verb:<reason>"/"parse-error"/"no-hint") for this row,
    across every outcome -- mirrors row_llm_decline_reason exactly, just
    for the "dep_status" field.

    This was the missing piece that made root-lemma-mismatch:no-
    governing-start's own real cause invisible in every prior corpus
    evaluation report -- dep_status was always computed by
    annotate_dependency_hints.py, but never itself surfaced anywhere
    run_automatic_contextual_pipeline.py reports, only consumed
    internally by resolve_action. score() aggregates this into a
    "dep_status_counts" report field, which is what a real corpus run
    needs to say which of _no_governing_verb's own four suffixes
    actually dominates.

    "no-hint" means no --dependency-hint was passed to this row's
    pipeline invocation at all (a genuinely distinct case from any
    status classify_word itself can produce); "not-applicable" for exit
    1/2 (tree-building was never attempted, so dep_status was never even
    read); "unrecognized" if a row that should have the field doesn't.
    """
    if "dep_status" in inference_row:
        return inference_row["dep_status"]
    exit_code = inference_row.get("exit_code")
    if exit_code in _EXIT_CODES_BEFORE_TREE_BUILDING:
        return "not-applicable"
    if exit_code in (3, 4, 7):
        try:
            return json.loads(inference_row.get("failure", "")).get(
                "dep_status", "unrecognized"
            )
        except (json.JSONDecodeError, TypeError):
            return "unrecognized"
    return "unrecognized"


def exit4_reason_bucket(failure_text: str) -> str:
    """Bucket an exit-4 (semantic-composition-failed) row by which of
    compile_gf_constraints's own fixed ValueError messages it raised.

    Mirrors exit2_candidate_bucket/exit7_gf_sentence_bucket: parse the
    JSON run_automatic_contextual_pipeline.py already prints on this path
    and derive a content-free bucket from its safe "detail" field only --
    never its "gf_tree" field, which does carry real sentence content (see
    EXIT4_KNOWN_FAILURE_TOKENS's own comment). Falls back to
    "unrecognized" both when the field isn't parseable JSON with a
    "detail" key and when "detail" doesn't contain any of the known fixed
    messages, the same degrade-gracefully policy as its siblings. One
    entry (EXIT4_SUFFIXED_TOKENS) gets a further suffix via
    exit4_suffixed_token -- see that function's own docstring.
    """
    try:
        detail = json.loads(failure_text)["detail"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return "unrecognized"
    for token in EXIT4_KNOWN_FAILURE_TOKENS:
        if token in detail:
            bucket = token.strip()
            if bucket in EXIT4_SUFFIXED_TOKENS:
                return exit4_suffixed_token(bucket, detail)
            return bucket
    return "unrecognized"


def exit4_suffixed_token(token: str, detail: str) -> str:
    """Recover parse_gf_tree's own unrecognized-constructor suffix.

    Unlike exit1_suffixed_token, ``detail`` here is already the clean,
    JSON-isolated string exit4_reason_bucket extracted (no risk of
    capturing a JSON string's own closing quote), and the marker this
    looks for is a fixed string this project's own code writes, not a
    bare ":" that could collide with unrelated text -- so a plain
    ``str.find`` is enough, no regex needed. Falls back to the bare token
    when the marker isn't present (a "malformed or incomplete GF tree"
    with no identifiable unrecognized constructor -- parse_gf_tree's own
    fallback case).
    """
    marker = "; unrecognized constructor(s): "
    index = detail.find(marker)
    if index == -1:
        return token
    suffix = detail[index + len(marker) :]
    return f"{token}:{suffix}" if suffix else token


def exit1_suffixed_token(token: str, failure_text: str) -> str:
    """Recover a SUFFIXED_FAILURE_TOKENS entry's ":<suffix>", if present.

    All three suffixed tokens can only originate from resolve_action, called
    exclusively from propose_contextual_scenario.py, which turns its
    ValueError into `raise SystemExit(str(error))` -- printing the bare
    message ("nested-modifier-unsupported:appos", say) to stderr with no
    extra formatting. run_automatic_contextual_pipeline.py's exit-1
    branch (its "propose-scenario-failed" case) then captures that
    subprocess's combined stdout+stderr into its own JSON payload's
    "detail" field and is what run_contextual_corpus.py in turn stores as
    this row's "failure" text -- so, unlike this function's first
    (real-CI-corrected) version assumed, this is JSON like exit2/exit4/
    exit7's payloads, not a raw Python traceback. Parsing it and reading
    only "detail" avoids a real bug a live evaluation run caught: matching
    against the *raw* pretty-printed JSON text (as the first version did)
    captured the value's own closing quote as part of the suffix (e.g.
    "nested-modifier-unsupported:appos\"" instead of
    "nested-modifier-unsupported:appos"), because a raw substring search
    has no way to know where the JSON string value actually ends. Falls
    back to searching failure_text directly (still excluding stray quote
    characters, as a second line of defense) when it isn't JSON-wrapped
    at all -- defensive only, since every known origin of these three
    particular tokens is confirmed JSON-wrapped as described above.
    Falls back to the bare token when there's no ":" at all (the
    backward-compatible, no-deprel/no-lemma raise still supported at each
    site -- see resolve_action's own comments).
    """
    try:
        detail = json.loads(failure_text).get("detail", "")
    except (json.JSONDecodeError, AttributeError, TypeError):
        detail = failure_text
    match = re.search(rf"{re.escape(token)}:([^\r\n\"]*)", detail)
    if match and match.group(1):
        return f"{token}:{match.group(1)}"
    return token


def exit2_candidate_bucket(failure_text: str) -> str:
    """Split exit 2 (source-qid-unresolved) into zero vs ambiguous candidates.

    run_automatic_contextual_pipeline.py's exit-2 branch prints the full
    proposal dict -- including "source_qid_candidates", a list of QIDs,
    never sentence text -- to stdout before raising SystemExit(2), and
    that is the only thing it prints on that path; run_contextual_corpus.py
    captures the subprocess's stdout+stderr into this row's "failure"
    field unconditionally on any non-zero exit, not only exit 1. Parsing
    it back out distinguishes "the surface matched no Wikidata alias at
    all" from "the surface matched more than one, and the linker's
    exact-alias-or-abstain policy (build_wikidata_api_index.py's
    search_exact: "an ambiguous surface simply resolves to more than one
    QID here, and callers decide what to do with that") refused to
    guess" -- two causes needing very different fixes, previously
    conflated under one undifferentiated "failed:exit2" tally. A QID list
    carries no sentence text, so this stays as safe to upload as the
    exit-1 token extraction above. Falls back to "unrecognized" if the
    field isn't parseable JSON with that key, so an unexpected shape
    degrades gracefully instead of crashing the scorer.
    """
    try:
        candidates = json.loads(failure_text)["source_qid_candidates"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return "unrecognized"
    if not candidates:
        return "zero-candidates"
    return "ambiguous-candidates"


def exit7_max_capitalized_run(gf_sentence: str) -> int:
    """Longest run of consecutive capitalized word-tokens in gf_sentence.

    A safe, content-free proxy for "how many tokens long is the proper-
    noun span GF was actually asked to parse". grammar/Metonymy.gf's
    OpenPN/OpenPN2/OpenPN3 cover spans of exactly 1/2/3 tokens
    respectively (see docs/contextual-tower.md's "OpenPN only matches one
    token" section) -- so among rows that still fail with gf-parse-empty
    after that fix, a run of 4+ is a direct structural signal that the
    row is the *same* class of gap OpenPN2/OpenPN3 were built to close,
    just one token longer than either covers; a run of 1-3 means
    something else caused that particular row to fail, since the grammar
    already has a matching NP-building alternative for spans that short.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", gf_sentence)
    longest = current = 0
    for token in tokens:
        if token[:1].isupper():
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def exit7_gf_sentence_bucket(failure_text: str) -> str:
    """Bucket an exit-7 (gf-parse-empty) row by its longest capitalized
    token run -- never by any of its actual text.

    Mirrors exit2_candidate_bucket's approach: parse the JSON
    run_automatic_contextual_pipeline.py already prints on this path
    (`{"status": "gf-parse-empty", "gf_sentence": ...}`), derive a
    content-free structural feature from it, and report only the derived
    bucket -- never the sentence itself, which is exactly why this
    workflow cannot upload raw inference rows as a CI artifact in the
    first place. Falls back to "unrecognized" on anything unparseable,
    the same degrade-gracefully policy exit2_candidate_bucket uses.
    """
    try:
        gf_sentence = json.loads(failure_text)["gf_sentence"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return "unrecognized"
    run = exit7_max_capitalized_run(gf_sentence)
    if run <= 0:
        return "run-0"
    if run >= 4:
        return "run-4-or-more"
    return f"run-{run}"


def exit7_gf_sentence_signals(failure_text: str) -> dict[str, bool] | None:
    """Three more content-free structural flags for an exit-7 row.

    Aggregated by score() into "exit7_signal_counts" -- never reported
    per-row -- to check this session's other standing hypotheses
    (appositive/fronted-clause commas, numerals, possessive 's) against
    the real corpus independently of the capitalized-run bucket above,
    from the same already-parsed gf_sentence, still never exposing it.
    Returns None on anything unparseable (same policy as the bucket
    function above), so a caller can skip aggregating a row it can't
    read rather than counting a false negative for every flag.
    """
    try:
        gf_sentence = json.loads(failure_text)["gf_sentence"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    return {
        "has_comma": "," in gf_sentence,
        "has_digit": any(character.isdigit() for character in gf_sentence),
        "has_apostrophe": "'" in gf_sentence,
    }


def literal_reason(inference_row: dict) -> str:
    """A text-free tag for why a row predicted "literal" -- status plus
    exit code (run_automatic_contextual_pipeline.py uses a distinct exit
    code per failure kind: 3 gf-parse-failed, 4 semantic-composition-
    failed, 5 contract-target-qid-unresolved, 7 gf-parse-empty (GF's
    parser ran successfully but produced zero lexicalized trees), 2
    source-qid-unresolved -- no candidate QID at all for the source
    surface in the snapshot's own aliases.jsonl, or (--contract-target
    only) not exactly one -- 6 source-disambiguation-ambiguous -- two or
    more source candidates each independently ran the tower's full
    per-layer narrowing to a non-empty final fiber, and the pipeline
    refuses to guess between them). Exit 1 covers three different origins
    that all end up looking identical at this level -- everything
    resolve_action/propose_contextual_scenario.py itself raises as a
    ValueError (target-occurrence-not-found/unsupported-action-role/
    nested-modifier-unsupported), reaching run_automatic_contextual_pipeline.py
    as an uncaught CalledProcessError from its own `subprocess.run(...,
    check=True)` call; the case where every one of the disambiguation
    loop's candidates failed its own engine invocation outright (not just
    an empty fiber), which the pipeline surfaces by propagating that
    candidate's own exit code; and, within that same case, GHC's own exit
    code for an uncaught runtime exception -- always 1 as well, same as
    System.Exit.die and a `fail` reaching GHC's default top-level handler,
    so the exit code alone genuinely cannot tell any of these three apart
    (see GENERIC_RUNTIME_CRASH_TOKENS's own comment for why that
    possibility gets a second, broader pass). A fourth exit-1 origin used
    to exist here too: a bare `raise SystemExit("some string")` prints
    that string and exits 1 without the JSON-"status" convention every
    sibling failure follows -- this is exactly what
    run_automatic_contextual_pipeline.py's "GF returned no lexicalized
    trees" case did until fingerprint_failure_text's safe, content-free
    hashing (no guessed token needed) matched a locally-reproduced
    fingerprint of that exact 32-character string, confirming it as the
    single cause behind every "unrecognized" row two guessed rounds of
    KNOWN_FAILURE_TOKENS/GENERIC_RUNTIME_CRASH_TOKENS additions had missed.
    Fixed at the source (now exit 7, JSON-wrapped like every sibling); the
    string is kept in KNOWN_FAILURE_TOKENS below purely as a defensive
    backward-compat match, in case any already-produced data still has
    it. So for exit 1 this also searches the row's own "failure" text
    (never exposed itself) for one of KNOWN_FAILURE_TOKENS, then -- if
    none of those precise, this-codebase tokens match -- one of
    GENERIC_RUNTIME_CRASH_TOKENS (see its own comment for why a separate,
    broader pass exists), and reports only the matched token name, or
    "failed:exit1:unrecognized" if neither matches. Two KNOWN_FAILURE_TOKENS
    entries (SUFFIXED_FAILURE_TOKENS: nested-modifier-unsupported,
    unsupported-action-role) get a ":<suffix>" appended via
    exit1_suffixed_token when resolve_action's own raise included one --
    see that function's and each raise site's own comments for why a UD
    deprel or a single governing verb lemma is safe to surface this way.
    Exit 2 similarly gets a sub-tag from exit2_candidate_bucket, exit 4
    from exit4_reason_bucket, and exit 7 from exit7_gf_sentence_bucket --
    see each one's own docstring. Carries no sentence text either way, so
    this is safe to upload as a CI artifact even though the inference row
    it's drawn from is not.
    """
    if inference_row.get("status") == "ok":
        return "ok:empty-fiber"
    exit_code = inference_row.get("exit_code", "unknown")
    if exit_code == 1:
        failure_text = inference_row.get("failure", "")
        for token in KNOWN_FAILURE_TOKENS:
            if token in failure_text:
                if token in SUFFIXED_FAILURE_TOKENS:
                    return f"failed:exit1:{exit1_suffixed_token(token, failure_text)}"
                return f"failed:exit1:{token}"
        for token in GENERIC_RUNTIME_CRASH_TOKENS:
            if token in failure_text:
                return f"failed:exit1:{token}"
        return "failed:exit1:unrecognized"
    if exit_code == 2:
        return f"failed:exit2:{exit2_candidate_bucket(inference_row.get('failure', ''))}"
    if exit_code == 4:
        return f"failed:exit4:{exit4_reason_bucket(inference_row.get('failure', ''))}"
    if exit_code == 7:
        return f"failed:exit7:{exit7_gf_sentence_bucket(inference_row.get('failure', ''))}"
    return f"failed:exit{exit_code}"


def empty_fiber_reason(inference_row: dict) -> str:
    """For an "ok:empty-fiber" row (a real tree built, the tower ran to
    completion, but the final fiber came back empty), the safe, closed-
    vocabulary reason why -- the *first* stage (in narrowing order)
    whose own "survivors" list is already empty, naming that stage's own
    "constraint" string (run_contextual_corpus.py's line-scan already
    captures this onto ``inference_row["stages"][i]["constraint"]``).

    Once a stage's survivors reach zero, every later stage only narrows
    further, so the first empty stage is exactly the elimination point
    -- the same "first blocker" principle used throughout this module.

    Confirmed safe to aggregate by reading the engine's own renderConstraint
    directly (engine/app/Main.hs), not assumed: it prints
    ``show(ConstraintPayload) <> "@" <> anchorLemma(...)`` -- a
    ConstraintPayload is Requires/RequiresRelation/RequiresSome/Prefers/
    PrefersRelation/PrefersSome wrapping only a Requirement (composed of
    Sort, a 46-member closed enum), a Relation (a 19-member closed enum),
    or an EntityId (a public, stable Wikidata QID, already printed
    throughout this project's own "survivors="/"obstruction=" lines) --
    and a single anchor lemma (the same safety class already established
    for governing_lemma elsewhere). The full sentence-text-carrying
    LexicalAnchor (surface/start/end) is never rendered, only its own
    ``anchorLemma`` field, extracted explicitly -- confirmed by reading
    engine/src/Metonymy/Contextual.hs's LexicalAnchor record directly.

    "no-constraints-derived" when the row has no stages at all (zero
    constraints were ever derived from the tree -- a structurally
    different, earlier cause than any one stage's own filter). Falls
    back to "unrecognized" if every stage somehow shows non-empty
    survivors despite an empty final fiber (shouldn't happen in
    practice, degrading gracefully rather than crashing the scorer).
    """
    stages = inference_row.get("stages") or []
    if not stages:
        return "no-constraints-derived"
    for stage in stages:
        if not stage.get("survivors"):
            return stage.get("constraint") or "unrecognized"
    return "unrecognized"


def fingerprint_failure_text(failure_text: str) -> dict:
    """A safe, content-free fingerprint of a failure text: a short hash
    prefix and a character length, never the text itself.

    Exists specifically for "failed:exit1:unrecognized" rows -- two
    consecutive contextual-tower-evaluation.yml runs added 18 precise
    KNOWN_FAILURE_TOKENS entries and 3 broad GENERIC_RUNTIME_CRASH_TOKENS
    ones with zero matches either time, burning a CI round trip each time
    on a guess. This answers a cheaper, more useful question first --
    "is this one repeated message or many different ones" -- without
    needing another guess: a single dominant sha256_prefix repeated
    across most/all "unrecognized" rows means one root cause; many
    distinct ones means several unrelated things are going wrong at once.
    12 hex characters of SHA-256 (48 bits) makes an accidental collision
    among a few hundred rows astronomically unlikely, so equal prefixes
    reliably mean equal underlying text without ever transmitting it.
    """
    return {
        "sha256_prefix": hashlib.sha256(failure_text.encode("utf-8")).hexdigest()[:12],
        "length": len(failure_text),
    }


def _precision_recall_f1(
    true_positive: int, false_positive: int, true_negative: int, false_negative: int
) -> tuple[float | None, float | None, float | None]:
    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive)
        else None
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative)
        else None
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall)
        else None
    )
    return precision, recall, f1


def score(inference_rows: list[dict], gold_rows: list[dict]) -> dict:
    inference_by_id = {row["id"]: row for row in inference_rows}
    true_positive = false_positive = true_negative = false_negative = 0
    # The same four counts, but restricted to rows row_tree_really_built
    # confirms actually reached compile_gf_constraints with a real tree
    # -- i.e., where the contextual tower's own Agda-checked layered
    # filtering genuinely ran at all, regardless of which of the three
    # untrusted proposers supplied the tree (the tower itself is provably
    # agnostic to tree provenance -- see docs/contextual-tower.md).
    # "not-applicable" rows (resolve_action itself declined before tree-
    # building was ever attempted), and exit 3/7 rows (tree-building was
    # attempted but produced nothing -- see row_tree_really_built's own
    # comment for why row_tree_source alone would wrongly count these as
    # "gf-parser"), never exercise the formal core at all, so folding
    # them into the same precision/recall as tree-available rows
    # conflates "the tower is wrong" with "the tower never ran" -- two
    # very different claims for a paper.
    tree_available_true_positive = tree_available_false_positive = 0
    tree_available_true_negative = tree_available_false_negative = 0
    missing = 0
    literal_prediction_reasons: Counter[str] = Counter()
    # Sub-bucket of literal_prediction_reasons's own "ok:empty-fiber" --
    # which stage's own constraint eliminated the last survivor, for the
    # rows where a real tree built and the tower ran to completion but
    # still ended up predicting "literal". A real corpus run found this
    # the single largest cause of false negatives once a tree exists at
    # all (56/150 ConMeC in one round), and it had no diagnosis at all
    # until now -- see empty_fiber_reason's own docstring for why this is
    # safe to aggregate.
    empty_fiber_reason_counts: Counter[str] = Counter()
    unrecognized_fingerprints: Counter[tuple[str, int]] = Counter()
    exit7_signal_counts: Counter[str] = Counter(
        {"has_comma": 0, "has_digit": 0, "has_apostrophe": 0}
    )
    exit7_rows_seen = 0
    exit4_tree_source_counts: Counter[str] = Counter()
    tree_source_counts: Counter[str] = Counter()
    decline_reason_counts: Counter[str] = Counter()
    llm_decline_reason_counts: Counter[str] = Counter()
    dep_status_counts: Counter[str] = Counter()
    # How many *independent* blockers a sentence actually carries at
    # once (0 = already builds, 1 = decline_reason_counts's own first-
    # blocker view already captures it fully, 2+ = the compounding
    # pattern several real rounds' growing decline_reason buckets only
    # ever suggested indirectly) -- keyed by len(row_all_decline_reasons(...)).
    blockers_per_sentence_histogram: Counter[int] = Counter()
    # Which pairs of reason codes co-occur in the same sentence most
    # often -- points at which TWO fixes together would actually free a
    # sentence, rather than just shifting it one blocker forward.
    co_occurring_blocker_pairs: Counter[str] = Counter()
    for gold in gold_rows:
        inference_row = inference_by_id.get(gold["id"])
        if inference_row is None:
            missing += 1
            continue
        tree_source_counts[row_tree_source(inference_row)] += 1
        decline_reason_counts[row_decline_reason(inference_row)] += 1
        llm_decline_reason_counts[row_llm_decline_reason(inference_row)] += 1
        dep_status_counts[row_dep_status(inference_row)] += 1
        all_reasons = row_all_decline_reasons(inference_row)
        blockers_per_sentence_histogram[len(all_reasons)] += 1
        for first, second in itertools.combinations(sorted(set(all_reasons)), 2):
            co_occurring_blocker_pairs[f"{first} + {second}"] += 1
        predicted = predict(inference_row)
        actual = gold["gold_label"]
        tree_available = row_tree_really_built(inference_row)
        if predicted == "metonymic" and actual == "metonymic":
            true_positive += 1
            if tree_available:
                tree_available_true_positive += 1
        elif predicted == "metonymic" and actual == "literal":
            false_positive += 1
            if tree_available:
                tree_available_false_positive += 1
        elif predicted == "literal" and actual == "literal":
            true_negative += 1
            if tree_available:
                tree_available_true_negative += 1
        else:
            false_negative += 1
            if tree_available:
                tree_available_false_negative += 1
        if predicted == "literal":
            reason = literal_reason(inference_row)
            literal_prediction_reasons[reason] += 1
            if reason == "ok:empty-fiber":
                empty_fiber_reason_counts[empty_fiber_reason(inference_row)] += 1
            if reason == "failed:exit1:unrecognized":
                fingerprint = fingerprint_failure_text(inference_row.get("failure", ""))
                unrecognized_fingerprints[
                    (fingerprint["sha256_prefix"], fingerprint["length"])
                ] += 1
            if inference_row.get("exit_code") == 7:
                exit7_rows_seen += 1
                signals = exit7_gf_sentence_signals(inference_row.get("failure", ""))
                if signals:
                    for name, present in signals.items():
                        if present:
                            exit7_signal_counts[name] += 1
            if inference_row.get("exit_code") == 4:
                exit4_tree_source_counts[
                    exit4_tree_source(inference_row.get("failure", ""))
                ] += 1

    precision, recall, f1 = _precision_recall_f1(
        true_positive, false_positive, true_negative, false_negative
    )
    (
        tree_available_precision,
        tree_available_recall,
        tree_available_f1,
    ) = _precision_recall_f1(
        tree_available_true_positive,
        tree_available_false_positive,
        tree_available_true_negative,
        tree_available_false_negative,
    )
    return {
        "instances": len(gold_rows),
        "missing_inference_rows": missing,
        "confusion": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "false_negative": false_negative,
        },
        "precision": precision,
        "recall": recall,
        "f1": f1,
        # The same detection metric, restricted to rows where a real
        # tree actually reached the contextual tower (row_tree_source in
        # {"stanza","llm","gf-parser"}) -- the number that answers "how
        # well does the formally-verified tower itself detect metonymy
        # on real corpus sentences", decoupled from "what fraction of
        # arbitrary real text our frontend can turn into a tree at all"
        # (that second, separate question is exactly what tree_source_
        # counts/decline_reason_counts/dep_status_counts below measure).
        "tree_available_instances": (
            tree_available_true_positive
            + tree_available_false_positive
            + tree_available_true_negative
            + tree_available_false_negative
        ),
        "tree_available_confusion": {
            "true_positive": tree_available_true_positive,
            "false_positive": tree_available_false_positive,
            "true_negative": tree_available_true_negative,
            "false_negative": tree_available_false_negative,
        },
        "tree_available_precision": tree_available_precision,
        "tree_available_recall": tree_available_recall,
        "tree_available_f1": tree_available_f1,
        "literal_prediction_reasons": dict(sorted(literal_prediction_reasons.items())),
        "empty_fiber_reason_counts": dict(sorted(empty_fiber_reason_counts.items())),
        "exit7_rows_seen": exit7_rows_seen,
        "exit7_signal_counts": dict(sorted(exit7_signal_counts.items())),
        "exit4_tree_source_counts": dict(sorted(exit4_tree_source_counts.items())),
        "tree_source_counts": dict(sorted(tree_source_counts.items())),
        "dep_status_counts": dict(sorted(dep_status_counts.items())),
        "decline_reason_counts": dict(sorted(decline_reason_counts.items())),
        "llm_decline_reason_counts": dict(sorted(llm_decline_reason_counts.items())),
        # JSON object keys are always strings -- len(...) counts are
        # stringified here rather than relying on json.dumps to do it
        # implicitly, so the report's own on-disk shape is explicit.
        "blockers_per_sentence_histogram": {
            str(count): occurrences
            for count, occurrences in sorted(blockers_per_sentence_histogram.items())
        },
        "co_occurring_blocker_pairs": dict(
            sorted(co_occurring_blocker_pairs.items(), key=lambda item: (-item[1], item[0]))
        ),
        "unrecognized_fingerprints": [
            {"sha256_prefix": prefix, "length": length, "count": count}
            for (prefix, length), count in sorted(
                unrecognized_fingerprints.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inference", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    gold_rows = list(jsonl(args.gold))
    if not gold_rows:
        raise SystemExit("gold file is empty")
    report = score(list(jsonl(args.inference)), gold_rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"f1": report["f1"], "instances": report["instances"]}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
