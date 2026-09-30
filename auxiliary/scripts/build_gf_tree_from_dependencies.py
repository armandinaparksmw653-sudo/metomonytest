#!/usr/bin/env python3
"""Build a GF abstract-syntax tree directly from a UD dependency parse.

Phase 1+ of the "Stanza instead of GF-as-parser" transition (see
docs/contextual-tower.md's own section on this and the plan file this
session used). Today, run_automatic_contextual_pipeline.py asks GF's own
parser to turn a raw English sentence into a tree -- meaning every
sentence shape GF hasn't been hand-taught a grammar rule for fails with
gf-parse-empty, however semantically simple it is. This module instead
walks a UD dependency graph (already computed once, offline, by
annotate_dependency_hints.py -- the same tool resolve_action's own
dependency_hint already relies on) and constructs the *text* of a GF
tree directly, in the exact syntax grammar/Metonymy.gf's constructors
already define. compile_gf_constraints (contextual_rule_compiler.py)
consumes tree text with its own, GF-independent parse_gf_tree/ARITIES
walker -- so a hand-built tree in the same syntax is a drop-in
replacement for one GF's parser would have produced; nothing downstream
of it (the TSV-encoded constraints that actually reach the Haskell/Agda
formal core) changes shape at all. See run_automatic_contextual_pipeline.py
for where this plugs in: try this first, and only fall back to asking
GF's own parser to read the raw sentence when this returns None.

Every accept path here was verified directly against the local GF
toolchain (`gf.exe`'s own `l -lang=MetonymyEng`, not just read from
source) before being written into this module -- including one real,
previously undocumented finding: PossNP/DefCN/IndefCN/ModifyRelCN/
ModifyRelCNVP (grammar/Metonymy.gf) cannot actually be constructed at
all today -- Metonymy.gf declares no function that *produces* a bare CN
from scratch, only ones that *consume* one, confirmed by GF's own type
checker rejecting `DefCN (OpenIndefCN ...)` with "Couldn't match
expected type CN against inferred type NP". (A handful of existing pure-
Python tests in tests/evaluation/test_compile_gf_constraints_copula_
relative_genitive.py exercise PossNP/DefCN with exactly that ill-typed
shape -- they test compile_gf_constraints's own tree-walking code
against text no real GF parse could ever produce, the same false-
confidence trap as the ApposCommaPN/OpenPN2 story earlier this project's
history; not fixed here, out of scope for this module.) Consequently
this module never builds a possessive (UD "nmod:poss") -- doing so needs
a grammar/Metonymy.gf addition first (a CN-producing base function), not
just a tree-builder change.

Also deliberately not built here, each for its own reason (see the
plan file / docs/contextual-tower.md for the full writeup):
- A copula clause ("Waterloo is a county") is UD-structured with a NOUN
  (not VERB/AUX) as its own root, which annotate_dependency_hints.py's
  classify_word never classifies as "direct-argument" (its
  GOVERNING_UPOS check requires VERB/AUX) -- so resolve_action itself
  never resolves an action for it, and the whole pipeline never reaches
  this module for such a sentence in the first place. Fixing this needs
  a new dep_status/resolve_action branch, not a tree-builder change.
- A verb-level oblique PP adjunct ("announces X in Y", the "in Y" part)
  has no VP-level attachment point in grammar/Metonymy.gf at all --
  ModifyNP only attaches a PP to a specific NP, not to a VP. Folding it
  into the object NP anyway ("announces (X in Y)") would silently
  reinterpret which constituent the PP modifies -- exactly the "wrong
  but type-correct" failure mode this module exists to avoid, so it
  isn't attempted. The one narrow exception: a *fronted* date/time PP at
  the very start of a sentence (OnFrontedS/InFrontedS/FromFrontedS)
  *is* built (below) -- those constructors take the PP's own NP
  directly and hardcode the preposition, so there is no attachment
  ambiguity to resolve.
- Coordination (UD "conj"/"cc") is deferred pending a closer read of
  how compile_gf_constraints's first_node (a depth-first search for the
  first Compl/PassCompl) would attribute constraints when a tree has
  more than one -- a real subtlety a rushed implementation could get
  wrong silently, so it waits for its own dedicated round.
- Nested UD nmod (an NP modified by another NP/PP, "the museum in
  Kent") stays out of reach here for a different reason than the above:
  a target sitting inside one is rejected by resolve_action itself
  (dep_status == "nested-modifier") *before* this module would ever
  run, the same "Deliberately left unresolved" gap
  annotate_dependency_hints.py's own module docstring already names.

Every accept path tracks the set of word ids it has legitimately
consumed; if any word in the sentence is left over at the end (besides
punctuation, always silently ignored), the whole build declines
(returns None) rather than silently drop or misrepresent content -- the
same "only build when confident, otherwise fall back" contract Phase
1's original narrower version already used.

A real corpus evaluation run of Phase 1 (round 3 of this session's own
plan) measured *zero* successful uses of this module across 300 real
WiMCor/ConMeC rows (tree_source_counts: 100% "gf-parser") -- every
single row that reached tree-building fell all the way through to the
legacy path. To find out why without guessing, every ``_Bail`` here now
carries a closed-vocabulary reason code (see each raise site's own
comment), exposed via ``build_gf_tree_decline_reason`` -- a second,
diagnostics-only entry point run_automatic_contextual_pipeline.py calls
whenever ``build_gf_tree`` itself returns ``None``, purely to answer
that question with real data instead of another hypothesis.

``build_gf_tree_decline_reason`` only ever reports the *first* _Bail a
sentence hits, though -- several fix rounds later, real corpus data
showed decline_reason_counts buckets growing even as others shrank,
exactly what "a sentence that now passes an earlier check just hits a
different, still-unaddressed one" predicts, but unprovable from a
single reason per row. ``enumerate_gf_tree_blockers`` answers that
directly: on each _Bail it applies a small, safe "ablation" (delete
already-unbuildable content, or coerce one already-wrong field -- never
invent new structure) and retries, to find every blocker a sentence
would hit in turn, not just the first.
"""

from __future__ import annotations

from typing import Any, Callable

_PRONOUN_CONSTRUCTORS = {
    "he": "HePN",
    "she": "ShePN",
    "it": "ItPN",
    "they": "TheyPN",
}

_PROPER_NOUN_CONSTRUCTORS = {1: "OpenPN", 2: "OpenPN2", 3: "OpenPN3"}

_INDEFINITE_DETERMINERS = {"a", "an"}
_DEFINITE_DETERMINERS = {"the"}

# grammar/MetonymyEng.gf's own fixed preposition words for the fronted
# date/time clause constructors -- the one exception to this module's
# "no verb-level oblique PP" rule (see the module docstring for why).
_FRONTED_DATE_CONSTRUCTORS = {
    "on": "OnFrontedS",
    "in": "InFrontedS",
    "from": "FromFrontedS",
}

# The same 13 ModifyNP+PP constructors scripts/contextual_rule_compiler.py's
# own compile_gf_constraints already walks generically (its "pp_constructions"
# table, keyed the other way around -- constructor name to preposition) --
# used here for a *noun's own* "nmod"+"case" modifier ("the museum in Kent"),
# a different UD attachment point than the fronted-date family above (which
# is "obl"+"case" on the *verb*), but the same closed preposition vocabulary
# and the same already-compiled, already-verified grammar constructors.
_NMOD_PP_CONSTRUCTORS = {
    "in": "InPP",
    "about": "AboutPP",
    "with": "WithPP",
    "for": "ForPP",
    "on": "OnPP",
    "at": "AtPP",
    "from": "FromPP",
    "by": "ByPP",
    "over": "OverPP",
    "under": "UnderPP",
    "during": "DuringPP",
    "near": "NearPP",
    "of": "OfPP",
}


