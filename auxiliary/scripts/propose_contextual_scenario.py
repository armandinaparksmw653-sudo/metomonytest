#!/usr/bin/env python3
"""Propose a lexicalized contextual scenario from text and an offline snapshot."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from contextual_rule_compiler import (
    load_action_frames,
    load_action_roles,
    resolve_action,
)


def rows(path: Path):
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
COMMON_ABBREVIATIONS = (
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "St.", "vs.", "etc.",
    "Jr.", "Sr.", "Inc.", "Ltd.", "Co.", "U.S.", "U.K.",
)


def sentence_span_containing(text: str, start: int, end: int) -> tuple[int, int]:
    """The [span_start, span_end) of the single sentence containing
    [start, end) within a larger, possibly multi-sentence text.

    WiMCor/ConMeC's "sentence" field is really a discourse-level excerpt
    -- often several sentences long (a real corpus-driven sample went up
    to 21) -- kept that way on purpose, since lexical_evidence below
    deliberately scans the *whole* excerpt for context clues. But
    Metonymy.gf's abstract syntax has exactly one clause-level category
    (`flags startcat = S`, a handful of Pred/Compl-style constructions,
    nothing above sentence level), so feeding the entire excerpt to
    `engine parse` was asking a single-sentence grammar to parse an
    entire paragraph -- confirmed locally by running this script's own
    resolve_action against the real corpus-driven sample: every
    gf_sentence produced was the full multi-sentence excerpt, verb
    substituted in place, structurally unparseable as one `S` regardless
    of vocabulary or construction coverage. This narrows gf_sentence to
    just the sentence containing the action's own span, using a simple
    period/question/exclamation-mark-plus-capital-letter heuristic (a
    short common-abbreviation list reduces false splits, e.g. "Dr. Smith"
    or "U.S. forces"). Deliberately does not touch action["start"]/["end"]
    themselves, proposal["sentence"], or anything compile_gf_constraints
    later searches within -- those stay relative to the full excerpt,
    unaffected by this. Falls back to the whole text if start/end don't
    fall inside any computed span (should not happen, but never narrows
    to something that would exclude the action itself).
    """
    boundaries = [0]
    for match in SENTENCE_BOUNDARY.finditer(text):
        preceding = text[: match.start()]
        if any(preceding.endswith(abbreviation) for abbreviation in COMMON_ABBREVIATIONS):
            continue
        boundaries.append(match.end())
    boundaries.append(len(text))
    for span_start, span_end in zip(boundaries, boundaries[1:]):
        if span_start <= start and end <= span_end:
            return span_start, span_end
    return 0, len(text)


def load_framenet_snapshot(path: Path, lemma: str) -> tuple[list[dict], list[dict]]:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    lexical_units = [
        row
        for row in rows(path / "lexical-units.jsonl")
        if row["name"].rsplit(".", 1)[0].casefold() == lemma.casefold()
    ]
    identifiers = {row["id"] for row in lexical_units}
    patterns = [
        row
        for row in rows(path / "valence-patterns.jsonl")
        if row["lexical_unit_id"] in identifiers
    ]
    frames = [
        {
            "frame": row["frame"],
            "action_id": f"FrameNet-LU:{row['id']}",
            "provenance": (
                f"{row['provenance']}:snapshot:{manifest['source_sha256']}"
            ),
        }
        for row in lexical_units
    ]
    return frames, patterns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--sentence", required=True)
    parser.add_argument("--source")
    parser.add_argument(
        "--linker-cache",
        type=Path,
        help="frozen exact-alias cache produced by build_wikidata_linker_cache.py",
    )
    parser.add_argument("--target-surface")
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path("auxiliary/data/contextual-language-rules.json"),
    )
    parser.add_argument(
        "--wordnet-rules",
        type=Path,
        default=Path("auxiliary/data/wordnet-context-rules.json"),
    )
    parser.add_argument(
        "--predicates",
        type=Path,
        default=Path("auxiliary/data/predicates.tsv"),
    )
    parser.add_argument(
        "--verbnet-action-roles",
        type=Path,
        default=Path("auxiliary/data/verbnet-action-roles.tsv"),
    )
    parser.add_argument(
        "--verbnet-actions",
        type=Path,
        default=Path("auxiliary/data/verbnet-actions.tsv"),
    )
    parser.add_argument(
        "--framenet-capabilities",
        type=Path,
        default=Path("auxiliary/data/framenet-role-capabilities.json"),
    )
    parser.add_argument("--disable-framenet", action="store_true")
    parser.add_argument("--framenet-snapshot", type=Path)
    parser.add_argument(
        "--dependency-hint",
        help=(
            "compact JSON object with dep_status/hole_role/governing_lemma/"
            "governing_start/governing_end, precomputed by "
            "annotate_dependency_hints.py"
        ),
    )
    args = parser.parse_args()
    dependency_hint = (
        json.loads(args.dependency_hint) if args.dependency_hint else None
    )
    aliases = {}
    for row in rows(args.snapshot / "aliases.jsonl"):
        aliases.setdefault(row["alias"].casefold(), []).append(row["id"])
    manifest = json.loads((args.snapshot / "manifest.json").read_text())
    snapshot_rules = json.loads(
        (args.snapshot / "rules.json").read_text(encoding="utf-8")
    )
    language_rules = json.loads(args.rules.read_text(encoding="utf-8"))
    wordnet_rules = (
        json.loads(args.wordnet_rules.read_text(encoding="utf-8"))
        if args.wordnet_rules.exists()
        else None
    )
    tokens = list(re.finditer(r"[A-Za-z][A-Za-z'-]*", args.sentence))
    source_text = args.source or args.target_surface
    if not source_text:
        source_text = tokens[0].group() if tokens else ""
    action_roles = load_action_roles(
        args.predicates, args.verbnet_action_roles
    )
    try:
        action = resolve_action(
            args.sentence,
            [value for value in (args.target_surface, source_text) if value],
            action_roles,
            language_rules.get(
                "morphology_overrides",
                language_rules.get("actions", {}),
            ),
            dependency_hint=dependency_hint,
            wordnet_rules=wordnet_rules,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    lemma = action["lemma"]
    role = action["role"]
    requirement = action["requirement"]
    candidates = aliases.get(source_text.casefold(), [])
    linker_provenance = None
    if not candidates and args.linker_cache:
        cache = json.loads(args.linker_cache.read_text(encoding="utf-8"))
        if cache.get("schema_version") != "wikidata-linker-cache-1":
            raise SystemExit("unsupported-linker-cache-schema")
        linked = [
            row
            for row in cache["resolved"]
            if row["normalized"] == " ".join(source_text.casefold().split())
        ]
        candidates = sorted({row["id"] for row in linked})
        linker_provenance = (
            linked[0]["provenance"] if len(linked) == 1 else None
        )
    action_frames = (
        []
        if args.disable_framenet
        else load_action_frames(args.verbnet_actions).get(lemma, [])
    )
    framenet_valence_patterns = []
    if (
        not args.disable_framenet
        and args.framenet_snapshot
        and (args.framenet_snapshot / "manifest.json").exists()
    ):
        imported_frames, framenet_valence_patterns = load_framenet_snapshot(
            args.framenet_snapshot, lemma
        )
        action_frames = imported_frames or action_frames
    frame_names = {frame["frame"] for frame in action_frames}
    frame_capabilities = (
        json.loads(args.framenet_capabilities.read_text(encoding="utf-8"))
        if not args.disable_framenet and args.framenet_capabilities.exists()
        else {"projections": []}
    )
    matching_frame_projections = [
        projection
        for projection in frame_capabilities.get("projections", [])
        if projection["frame"] in frame_names
        and projection["hole_role"] == role
    ]
    snapshot_relations = list(
        dict.fromkeys(rule["internal"] for rule in snapshot_rules["relations"])
    )
    requirement_sorts = set(
        re.findall(r"HasSort ([A-Za-z][A-Za-z0-9]*)", requirement)
    )
    configured_relations = [
        relation
        for sort_name in sorted(requirement_sorts)
        for relation in language_rules.get("bridge_relations_by_sort", {}).get(
            sort_name, []
        )
    ]
    bridge_relations = [
        relation
        for relation in dict.fromkeys(configured_relations)
        if relation in snapshot_relations
    ] or snapshot_relations
    gf_scope_start, gf_scope_end = sentence_span_containing(
        args.sentence, action["start"], action["end"]
    )
    proposal = {
        "schema_version": "contextual-scenario-proposal-1",
        "graph_sha256": manifest["graph_sha256"],
        "sentence": args.sentence,
        "gf_sentence": (
            args.sentence[gf_scope_start : action["start"]]
            + action["gf_form"]
            + args.sentence[action["end"] : gf_scope_end]
        ),
        "source_surface": source_text,
        "source_qid_candidates": sorted(candidates),
        "action": lemma,
        "frames": action_frames,
        "frame_role_projections": matching_frame_projections,
        "framenet_valence_patterns": framenet_valence_patterns,
        "role": role,
        "bridge_relations": bridge_relations,
        "max_depth": language_rules.get("max_bridge_depth", 1),
        "provenance": {
            "action": action["provenance"],
            "action_strength_policy": action["strength"],
            "action_evidence": action["evidence"],
            "rules": language_rules["schema_version"],
            **(
                {"entity_linker": linker_provenance}
                if linker_provenance
                else {}
            ),
        },
        "constraints": [
            {
                "origin": {
                    "constructor": "Verb",
                    "lemma": lemma,
                    "surface": action["surface"],
                    "start": action["start"],
                    "end": action["end"],
                },
                "payload": {
                    (
                        "requires"
                        if action["strength"] == "hard"
                        else "prefers"
                    ): requirement
                },
                "provenance": action["provenance"],
            }
        ],
    }
    if wordnet_rules is not None:
        lexical_evidence = []
        for match in tokens:
            lexical_rule = wordnet_rules.get("lexical_sorts", {}).get(
                match.group().casefold()
            )
            if lexical_rule:
                lexical_evidence.append(
                    {
                        "surface": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        **lexical_rule,
                    }
                )
        proposal["lexical_evidence"] = lexical_evidence
        proposal["provenance"]["wordnet"] = wordnet_rules["schema_version"]
    # Historically this required exactly one candidate: an ambiguous source
    # surface (more than one Wikidata item sharing the same exact label --
    # extremely common for place names, see data/SOURCES.md's entity-linking
    # section) aborted the whole pipeline here, before the contextual tower
    # ever ran. That meant the tower's own per-layer narrowing -- exactly
    # the mechanism that should be disambiguating "does this Liverpool have
    # a university connected to it via the roles this sentence needs" --
    # never got a chance to run on any of the ambiguous candidates. Now this
    # proposer only gates on the source resolving to *some* candidate at
    # all; run_automatic_contextual_pipeline.py runs the (candidate-
    # independent) action/GF-parse/constraint-compilation stages once and
    # then the tower once per candidate QID, keeping only the ones whose
    # own contextual fiber survives non-empty -- see its own module
    # docstring for the exact three-way outcome.
    proposal["status"] = "ready" if candidates else "source-qid-unresolved"
    print(json.dumps(proposal, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
