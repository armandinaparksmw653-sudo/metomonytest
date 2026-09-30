#!/usr/bin/env python3
"""Generate GF abstract and English lexicon modules from the data snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


def gf_suffix(identifier: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in identifier)


def gf_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def possessive(label: str) -> str:
    return f"{label}'" if label.endswith("s") else f"{label}'s"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def contextual_action_functions(
    predicates: list[dict[str, str]],
    action_roles: list[dict[str, str]],
) -> list[dict[str, str]]:
    represented = {
        row["lemma"].casefold().replace("_", " "): row["gf_function"]
        for row in predicates
    }
    represented.update(
        {
            "announce": "Announce",
            "read": "Read",
            "drink": "Drink",
            "sign": "Sign",
        }
    )
    contextual_lemmas = sorted(
        {
            row["lemma"].casefold().replace("_", " ")
            for row in action_roles
            if row["mapping_status"] == "compiled"
            and row["hole_role"] in {"SubjectHole", "ObjectHole"}
            and row["requirement"] not in {"", "null"}
        }
        - represented.keys()
    )
    generated = {
        lemma: f"CTX_{hashlib.sha256(lemma.encode()).hexdigest()[:16]}"
        for lemma in contextual_lemmas
    }
    return [
        {"lemma": lemma, "gf_function": function}
        for lemma, function in sorted((represented | generated).items())
    ]


def contextual_noun_functions(wordnet_rules: dict) -> list[dict[str, str]]:
    lemmas = sorted(
        lemma
        for lemma in wordnet_rules.get("lexical_sorts", {})
        if re.fullmatch(r"[a-z][a-z '-]{1,48}", lemma)
    )
    return [
        {
            "lemma": lemma,
            "gf_function": (
                "WN_" + hashlib.sha256(lemma.encode()).hexdigest()[:16]
            ),
        }
        for lemma in lemmas
    ]


def generate(
    rows: list[dict[str, str]],
    semantic_entities: list[dict[str, str]],
    predicates: list[dict[str, str]],
    action_roles: list[dict[str, str]],
    wordnet_rules: dict,
) -> tuple[str, str]:
    authors: dict[str, str] = {}
    works: dict[str, str] = {}
    for row in rows:
        authors[row["author_id"]] = row["author_label"]
        works[row["work_id"]] = row["work_label"]

    declarations: list[str] = []
    linearizations: list[str] = []

    for identifier, label in sorted(authors.items()):
        suffix = gf_suffix(identifier)
        declarations.extend(
            [
                f"    Author_{suffix} : NP ;",
                f"    Works_{suffix} : NP ;",
            ]
        )
        linearizations.extend(
            [
                f'    Author_{suffix} = mkNP (mkPN "{gf_string(label)}") ;',
                (
                    f'    Works_{suffix} = mkNP (mkPN "'
                    f'{gf_string(possessive(label) + " works")}") ;'
                ),
            ]
        )

    for identifier, label in sorted(works.items()):
        suffix = gf_suffix(identifier)
        declarations.append(f"    Work_{suffix} : NP ;")
        linearizations.append(
            f'    Work_{suffix} = mkNP (mkPN "{gf_string(label)}") ;'
        )

    for row in sorted(semantic_entities, key=lambda item: item["gf_function"]):
        function = row["gf_function"]
        declarations.append(f"    {function} : NP ;")
        linearizations.append(
            f'    {function} = mkNP (mkPN "{gf_string(row["label"])}") ;'
        )

    base_predicates = {"Read", "Drink", "Sign"}
    for row in predicates:
        function = row["gf_function"]
        if function in base_predicates:
            continue
        declarations.append(f"    {function} : V2 ;")
        linearizations.append(
            f'    {function} = {row["gf_expression"]} ;'
        )

    action_functions = contextual_action_functions(predicates, action_roles)
    predicate_functions = {row["gf_function"] for row in predicates} | base_predicates | {"Announce"}
    for action in action_functions:
        function = action["gf_function"]
        if function in predicate_functions:
            continue
        lemma = action["lemma"]
        declarations.append(f"    {function} : V2 ;")
        linearizations.append(
            f'    {function} = mkV2 "{gf_string(lemma)}" ;'
        )
    for noun in contextual_noun_functions(wordnet_rules):
        declarations.append(f'    {noun["gf_function"]} : CN ;')
        linearizations.append(
            f'    {noun["gf_function"]} = mkCN (mkN "'
            f'{gf_string(noun["lemma"])}") ;'
        )

    abstract = "\n".join(
        [
            "abstract GeneratedMetonymy = Metonymy ** {",
            "  fun",
            *declarations,
            "}",
            "",
        ]
    )
    concrete = "\n".join(
        [
            "concrete GeneratedMetonymyEng of GeneratedMetonymy =",
            "  MetonymyEng ** open SyntaxEng, ParadigmsEng in {",
            "  lin",
            *linearizations,
            "}",
            "",
        ]
    )
    return abstract, concrete


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("auxiliary/data/wikidata-author-works.tsv"),
    )
    parser.add_argument(
        "--semantic-entities",
        type=Path,
        default=Path("auxiliary/data/semantic-entities.tsv"),
    )
    parser.add_argument(
        "--predicates",
        type=Path,
        default=Path("auxiliary/data/predicates.tsv"),
    )
    parser.add_argument(
        "--verbnet-predicates",
        type=Path,
        default=Path("auxiliary/data/verbnet-predicates.tsv"),
    )
    parser.add_argument(
        "--verbnet-action-roles",
        type=Path,
        default=Path("auxiliary/data/verbnet-action-roles.tsv"),
    )
    parser.add_argument(
        "--abstract-output",
        type=Path,
        default=Path("auxiliary/grammar/GeneratedMetonymy.gf"),
    )
    parser.add_argument(
        "--concrete-output",
        type=Path,
        default=Path("auxiliary/grammar/GeneratedMetonymyEng.gf"),
    )
    parser.add_argument(
        "--action-map-output",
        type=Path,
        default=Path("auxiliary/data/contextual-gf-actions.json"),
    )
    parser.add_argument(
        "--wordnet-rules",
        type=Path,
        default=Path("auxiliary/data/wordnet-context-rules.json"),
    )
    parser.add_argument(
        "--noun-map-output",
        type=Path,
        default=Path("auxiliary/data/contextual-gf-nouns.json"),
    )
    arguments = parser.parse_args()

    predicates = read_rows(arguments.predicates) + read_rows(
        arguments.verbnet_predicates
    )
    action_roles = read_rows(arguments.verbnet_action_roles)
    wordnet_rules = json.loads(
        arguments.wordnet_rules.read_text(encoding="utf-8")
    )
    abstract, concrete = generate(
        read_rows(arguments.input),
        read_rows(arguments.semantic_entities),
        predicates,
        action_roles,
        wordnet_rules,
    )
    arguments.abstract_output.write_text(abstract, encoding="utf-8")
    arguments.concrete_output.write_text(concrete, encoding="utf-8")
    arguments.action_map_output.write_text(
        json.dumps(
            {
                "schema_version": "contextual-gf-actions-1",
                "actions": contextual_action_functions(predicates, action_roles),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    arguments.noun_map_output.write_text(
        json.dumps(
            {
                "schema_version": "contextual-gf-nouns-1",
                "nouns": contextual_noun_functions(wordnet_rules),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"generated {arguments.abstract_output} and {arguments.concrete_output}"
    )


if __name__ == "__main__":
    main()