class _Bail(Exception):
    """Internal control-flow only: this narrow builder hit a UD shape it
    doesn't (yet, safely) model. Always caught at _build_gf_tree_inner's
    two callers (build_gf_tree/build_gf_tree_decline_reason) -- never
    leaks. Carries a closed-vocabulary ``reason`` code (see each raise
    site's own comment for what it means and why it's safe to aggregate
    -- always one of a small, fixed set of internal check names, never
    sentence text).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _quote(text: str) -> str:
    if '"' in text or "\\" in text:
        # Defensive only -- Stanza tokenizes a literal quote as its own
        # token, so a real word surface form realistically never
        # contains one.
        raise _Bail("unsafe-text")
    return f'"{text}"'


def _apply(constructor: str, *args: str) -> str:
    if not args:
        return constructor
    return f"({constructor} {' '.join(args)})"


def _strip_outer_parens(tree: str) -> str:
    """GF's own tree printer (and every hand-written tree elsewhere in
    this project) never parenthesizes the outermost expression, only
    nested ones -- _apply above parenthesizes unconditionally (simplest
    to get right when composing arbitrarily deep, always-nested
    subexpressions), so build_gf_tree strips exactly one such layer off
    its own final result before returning it.
    """
    if tree.startswith("(") and tree.endswith(")"):
        return tree[1:-1]
    return tree


def _children(words: list[dict[str, Any]], head_id: int) -> list[dict[str, Any]]:
    return [word for word in words if word["head"] == head_id]


def _children_with_deprel(
    words: list[dict[str, Any]], head_id: int, deprel: str
) -> list[dict[str, Any]]:
    return [word for word in _children(words, head_id) if word["deprel"] == deprel]


def _np_from_proper_noun(
    words: list[dict[str, Any]], head: dict[str, Any], accounted: set[int]
) -> str:
    chain = [head] + [
        word
        for word in words
        if word["head"] == head["id"]
        and word["deprel"] == "compound"
        and word["upos"] == "PROPN"
    ]
    chain.sort(key=lambda word: word["start_char"])
    constructor = _PROPER_NOUN_CONSTRUCTORS.get(len(chain))
    if constructor is None:
        # Either the compound chain is longer than OpenPN3's 3-token
        # limit, or (impossible in practice, since `head` is always
        # included) somehow empty.
        raise _Bail("proper-noun-chain-too-long")
    for word in chain:
        accounted.add(word["id"])
    return _apply(constructor, *(_quote(word["text"]) for word in chain))


def _np_from_common_noun(
    words: list[dict[str, Any]], noun: dict[str, Any], accounted: set[int]
) -> str:
    determiners = _children_with_deprel(words, noun["id"], "det")
    adjectives = _children_with_deprel(words, noun["id"], "amod")
    # Not confident enough to guess a shape (OpenIndefCN/OpenDefCN/
    # OpenAdjIndefCN/OpenAdjDefCN each take exactly one determiner-
    # implied article and at most one adjective) -- suffixed by which of
    # the three distinct causes fired (a real corpus run found this the
    # second-largest decline_reason bucket, with no way to tell whether
    # a bare noun with no article at all, 2+ determiners, or 2+
    # adjectives actually dominated).
    if len(determiners) == 0:
        raise _Bail("common-noun-determiner-or-adjective-count:zero-determiners")
    if len(determiners) > 1:
        raise _Bail("common-noun-determiner-or-adjective-count:multiple-determiners")
    if len(adjectives) > 1:
        raise _Bail("common-noun-determiner-or-adjective-count:multiple-adjectives")
    determiner = determiners[0]
    det_lemma = determiner["lemma"].casefold()
    if det_lemma in _DEFINITE_DETERMINERS:
        is_definite = True
    elif det_lemma in _INDEFINITE_DETERMINERS:
        is_definite = False
    else:
        # The determiner's own lemma -- a small closed vocabulary of
        # English function words (this/that/some/every/...), the same
        # safety class as governing_lemma elsewhere -- names exactly
        # which determiner to add support for next.
        raise _Bail(f"common-noun-unrecognized-determiner:{det_lemma}")
    accounted.add(determiner["id"])
    accounted.add(noun["id"])
    noun_text = _quote(noun["text"])
    if adjectives:
        accounted.add(adjectives[0]["id"])
        constructor = "OpenAdjDefCN" if is_definite else "OpenAdjIndefCN"
        adjective_text = _quote(adjectives[0]["text"])
        # OpenAdjDefCN/OpenAdjIndefCN's third argument (grammar/Metonymy.gf:
        # String -> String -> String -> NP, "plural") is never read by
        # its own linearization (only "singular" is used) nor by
        # compile_gf_constraints's _noun_lemma (only arguments[1]) -- see
        # each's own comment. Reusing the same surface text for it loses
        # nothing.
        return _apply(constructor, adjective_text, noun_text, noun_text)
    constructor = "OpenDefCN" if is_definite else "OpenIndefCN"
    return _apply(constructor, noun_text, noun_text)


def _np_base(
    words: list[dict[str, Any]],
    head: dict[str, Any],
    accounted: set[int],
) -> str:
    """The base NP shape for one head word (proper noun / pronoun /
    common noun), with no relative-clause attachment -- factored out of
    _np so a caller that already knows what to do with an attached
    "acl:relcl" itself (see _implicit_subject_relative_clause_np) can
    still reuse this same per-UPOS dispatch without _np's own automatic
    ModifyRelVP wrapping kicking in a second time.
    """
    if head["upos"] == "PROPN":
        return _np_from_proper_noun(words, head, accounted)
    if head["upos"] == "PRON":
        constructor = _PRONOUN_CONSTRUCTORS.get(head["lemma"].casefold())
        if constructor is None:
            raise _Bail("pronoun-unrecognized")
        accounted.add(head["id"])
        return _apply(constructor)
    if head["upos"] == "NOUN":
        return _np_from_common_noun(words, head, accounted)
    # Anything else this module doesn't build an NP from at all -- NUM,
    # ADJ used substantively, a bare DET, etc. -- suffixed by the head's
    # own UPOS to say which.
    raise _Bail(f"np-unsupported-upos:{head['upos']}")


def _np(
    words: list[dict[str, Any]],
    head: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    """Build one NP, including an attached relative clause or "nmod" PP
    modifier if present.

    Dispatches on the head word's own UPOS for the base NP shape via
    _np_base, then separately checks for a UD "acl:relcl" or "nmod"
    child of the *same* head -- either modifier can attach to any of
    those three NP shapes, so this check lives above the per-UPOS
    dispatch, not inside any one branch of it. Real corpus evaluation
    data found a trailing "nmod" ("the museum in Kent") a real share of
    what "leftover-words"/"embedded-leftover-words" were catching --
    scripts/contextual_rule_compiler.py's own compile_gf_constraints
    already walks any ModifyNP node generically (built for the fronted-
    date path), so this needed no changes there at all, only here.
    """
    base = _np_base(words, head, accounted)
    relative_clauses = _children_with_deprel(words, head["id"], "acl:relcl")
    nmods = _children_with_deprel(words, head["id"], "nmod")
    if relative_clauses and nmods:
        # Both a relative clause and an nmod PP on the same head -- not
        # confident which one actually matters (or how they'd compose),
        # so decline rather than guess, the same "only one shape at a
        # time" discipline relative-clause-count already applies.
        raise _Bail("nmod-and-relative-clause")
    if relative_clauses:
        if len(relative_clauses) != 1:
            raise _Bail("relative-clause-count")
        embedded_vp = _relative_clause_vp(
            words, relative_clauses[0], accounted, gf_function_by_lemma
        )
        return _apply("ModifyRelVP", base, embedded_vp)
    if nmods:
        if len(nmods) != 1:
            raise _Bail("nmod-count")
        nmod = nmods[0]
        case_children = _children_with_deprel(words, nmod["id"], "case")
        if len(case_children) != 1:
            raise _Bail("nmod-case-count")
        case_word = case_children[0]
        constructor = _NMOD_PP_CONSTRUCTORS.get(case_word["text"].casefold())
        if constructor is None:
            raise _Bail("nmod-preposition-unrecognized")
        # Recurses on a different word id each call (nmod's own id, not
        # head's) -- UD dependency graphs are acyclic, so this always
        # terminates; also lets the modifier NP have its own relcl/nmod
        # of its own ("the museum in the county of Kent").
        modifier_np = _np(words, nmod, accounted, gf_function_by_lemma)
        accounted.add(case_word["id"])
        return _apply("ModifyNP", base, _apply(constructor, modifier_np))
    return base


def _object_np(
    words: list[dict[str, Any]],
    verb_id: int,
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    objects = _children_with_deprel(words, verb_id, "obj") + _children_with_deprel(
        words, verb_id, "iobj"
    )
    if len(objects) == 0:
        # grammar/Metonymy.gf has no intransitive VP (Compl/PassCompl
        # both require an object NP) -- an object-less clause is out of
        # scope for the whole grammar today, not just this module.
        raise _Bail("object-count:zero")
    if len(objects) > 1:
        raise _Bail("object-count:multiple")
    return _np(words, objects[0], accounted, gf_function_by_lemma)


def _relative_clause_vp(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    """The VP for a relative clause's own embedded verb.

    UD's "acl:relcl" attaches the embedded verb directly to the noun it
    modifies; the relativized noun itself fills the embedded clause's
    subject slot implicitly (no separate "nsubj" word for it), so this
    only ever looks for the embedded verb's own object -- and, unlike
    the main clause, does not need a caller-resolved lemma: it looks
    itself up by the embedded verb's own UD lemma directly, since it is
    a genuinely different predicate from the main action (a faithful
    structural mapping, not a semantic reinterpretation -- see the
    module docstring for why that distinction is what rules out a
    general oblique-PP attachment but not this).
    """
    if verb["upos"] not in {"VERB", "AUX"}:
        raise _Bail("relative-clause-verb-not-verb")
    if _children_with_deprel(words, verb["id"], "nsubj") or _children_with_deprel(
        words, verb["id"], "nsubj:pass"
    ):
        # A relative clause with its own separate subject isn't "which
        # VERB OBJECT" (ModifyRelVP's only shape) -- out of scope.
        raise _Bail("relative-clause-has-own-subject")
    gf_function = gf_function_by_lemma.get(verb["lemma"].casefold())
    if gf_function is None:
        raise _Bail("relative-clause-verb-not-in-lexicon")
    object_np = _object_np(words, verb["id"], accounted, gf_function_by_lemma)
    accounted.add(verb["id"])
    return _apply("Compl", gf_function, object_np)


def _fronted_date_clause(
    words: list[dict[str, Any]], root: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], str] | None:
    """(oblique_word, case_word, constructor) for a fronted date/time
    oblique on the root verb, or None if there isn't one.

    Narrow by construction: the case word's own text must be exactly
    one of the three fixed prepositions grammar/MetonymyEng.gf's
    OnFrontedS/InFrontedS/FromFrontedS actually hardcode, and the whole
    oblique phrase must sit before the subject (a real fronted
    position), not merely exist somewhere in the sentence.
    """
    obliques = _children_with_deprel(words, root["id"], "obl")
    if len(obliques) != 1:
        return None
    oblique = obliques[0]
    case_children = _children_with_deprel(words, oblique["id"], "case")
    if len(case_children) != 1:
        return None
    case_word = case_children[0]
    constructor = _FRONTED_DATE_CONSTRUCTORS.get(case_word["text"].casefold())
    if constructor is None:
        return None
    subjects = _children_with_deprel(words, root["id"], "nsubj")
    if len(subjects) != 1 or oblique["start_char"] >= subjects[0]["start_char"]:
        return None
    return oblique, case_word, constructor


# grammar/MetonymyEng.gf's own fixed subordinating conjunctions -- each
# maps to a (fronted_constructor, trailing_constructor) pair
# ("Because EMBEDDED, MAIN" vs "MAIN, because EMBEDDED").
_SUBORDINATE_CLAUSE_CONSTRUCTORS = {
    "because": ("BecauseS", "SBecauseS"),
    "if": ("IfS", "SIfS"),
    "when": ("WhenS", "SWhenS"),
    "although": ("AlthoughS", "SAlthoughS"),
}


def _clause(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str:
    """"SubjectNP (Compl/PassCompl/PassCompl0 V2 [ObjectNP])" for any verb
    -- shared by the main action clause and any embedded clause
    (relative, fronted/trailing subordinate) this module builds, since
    each is structurally the same shape, just with a different governing
    verb.
    """
    gf_function = gf_function_by_lemma.get(verb["lemma"].casefold())
    if gf_function is None:
        raise _Bail("verb-not-in-lexicon")

    passive_subjects = _children_with_deprel(words, verb["id"], "nsubj:pass")
    if passive_subjects:
        aux_pass = _children_with_deprel(words, verb["id"], "aux:pass")
        if len(aux_pass) != 1:
            raise _Bail("passive-aux-count")
        agents = [
            oblique
            for oblique in _children_with_deprel(words, verb["id"], "obl")
            if any(
                case["text"].casefold() == "by"
                for case in _children_with_deprel(words, oblique["id"], "case")
            )
        ]
        if len(agents) > 1:
            # 2+ "by"-agents is a genuine ambiguity (which one is real?)
            # -- still declines, unlike the 0-agent case below.
            raise _Bail("passive-agent-count")
        subject_np = _np(words, passive_subjects[0], accounted, gf_function_by_lemma)
        accounted.add(aux_pass[0]["id"])
        accounted.add(verb["id"])
        if agents:
            agent_np = _np(words, agents[0], accounted, gf_function_by_lemma)
            for case in _children_with_deprel(words, agents[0]["id"], "case"):
                accounted.add(case["id"])
            return _apply("Pred", subject_np, _apply("PassCompl", gf_function, agent_np))
        # No "by"-agent at all ("Henry is announced") -- grammar/Metonymy.gf's
        # PassCompl0 (V2 -> VP, added alongside this) is a bare passive
        # with no agent slot, verified locally against gf.exe/pinned
        # gf-rgl before this round: `l -lang=MetonymyEng (Pred (OpenPN
        # "Henry") (PassCompl0 Announce))` -> "Henry is announced". A
        # real corpus run found this the dominant share of what used to
        # be a blanket "passive-agent-count" decline -- most real
        # passives simply never name an agent at all.
        return _apply("Pred", subject_np, _apply("PassCompl0", gf_function))

    subjects = _children_with_deprel(words, verb["id"], "nsubj")
    if len(subjects) != 1:
        # Suffixed with the clause-building verb's own UD deprel (a
        # small closed vocabulary -- "root" for the ordinary root-
        # anchored path, or whatever real relation attaches an embedded
        # governing verb to the rest of the sentence -- "conj", "xcomp",
        # "ccomp", etc. -- for the governing_start branch) so a future
        # real corpus run can tell which shape actually dominates,
        # rather than guessing again: an earlier guess here
        # (_implicit_subject_relative_clause_np, for "acl:relcl") had
        # zero measurable effect on real data, the exact kind of mistake
        # this suffix exists to prevent repeating blindly.
        raise _Bail(f"subject-count:{verb['deprel']}")
    subject_np = _np(words, subjects[0], accounted, gf_function_by_lemma)
    object_np = _object_np(words, verb["id"], accounted, gf_function_by_lemma)
    accounted.add(verb["id"])
    return _apply("Pred", subject_np, _apply("Compl", gf_function, object_np))


def _word_by_governing_start(
    words: list[dict[str, Any]], governing_start: int
) -> dict[str, Any] | None:
    """The ud_words entry annotate_dependency_hints.py's classify_word
    actually pointed resolve_action at, given its own "governing_start"
    hint field -- not always a direct start_char match: for a passive
    clause, classify_word's own _passive_verb_span anchors
    governing_start to min(content_verb.start, aux_pass.start), which in
    real English is almost always the auxiliary's own start_char ("was
    announced" -- "was" starts first), never the content verb _clause
    actually needs to build a clause around. Resolves through exactly
    that one hop -- an "aux:pass" word is never itself the governing verb,
    only ever a modifier of one. (No such hop is needed for the other
    multi-word case, an obl+case phrasal verb like "listen to": there,
    governing_start is min(verb.start, preposition.start), and in real
    English the preposition always follows the verb, so that minimum is
    already the verb's own start_char -- the same word-order guarantee
    resolve_action's own obl-fallback fix already relies on.)

    Returns None on zero or more-than-one start_char match (the latter
    possible if two sub-words share a parent multi-word token's span) --
    either way, the caller degrades to declining, never guessing.
    """
    candidates = [word for word in words if word["start_char"] == governing_start]
    if len(candidates) != 1:
        return None
    candidate = candidates[0]
    if candidate["deprel"] == "aux:pass":
        heads = [word for word in words if word["id"] == candidate["head"]]
        return heads[0] if len(heads) == 1 else None
    return candidate


def _subtree_ids(words: list[dict[str, Any]], root_id: int) -> set[int]:
    """root_id plus every word transitively dependent on it (walking
    "head" pointers via the existing _children helper) -- scopes the
    embedded-governing-verb branch's own "did we account for everything"
    check to just the local clause it actually represents, the same
    "represent everything faithfully or decline" discipline
    _build_gf_tree_inner's whole-sentence version already applies to the
    root-anchored branch, just scoped down to this one clause.
    """
    ids = {root_id}
    frontier = [root_id]
    while frontier:
        current = frontier.pop()
        for child in _children(words, current):
            if child["id"] not in ids:
                ids.add(child["id"])
                frontier.append(child["id"])
    return ids


def _leftover_reason(words: list[dict[str, Any]], leftover: set[int], prefix: str) -> str:
    """Suffixes ``prefix`` ("leftover-words"/"embedded-leftover-words")
    with the UD deprel of the earliest-starting (by start_char) leftover
    word -- not a full audit of everything left over, just enough to
    tell which kind of unaccounted content actually dominates real
    corpus data before guessing a fix, the same "first blocker"
    principle every other multi-cause _Bail site in this module already
    follows. Real UD deprels only (a small, closed vocabulary), never
    sentence text.
    """
    earliest = min(
        (word for word in words if word["id"] in leftover),
        key=lambda word: word["start_char"],
    )
    return f"{prefix}:{earliest['deprel']}"


def _implicit_subject_relative_clause_np(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
) -> str | None:
    """The subject NP for a governing verb that is itself a UD
    "acl:relcl" with no own "nsubj"/"nsubj:pass" -- the relativized noun
    implicitly fills its subject role ("the county which governs
    Prussia"; contrast _relative_clause_vp, which already handles this
    exact shape, but only when SOME OTHER clause's object attaches it as
    a ModifyRelVP modifier -- this handles the case where the metonymy
    target itself is the argument this verb governs).

    Returns None when ``verb`` isn't this shape at all (a different verb
    entirely -- a real root-anchored clause, or an embedded verb with its
    own explicit subject), so the caller can fall through to its own
    ordinary _clause handling. Deliberately does NOT reuse _np on the
    head noun (that would also re-attach ``verb`` a second time, as a
    ModifyRelVP wrapper around the very subject this function is
    building) -- uses _np_base instead, after confirming the head noun
    has no *other* relative clause attached that would otherwise be
    silently dropped.

    First tried as the leading hypothesis for the new "subject-count"
    bucket the governing_start branch introduced (12/150 WiMCor, 13/150
    ConMeC, the single largest of them) -- but a real corpus run measured
    ZERO effect from this fix alone: decline_reason_counts came back
    byte-identical, a real reversal (see docs/contextual-tower.md's own
    writeup). A follow-up round suffixed "subject-count" with the
    governing verb's own UD deprel and measured the real breakdown:
    "acl:relcl" (this function's own shape) turned out to be only a
    modest slice (1/150 WiMCor, 3/150 ConMeC) -- "conj" (coordination
    with a shared subject, see _shared_subject_from_conjunct) is the
    actual largest single share, with "advcl" and "xcomp" both
    significant too. This function stays (it is a real, correct shape,
    just not the dominant one guessed).
    """
    if verb["deprel"] != "acl:relcl":
        return None
    if _children_with_deprel(words, verb["id"], "nsubj") or _children_with_deprel(
        words, verb["id"], "nsubj:pass"
    ):
        return None
    heads = [word for word in words if word["id"] == verb["head"]]
    if len(heads) != 1:
        raise _Bail("governing-relcl-head-not-found")
    head_noun = heads[0]
    other_relative_clauses = [
        word
        for word in _children_with_deprel(words, head_noun["id"], "acl:relcl")
        if word["id"] != verb["id"]
    ]
    if other_relative_clauses:
        raise _Bail("governing-relcl-head-has-other-relative-clause")
    subject_np = _np_base(words, head_noun, accounted)
    accounted.add(head_noun["id"])
    return subject_np


def _shared_subject_from_conjunct(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str | None:
    """The subject NP for a governing verb that is itself a UD "conj"
    with no own "nsubj"/"nsubj:pass" -- English coordination shares the
    first conjunct's subject with every later one unless a later
    conjunct states its own ("Napoleon announced Henry and praised
    Waterloo" -- "praised" has no subject of its own; it is Napoleon's,
    the same subject "announced" already has). A real syntactic fact UD's
    own "conj" relation encodes, not a guess -- the same class of
    confidence as _implicit_subject_relative_clause_np's own relativized-
    noun-fills-the-subject-role reasoning, just for a different UD shape.

    Walks the "conj" chain up to whichever word is NOT itself a further
    "conj" (the true first conjunct -- for a 3+-way list, "A, B, and C",
    UD may attach both B and C as "conj" of A directly, or chain C as
    "conj" of B; either shape resolves to A here the same way).

    Returns None when ``verb`` isn't this shape (has its own subject, or
    isn't a "conj" at all), or when the first conjunct itself doesn't
    have exactly one plain "nsubj" -- a passive (or otherwise-shaped)
    first conjunct is a genuinely different, unexplored case, not
    guessed at here.

    Real corpus evaluation data (after suffixing "subject-count" with
    the governing verb's own deprel) found "conj" the single largest
    share of that bucket (6/150 WiMCor, 4/150 ConMeC) -- bigger than
    _implicit_subject_relative_clause_np's own "acl:relcl" share.
    """
    if verb["deprel"] != "conj":
        return None
    if _children_with_deprel(words, verb["id"], "nsubj") or _children_with_deprel(
        words, verb["id"], "nsubj:pass"
    ):
        return None
    current = verb
    while current["deprel"] == "conj":
        heads = [word for word in words if word["id"] == current["head"]]
        if len(heads) != 1:
            raise _Bail("governing-conj-head-not-found")
        current = heads[0]
    first_conjunct_subjects = _children_with_deprel(words, current["id"], "nsubj")
    if len(first_conjunct_subjects) != 1:
        return None
    subject_np = _np(words, first_conjunct_subjects[0], accounted, gf_function_by_lemma)
    for cc_word in _children_with_deprel(words, verb["id"], "cc"):
        # The coordinating conjunction itself ("and"/"or") -- wrapper
        # information (what signals this clause is coordinated at all),
        # not local-clause content, the same treatment the embedded
        # branch's own "mark" exclusion already gives "because"/"if"/
        # "when"/"although". Without this, embedded-leftover-words would
        # incorrectly fire on nearly every real coordinated sentence
        # (almost all of them spell out "and"/"or" explicitly) even
        # though the shared subject was found correctly -- caught by a
        # real fixture with an explicit "and" word, not by the first,
        # simpler test that happened to omit it.
        accounted.add(cc_word["id"])
    return subject_np


def _implicit_subject_np(
    words: list[dict[str, Any]],
    verb: dict[str, Any],
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
) -> str | None:
    """The subject NP for a governing verb with no own "nsubj"/
    "nsubj:pass" but still an unambiguous, structurally-determined
    subject elsewhere in the sentence -- tries each shape this module
    knows in turn (subject-relative acl:relcl, then conj-coordination
    sharing), returning None (the caller falls through to _clause's own
    literal-nsubj-only handling, which correctly declines) if none
    apply.
    """
    relative_clause_subject = _implicit_subject_relative_clause_np(
        words, verb, accounted
    )
    if relative_clause_subject is not None:
        return relative_clause_subject
    return _shared_subject_from_conjunct(words, verb, accounted, gf_function_by_lemma)


def _main_clause(
    words: list[dict[str, Any]],
    root: dict[str, Any],
    lemma: str,
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str:
    """The S built around the resolved action's own root verb -- active
    or passive, matching whichever UD shape is actually present.
    """
    if root["lemma"].casefold() != lemma.casefold():
        # The resolved action's own lemma must be this same root verb's
        # lemma -- guards against two distinct real causes: (a)
        # resolve_action's positional fallback (used whenever
        # dependency_hint's dep_status isn't "direct-argument") having
        # matched an entirely different word than UD's own root; (b),
        # confirmed as the more likely dominant real-corpus cause by
        # re-reading annotate_dependency_hints.py's own classify_word --
        # even on the "direct-argument" path, the target's *governing*
        # verb (whatever word it's syntactically attached to) is not
        # required to be the *sentence's own* root at all, e.g. a target
        # embedded inside a relative/subordinate clause of a more
        # complex real sentence. Either way, building a tree around the
        # wrong clause must never happen silently.
        #
        # Suffixed with whether dependency_hint's own "governing_start"
        # was even available for this call -- a real corpus run found
        # root-lemma-mismatch the single largest *terminal* blocker in
        # both corpora after enumerate_gf_tree_blockers shipped, and it
        # can fire for two structurally distinct reasons this suffix
        # tells apart: "no-governing-start" is exactly cause (a) above
        # (no UD grounding at all, pure positional guess); "governing-
        # start-is-root" is a *third*, previously unnamed case --
        # _build_gf_tree_inner's own governing_start branch resolved
        # successfully and found it equals this very root, yet the
        # lemmas still disagree (a genuine Stanza/resolve_action
        # lemmatization discrepancy, or an MWT edge case), never before
        # distinguished from cause (b), which the governing_start branch
        # already reports separately as "governing-lemma-mismatch".
        suffix = (
            "no-governing-start" if governing_start is None else "governing-start-is-root"
        )
        raise _Bail(f"root-lemma-mismatch:{suffix}")
    return _clause(words, root, accounted, gf_function_by_lemma)


def _subordinate_clause(
    words: list[dict[str, Any]], root: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], str, str] | None:
    """(embedded_verb, mark_word, fronted_constructor, trailing_constructor)
    for a UD "advcl"+"mark" subordinate clause attached to the root verb,
    or None if there isn't exactly one recognizable one.

    UD attaches the embedded clause's own verb to the main verb via
    "advcl", with the subordinating word itself ("because"/"if"/"when"/
    "although") as that embedded verb's own "mark" child -- whichever of
    grammar/MetonymyEng.gf's four fixed subordinators it actually is.
    """
    advcls = _children_with_deprel(words, root["id"], "advcl")
    if len(advcls) != 1:
        return None
    embedded_verb = advcls[0]
    if embedded_verb["upos"] not in {"VERB", "AUX"}:
        return None
    marks = _children_with_deprel(words, embedded_verb["id"], "mark")
    if len(marks) != 1:
        return None
    mark = marks[0]
    pair = _SUBORDINATE_CLAUSE_CONSTRUCTORS.get(mark["text"].casefold())
    if pair is None:
        return None
    return embedded_verb, mark, pair[0], pair[1]


def _copula_clause(
    words: list[dict[str, Any]],
    root: dict[str, Any],
    lemma: str,
    accounted: set[int],
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str:
    """"SubjectNP (PredCopNP) PredicateNP" for a copula clause ("Waterloo
    is a county") -- the sentence's UD root is the predicate NOUN itself
    (not a verb at all; classify_word never classifies this case as
    "direct-argument", see annotate_dependency_hints.py's own "cop"-child
    check), with the copula word ("is"/"was"/...) attached to it via UD
    "cop". grammar/Metonymy.gf's PredCopNP : NP -> NP -> S already
    existed before this module ever produced one -- both NPs reuse _np
    (not _np_base), so a copula predicate/subject with its own nmod/
    relative-clause modifier is fully supported for free, the same way
    _clause's own subject/object already are.

    gf_function_by_lemma is unused here (a copula has no V2 to look up)
    -- kept in the signature only so this matches _clause's own call
    shape, in case a future round needs it (e.g. a modifier on the
    predicate/subject NP that itself requires a verb lookup).
    """
    if root["lemma"].casefold() != lemma.casefold():
        # Same "no-governing-start" half of _main_clause's own suffix
        # vocabulary -- but this branch is dispatched *before*
        # _build_gf_tree_inner's own governing_start-resolution code
        # ever runs (the copula check short-circuits ahead of it), so
        # there is no verified "resolves to this same root" fact to
        # report the way _main_clause's "governing-start-is-root" can --
        # only ever "the hint carried one at all" or not.
        suffix = "no-governing-start" if governing_start is None else "governing-start-present"
        raise _Bail(f"root-lemma-mismatch:{suffix}")
    subjects = _children_with_deprel(words, root["id"], "nsubj")
    if len(subjects) != 1:
        raise _Bail(f"subject-count:{root['deprel']}")
    cop_children = _children_with_deprel(words, root["id"], "cop")
    if len(cop_children) != 1:
        raise _Bail("copula-count")
    subject_np = _np(words, subjects[0], accounted, gf_function_by_lemma)
    predicate_np = _np(words, root, accounted, gf_function_by_lemma)
    accounted.add(cop_children[0]["id"])
    return _apply("PredCopNP", subject_np, predicate_np)


def _build_gf_tree_inner(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str:
    """The single implementation build_gf_tree and
    build_gf_tree_decline_reason both delegate to -- returns tree text
    (parens-stripped) on success, always raises _Bail (never returns
    None) on any unhandled UD shape, so a caller can choose whether it
    wants the resulting tree or the reason for its absence.

    ``governing_start`` is annotate_dependency_hints.py's own
    dependency_hint field of the same name -- the char offset of the
    word resolve_action actually resolved the target's role against.
    When it names a word other than the sentence's own UD root (a real
    corpus run found this dominates real-world failures: the target's
    governing verb is very often embedded in a relative/subordinate/
    complement clause of a more complex sentence, not the sentence's own
    root), this builds ONLY that local clause -- reusing the exact same
    _clause/_np/_object_np/_relative_clause_vp machinery the root-
    anchored path below already uses, since it is structurally the same
    shape, just a different governing verb -- and deliberately does not
    attempt to represent whatever wraps it (no fronted-date/subordinate-
    clause enrichment, no attaching it as a relative-clause modifier of
    some outer NP). This is safe, not merely convenient: compile_gf_
    constraints's own tree-walkers (first_node's depth-first Compl/
    PassCompl search, and walk's separate OpenAdjDefCN/OpenAdjIndefCN
    scan for FrameModifier/FrameComposition) only ever derive constraints
    from whatever tree they are actually given -- never anything "outside"
    it -- so omitting the wrapper can only under-generate constraints,
    never derive a wrong one, the same risk class already accepted for
    this module's other deliberately-unbuilt shapes (see the module
    docstring's verb-level-oblique-PP paragraph). When ``governing_start``
    is None (the caller has no such hint -- resolve_action fell back to
    its own positional heuristic) or it resolves to the sentence's own
    root, this is byte-for-byte today's existing root-anchored behavior.
    """
    roots = [word for word in words if word["deprel"] == "root"]
    if len(roots) != 1:
        raise _Bail("root-count")
    root = roots[0]
    if root["upos"] not in {"VERB", "AUX"}:
        if root["upos"] == "NOUN" and _children_with_deprel(words, root["id"], "cop"):
            # Copula ("Waterloo is a county") -- the sentence's own root
            # is the predicate NOUN, never VERB/AUX, so this must be
            # checked before the unconditional root-not-verb bail below,
            # not folded into the governing_start branch (copula-
            # argument's own dependency_hint carries a governing_start,
            # but nothing here actually needs it -- see _copula_clause's
            # own docstring). Deliberately not hooked into fronted-date/
            # subordinate-clause dispatch this round; a fronted-date
            # copula sentence still safely declines via leftover-words.
            accounted: set[int] = set()
            tree = _copula_clause(
                words, root, lemma, accounted, gf_function_by_lemma,
                governing_start=governing_start,
            )
            leftover = {
                word["id"] for word in words if word["deprel"] != "punct"
            } - accounted
            if leftover:
                raise _Bail(_leftover_reason(words, leftover, "leftover-words"))
            return _strip_outer_parens(tree)
        raise _Bail(f"root-not-verb:{root['upos']}")

    if governing_start is not None:
        governing_word = _word_by_governing_start(words, governing_start)
        if governing_word is None:
            raise _Bail("governing-start-not-found")
        if governing_word["upos"] not in {"VERB", "AUX"}:
            raise _Bail("governing-word-not-verb")
        if governing_word["id"] != root["id"]:
            if governing_word["lemma"].casefold() != lemma.casefold():
                raise _Bail("governing-lemma-mismatch")
            accounted = set()
            implicit_subject_np = _implicit_subject_np(
                words, governing_word, accounted, gf_function_by_lemma
            )
            if implicit_subject_np is not None:
                # The governing verb has no own "nsubj"/"nsubj:pass" but
                # an unambiguous, structurally-determined subject
                # elsewhere in the sentence -- a subject-relative
                # acl:relcl ("the county which governs Prussia", the
                # relativized head noun) or a conj-coordination sharing
                # the first conjunct's own subject ("announced Henry and
                # praised Waterloo"). A bare _clause call has no notion
                # of either at all, only ever looks for a literal
                # "nsubj" child -- see _implicit_subject_np's own
                # docstring for which of these two actually dominates
                # real corpus data.
                gf_function = gf_function_by_lemma.get(lemma.casefold())
                if gf_function is None:
                    raise _Bail("verb-not-in-lexicon")
                object_np = _object_np(
                    words, governing_word["id"], accounted, gf_function_by_lemma
                )
                accounted.add(governing_word["id"])
                tree = _apply(
                    "Pred", implicit_subject_np, _apply("Compl", gf_function, object_np)
                )
            else:
                tree = _clause(words, governing_word, accounted, gf_function_by_lemma)
            for mark_word in _children_with_deprel(words, governing_word["id"], "mark"):
                # Wrapper information (the word that signals this clause
                # is itself embedded, e.g. "because") -- not local-clause
                # content, so it is explicitly excluded from the
                # completeness check below rather than left to trip
                # "embedded-leftover-words", the same technique the
                # existing subordinate-clause branch already uses for its
                # own "mark" word once it picks a Because/If/When/
                # Although constructor to account for it; here there is
                # no such wrapper constructor, so this is the only place
                # that ever accounts for it.
                accounted.add(mark_word["id"])
            subtree_ids = _subtree_ids(words, governing_word["id"])
            leftover = {
                word["id"]
                for word in words
                if word["id"] in subtree_ids and word["deprel"] != "punct"
            } - accounted
            if leftover:
                raise _Bail(_leftover_reason(words, leftover, "embedded-leftover-words"))
            return _strip_outer_parens(tree)

    accounted: set[int] = set()
    fronted_date = _fronted_date_clause(words, root)
    subordinate = _subordinate_clause(words, root) if fronted_date is None else None
    if fronted_date is not None:
        oblique, case_word, constructor = fronted_date
        date_np = _np(words, oblique, accounted, gf_function_by_lemma)
        accounted.add(case_word["id"])
        main = _main_clause(
            words, root, lemma, accounted, gf_function_by_lemma,
            governing_start=governing_start,
        )
        tree = _apply(constructor, date_np, main)
    elif subordinate is not None:
        embedded_verb, mark, fronted_name, trailing_name = subordinate
        main_subjects = _children_with_deprel(words, root["id"], "nsubj")
        if len(main_subjects) != 1:
            # root["deprel"] is always "root" here (see the module-level
            # root lookup above) -- suffixed only for a uniform
            # "subject-count:<deprel>" vocabulary alongside _clause's own
            # same-named check, not because this particular site can
            # vary.
            raise _Bail(f"subject-count:{root['deprel']}")
        is_fronted = embedded_verb["start_char"] < main_subjects[0]["start_char"]
        embedded = _clause(words, embedded_verb, accounted, gf_function_by_lemma)
        accounted.add(mark["id"])
        main = _main_clause(
            words, root, lemma, accounted, gf_function_by_lemma,
            governing_start=governing_start,
        )
        tree = (
            _apply(fronted_name, embedded, main)
            if is_fronted
            else _apply(trailing_name, main, embedded)
        )
    else:
        tree = _main_clause(
            words, root, lemma, accounted, gf_function_by_lemma,
            governing_start=governing_start,
        )
    leftover = {word["id"] for word in words if word["deprel"] != "punct"} - accounted
    if leftover:
        raise _Bail(_leftover_reason(words, leftover, "leftover-words"))
    return _strip_outer_parens(tree)


def build_gf_tree(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str | None:
    """Build GF tree text for one sentence, or None if it can't (yet).

    ``words`` is a flat list of UD word dicts -- the same shape
    annotate_dependency_hints.py's "ud_words" hint field carries --
    each with "id", "head" (0 for the root), "deprel", "upos", "lemma",
    "text", "start_char", "end_char". ``lemma`` is the already-resolved
    action lemma (resolve_action/propose_contextual_scenario.py's
    "action" field) -- reused as-is, never recomputed here; this module
    only places it into a tree. ``gf_function_by_lemma`` is a
    lemma -> "CTX_<hash>" reverse lookup built from
    data/contextual-gf-actions.json (see load_gf_function_by_lemma).
    ``governing_start`` is optional -- see _build_gf_tree_inner's own
    docstring for what it does when given; omitting it (the default)
    is byte-for-byte today's pre-existing root-anchored-only behavior.
    """
    try:
        return _build_gf_tree_inner(
            words, lemma, gf_function_by_lemma, governing_start
        )
    except _Bail:
        return None


def build_gf_tree_decline_reason(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
) -> str:
    """Empty string if build_gf_tree would succeed on the same input,
    else a closed-vocabulary reason code for why it declines (see each
    _Bail call site's own comment for the full vocabulary and what each
    one means) -- diagnostics only, reruns the exact same logic rather
    than being called from inside build_gf_tree, so the normal success
    path never pays for it. Every reason code names one of this
    module's own internal structural checks, never sentence text.
    """
    try:
        _build_gf_tree_inner(words, lemma, gf_function_by_lemma, governing_start)
        return ""
    except _Bail as bail:
        return bail.reason


def _group_children_by_head(
    words: list[dict[str, Any]], deprels: set[str]
) -> dict[int, list[dict[str, Any]]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for word in words:
        if word["deprel"] in deprels:
            groups.setdefault(word["head"], []).append(word)
    return groups


def _keep_earliest_per_group(
    words: list[dict[str, Any]], groups: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]] | None:
    """For every head with 2+ candidates, delete every candidate's own
    subtree except the earliest by ``start_char`` -- the shared
    "multiplicity" ablation enumerate_gf_tree_blockers uses for every
    "N != 1" _Bail this module raises (subject-count, object-count,
    nmod-count, ...). Returns None (a no-op) when no head actually had
    2+ candidates -- the caller reads that as "this _Bail wasn't a
    multiplicity problem after all" (e.g. the real count was 0, not 2+)
    and treats the reason as terminal rather than looping forever on an
    ablation that changes nothing.

    Safe by construction for enumerate_gf_tree_blockers's purposes: the
    candidates passed in are always *dependents* of some clause verb
    (nsubj/obj/nmod/relcl/cop/aux:pass/by-agent children), never a verb
    itself, so this can never delete the word a later
    _word_by_governing_start lookup depends on.
    """
    to_delete: set[int] = set()
    changed = False
    for candidates in groups.values():
        if len(candidates) < 2:
            continue
        changed = True
        for extra in sorted(candidates, key=lambda word: word["start_char"])[1:]:
            to_delete |= _subtree_ids(words, extra["id"])
    if not changed:
        return None
    return [word for word in words if word["id"] not in to_delete]


def _ablate_passive_agent_count(words: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    groups: dict[int, list[dict[str, Any]]] = {}
    for word in words:
        if word["deprel"] != "obl":
            continue
        if any(
            case["text"].casefold() == "by"
            for case in _children_with_deprel(words, word["id"], "case")
        ):
            groups.setdefault(word["head"], []).append(word)
    return _keep_earliest_per_group(words, groups)


def _ablate_nmod_preposition_unrecognized(
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    to_delete: set[int] = set()
    for word in words:
        if word["deprel"] != "nmod":
            continue
        case_children = _children_with_deprel(words, word["id"], "case")
        if len(case_children) != 1:
            continue
        if case_children[0]["text"].casefold() not in _NMOD_PP_CONSTRUCTORS:
            to_delete |= _subtree_ids(words, word["id"])
    if not to_delete:
        return None
    return [word for word in words if word["id"] not in to_delete]


def _ablate_nmod_and_relative_clause(
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Drops the nmod (keeps the relative clause) wherever a head has
    both -- an arbitrary but deterministic tie-break; this diagnostic
    only needs forward progress, never the "right" choice, since the
    resulting tree is never used for anything but counting the next
    reason code.
    """
    to_delete: set[int] = set()
    for word in words:
        if word["deprel"] != "nmod":
            continue
        if _children_with_deprel(words, word["head"], "acl:relcl"):
            to_delete |= _subtree_ids(words, word["id"])
    if not to_delete:
        return None
    return [word for word in words if word["id"] not in to_delete]


def _ablate_proper_noun_chain_too_long(
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    to_delete: set[int] = set()
    for word in words:
        if word["upos"] != "PROPN" or word["deprel"] == "compound":
            continue
        chain = [word] + [
            child
            for child in _children(words, word["id"])
            if child["deprel"] == "compound" and child["upos"] == "PROPN"
        ]
        if len(chain) <= 3:
            continue
        # Real English compound-noun order puts the head *last*
        # (start_char-wise) -- "Royal Shipley School", not "School
        # Royal Shipley" -- the same ordering _np_from_proper_noun's
        # own chain.sort already relies on. Drop the earliest-starting
        # modifiers, keeping the head plus its nearest two, never the
        # head itself (chain[0] is always `word`, the actual obj/
        # nsubj/etc. head this ablation must not delete).
        chain.sort(key=lambda w: w["start_char"])
        for extra in chain[:-3]:
            to_delete |= _subtree_ids(words, extra["id"])
    if not to_delete:
        return None
    return [word for word in words if word["id"] not in to_delete]


def _ablate_pronoun_unrecognized(
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    changed = False
    new_words = []
    for word in words:
        if word["upos"] == "PRON" and word["lemma"].casefold() not in _PRONOUN_CONSTRUCTORS:
            word = dict(word)
            word["lemma"] = "he"
            changed = True
        new_words.append(word)
    return new_words if changed else None


def _ablate_common_noun_unrecognized_determiner(
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    recognized = _DEFINITE_DETERMINERS | _INDEFINITE_DETERMINERS
    changed = False
    new_words = []
    for word in words:
        if word["deprel"] == "det" and word["lemma"].casefold() not in recognized:
            word = dict(word)
            word["lemma"] = "the"
            changed = True
        new_words.append(word)
    return new_words if changed else None


def _ablate_common_noun_determiner_or_adjective_count(
    words: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Only handles the "2+ determiners" and "2+ adjectives" sub-cases
    (dedupe each independently, chaining the second dedupe onto the
    first's own result) -- the "0 determiners" sub-case stays terminal
    on purpose: there is no existing word to keep, and inventing one
    out of thin air is a different, riskier kind of ablation this round
    deliberately does not attempt (see the plan file).
    """
    det_result = _keep_earliest_per_group(words, _group_children_by_head(words, {"det"}))
    working = det_result if det_result is not None else words
    amod_result = _keep_earliest_per_group(working, _group_children_by_head(working, {"amod"}))
    if amod_result is not None:
        return amod_result
    return det_result


def _ablate_lexicon_gap(
    words: list[dict[str, Any]], gf_function_by_lemma: dict[str, str], lemma: str
) -> dict[str, str] | None:
    """Injects a placeholder GF-function entry for whichever lemma
    _clause's own lexicon lookup actually missed -- the main clause's
    own governing lemma (always exactly ``lemma``, the same identity
    root-lemma-mismatch/governing-lemma-mismatch already verify) and/or
    any acl:relcl embedded verb's lemma (_relative_clause_vp's own,
    separate lookup). The placeholder function name is never checked
    against grammar/Metonymy.gf or fed to compile_gf_constraints for
    real -- this ablated tree is only ever used to find the *next*
    reason code, never trusted.
    """
    changed = False
    new_lexicon = dict(gf_function_by_lemma)
    if lemma.casefold() not in new_lexicon:
        new_lexicon[lemma.casefold()] = "CTX_DIAGNOSTIC_PLACEHOLDER"
        changed = True
    for word in words:
        if word["deprel"] == "acl:relcl" and word["upos"] in {"VERB", "AUX"}:
            relcl_lemma = word["lemma"].casefold()
            if relcl_lemma not in new_lexicon:
                new_lexicon[relcl_lemma] = "CTX_DIAGNOSTIC_PLACEHOLDER"
                changed = True
    return new_lexicon if changed else None


# Reason code (the part before any ":" suffix) -> ablation over `words`.
# Every entry here is a "multiplicity" or "unrecognized vocabulary"
# check whose failure can be safely neutralized without inventing new
# structure -- see the plan file's own table for the full rationale.
# Any reason code NOT in this dict (root-count, root-not-verb,
# leftover-words, ...) is treated as terminal by enumerate_gf_tree_
# blockers: a real, not-yet-diagnosable-further limitation, honestly
# reported rather than guessed past.
_GROUP_ABLATIONS: dict[str, Callable[[list[dict[str, Any]]], list[dict[str, Any]] | None]] = {
    "subject-count": lambda words: _keep_earliest_per_group(
        words, _group_children_by_head(words, {"nsubj"})
    ),
    "object-count": lambda words: _keep_earliest_per_group(
        words, _group_children_by_head(words, {"obj", "iobj"})
    ),
    "passive-agent-count": _ablate_passive_agent_count,
    "passive-aux-count": lambda words: _keep_earliest_per_group(
        words, _group_children_by_head(words, {"aux:pass"})
    ),
    "nmod-count": lambda words: _keep_earliest_per_group(
        words, _group_children_by_head(words, {"nmod"})
    ),
    "nmod-case-count": lambda words: _keep_earliest_per_group(
        words, _group_children_by_head(words, {"case"})
    ),
    "relative-clause-count": lambda words: _keep_earliest_per_group(
        words, _group_children_by_head(words, {"acl:relcl"})
    ),
    "copula-count": lambda words: _keep_earliest_per_group(
        words, _group_children_by_head(words, {"cop"})
    ),
    "nmod-preposition-unrecognized": _ablate_nmod_preposition_unrecognized,
    "nmod-and-relative-clause": _ablate_nmod_and_relative_clause,
    "proper-noun-chain-too-long": _ablate_proper_noun_chain_too_long,
    "pronoun-unrecognized": _ablate_pronoun_unrecognized,
    "common-noun-unrecognized-determiner": _ablate_common_noun_unrecognized_determiner,
    "common-noun-determiner-or-adjective-count": _ablate_common_noun_determiner_or_adjective_count,
}

_LEXICON_ABLATION_REASONS = {"verb-not-in-lexicon", "relative-clause-verb-not-in-lexicon"}


def enumerate_gf_tree_blockers(
    words: list[dict[str, Any]],
    lemma: str,
    gf_function_by_lemma: dict[str, str],
    governing_start: int | None = None,
    max_iterations: int = 12,
) -> list[str]:
    """Every _Bail reason this sentence would hit, in order -- not just
    the first one build_gf_tree/build_gf_tree_decline_reason report.

    A real corpus run after this module's third feature batch (nmod/
    agentless-passive/copula) found several decline_reason buckets grow
    even as others shrank -- exactly what "a sentence now passes an
    earlier check only to hit a different, still-unaddressed one"
    predicts, but decline_reason_counts alone can never confirm it:
    _build_gf_tree_inner raises _Bail (and therefore returns) on the
    very first unmet check. This answers that directly: on each _Bail,
    it applies a small, safe "ablation" (see _GROUP_ABLATIONS/
    _ablate_lexicon_gap) that only ever deletes already-unbuildable
    content or coerces one already-wrong field, never invents new
    structure, and retries the exact same _build_gf_tree_inner (never
    modified itself) to see what the *next* independent blocker is.

    Returns [] when build_gf_tree would already succeed (no blockers at
    all). Stops and returns the reasons collected so far as soon as a
    reason has no known ablation, or its ablation is a no-op (the
    _Bail's real cause wasn't the kind of "multiplicity"/"unrecognized
    vocabulary" problem this diagnostic can safely see past) -- that
    last entry is honestly terminal, not a guess. Never raises: any
    reason code outside the closed vocabulary this module itself
    defines simply stops the search, and max_iterations is a defensive
    cap (each successful ablation strictly shrinks the word list, drops
    a lexicon gap, or coerces a field, so runaway looping isn't expected
    in practice).

    The ablated words/lexicon are purely internal to this search --
    never returned, never linearized, never reaching compile_gf_
    constraints or any real prediction. Only the list of reason codes
    (the same closed, safe-to-aggregate vocabulary build_gf_tree_
    decline_reason already uses) is ever returned.
    """
    working_words = words
    working_lexicon = gf_function_by_lemma
    reasons: list[str] = []
    for _ in range(max_iterations):
        try:
            _build_gf_tree_inner(working_words, lemma, working_lexicon, governing_start)
            return reasons
        except _Bail as bail:
            reasons.append(bail.reason)
            reason_key = bail.reason.split(":", 1)[0]
            if reason_key in _LEXICON_ABLATION_REASONS:
                new_lexicon = _ablate_lexicon_gap(working_words, working_lexicon, lemma)
                if new_lexicon is None:
                    return reasons
                working_lexicon = new_lexicon
                continue
            ablation = _GROUP_ABLATIONS.get(reason_key)
            if ablation is None:
                return reasons
            new_words = ablation(working_words)
            if new_words is None:
                return reasons
            working_words = new_words
    reasons.append("max-iterations-reached")
    return reasons


def _np_from_llm_description(np: Any) -> str:
    """One NP from an LLM-proposed clause structure (see
    scripts/llm_propose_clause_structure.py's own docstring for the
    full JSON schema this consumes) -- reuses the exact same rendering
    primitives (_apply/_quote/_PROPER_NOUN_CONSTRUCTORS/
    _PRONOUN_CONSTRUCTORS) as the UD-tree-derived _np above, since both
    ultimately build the same three NP shapes; only how the shape is
    identified differs (UD upos/deprel vs. the LLM's own classification).
    Every failure mode raises _Bail with an "llm-"-prefixed reason code,
    distinct from the UD path's own vocabulary, so
    decline_reason_counts can tell which tier actually produced a given
    decline.
    """
    if not isinstance(np, dict):
        raise _Bail("llm-np-not-a-dict")
    kind = np.get("kind")
    if kind == "proper_noun":
        tokens = np.get("tokens")
        if not isinstance(tokens, list) or not tokens or not all(
            isinstance(token, str) and token for token in tokens
        ):
            raise _Bail("llm-proper-noun-tokens-invalid")
        constructor = _PROPER_NOUN_CONSTRUCTORS.get(len(tokens))
        if constructor is None:
            raise _Bail("llm-proper-noun-chain-too-long")
        return _apply(constructor, *(_quote(token) for token in tokens))
    if kind == "pronoun":
        pronoun = np.get("pronoun")
        constructor = _PRONOUN_CONSTRUCTORS.get(
            pronoun.casefold() if isinstance(pronoun, str) else ""
        )
        if constructor is None:
            raise _Bail("llm-pronoun-unrecognized")
        return _apply(constructor)
    if kind == "common_noun":
        noun = np.get("noun")
        if not isinstance(noun, str) or not noun:
            raise _Bail("llm-common-noun-missing-noun")
        determiner = np.get("determiner")
        if determiner == "the":
            is_definite = True
        elif determiner in _INDEFINITE_DETERMINERS:
            is_definite = False
        else:
            raise _Bail("llm-common-noun-unrecognized-determiner")
        noun_text = _quote(noun)
        adjective = np.get("adjective")
        if adjective is not None:
            if not isinstance(adjective, str) or not adjective:
                raise _Bail("llm-common-noun-invalid-adjective")
            constructor = "OpenAdjDefCN" if is_definite else "OpenAdjIndefCN"
            adjective_text = _quote(adjective)
            return _apply(constructor, adjective_text, noun_text, noun_text)
        constructor = "OpenDefCN" if is_definite else "OpenIndefCN"
        return _apply(constructor, noun_text, noun_text)
    raise _Bail("llm-np-unrecognized-kind")


def _build_gf_tree_from_llm_structure_inner(
    structure: Any,
    lemma: str,
    gf_function_by_lemma: dict[str, str],
) -> str:
    """The single implementation build_gf_tree_from_llm_structure and
    build_gf_tree_from_llm_structure_decline_reason both delegate to --
    mirrors _build_gf_tree_inner's own contract (always raises _Bail,
    never returns None, on any unhandled/invalid structure).
    """
    if not isinstance(structure, dict):
        raise _Bail("llm-structure-not-a-dict")
    gf_function = gf_function_by_lemma.get(lemma)
    if gf_function is None:
        # Same reason code the UD path's own _clause already uses for
        # this exact condition -- one shared vocabulary entry for "this
        # lemma has no compiled GF action", regardless of which tier
        # found that out.
        raise _Bail("verb-not-in-lexicon")
    voice = structure.get("voice")
    if voice == "passive":
        subject_description = structure.get("subject")
        agent_description = structure.get("agent")
        if subject_description is None or agent_description is None:
            raise _Bail("llm-passive-missing-np")
        subject_np = _np_from_llm_description(subject_description)
        agent_np = _np_from_llm_description(agent_description)
        return _apply("Pred", subject_np, _apply("PassCompl", gf_function, agent_np))
    if voice == "active":
        subject_description = structure.get("subject")
        object_description = structure.get("object")
        if subject_description is None or object_description is None:
            raise _Bail("llm-active-missing-np")
        subject_np = _np_from_llm_description(subject_description)
        object_np = _np_from_llm_description(object_description)
        return _apply("Pred", subject_np, _apply("Compl", gf_function, object_np))
    raise _Bail("llm-voice-unrecognized")


def build_gf_tree_from_llm_structure(
    structure: Any,
    lemma: str,
    gf_function_by_lemma: dict[str, str],
) -> str | None:
    """Build GF tree text from an LLM-proposed clause structure (the
    dict scripts/llm_propose_clause_structure.py's propose_clause_structure
    returns), or None if the structure is missing, malformed, or
    describes something this narrow first schema doesn't cover. Mirrors
    build_gf_tree's own contract exactly, just for a different (LLM-
    derived rather than UD-derived) structured input -- same lemma/
    gf_function_by_lemma reuse, same "never guess, only build when
    confident" discipline.
    """
    try:
        return _strip_outer_parens(
            _build_gf_tree_from_llm_structure_inner(structure, lemma, gf_function_by_lemma)
        )
    except _Bail:
        return None


def build_gf_tree_from_llm_structure_decline_reason(
    structure: Any,
    lemma: str,
    gf_function_by_lemma: dict[str, str],
) -> str:
    """Empty string if build_gf_tree_from_llm_structure would succeed on
    the same input, else a closed-vocabulary reason code -- mirrors
    build_gf_tree_decline_reason exactly, for the LLM-structure path.
    """
    try:
        _build_gf_tree_from_llm_structure_inner(structure, lemma, gf_function_by_lemma)
        return ""
    except _Bail as bail:
        return bail.reason


def load_gf_function_by_lemma(actions_json: dict[str, Any]) -> dict[str, str]:
    """lemma -> "CTX_<hash>" reverse lookup from a loaded contextual-gf-actions.json.

    Mirrors run_automatic_contextual_pipeline.py's own
    ``{action["gf_function"]: action["lemma"] for ...}`` (the direction
    compile_gf_constraints needs), just inverted for this module's own
    lemma-to-function direction.
    """
    return {
        action["lemma"]: action["gf_function"] for action in actions_json["actions"]
    }
