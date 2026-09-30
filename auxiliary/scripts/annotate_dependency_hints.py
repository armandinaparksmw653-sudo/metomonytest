#!/usr/bin/env python3
"""Offline UD dependency-parser preprocessing for the open-domain frontend.

Reads a corpus ``*.inputs.jsonl`` file (the same format consumed by
``scripts/evaluation/run_engine_predictions.py``) and emits one JSON object
per row describing, for the marked target occurrence, whether it is the
direct subject/object of a governing verb, a modifier nested inside a noun
phrase, or unresolved. This is a pure, untrusted proposal: the Haskell
engine's ``analyzeOpenAtWithDependencyHint`` (engine/src/Metonymy/OpenDomain.hs)
treats it exactly like every other candidate source, and the compiled Agda
``runtimeCheck`` independently re-derives admissibility regardless of how the
candidate was found. See docs/architecture.md for the trust boundary.

Output schema, one object per input row keyed by ``id``:

    {"id": ..., "dep_status": "direct-argument" | "copula-argument"
                              | "nested-modifier"
                              | "no-governing-verb:<reason>"
                              | "parse-error",
     "hole_role": "Subject" | "Object" | "",
     "governing_lemma": "<verb lemma>" | "<verb lemma> <preposition>"
                       | "<predicate noun lemma>" | "",
     "governing_start": <int or null>, "governing_end": <int or null>,
     "voice": "active" | "passive",
     "nested_modifier_deprel": "<UD deprel>" | "",
     "ud_words": [{"id": int, "head": int, "deprel": str, "upos": str,
                   "lemma": str, "text": str, "start_char": int,
                   "end_char": int}, ...] | null}

``ud_words`` is every UD word in the sentence containing the target span
(see ``serialize_sentence_words``), not just the one target word the
other fields classify -- feeds
scripts/build_gf_tree_from_dependencies.py's build_gf_tree, which
constructs a *whole* GF tree directly from the dependency graph instead
of asking GF's own parser to read raw text (see that module's own
docstring and docs/contextual-tower.md). ``null`` when the row's text
didn't parse at all (mirrors ``dep_status == "parse-error"``).

``hole_role``, ``governing_lemma``, ``governing_start`` and
``governing_end`` are non-empty/non-null only when ``dep_status`` is
``"direct-argument"`` or ``"copula-argument"``. ``governing_start``/
``governing_end`` are the governing word's own absolute character span
in the input text (covering the case-marking preposition too for a
reconstructed phrasal verb, or the passive auxiliary too for a passive
clause) -- needed by consumers that substitute a canonical verb form
back into the sentence (e.g. scripts/contextual_rule_compiler.py's
``resolve_action``, which builds a GF-parseable sentence this way); the
open-domain frontend consuming ``hole_role``/``governing_lemma`` alone
does not need them. For ``"copula-argument"`` specifically these three
fields mean something structurally different, since there is no verb at
all: ``governing_lemma`` is the *predicate noun's* own lemma ("county"
for "Waterloo is a county"), and ``governing_start``/``governing_end``
cover only the copula word itself ("is"/"was"/etc), not the whole
predicate NP -- see ``contextual_rule_compiler.py``'s
``_resolve_copula_predicate`` for how this is consumed.

``nested_modifier_deprel`` is non-empty only when
``dep_status == "nested-modifier"`` -- the specific closed-vocabulary UD
relation (one of ``NESTED_MODIFIER_DEPRELS`` below, e.g. ``"nmod:poss"``
for "Tolstoy's books") that made the target unresolvable, safe to
aggregate (a fixed relation label, never sentence text) so
scripts/evaluation/score_contextual_detection.py can report which
specific nested-modifier shape actually dominates instead of one
undifferentiated count.

``"no-governing-verb"`` (see ``classify_word``/``_no_governing_verb``)
always carries one of a closed-vocabulary set of ``:<reason>`` suffixes
for the same reason: ``:head-upos-<UPOS>`` (or ``:no-head``) when the
target's own deprel *was* one of the checked clause-argument relations
but its UD head wasn't a usable governor, or ``:no-case-word`` (an
oblique with a verbal head but no preposition attached at all), or
``:conj-chain-broken`` (a dangling "conj" chain, defensive only), or
``:target-deprel-<deprel>`` when the target's own deprel isn't in any
checked relation set to begin with (e.g. ``"xcomp"``, ``"ccomp"``,
``"advcl"`` -- a coordinated target, deprel ``"conj"``, is instead
classified against whichever role its first conjunct shares with it;
see ``classify_word``'s own ``"conj"`` branch). Added after a real
corpus run found this status the dominant cause behind
``build_gf_tree_decline_reason``'s own ``root-lemma-mismatch:no-
governing-start`` -- ``resolve_action`` falls back to its own
(unreliable) positional heuristic whenever ``dep_status`` isn't
``"direct-argument"``/``"copula-argument"``, and undifferentiated
``"no-governing-verb"`` was by far the largest such case; a follow-up
round found ``:target-deprel-conj`` alone was ~82% of what remained in
WiMCor after fixing the ``nmod:*``/``obl:*`` subtype gap, which is what
prompted resolving coordinated targets properly instead of leaving them
in the catch-all.

``voice`` is ``"passive"`` only for a passive subject (UD ``nsubj:pass``,
correctly reported as ``hole_role="Object"`` -- it is semantically the
patient, not the agent) or its "by"-agent phrase (reported as
``hole_role="Subject"``, the agent); ``"active"`` otherwise, including
every non-``direct-argument`` status, where it carries no meaning.

This module works on two input shapes: rows with an explicit
``target_span``/``target_spans`` (the open-domain corpus format, offsets
computed by scripts/evaluation/prepare_wimcor.py etc.) are validated
strictly against that exact span; rows with only a plain mention string
(e.g. the contextual-tower corpus format's ``source``/``target`` field,
no span) fall back to the first case-insensitive word-boundary match,
mirroring scripts/contextual_rule_compiler.py's own ``_mention_span``.

Sentences are parsed in batches (see ``annotate``/``--batch-size``), not one
``pipeline(text)`` call per row: Stanza's own documentation warns that
calling the pipeline once per short text is very slow on CPU, since each
call pays fixed per-call overhead instead of letting the neural processors
batch across many sentences at once. Pass a list of ``stanza.Document``
objects to the pipeline in one call to get that batching.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
    return rows

# Target occupies a clause-argument position directly.
SUBJECT_DEPRELS = {"nsubj", "csubj"}
# The passive subject is semantically the patient/theme -- the same
# ActionRole slot ("object_sort") a direct object occupies in the active
# voice, not the agent's ("subject_sort"). Handled separately from
# SUBJECT_DEPRELS so it is never silently treated as an agent.
PASSIVE_SUBJECT_DEPRELS = {"nsubj:pass", "csubj:pass"}
OBJECT_DEPRELS = {"obj", "iobj"}
OBLIQUE_DEPRELS = {"obl"}
GOVERNING_UPOS = {"VERB", "AUX"}

# Target is a modifier inside a noun phrase, not itself a clause argument
# (e.g. "Tolstoy" in "Tolstoy's books"). Deliberately left unresolved in
# this phase: promoting it correctly requires widening the checked
# construction vocabulary in engine/src/Metonymy/Elaborator.hs
# (PositiveGFTree), which is out of scope here. See the plan's "Дальше"
# section. classify_word also matches any colon-subtyped "nmod:*"
# variant (e.g. "nmod:unmarked") against this set's own bare "nmod"
# entry -- see that function's own check for why only "nmod" (and
# "obl", checked the same way against OBLIQUE_DEPRELS) get this
# treatment, not every member here.
NESTED_MODIFIER_DEPRELS = {
    "nmod",
    "nmod:poss",
    "amod",
    "appos",
    "compound",
    "acl",
    "acl:relcl",
    "nummod",
}

OPEN_DOMAIN_SOURCES = {"wimcor-v1.1", "conmec"}
DEFAULT_BATCH_SIZE = 500

Hint = dict[str, "str | int | None"]
ValidatedRow = tuple[str, int, int]


ClassifyResult = tuple[str, str, str, "int | None", "int | None", str, str]


def _passive_verb_span(sentence: Any, head: Any) -> tuple[int, int]:
    """Span of the full "was/is V-ed" chunk, aux included, for substitution.

    Falls back to the content verb's own span if no ``aux:pass`` child is
    found (defensive only -- a genuine passive clause always has one).
    """
    aux_children = [
        candidate
        for candidate in sentence.words
        if candidate.head == head.id and candidate.deprel == "aux:pass"
    ]
    if not aux_children:
        return head.parent.start_char, head.parent.end_char
    aux = aux_children[0]
    return (
        min(head.parent.start_char, aux.parent.start_char),
        max(head.parent.end_char, aux.parent.end_char),
    )


def _is_passive(sentence: Any, head: Any) -> bool:
    return any(
        candidate.head == head.id and candidate.deprel == "aux:pass"
        for candidate in sentence.words
    )


def _no_governing_verb(head: Any) -> ClassifyResult:
    """The shared "no-governing-verb" result for the four clause-argument
    deprel branches (SUBJECT_DEPRELS/PASSIVE_SUBJECT_DEPRELS/
    OBJECT_DEPRELS/OBLIQUE_DEPRELS) -- suffixed by the *head's* own UPOS
    (or "no-head" when there isn't one at all), a small closed
    vocabulary, safe to aggregate. A real corpus run found
    "no-governing-verb" (undifferentiated) the dominant cause behind
    root-lemma-mismatch:no-governing-start -- resolve_action falls back
    to its own positional heuristic whenever dep_status isn't
    "direct-argument"/"copula-argument", and "no-governing-verb" is by
    far the most common of the non-"direct-argument" statuses. This
    suffix (and the deprel-based one the catch-all branch below uses
    instead, since there ``head.upos`` isn't the discriminating fact --
    the target's own deprel not being in the checked vocabulary at all
    is) exists to tell apart which UD shape actually dominates before
    guessing which one to extend classify_word's own coverage for next.
    """
    suffix = "no-head" if head is None else f"head-upos-{head.upos}"
    return (f"no-governing-verb:{suffix}", "", "", None, None, "active", "")


def _first_conjunct(by_id: dict[int, Any], word: Any) -> Any | None:
    """Walk a UD "conj" chain up to the true first conjunct -- for
    "A, B, and C", UD may attach B and C both directly as "conj" of A,
    or chain C as "conj" of B; either shape resolves to A here (the
    first word whose own deprel is NOT itself "conj"). Mirrors
    build_gf_tree_from_dependencies.py's own _shared_subject_from_conjunct
    exactly, just for classify_word's different purpose below (classifying
    the *target* itself when it is a coordinated conjunct, not borrowing a
    governing verb's subject for tree-building). Returns None on a
    dangling "head" reference (defensive only -- a well-formed UD graph
    always terminates this walk).
    """
    current = word
    while current.deprel == "conj":
        head = by_id.get(current.head) if current.head else None
        if head is None:
            return None
        current = head
    return current


def classify_word(sentence: Any, word: Any) -> ClassifyResult:
    """Classify one target word given its UD parent sentence.

    ``sentence`` must expose ``.words`` (a list of word-like objects with
    ``.id``, ``.head``, ``.deprel``, ``.upos``, ``.lemma``, ``.text``, and a
    ``.parent`` exposing ``.start_char``/``.end_char``); ``word`` is the
    target word itself. Duck-typed so tests can pass plain stand-in objects
    instead of real Stanza objects.

    Returns ``(dep_status, hole_role, governing_lemma, governing_start,
    governing_end, voice, nested_modifier_deprel)``. ``governing_start``/
    ``governing_end`` are the governing word's own absolute character
    span -- covering the case-marking preposition too for a
    reconstructed phrasal verb, or the passive auxiliary too for a
    passive clause, or (for ``"copula-argument"``) just the copula word
    itself, with ``governing_lemma`` then being the *predicate noun's*
    lemma, not a verb at all -- or ``None`` when there is no governing
    verb to report. ``voice`` is ``"passive"`` only for a passive
    subject or its "by"-agent phrase; ``"active"`` otherwise (including
    every non-``direct-argument`` status, where it is unused).
    ``nested_modifier_deprel`` is the specific closed-vocabulary UD
    relation from ``NESTED_MODIFIER_DEPRELS`` that matched, non-empty
    only when ``dep_status == "nested-modifier"``.
    """
    by_id = {candidate.id: candidate for candidate in sentence.words}
    head = by_id.get(word.head) if word.head else None

    if word.deprel in SUBJECT_DEPRELS:
        if head is not None and head.upos in GOVERNING_UPOS:
            return (
                "direct-argument",
                "Subject",
                head.lemma,
                head.parent.start_char,
                head.parent.end_char,
                "active",
                "",
            )
        if head is not None and head.upos == "NOUN":
            # Copula ("Waterloo is a county") -- UD attaches nsubj to
            # the predicate NOUN, not the copula AUX, so the ordinary
            # GOVERNING_UPOS check above never fires for it; this is a
            # structurally different resolution path (see
            # contextual_rule_compiler.py's resolve_action -- there is
            # no VerbNet "action" for a copula at all, the predicate
            # noun's own lexical_sorts entry is the only evidence
            # source), so it gets its own dep_status rather than being
            # folded into "direct-argument". Deliberately scoped to a
            # NOUN predicate only -- grammar/Metonymy.gf has no AP
            # (adjective-predicate) category at all, so "Waterloo is
            # beautiful" is structurally unreachable regardless of this
            # classification, not worth reporting differently here.
            cop_children = [
                candidate
                for candidate in sentence.words
                if candidate.head == head.id and candidate.deprel == "cop"
            ]
            if len(cop_children) == 1:
                cop = cop_children[0]
                return (
                    "copula-argument",
                    "Subject",
                    head.lemma,
                    cop.parent.start_char,
                    cop.parent.end_char,
                    "active",
                    "",
                )
        return _no_governing_verb(head)

    if word.deprel in PASSIVE_SUBJECT_DEPRELS:
        if head is not None and head.upos in GOVERNING_UPOS:
            start, end = _passive_verb_span(sentence, head)
            return (
                "direct-argument", "Object", head.lemma, start, end, "passive", ""
            )
        return _no_governing_verb(head)

    if word.deprel in OBJECT_DEPRELS:
        if head is not None and head.upos in GOVERNING_UPOS:
            return (
                "direct-argument",
                "Object",
                head.lemma,
                head.parent.start_char,
                head.parent.end_char,
                "active",
                "",
            )
        return _no_governing_verb(head)

    if word.deprel in OBLIQUE_DEPRELS or word.deprel.startswith("obl:"):
        # UD English EWT emits several colon-subtyped "obl" relations
        # ("obl:agent", "obl:tmod", "obl:unmarked", ...) that carry the
        # exact same structural meaning as bare "obl" for this module's
        # purposes -- the real semantic work below (case-word lookup,
        # by-agent/_is_passive detection) already does the right thing
        # regardless of which subtype fired; a real corpus run found
        # these falling through to the undifferentiated catch-all
        # unrecognized, not even reaching this branch's own dedicated
        # "no-case-word" reason. Deliberately scoped to just "obl" (not
        # generalized to every deprel family) -- confirmed as the one
        # the data actually showed being missed, not guessed broader.
        if head is not None and head.upos in GOVERNING_UPOS:
            case_children = [
                candidate
                for candidate in sentence.words
                if candidate.head == word.id and candidate.deprel == "case"
            ]
            if case_children:
                case_word = case_children[0]
                if case_word.text.casefold() == "by" and _is_passive(sentence, head):
                    start, end = _passive_verb_span(sentence, head)
                    return (
                        "direct-argument",
                        "Subject",
                        head.lemma,
                        start,
                        end,
                        "passive",
                        "",
                    )
                lemma = f"{head.lemma} {case_word.text.lower()}"
                start = min(head.parent.start_char, case_word.parent.start_char)
                end = max(head.parent.end_char, case_word.parent.end_char)
                return ("direct-argument", "Object", lemma, start, end, "active", "")
            # A good VERB/AUX head, but no "case" (preposition) word at
            # all -- e.g. "obl:tmod" -- a genuinely different reason than
            # the head itself being wrong, so _no_governing_verb's own
            # head-upos suffix (which would misleadingly say "head-upos-
            # VERB" here, as if the head were the problem) doesn't apply.
            return ("no-governing-verb:no-case-word", "", "", None, None, "active", "")
        return _no_governing_verb(head)

    if word.deprel in NESTED_MODIFIER_DEPRELS or word.deprel.startswith("nmod:"):
        # Same colon-subtype broadening as OBLIQUE_DEPRELS above, scoped
        # just as narrowly -- a real corpus run found "nmod:unmarked"/
        # "nmod:desc" (among others "nmod:poss" already names explicitly)
        # falling through unrecognized, even though any "nmod:*" subtype
        # means the same "modifier nested inside an NP, not a clause
        # argument" thing this branch already declines for.
        return ("nested-modifier", "", "", None, None, "active", word.deprel)

    if word.deprel == "conj":
        # Target itself is a coordinated conjunct ("Napoleon and
        # Waterloo announced a treaty", target="Waterloo") -- UD's own
        # "conj" relation means coordinated elements share their first
        # conjunct's syntactic role, so classify against that shared
        # role (whatever it turns out to be -- direct-argument, nested-
        # modifier, another "no-governing-verb" case, ...) instead of
        # falling through to the undifferentiated catch-all below. A
        # real corpus run found this the single dominant cause of
        # "no-governing-verb" (27/33 in WiMCor, ~82% of what remained
        # after the nmod:*/obl:* subtype fix). Recursing into
        # classify_word on the resolved first conjunct can never loop
        # (that word's own deprel is, by _first_conjunct's own
        # construction, never itself "conj").
        first_conjunct = _first_conjunct(by_id, word)
        if first_conjunct is None:
            return ("no-governing-verb:conj-chain-broken", "", "", None, None, "active", "")
        return classify_word(sentence, first_conjunct)

    # The target's own deprel isn't in any checked vocabulary at all
    # (e.g. "xcomp", "ccomp", "advcl", "parataxis") -- unlike the four
    # clause-argument branches above, the head's own UPOS was never even
    # examined here, so the *target's* deprel is the discriminating
    # fact, not the head's.
    return (f"no-governing-verb:target-deprel-{word.deprel}", "", "", None, None, "active", "")


def _sentence_containing_span(
    document: Any, start: int, end: int
) -> tuple[Any, list[Any]] | None:
    """The (sentence, words_in_span) pair for the first sentence overlapping
    [start, end), or None if none does.

    Character offsets on Stanza ``Word``/``Token`` objects are absolute
    over the whole input text, so sentences can be scanned in order
    without renumbering. Shared by find_governing_structure (below) and
    find_sentence_ud_words, so both agree on exactly which sentence "the"
    target's sentence is.
    """
    for sentence in document.sentences:
        words_in_span = [
            word
            for word in sentence.words
            if word.parent.start_char is not None
            and word.parent.end_char is not None
            and word.parent.start_char < end
            and word.parent.end_char > start
        ]
        if words_in_span:
            return sentence, words_in_span
    return None


def find_governing_structure(
    document: Any, start: int, end: int
) -> ClassifyResult:
    """Locate the target span in a parsed document and classify it.

    ``.head`` indices are only valid within their own sentence, which is
    why classification happens once the owning sentence is found.
    """
    found = _sentence_containing_span(document, start, end)
    if found is None:
        return ("parse-error", "", "", None, None, "active", "")
    sentence, words_in_span = found
    span_ids = {word.id for word in words_in_span}
    roots = [
        word
        for word in words_in_span
        if word.head == 0 or word.head not in span_ids
    ]
    target_word = roots[-1] if roots else words_in_span[-1]
    return classify_word(sentence, target_word)


def serialize_sentence_words(sentence: Any) -> list[dict]:
    """Flat, JSON-safe serialization of every word in one UD sentence.

    Feeds scripts/build_gf_tree_from_dependencies.py's build_gf_tree,
    which needs the *whole* sentence's dependency graph (not just the
    one target word find_governing_structure classifies) to construct a
    complete GF tree. Every field here is either a small closed-
    vocabulary tag (deprel, upos) or already present, unredacted, in the
    corpus's own input text (lemma, text, character offsets) -- the same
    risk class already accepted for governing_lemma/nested_modifier_deprel
    above, just for every word instead of one.
    """
    return [
        {
            "id": word.id,
            "head": word.head,
            "deprel": word.deprel,
            "upos": word.upos,
            "lemma": word.lemma,
            "text": word.text,
            "start_char": word.parent.start_char,
            "end_char": word.parent.end_char,
        }
        for word in sentence.words
    ]


def find_sentence_ud_words(
    document: Any, start: int, end: int
) -> list[dict] | None:
    """serialize_sentence_words for the sentence containing [start, end),
    or None if no sentence does (mirrors find_governing_structure's own
    "parse-error" case, just returning None instead of a status string).
    """
    found = _sentence_containing_span(document, start, end)
    if found is None:
        return None
    sentence, _words_in_span = found
    return serialize_sentence_words(sentence)


def validate_row(
    row: dict, text_field: str = "text", target_field: str = "target"
) -> ValidatedRow | None:
    """Return ``(text, start, end)`` if the row's span is trustworthy.

    With an explicit ``target_span``/``target_spans``: mirrors
    OpenDomain.hs's ``validSpan`` check exactly -- never trust parser
    output against an offset that does not actually cover the target
    string in this exact text. Pure and parser-independent, so invalid
    rows are filtered out before anything is sent to Stanza.

    Without one (the contextual-tower corpus format, which only supplies a
    mention string): falls back to the first case-insensitive
    word-boundary match, mirroring
    scripts/contextual_rule_compiler.py's ``_mention_span``. The match
    itself is the source of truth here, so it is not re-checked against
    case-sensitive equality the way an explicit span is.
    """
    text = row.get(text_field)
    target = row.get(target_field)
    if not text or not target:
        return None
    span = row.get("target_span", row.get("target_spans", [None])[0])
    if span is not None:
        start, end = span
        if text[start:end] != target:
            return None
        return text, start, end
    match = re.search(rf"\b{re.escape(target)}\b", text, re.IGNORECASE)
    if match is None:
        return None
    return text, match.start(), match.end()


def annotate(
    pipeline_batch: Callable[[list[str]], list[Any]],
    rows: Iterable[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
    on_progress: Callable[[int, int], None] | None = None,
    text_field: str = "text",
    target_field: str = "target",
) -> Iterator[Hint]:
    """Annotate every row, parsing distinct sentence texts in batches.

    Several rows (different targets/categories) can share the same source
    sentence, and processing many short texts one at a time is very slow
    on CPU (see the module docstring), so this collects every distinct
    valid text once, parses them ``batch_size`` at a time via
    ``pipeline_batch``, and only then walks the rows to classify each
    target against its (already parsed) sentence.
    """
    rows = list(rows)
    validated: dict[str, ValidatedRow | None] = {
        row["id"]: validate_row(row, text_field, target_field) for row in rows
    }

    unique_texts: list[str] = []
    seen_texts: set[str] = set()
    for result in validated.values():
        if result is not None and result[0] not in seen_texts:
            seen_texts.add(result[0])
            unique_texts.append(result[0])

    documents: dict[str, Any] = {}
    total_batches = (len(unique_texts) + batch_size - 1) // batch_size or 1
    for batch_index, start_index in enumerate(
        range(0, len(unique_texts), batch_size), start=1
    ):
        chunk = unique_texts[start_index : start_index + batch_size]
        try:
            parsed = pipeline_batch(chunk)
        except Exception:  # noqa: BLE001 - a batch failure degrades to parse-error
            parsed = [None] * len(chunk)
        for text, document in zip(chunk, parsed):
            documents[text] = document
        if on_progress is not None:
            on_progress(batch_index, total_batches)

    for row in rows:
        result = validated[row["id"]]
        if result is None:
            yield {
                "id": row["id"],
                "dep_status": "parse-error",
                "hole_role": "",
                "governing_lemma": "",
                "governing_start": None,
                "governing_end": None,
                "voice": "active",
                "nested_modifier_deprel": "",
                "ud_words": None,
            }
            continue
        text, start, end = result
        document = documents.get(text)
        if document is None:
            status, hole_role, lemma, g_start, g_end, voice, nested_deprel = (
                "parse-error", "", "", None, None, "active", "",
            )
            ud_words = None
        else:
            try:
                status, hole_role, lemma, g_start, g_end, voice, nested_deprel = (
                    find_governing_structure(document, start, end)
                )
            except Exception:  # noqa: BLE001 - malformed parse -> parse-error
                status, hole_role, lemma, g_start, g_end, voice, nested_deprel = (
                    "parse-error", "", "", None, None, "active", "",
                )
            try:
                ud_words = find_sentence_ud_words(document, start, end)
            except Exception:  # noqa: BLE001 - malformed parse -> no tree-builder input
                ud_words = None
        yield {
            "id": row["id"],
            "dep_status": status,
            "hole_role": hole_role,
            "governing_lemma": lemma,
            "governing_start": g_start,
            "governing_end": g_end,
            "voice": voice,
            "nested_modifier_deprel": nested_deprel,
            "ud_words": ud_words,
        }


def build_pipeline() -> Callable[[list[str]], list[Any]]:
    """Build the pinned UD English-EWT pipeline as a batch-callable: pass a
    list of texts, get back a list of parsed ``stanza.Document`` objects in
    the same order (see scripts/bootstrap_dependency_frontend.sh and
    toolchain.lock.json's "stanza" entry for the exact pinned versions and
    model provenance).
    """
    import os

    import stanza

    model_dir = os.environ.get("STANZA_MODEL_DIR")
    kwargs: dict[str, Any] = {}
    if model_dir:
        kwargs["model_dir"] = model_dir
    nlp = stanza.Pipeline(
        lang="en",
        package="ewt",
        processors="tokenize,mwt,pos,lemma,depparse",
        verbose=False,
        **kwargs,
    )

    def run_batch(texts: list[str]) -> list[Any]:
        return nlp([stanza.Document([], text=text) for text in texts])

    return run_batch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="how many distinct sentences to parse per pipeline call "
        f"(default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--text-field",
        default="text",
        help="dataset field holding the full sentence text (default: text; "
        "the contextual-tower corpus format uses 'sentence')",
    )
    parser.add_argument(
        "--target-field",
        default="target",
        help="dataset field holding the marked mention (default: target; "
        "the contextual-tower corpus format uses 'source')",
    )
    parser.add_argument(
        "--no-source-filter",
        action="store_true",
        help="do not filter rows by source in "
        f"{sorted(OPEN_DOMAIN_SOURCES)!r} -- use for datasets without a "
        "matching 'source' field, e.g. the contextual-tower corpus format",
    )
    arguments = parser.parse_args()

    all_rows = read_jsonl(arguments.dataset)
    rows = (
        all_rows
        if arguments.no_source_filter
        else [row for row in all_rows if row.get("source") in OPEN_DOMAIN_SOURCES]
    )
    pipeline = build_pipeline()

    def report_progress(batch_index: int, total_batches: int) -> None:
        print(
            f"annotate_dependency_hints: parsed batch {batch_index}/{total_batches}",
            file=sys.stderr,
            flush=True,
        )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="utf-8") as handle:
        for hint in annotate(
            pipeline,
            rows,
            batch_size=arguments.batch_size,
            on_progress=report_progress,
            text_field=arguments.text_field,
            target_field=arguments.target_field,
        ):
            handle.write(json.dumps(hint, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
