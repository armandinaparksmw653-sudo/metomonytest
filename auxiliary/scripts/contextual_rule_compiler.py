#!/usr/bin/env python3
"""Compile versioned lexical resources into contextual tower constraints."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ActionRole:
    lemma: str
    hole_role: str
    requirement: str
    strength: str
    provenance: str
    identity: str


@dataclass(frozen=True)
class GFNode:
    constructor: str
    arguments: tuple["GFNode | str", ...] = ()


ARITIES = {
    "Pred": 2,
    "NegPred": 2,
    "Compl": 2,
    "PassCompl": 2,
    "PassCompl0": 1,
    "PassComplRetained": 2,
    "ComplOblique": 2,
    "InPP": 1,
    "AboutPP": 1,
    "WithPP": 1,
    "ForPP": 1,
    "OnPP": 1,
    "AtPP": 1,
    "FromPP": 1,
    "ByPP": 1,
    "OverPP": 1,
    "UnderPP": 1,
    "DuringPP": 1,
    "NearPP": 1,
    "OfPP": 1,
    "AsPP": 1,
    "AndS": 2,
    "OrS": 2,
    "AndNP": 2,
    "OrNP": 2,
    "PredConjVP": 3,
    "PredOrConjVP": 3,
    "PredCopNP": 2,
    "ModifyNP": 2,
    "ModifyRel": 3,
    "ModifyRelVP": 2,
    "ModifyRelAtVP": 3,
    "IndefCN": 1,
    "DefCN": 1,
    "ModifyRelCN": 3,
    "ModifyRelCNVP": 2,
    "PossNP": 2,
    "EveryCN": 2,
    "OpenAdjDefCN": 3,
    "OpenAdjIndefCN": 3,
    "OpenPN": 1,
    "OpenPN2": 2,
    "OpenPN3": 3,
    "OpenIndefCN": 2,
    "OpenDefCN": 2,
    "BecauseS": 2,
    "IfS": 2,
    "WhenS": 2,
    "AlthoughS": 2,
    "SBecauseS": 2,
    "SIfS": 2,
    "SWhenS": 2,
    "SAlthoughS": 2,
    "ApposCommaPN1": 2,
    "ApposCommaPN2": 3,
    "OnFrontedS": 2,
    "InFrontedS": 2,
    "FromFrontedS": 2,
    "ParenNP": 2,
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def action_forms(raw_lemma: str) -> set[str]:
    lemma = raw_lemma.casefold().replace("_", " ")
    if " " in lemma:
        return {lemma}
    forms = {lemma}
    if lemma.endswith(("s", "sh", "ch", "x", "z", "o")):
        forms.add(lemma + "es")
    elif lemma.endswith("y") and len(lemma) > 1 and lemma[-2] not in "aeiou":
        forms.add(lemma[:-1] + "ies")
    else:
        forms.add(lemma + "s")
    forms.add(lemma[:-1] + "ed" if lemma.endswith("e") else lemma + "ed")
    forms.add(lemma[:-1] + "ing" if lemma.endswith("e") else lemma + "ing")
    return forms


def third_person(lemma: str) -> str:
    candidates = action_forms(lemma)
    if lemma.endswith(("s", "sh", "ch", "x", "z", "o")):
        wanted = lemma + "es"
    elif lemma.endswith("y") and len(lemma) > 1 and lemma[-2] not in "aeiou":
        wanted = lemma[:-1] + "ies"
    else:
        wanted = lemma + "s"
    return wanted if wanted in candidates else lemma


def regular_participle(lemma: str) -> str:
    """Regular "-ed" past-participle form, for the default passive gf_form.

    Irregular verbs need an explicit ``passive_gf_form`` morphology
    override; this is only ever a fallback, same as ``third_person``.
    """
    return lemma[:-1] + "ed" if lemma.endswith("e") else lemma + "ed"


def load_action_roles(
    predicates_path: Path, verbnet_roles_path: Path
) -> list[ActionRole]:
    roles = []
    for row in read_tsv(predicates_path):
        for hole, column in (
            ("SubjectHole", "subject_sort"),
            ("ObjectHole", "object_sort"),
        ):
            roles.append(
                ActionRole(
                    lemma=row["lemma"].casefold(),
                    hole_role=hole,
                    requirement=f"HasSort {row[column]}",
                    strength=row["strength"],
                    provenance=row["provenance"],
                    identity=f"predicate:{row['predicate_id']}:{hole}",
                )
            )
    for row in read_tsv(verbnet_roles_path):
        if (
            row["mapping_status"] != "compiled"
            or row["hole_role"] not in {"SubjectHole", "ObjectHole"}
            or not row["requirement"]
            or row["requirement"] == "null"
        ):
            continue
        roles.append(
            ActionRole(
                lemma=row["lemma"].casefold().replace("_", " "),
                hole_role=row["hole_role"],
                requirement=row["requirement"],
                strength=row["strength"],
                provenance=row["provenance"],
                identity=f"{row['action_id']}:{row['frame_id']}:{row['thematic_role']}",
            )
        )
    return roles


def load_action_frames(actions_path: Path) -> dict[str, list[dict[str, str]]]:
    frames: dict[str, list[dict[str, str]]] = {}
    for row in read_tsv(actions_path):
        lemma = row["lemma"].casefold().replace("_", " ")
        for frame in json.loads(row["framenet_frames_json"]):
            if not frame or frame == "None":
                continue
            entry = {
                "frame": frame,
                "action_id": row["action_id"],
                "provenance": row["provenance"],
            }
            if entry not in frames.setdefault(lemma, []):
                frames[lemma].append(entry)
    return frames


def _surface_phrases(sentence: str) -> list[tuple[str, int, int]]:
    tokens = list(re.finditer(r"[A-Za-z][A-Za-z'-]*", sentence))
    phrases = []
    for size in (1, 2, 3):
        for index in range(len(tokens) - size + 1):
            selected = tokens[index : index + size]
            phrases.append(
                (
                    sentence[selected[0].start() : selected[-1].end()].casefold(),
                    selected[0].start(),
                    selected[-1].end(),
                )
            )
    return phrases


def _mention_span(sentence: str, surfaces: list[str]) -> tuple[int, int] | None:
    # \b requires a word/non-word transition on BOTH sides -- fails for a
    # surface ending in punctuation (e.g. "Apple Inc.", an alias verbatim
    # from a real Wikidata snapshot) followed by whitespace, since "."
    # and " " are both non-word characters and no such transition exists
    # there. (?<!\w)/(?!\w) only assert what's immediately outside the
    # match isn't a word character -- identical to \b for the common
    # word-ending case, but correct for punctuation-ending surfaces too.
    for surface in surfaces:
        match = re.search(
            rf"(?<!\w){re.escape(surface)}(?!\w)", sentence, re.IGNORECASE
        )
        if match:
            return match.start(), match.end()
    return None


_BE_FORMS = {"is", "was", "are", "were", "be", "been", "being"}


def _preceded_by_be_verb(sentence: str, position: int) -> bool:
    """Is the word immediately before ``position`` some form of "be"?

    A cheap, local stand-in for the voice detection a real dependency
    parse would give (Stanza is unavailable in this project's own CI,
    so ``dependency_hint`` never carries "voice" in practice) -- looking
    at the single word already in the text right before the match is
    enough to tell active from passive without one.
    """
    preceding = re.search(r"[A-Za-z]+\s*$", sentence[:position])
    return bool(preceding) and preceding.group().strip().casefold() in _BE_FORMS


def _split_top_level(value: str) -> list[str]:
    fields, start, depth = [], 0, 0
    for index, character in enumerate(value):
        if character in "[(":
            depth += 1
        elif character in "])":
            depth -= 1
        elif character == "," and depth == 0:
            fields.append(value[start:index])
            start = index + 1
    fields.append(value[start:])
    return [field.strip() for field in fields if field.strip()]


def _disjunction_members(requirement: str) -> list[str]:
    prefix = "AnyOf ["
    if requirement.startswith(prefix) and requirement.endswith("]"):
        return _split_top_level(requirement[len(prefix) : -1])
    return [requirement]


def _resolve_copula_predicate(
    sentence: str, dependency_hint: dict, wordnet_rules: dict | None
) -> dict:
    """Resolve a "copula-argument" dependency_hint ("Waterloo is a
    county") -- structurally separate from the rest of resolve_action
    since there is no VerbNet "action" for a copula at all (confirmed:
    data/predicates.tsv and data/verbnet-action-roles.tsv contain zero
    "is-a" entries). The predicate noun's own lemma stands in for
    "action" (reused exactly the way the verb path reuses a resolved
    verb lemma -- build_gf_tree_from_dependencies.py's _copula_clause
    checks the UD root's own lemma against it, the same
    "root-lemma-mismatch" meaning, generalized to a non-verb root); the
    requirement comes directly from wordnet_rules["lexical_sorts"], not
    from any ActionRole (a genuinely different data source than every
    other branch of this function uses).

    Real corpus data found this predicate-noun-lookup a hard coverage
    ceiling, not just a wiring detail: data/wordnet-context-rules.json's
    lexical_sorts (5148 entries) does not contain "county"/"museum"/
    "town"/"city"/"river" -- correctly, safely declining
    ("unsupported-copula-predicate:<lemma>") for a real share of "X is a
    Y" sentences is expected, not a bug to chase further this round.
    """
    start = dependency_hint.get("governing_start")
    end = dependency_hint.get("governing_end")
    predicate_lemma = (dependency_hint.get("governing_lemma") or "").casefold()
    if start is None or end is None or not predicate_lemma:
        raise ValueError("copula-predicate-unresolved")
    head_rule = (wordnet_rules or {}).get("lexical_sorts", {}).get(predicate_lemma)
    if not head_rule:
        raise ValueError(f"unsupported-copula-predicate:{predicate_lemma}")
    evidence = [
        {
            "identity": f"wordnet-lexical-sort:{predicate_lemma}",
            "provenance": head_rule["provenance"],
            "strength": "hard",
            "requirement": head_rule["requirement"],
        }
    ]
    digest = hashlib.sha256(
        json.dumps(evidence, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    role = (dependency_hint.get("hole_role") or "Subject") + "Hole"
    return {
        "lemma": predicate_lemma,
        "surface": sentence[start:end],
        "start": start,
        "end": end,
        "role": role,
        "requirement": head_rule["requirement"],
        "strength": "hard",
        "provenance": f"compiled-copula-predicate:v1:hard:{digest}",
        "evidence": evidence,
        # A fixed present-tense normalization of whatever copula form
        # was actually in the text ("was"/"are"/"were" -> "is"), mirroring
        # the existing tense-normalization discipline this function
        # already applies to verbs (third_person(lemma) for active, "is
        # " + passive_form for passive) -- needed for the legacy `engine
        # parse` fallback path to have any chance, since PredCopNP's own
        # linearization always defaults to present tense regardless of
        # input.
        "gf_form": "is",
        "voice": "active",
    }


def resolve_action(
    sentence: str,
    target_surfaces: list[str],
    roles: list[ActionRole],
    morphology_overrides: dict,
    dependency_hint: dict | None = None,
    wordnet_rules: dict | None = None,
) -> dict:
    by_form: dict[str, list[ActionRole]] = {}
    for role in roles:
        for form in action_forms(role.lemma):
            by_form.setdefault(form, []).append(role)
    for lemma, definition in morphology_overrides.items():
        matching = [role for role in roles if role.lemma == lemma.casefold()]
        for form in definition.get("forms", []):
            by_form.setdefault(form.casefold(), []).extend(matching)

    dep_status = dependency_hint.get("dep_status") if dependency_hint else None
    if dep_status == "copula-argument":
        return _resolve_copula_predicate(sentence, dependency_hint, wordnet_rules)
    if dep_status == "nested-modifier":
        # nested_modifier_deprel (annotate_dependency_hints.py) is a
        # closed-vocabulary UD relation label (one of
        # NESTED_MODIFIER_DEPRELS there), never sentence text -- safe to
        # include so score_contextual_detection.py can report which
        # specific nested-modifier shape actually dominates instead of
        # one undifferentiated count.
        deprel = dependency_hint.get("nested_modifier_deprel") or ""
        raise ValueError(
            f"nested-modifier-unsupported:{deprel}" if deprel
            else "nested-modifier-unsupported"
        )

    governing_start = dependency_hint.get("governing_start") if dependency_hint else None
    governing_end = dependency_hint.get("governing_end") if dependency_hint else None
    hint_governing_lemma = None
    if (
        dep_status == "direct-argument"
        and governing_start is not None
        and governing_end is not None
        and dependency_hint.get("hole_role")
    ):
        # annotate_dependency_hints.py reports "Subject"/"Object";
        # ActionRole.hole_role uses "SubjectHole"/"ObjectHole".
        hint_hole_role = dependency_hint["hole_role"] + "Hole"
        governing_lemma = (dependency_hint.get("governing_lemma") or "").casefold()
        hint_governing_lemma = governing_lemma
        candidates = [
            (0, governing_start, governing_end, sentence[governing_start:governing_end].casefold(), role)
            for role in by_form.get(governing_lemma, [])
            if role.hole_role == hint_hole_role
        ]
        if not candidates and " " in governing_lemma:
            # governing_lemma is "<verb> <preposition>" -- reconstructed
            # by annotate_dependency_hints.py for an "obl"+"case" phrase
            # ("based in", "raised in Hertfordshire") -- but by_form is
            # built from action_forms() over data/predicates.tsv and
            # data/verbnet-action-roles.tsv, and both files contain zero
            # lemmas with a space (confirmed by grepping both, not
            # guessed): every ActionRole is indexed by a single bare
            # verb. A phrasal key can therefore never hit that index,
            # regardless of whether the bare verb itself ("arrive",
            # "raise", "base", ...) already has real ActionRole coverage
            # under its own lemma -- confirmed as the dominant real cause
            # of unsupported-action-role in a live corpus evaluation (see
            # docs/contextual-tower.md's "Sub-bucketing the three new
            # dominant abstain reasons" section). Retry with just the
            # bare verb.
            #
            # governing_start/governing_end span the *whole* phrase
            # (verb through the case-marking preposition), so re-matching
            # on the bare verb also needs the verb's own, narrower span --
            # otherwise the later gf_sentence substitution
            # (propose_contextual_scenario.py replaces exactly
            # [action["start"]:action["end"]] with action["gf_form"])
            # would delete the preposition from the sentence entirely,
            # e.g. turning "...is based in Hertfordshire..." into
            # "...is bases Hertfordshire...". English always places an
            # obl's governing verb before its case-marking preposition,
            # so the first word-token in the combined span is reliably
            # just the verb, with or without an adverb separating them
            # ("argued strongly against" -> "argued").
            bare_lemma = governing_lemma.split(" ", 1)[0]
            verb_match = re.search(
                r"[A-Za-z][A-Za-z'-]*", sentence[governing_start:governing_end]
            )
            if verb_match:
                verb_start = governing_start + verb_match.start()
                verb_end = governing_start + verb_match.end()
                candidates = [
                    (0, verb_start, verb_end, sentence[verb_start:verb_end].casefold(), role)
                    for role in by_form.get(bare_lemma, [])
                    if role.hole_role == hint_hole_role
                ]
    else:
        target_span = _mention_span(sentence, target_surfaces)
        if target_span is None:
            raise ValueError("target-occurrence-not-found")

        candidates = []
        for surface, start, end in _surface_phrases(sentence):
            # A word inside the target's own mention span can itself
            # happen to match some unrelated VerbNet lemma's inflected
            # form (e.g. the source "High Point" contains "Point", which
            # is also a verb) -- and since it sits at distance ~0 from
            # target_span[0], it would otherwise almost always outrank
            # the real governing verb elsewhere in the sentence, purely
            # on proximity. Confirmed directly against real WiMCor/ConMeC
            # sample sentences (locally reproduced, not guessed): this
            # produced literal nonsense like "raised in High points" --
            # the source's own second word verb-conjugated in place.
            if start < target_span[1] and end > target_span[0]:
                continue
            for role in by_form.get(surface, []):
                expected_role = "SubjectHole" if target_span[0] < start else "ObjectHole"
                if role.hole_role == expected_role:
                    candidates.append((abs(start - target_span[0]), start, end, surface, role))
    if not candidates:
        # hint_governing_lemma is a single common English verb lemma (or
        # "<verb> <preposition>" for a reconstructed phrasal verb), never
        # sentence text -- safe to include, same risk class as the
        # has_comma/has_digit counts score_contextual_detection.py
        # already reports. Only set on the dependency-hint path: the
        # no-hint fallback searches every window in the sentence at
        # once, so there is no single "the lemma that should have
        # matched" to report there.
        raise ValueError(
            f"unsupported-action-role:{hint_governing_lemma}"
            if hint_governing_lemma
            else "unsupported-action-role"
        )

    candidates.sort(
        key=lambda item: (
            item[0],
            0 if item[4].strength == "HardRequirement" else 1,
            -len(item[4].lemma),
            item[4].identity,
        )
    )
    _, start, end, surface, selected = candidates[0]
    same_action = [
        item[4]
        for item in candidates
        if item[1] == start
        and item[4].lemma == selected.lemma
        and item[4].hole_role == selected.hole_role
    ]
    hard = [role for role in same_action if role.strength == "HardRequirement"]
    chosen = hard or same_action
    requirements = sorted(
        {
            member
            for role in chosen
            for member in _disjunction_members(role.requirement)
        }
    )
    requirement = (
        requirements[0]
        if len(requirements) == 1
        else "AnyOf [" + ",".join(requirements) + "]"
    )
    evidence = sorted(
        {
            (role.identity, role.provenance, role.strength, role.requirement)
            for role in chosen
        }
    )
    digest = hashlib.sha256(
        json.dumps(evidence, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    strength = "hard" if hard else "selectional-preference"
    override = morphology_overrides.get(selected.lemma, {})
    voice = dependency_hint.get("voice") if dependency_hint else None
    passive_form = override.get("passive_gf_form", regular_participle(selected.lemma))
    already_passive_in_text = (
        voice is None
        and surface == passive_form.casefold()
        and _preceded_by_be_verb(sentence, start)
    )
    if already_passive_in_text:
        # No dependency hint means voice is never detected from real
        # syntax -- confirmed directly against real WiMCor/ConMeC sample
        # sentences (locally reproduced): this silently defaulted every
        # such sentence to active, replacing an already-correct passive
        # surface form ("is based") with a freshly reconjugated active
        # one ("is bases"), producing nonsense. The matched surface text
        # itself already carries the answer here: if what actually
        # matched in the sentence is the participle form used for
        # passive (not the bare lemma or the "-ing" form) and it is
        # immediately preceded by a form of "be", the sentence was
        # already passive -- no dependency parse needed to see that.
        voice = "passive"
    gf_form = (
        # already_passive_in_text means the "is"/"was" this needs is
        # already sitting untouched right before `start` in the original
        # text (that's the whole signal `_preceded_by_be_verb` checked)
        # -- prepending another one here would double it ("is is based").
        # The dependency_hint-driven passive path below it still needs
        # its own, since there the auxiliary isn't already in the kept
        # prefix.
        passive_form
        if already_passive_in_text
        else "is " + passive_form
        if voice == "passive"
        else override.get("gf_form", third_person(selected.lemma))
    )
    return {
        "lemma": selected.lemma,
        "surface": sentence[start:end],
        "start": start,
        "end": end,
        "role": selected.hole_role,
        "requirement": requirement,
        "strength": strength,
        "provenance": f"compiled-action-role:v1:{strength}:{digest}",
        "evidence": [
            {
                "identity": identity,
                "provenance": provenance,
                "strength": source_strength,
                "requirement": source_requirement,
            }
            for identity, provenance, source_strength, source_requirement in evidence
        ],
        "gf_form": gf_form,
        "voice": voice or "active",
    }


def tokenize_gf(tree: str) -> list[str]:
    return re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', tree)


# GF constructor names this grammar itself defines (grammar/Metonymy.gf's
# `fun` declarations), never sentence text -- unlike ARITIES, these
# genuinely take zero arguments (HePN/ShePN/ItPN/TheyPN, and
# IPN/WePN/YouPN added alongside them for first/second-person pronouns),
# so their absence from ARITIES (which only lists arity>=1 constructors,
# relying on ARITIES.get(token, 0) for everything else) is expected, not
# a sign of a missing entry the way any other unrecognized
# constructor-shaped token is.
_KNOWN_ZERO_ARITY_CONSTRUCTORS = {
    "HePN",
    "ShePN",
    "ItPN",
    "TheyPN",
    "IPN",
    "WePN",
    "YouPN",
}


def _unrecognized_constructors(tokens: list[str]) -> list[str]:
    """Constructor-shaped tokens in a GF tree that ARITIES doesn't know.

    A GF tree's own function-application tokens (this grammar's own
    naming convention: PascalCase, e.g. "PredCopNP", "OpenPN2") are a
    closed vocabulary defined entirely by grammar/Metonymy.gf -- never
    sentence text, the same safety class already established for
    exit4_reason_bucket's fixed message set. String leaves (quoted) and
    parentheses are excluded by construction; ``?`` metavariables by their
    own leading character. Order-preserving and de-duplicated, so a
    single one-word answer names the actual gap when there is one.
    """
    seen: list[str] = []
    for token in tokens:
        if (
            token not in ("(", ")")
            and not token.startswith('"')
            and not token.startswith("?")
            and re.fullmatch(r"[A-Z][A-Za-z0-9]*", token)
            and token not in ARITIES
            and token not in _KNOWN_ZERO_ARITY_CONSTRUCTORS
            and token not in seen
        ):
            seen.append(token)
    return seen


def parse_gf_tree(tree: str) -> GFNode:
    tokens = tokenize_gf(tree)

    def parse(index: int) -> tuple[GFNode | str, int]:
        parenthesized = tokens[index] == "("
        if parenthesized:
            index += 1
        token = tokens[index]
        index += 1
        if token.startswith('"') or token.startswith("?"):
            value: GFNode | str = token[1:-1] if token.startswith('"') else token
        else:
            arguments = []
            for _ in range(ARITIES.get(token, 0)):
                argument, index = parse(index)
                arguments.append(argument)
            value = GFNode(token, tuple(arguments))
        if parenthesized:
            if index >= len(tokens) or tokens[index] != ")":
                raise ValueError(f"malformed GF tree near {token}")
            index += 1
        return value, index

    parsed, index = parse(0)
    if not isinstance(parsed, GFNode) or index != len(tokens):
        # The most common real cause (confirmed by a live corpus
        # evaluation: this is exit4's dominant failure) is a GF
        # constructor missing from ARITIES entirely -- ARITIES.get(token,
        # 0) silently treats it as 0-ary, so every one of its intended
        # arguments is left dangling as unconsumed top-level tokens
        # instead of being parsed as its children. When that's
        # identifiable, name it; the resulting message is still a prefix
        # match for every existing "malformed or incomplete GF tree"
        # consumer (KNOWN semantics unchanged, only extended).
        unrecognized = _unrecognized_constructors(tokens)
        if unrecognized:
            raise ValueError(
                "malformed or incomplete GF tree; unrecognized constructor(s): "
                + ",".join(unrecognized)
            )
        raise ValueError("malformed or incomplete GF tree")
    return parsed


def _origin(sentence: str, token: str, constructor: str) -> dict:
    match = re.search(rf"\b{re.escape(token)}\b", sentence, re.IGNORECASE)
    if not match:
        raise ValueError(f"GF lexical token is absent from source: {token}")
    return {
        "constructor": constructor,
        "lemma": token.casefold(),
        "surface": match.group(),
        "start": match.start(),
        "end": match.end(),
    }


def _cumulative_origin(
    proposal: dict,
    token: str,
    constructor: str,
    semantic_lemma: str,
) -> dict:
    sentence = proposal["sentence"]
    action_origin = proposal["constraints"][0]["origin"]
    match = re.search(
        rf"\b{re.escape(token)}\b",
        sentence[action_origin["end"] :],
        re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"GF lexical token is absent from source: {token}")
    end = action_origin["end"] + match.end()
    return {
        "constructor": constructor,
        "lemma": semantic_lemma,
        "surface": sentence[action_origin["start"] : end],
        "start": action_origin["start"],
        "end": end,
    }


def _noun_lemma(node: GFNode | str) -> str | None:
    if not isinstance(node, GFNode):
        return None
    if node.constructor in {"OpenIndefCN", "OpenDefCN"}:
        return node.arguments[0] if isinstance(node.arguments[0], str) else None
    if node.constructor in {"OpenAdjDefCN", "OpenAdjIndefCN"}:
        return node.arguments[1] if isinstance(node.arguments[1], str) else None
    return None


def _proper_lemma(node: GFNode | str) -> str | None:
    if not isinstance(node, GFNode):
        return None
    if (
        node.constructor == "OpenPN"
        and node.arguments
        and isinstance(node.arguments[0], str)
    ):
        return node.arguments[0]
    if node.constructor in {"OpenPN2", "OpenPN3"} and all(
        isinstance(argument, str) for argument in node.arguments
    ):
        # Space-joined, matching how a multi-word alias is actually
        # stored in aliases.jsonl (the lookup this lemma ultimately
        # feeds) -- see OpenPN2/OpenPN3's own comment in
        # grammar/MetonymyEng.gf for why they exist at all.
        return " ".join(node.arguments)
    return None


def _sorts(requirement: str) -> set[str]:
    return set(re.findall(r"HasSort ([A-Za-z][A-Za-z0-9]*)", requirement))


def _lookup_context_trigger(
    context_triggers: dict | None, construction: str, lemma: str
) -> dict | None:
    """(lemma, structural relation to the metonymy target) -> constraint.

    Deliberately keyed on BOTH the lemma and the construction (the same
    discipline language_rules["context_templates"] already uses for
    ModifyNP+PP -- not a bag-of-words match on the lemma alone). A word
    reachable in the tree only through some OTHER construction (e.g.
    inside an unrelated relative clause) must never match here, however
    tempting a flat word->requirement table would be -- see
    docs/contextual-tower.md's note on why a flat table would have
    wrongly attached "degree" from an unrelated dean/Yale clause to an
    unrelated target.
    """
    if not context_triggers:
        return None
    return next(
        (
            trigger
            for trigger in context_triggers.get("triggers", [])
            if trigger["construction"] == construction
            and trigger["lemma"] == lemma.casefold()
        ),
        None,
    )


def _context_trigger_constraint(
    proposal: dict, token: str, construction: str, trigger: dict
) -> dict:
    payload_key = "requires" if trigger.get("strength") == "requires" else "prefers"
    return {
        "origin": _cumulative_origin(
            proposal, token, f"ContextTrigger:{construction}", token.casefold()
        ),
        "payload": {payload_key: trigger["requirement"]},
        "provenance": trigger["provenance"],
    }


def compile_gf_constraints(
    proposal: dict,
    tree: str,
    language_rules: dict,
    wordnet_rules: dict,
    aliases: dict[str, list[str]],
    *,
    enable_existential: bool = True,
    gf_actions: dict[str, str] | None = None,
    gf_nouns: dict[str, str] | None = None,
    context_triggers: dict | None = None,
) -> list[dict]:
    root = parse_gf_tree(tree)
    constraints = []
    if not wordnet_rules.get("lexical_sorts"):
        return constraints
    action_payload = proposal["constraints"][0]["payload"]
    action_requirement = action_payload.get(
        "requires", action_payload.get("prefers")
    )
    action_is_preference = "prefers" in action_payload
    gf_actions = gf_actions or {}
    gf_nouns = gf_nouns or {}

    def first_node(node: GFNode | str, constructors: set[str]) -> GFNode | None:
        if not isinstance(node, GFNode):
            return None
        if node.constructor in constructors:
            return node
        for argument in node.arguments:
            found = first_node(argument, constructors)
            if found:
                return found
        return None

    def coordinated_complements(node: GFNode | str) -> list[GFNode]:
        """Compl/PassCompl nodes reached ONLY as a direct VP argument of
        PredConjVP/PredOrConjVP -- deliberately NOT "every Compl/PassCompl
        anywhere in the tree" (a first, broken version of this used a
        generic all-nodes search and wrongly matched a Compl buried inside
        an unrelated ModifyRelVP relative clause -- caught by this
        module's own negative test). PredConjVP's shape (one NP argument
        shared by both VPs) is what licenses "shares the target's
        subject"; nothing else does, so nothing else is descended into
        for this purpose."""
        if not isinstance(node, GFNode):
            return []
        found = []
        if (
            node.constructor in {"PredConjVP", "PredOrConjVP"}
            and len(node.arguments) == 3
        ):
            found.extend(
                vp
                for vp in node.arguments[1:]
                if isinstance(vp, GFNode)
                and vp.constructor
                in {"Compl", "PassCompl", "PassComplRetained", "ComplOblique"}
            )
        for argument in node.arguments:
            found.extend(coordinated_complements(argument))
        return found

    def lexical_head(node: GFNode | str) -> GFNode | str:
        if isinstance(node, GFNode) and node.constructor in {
            "ModifyNP",
            "ModifyRel",
            "ModifyRelCN",
            "ModifyRelVP",
            "ModifyRelCNVP",
            "IndefCN",
            "DefCN",
        }:
            return lexical_head(node.arguments[0])
        return node

    def coordinated_object_lemma(vp: GFNode) -> str | None:
        """Compl/PassCompl/PassComplRetained's second argument is already
        a bare NP -- _noun_lemma handles it directly. ComplOblique's
        second argument is a PP (e.g. WithPP(OpenIndefCN ...)) wrapping
        the NP one level deeper; still passed through the same bare
        _noun_lemma check (no lexical_head), so a modifier on the PP's
        own object -- benign or institution-redirecting -- still safely
        declines. Used both for ConjClauseObject (a coordinated sibling
        VP) and RelativeClauseObject (a VP embedded in a ModifyRelAtVP
        that itself modifies the target) -- the same "what does this VP's
        own object say" question, just reached via a different tree
        relation each time."""
        if (
            vp.constructor in {"Compl", "PassCompl", "PassComplRetained"}
            and len(vp.arguments) == 2
        ):
            return _noun_lemma(vp.arguments[1])
        if vp.constructor == "ComplOblique" and len(vp.arguments) == 2:
            pp = vp.arguments[1]
            if isinstance(pp, GFNode) and len(pp.arguments) == 1:
                return _noun_lemma(pp.arguments[0])
        return None

    # PassCompl's second argument is the "by"-agent NP, not a grammatical
    # object -- but it is analyzed exactly like Compl's object here: when
    # it is the metonymy target itself (a bare proper noun, whichever hole
    # role that is for), _noun_lemma/gf_nouns naturally fail to resolve a
    # common-noun lemma for it below and this block is a no-op, same
    # protection Compl already relies on for the ObjectHole/target-as-
    # object case. When it is a separate common-noun argument, deriving a
    # FrameArgument capability constraint from it is equally valid
    # regardless of whether that argument is textually the object or the
    # agent.
    complement = first_node(
        root, {"Compl", "PassCompl", "PassComplRetained", "ComplOblique"}
    )
    if complement and len(complement.arguments) == 2:
        object_node = complement.arguments[1]
        # RelativeClauseObject: a content word inside the VP embedded in
        # a ModifyRelAtVP that modifies the TARGET's own NP directly
        # ("Padgate, at which he was awarded a Certificate...") --
        # distinct from ConjClauseObject (a sibling VP reached through
        # PredConjVP coordination): here the relative clause hangs off
        # the target NP itself, found as the primary complement's own
        # object, not a coordinated sibling. Reuses coordinated_object_
        # lemma (the same "what does this VP's own object say" check,
        # same no-lexical_head safety guarantee) since a ModifyRelAtVP's
        # third argument is an ordinary Compl/PassCompl/PassComplRetained/
        # ComplOblique VP, no different from one found via coordination.
        if (
            isinstance(object_node, GFNode)
            and object_node.constructor == "ModifyRelAtVP"
            and len(object_node.arguments) == 3
        ):
            embedded_vp = object_node.arguments[2]
            embedded_lemma = (
                coordinated_object_lemma(embedded_vp)
                if isinstance(embedded_vp, GFNode)
                else None
            )
            if embedded_lemma:
                relative_trigger = _lookup_context_trigger(
                    context_triggers, "RelativeClauseObject", embedded_lemma
                )
                if relative_trigger:
                    constraints.append(
                        _context_trigger_constraint(
                            proposal,
                            embedded_lemma,
                            "RelativeClauseObject",
                            relative_trigger,
                        )
                    )
        head = lexical_head(object_node)
        head_lemma = _noun_lemma(head)
        if (
            not head_lemma
            and isinstance(head, GFNode)
            and head.constructor in gf_nouns
        ):
            head_lemma = gf_nouns[head.constructor]
        head_rule = (
            wordnet_rules.get("lexical_sorts", {}).get(head_lemma.casefold())
            if head_lemma
            else None
        )
        if not head_rule:
            action_end = proposal["constraints"][0]["origin"]["end"]
            fallback_evidence = sorted(
                (
                    evidence
                    for evidence in proposal.get("lexical_evidence", [])
                    if evidence["start"] >= action_end
                ),
                key=lambda evidence: evidence["start"],
            )
            if fallback_evidence:
                evidence = fallback_evidence[0]
                head_lemma = evidence["surface"].casefold()
                head_rule = {
                    "requirement": evidence["requirement"],
                    "provenance": evidence["provenance"],
                }
        if head_lemma and head_rule:
            head_sorts = _sorts(head_rule["requirement"])
            frame_names = sorted(
                {frame["frame"] for frame in proposal.get("frames", [])}
            )
            capability = next(
                (
                    rule
                    for rule in language_rules.get(
                        "frame_argument_capabilities", []
                    )
                    if head_sorts.intersection(rule["argument_sorts"])
                    and (
                        not rule.get("frames")
                        or set(frame_names).intersection(rule["frames"])
                    )
                ),
                None,
            ) if enable_existential else None
            semantic_lemma = " ".join([proposal["action"], head_lemma])
            provenance_parts = [
                head_rule["provenance"],
                proposal["provenance"]["action"],
            ]
            if frame_names:
                provenance_parts.append("FrameNet:" + ",".join(frame_names))
            for projection in proposal.get("frame_role_projections", []):
                provenance_parts.append(projection["provenance"])
            for pattern in proposal.get("framenet_valence_patterns", []):
                provenance_parts.append(pattern["provenance"])
            if capability:
                payload = {
                    "requires_some": {
                        "relation": capability["relation"],
                        "requirement": capability["related_requirement"],
                    }
                }
                provenance_parts.append(capability["provenance"])
            else:
                payload = {
                    (
                        "prefers"
                        if action_is_preference
                        else "requires"
                    ): action_requirement
                }
                provenance_parts.append("frame-argument-compatibility:v1")
            constraints.append(
                {
                    "origin": _cumulative_origin(
                        proposal,
                        head_lemma,
                        "FrameArgument",
                        semantic_lemma,
                    ),
                    "payload": payload,
                    "provenance": "+".join(provenance_parts),
                }
            )

        relative_node = object_node
        if (
            isinstance(relative_node, GFNode)
            and relative_node.constructor in {"IndefCN", "DefCN"}
        ):
            relative_node = relative_node.arguments[0]
        if (
            proposal.get("role") == "ObjectHole"
            and isinstance(relative_node, GFNode)
            and relative_node.constructor in {"ModifyRel", "ModifyRelCN"}
        ):
            _, relative_verb, relative_object = relative_node.arguments
            relative_lemma = (
                gf_actions.get(relative_verb.constructor)
                if isinstance(relative_verb, GFNode)
                else None
            )
            relation_name = language_rules.get(
                "relation_lexicalizations", {}
            ).get(relative_lemma or "")
            object_lemma = _proper_lemma(relative_object)
            target_qids = (
                sorted(set(aliases.get(object_lemma.casefold(), [])))
                if object_lemma
                else []
            )
            if relative_lemma and relation_name and len(target_qids) == 1:
                constraints.append(
                    {
                        "origin": _cumulative_origin(
                            proposal,
                            object_lemma,
                            "FrameRelativeClause",
                            " ".join(
                                [
                                    proposal["action"],
                                    head_lemma or "target",
                                    "that",
                                    relative_lemma,
                                    object_lemma,
                                ]
                            ),
                        ),
                        "payload": {
                            "requires_relation": {
                                "relation": relation_name,
                                "target": target_qids[0],
                            }
                        },
                        "provenance": (
                            f"FrameNet:Relative_clause+"
                            f"relation-lexicalization:{relative_lemma}"
                        ),
                    }
                )

    # ConjClauseObject: a content word that is the object of the OTHER
    # Compl/PassCompl in a PredConjVP/PredOrConjVP coordination (shared
    # subject, guaranteed by that constructor's own shape -- see
    # coordinated_complements above). first_node already claimed the
    # FIRST Compl/PassCompl in the tree for the primary action; this is
    # only ever its coordinated sibling, never an unrelated Compl reached
    # through some other construction (e.g. a relative clause).
    #
    # Deliberately does NOT call lexical_head here (unlike the
    # FrameArgument code above) -- lexical_head strips a ModifyNP wrapper
    # to find the noun underneath, which would be unsafe for this
    # relation specifically: a real WiMCor sentence ("He attended
    # Gettysburg and received a Bachelor of Science degree AT the
    # University of Maryland...") shows the object can carry its own
    # location, explicitly naming a DIFFERENT institution than the
    # metonymy target -- the degree is from Maryland, not Gettysburg.
    # _noun_lemma only recognizes a BARE OpenIndefCN/OpenDefCN/
    # OpenAdjDefCN/OpenAdjIndefCN node (never a ModifyNP-wrapped one), so
    # skipping lexical_head means any object carrying its own modifier
    # -- benign ("with a double major...") or institution-redirecting
    # ("at the University of Maryland") alike -- safely declines to
    # match rather than risk the latter. (The Gettysburg sentence itself
    # is not buildable as a tree at all today regardless: "at the
    # University of Maryland" attaches to the verb "received", not to
    # "degree" -- a verb-level oblique PP, already documented in
    # build_gf_tree_from_dependencies.py as having no attachment point
    # in this grammar.)
    for extra_complement in coordinated_complements(root):
        if extra_complement is complement:
            continue
        extra_lemma = coordinated_object_lemma(extra_complement)
        if not extra_lemma:
            continue
        trigger = _lookup_context_trigger(
            context_triggers, "ConjClauseObject", extra_lemma
        )
        if trigger:
            constraints.append(
                _context_trigger_constraint(
                    proposal, extra_lemma, "ConjClauseObject", trigger
                )
            )

    def walk(node: GFNode | str) -> None:
        if not isinstance(node, GFNode):
            return
        if node.constructor in {"OpenAdjDefCN", "OpenAdjIndefCN"}:
            # Real corpus evaluation data (after the LLM tree-source tier
            # started building far more adjective-modified NPs than the
            # legacy GF-parser path ever did) showed this whole block
            # aborting compile_gf_constraints entirely for 38/150 ConMeC
            # rows (25% of the corpus) and a meaningful share of WiMCor.
            # Read directly: action_object_requirements below only ever
            # covered 3 actions (sign/announce/read) -- a narrow demo-
            # scale scope, never extended alongside the later VerbNet-
            # based action vocabulary (4499 real lemmas) -- so this was
            # always going to fail far more often than succeed on real
            # text, for almost any action outside those three, and
            # adjective_sorts's own 4-word coverage compounds it further.
            # FrameComposition is optional enrichment (an extra, narrowing
            # role constraint layered on top of the target's own core
            # action/role constraint, which first_node's independent
            # lookup already derives with no dependency on this block at
            # all) -- not being able to confidently compose one
            # adjective+noun pair should never discard every constraint
            # this tree could otherwise yield. Catching here and moving
            # on (safe under-generation -- fewer narrowing constraints,
            # never a wrong one) matches the same principle already
            # applied to the governing_start tree-builder's own "don't
            # represent the wrapper" choice
            # (build_gf_tree_from_dependencies.py).
            try:
                adjective, noun = node.arguments[:2]
                if not isinstance(adjective, str) or not isinstance(noun, str):
                    raise ValueError("malformed adjective-noun GF node")
                noun_rule = wordnet_rules.get("lexical_sorts", {}).get(
                    noun.casefold()
                )
                adjective_rule = wordnet_rules.get("adjective_sorts", {}).get(
                    adjective.casefold()
                )
                if not noun_rule or not adjective_rule:
                    raise ValueError(
                        f"unsupported GF adjective-noun semantics: {adjective} {noun}"
                    )
                noun_sorts = _sorts(noun_rule["requirement"])
                if len(noun_sorts) != 1:
                    raise ValueError(
                        f"ambiguous noun sort for GF composition: {noun}"
                    )
                noun_sort = next(iter(noun_sorts))
                action_rules = language_rules.get(
                    "action_object_requirements", {}
                ).get(proposal["action"], {})
                composition = next(
                    (
                        rule
                        for rule in language_rules.get("composition_matrix", [])
                        if rule["modifier_sort"] == adjective_rule["sort"]
                        and rule["noun_sort"] == noun_sort
                    ),
                    None,
                )
                if composition is None:
                    raise ValueError(
                        f"no semantic composition for "
                        f"{adjective_rule['sort']}×{noun_sort}"
                    )
                composed_rule = action_rules.get(composition["result_sort"])
                if composed_rule is None:
                    raise ValueError(
                        f"action {proposal['action']} has no role rule for "
                        f"{composition['result_sort']}"
                    )
                constraints.append(
                    {
                        "origin": _cumulative_origin(
                            proposal,
                            noun,
                            "FrameComposition",
                            " ".join(
                                [proposal["action"], adjective, noun]
                            ),
                        ),
                        "payload": {
                            "requires": composed_rule["candidate_requirement"]
                        },
                        "provenance": (
                            adjective_rule["provenance"]
                            + "+"
                            + composition["provenance"]
                            + "+"
                            + composed_rule["provenance"]
                        ),
                    }
                )
            except ValueError:
                pass

        if node.constructor == "ModifyNP" and len(node.arguments) == 2:
            head, modifier = node.arguments
            walk(head)
            # Grammar/Metonymy.gf's OnPP/AtPP/FromPP/ByPP/OverPP/UnderPP/
            # DuringPP/NearPP (added alongside AndS/OrS/AndNP/OrNP so more
            # real sentences can be GF-parsed at all -- see
            # docs/contextual-tower.md's "Coordination and arbitrary
            # prepositions" section for why parsing was the dominant
            # bottleneck) follow the same fixed-constructor-name shape as
            # the original four, so they slot into this table the same
            # way. A first attempt used one open-ended `PrepPP : String ->
            # NP -> PP` instead of eight fixed ones -- reverted after a
            # real CI run: GF's String category parses as "match any
            # token", which combined with the already-open OpenPN/Open*
            # family to create a genuine parse ambiguity ("the political
            # agreement" gained a spurious second reading as
            # OpenPN "the" + PrepPP "political" (OpenPN "agreement")),
            # breaking three existing tests. A closed, named set has no
            # such ambiguity -- each of these only ever matches its own
            # fixed word, exactly like the original four already did.
            pp_constructions = {
                "InPP": ("ModifyNP+InPP", "in"),
                "AboutPP": ("ModifyNP+AboutPP", "about"),
                "WithPP": ("ModifyNP+WithPP", "with"),
                "ForPP": ("ModifyNP+ForPP", "for"),
                "OnPP": ("ModifyNP+OnPP", "on"),
                "AtPP": ("ModifyNP+AtPP", "at"),
                "FromPP": ("ModifyNP+FromPP", "from"),
                "ByPP": ("ModifyNP+ByPP", "by"),
                "OverPP": ("ModifyNP+OverPP", "over"),
                "UnderPP": ("ModifyNP+UnderPP", "under"),
                "DuringPP": ("ModifyNP+DuringPP", "during"),
                "NearPP": ("ModifyNP+NearPP", "near"),
                "OfPP": ("ModifyNP+OfPP", "of"),
            }
            if (
                isinstance(modifier, GFNode)
                and modifier.constructor in pp_constructions
                and modifier.arguments
            ):
                resolved_head = lexical_head(head)
                head_lemma = _noun_lemma(resolved_head)
                if (
                    not head_lemma
                    and isinstance(resolved_head, GFNode)
                    and resolved_head.constructor in gf_nouns
                ):
                    head_lemma = gf_nouns[resolved_head.constructor]
                target_lemma = _proper_lemma(modifier.arguments[0])
                head_rule = (
                    wordnet_rules.get("lexical_sorts", {}).get(head_lemma.casefold())
                    if head_lemma
                    else None
                )
                if head_rule and target_lemma:
                    head_sorts = _sorts(head_rule["requirement"])
                    construction, preposition = pp_constructions[
                        modifier.constructor
                    ]
                    accepted_constructions = {construction}
                    template = next(
                        (
                            rule
                            for rule in language_rules.get("context_templates", [])
                            if rule["construction"] in accepted_constructions
                            and head_sorts.intersection(rule["head_sorts"])
                        ),
                        None,
                    )
                    if template:
                        qids = sorted(set(aliases.get(target_lemma.casefold(), [])))
                        if len(qids) != 1:
                            raise ValueError(
                                f"context modifier QID is not unique: {target_lemma}"
                            )
                        constraints.append(
                            {
                                "origin": _cumulative_origin(
                                    proposal,
                                    target_lemma,
                                    "FrameModifier",
                                    " ".join(
                                        [
                                            proposal["action"],
                                            head_lemma,
                                            preposition,
                                            target_lemma,
                                        ]
                                    ),
                                ),
                                "payload": {
                                    (
                                        "prefers_relation"
                                        if template.get("strength")
                                        == "SelectionalPreference"
                                        else "requires_relation"
                                    ): {
                                        "relation": template["relation"],
                                        "target": qids[0],
                                    }
                                },
                                "provenance": (
                                    head_rule["provenance"]
                                    + "+"
                                    + template["provenance"]
                                ),
                            }
                        )
                # ModifyNPObject: the modifier's object is a common noun
                # (not the proper-noun/entity case handled above --
                # _proper_lemma returns None for it, so target_lemma is
                # None and the QID-relation branch above is a no-op) --
                # look it up directly as a target-sort trigger instead of
                # trying to resolve it to a Wikidata entity at all.
                modifier_common_lemma = _noun_lemma(modifier.arguments[0])
                if modifier_common_lemma:
                    modifier_trigger = _lookup_context_trigger(
                        context_triggers, "ModifyNPObject", modifier_common_lemma
                    )
                    if modifier_trigger:
                        constraints.append(
                            _context_trigger_constraint(
                                proposal,
                                modifier_common_lemma,
                                "ModifyNPObject",
                                modifier_trigger,
                            )
                        )
            return
        for argument in node.arguments:
            walk(argument)

    walk(root)
    return constraints
