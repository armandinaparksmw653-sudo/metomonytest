#!/usr/bin/env python3
"""Extract useful transitive selectional preferences from VerbNet 3.4."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

VERBNET_REPOSITORY = "https://github.com/cu-clear/verbnet.git"
VERBNET_COMMIT = "ae8e9cfdc2c0d3414b748763612f1a0a34194cc1"

RESTRICTION_SORTS = {
    "garment": "Wearable",
}

FRAMENET_SORTS = {
    "Reading_perception": "Readable",
    "Scrutiny": "Readable",
    "Ingestion": "Edible",
    "Ingest_substance": "Edible",
    "Wearing": "Wearable",
}

CLASS_SORTS = {
    "eat-39.1": "Edible",
    "devour-39.4": "Edible",
    "gobble-39.3": "Edible",
    "gorge-39.6": "Edible",
}

LEMMA_SORTS = {
    "hear": "Audible",
    "overhear": "Audible",
    "listen": "Audible",
    "behold": "Watchable",
    "glimpse": "Watchable",
    "notice": "Watchable",
    "observe": "Watchable",
    "see": "Watchable",
    "view": "Watchable",
    "watch": "Watchable",
    "witness": "Watchable",
}

FEATURE_SORTS = {
    "+liquid": "Drinkable",
    "+solid": "Edible",
    "+substance": "Edible",
}

SORT_PRIORITY = {
    "Drinkable": 0,
    "Edible": 1,
    "Wearable": 2,
    "Audible": 3,
    "Watchable": 4,
    "Readable": 5,
}

EXCLUDED_POLYSEMOUS_LEMMAS = {
    "bolt",
    "down",
    "gum",
    "have",
    "inject",
    "mainline",
    "nurse",
    "peck",
    "pick",
    "smoke",
    "snort",
    "suck",
    "swill",
    "take",
    "teethe",
    "use",
    "vape",
}


@dataclass(frozen=True)
class ImportedPredicate:
    lemma: str
    object_sort: str
    class_id: str
    reason: str


@dataclass(frozen=True)
class ImportedAction:
    action_id: str
    lemma: str
    verbnet_key: str
    class_id: str
    wordnet_senses: str
    propbank_groupings: str
    framenet_frames: str
    provenance: str


@dataclass(frozen=True)
class ImportedActionRole:
    action_id: str
    lemma: str
    frame_id: str
    thematic_role: str
    hole_role: str
    requirement: str
    strength: str
    mapping_status: str
    provenance: str


def ensure_source(path: Path) -> Path:
    if not (path / ".git").exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--no-checkout", VERBNET_REPOSITORY, str(path)],
            check=True,
        )
    subprocess.run(
        ["git", "-C", str(path), "fetch", "--depth", "1", "origin", VERBNET_COMMIT],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "checkout", "--detach", VERBNET_COMMIT],
        check=True,
    )
    return path / "verbnet3.4"


def existing_lemmas(path: Path) -> set[str]:
    with path.open(encoding="utf-8", newline="") as source:
        return {
            row["lemma"].replace(" ", "_")
            for row in csv.DictReader(source, delimiter="\t")
        }


def role_restrictions(node: ET.Element) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    roles = node.find("THEMROLES")
    if roles is None:
        return result
    for role in roles.findall("THEMROLE"):
        role_name = role.get("type", "")
        result[role_name] = {
            restriction.get("type", "")
            for restriction in role.findall(".//SELRESTR")
            if restriction.get("Value") == "+"
        }
    return result


def transitive_object_roles(node: ET.Element) -> set[str]:
    roles: set[str] = set()
    frames = node.find("FRAMES")
    if frames is None:
        return roles
    for frame in frames.findall("FRAME"):
        syntax = frame.find("SYNTAX")
        if syntax is None:
            continue
        seen_verb = False
        for element in list(syntax):
            if element.tag == "VERB":
                seen_verb = True
            elif seen_verb and element.tag == "NP":
                roles.add(element.get("value", ""))
                break
            elif seen_verb and element.tag not in {"ADV", "LEX"}:
                break
    return roles


def class_sort(class_id: str) -> str | None:
    for prefix, target_sort in CLASS_SORTS.items():
        if class_id.startswith(prefix):
            return target_sort
    return None


def member_sort(
    member: ET.Element,
    class_id: str,
    restrictions: set[str],
) -> tuple[str, str] | None:
    lemma = member.get("name", "")
    features = set(member.get("features", "").split())
    for feature in features:
        if feature in FEATURE_SORTS:
            return FEATURE_SORTS[feature], f"member-feature:{feature}"
    if features:
        return None

    if lemma in LEMMA_SORTS:
        return LEMMA_SORTS[lemma], f"lemma-map:{lemma}"

    frame_mapping = member.get("fn_mapping", "")
    if frame_mapping in FRAMENET_SORTS:
        return FRAMENET_SORTS[frame_mapping], f"frame-map:{frame_mapping}"

    for restriction in sorted(restrictions):
        if restriction in RESTRICTION_SORTS:
            return (
                RESTRICTION_SORTS[restriction],
                f"selectional-preference:+{restriction}",
            )

    mapped_class = class_sort(class_id)
    if mapped_class is not None:
        return mapped_class, f"class-map:{class_id}"
    return None


def collect_from_node(
    node: ET.Element,
    inherited_roles: dict[str, set[str]],
    inherited_transitive_roles: set[str],
) -> list[ImportedPredicate]:
    class_id = node.get("ID", "")
    roles = {name: set(values) for name, values in inherited_roles.items()}
    roles.update(role_restrictions(node))

    local_object_roles = transitive_object_roles(node)
    object_roles = local_object_roles or inherited_transitive_roles
    restrictions = {
        restriction
        for role in object_roles
        for restriction in roles.get(role, set())
    }

    imported: list[ImportedPredicate] = []
    if object_roles:
        members = node.find("MEMBERS")
        if members is not None:
            for member in members.findall("MEMBER"):
                lemma = member.get("name", "")
                if not re.fullmatch(r"[a-z]+", lemma):
                    continue
                mapped = member_sort(member, class_id, restrictions)
                if mapped is None:
                    continue
                target_sort, reason = mapped
                imported.append(
                    ImportedPredicate(lemma, target_sort, class_id, reason)
                )

    subclasses = node.find("SUBCLASSES")
    if subclasses is not None:
        for subclass in subclasses.findall("VNSUBCLASS"):
            imported.extend(
                collect_from_node(subclass, roles, object_roles)
            )
    return imported


def extract(source: Path, excluded: set[str]) -> list[ImportedPredicate]:
    candidates: list[ImportedPredicate] = []
    for xml_path in sorted(source.glob("*.xml")):
        root = ET.parse(xml_path).getroot()
        candidates.extend(collect_from_node(root, {}, set()))

    by_lemma: dict[str, ImportedPredicate] = {}
    for candidate in candidates:
        if (
            candidate.lemma in excluded
            or candidate.lemma in EXCLUDED_POLYSEMOUS_LEMMAS
        ):
            continue
        previous = by_lemma.get(candidate.lemma)
        if previous is None or (
            SORT_PRIORITY[candidate.object_sort],
            candidate.class_id,
        ) < (
            SORT_PRIORITY[previous.object_sort],
            previous.class_id,
        ):
            by_lemma[candidate.lemma] = candidate
    return sorted(by_lemma.values(), key=lambda item: item.lemma)


def gf_function(lemma: str) -> str:
    return "VN_" + "".join(part.capitalize() for part in lemma.split("_"))


def write_snapshot(path: Path, predicates: list[ImportedPredicate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "predicate_id",
                "lemma",
                "gf_function",
                "subject_sort",
                "object_sort",
                "strength",
                "gf_expression",
                "provenance",
            ]
        )
        for predicate in predicates:
            writer.writerow(
                [
                    f"verbnet-{predicate.lemma}",
                    predicate.lemma,
                    gf_function(predicate.lemma),
                    "Human",
                    predicate.object_sort,
                    "SelectionalPreference",
                    f'mkV2 "{predicate.lemma}"',
                    (
                        f"VerbNet-3.4:{VERBNET_COMMIT}:"
                        f"{predicate.class_id}:{predicate.reason}"
                    ),
                ]
            )


AUDITED_ROLE_SORTS = {
    "human": "Human",
    "animate": "Animate",
    "organization": "Organization",
    "location": "Place",
    "eventive": "Event",
    "garment": "Wearable",
    "comestible": "Edible",
    "sound": "Audible",
    # Direct correspondence to an existing sort, same confidence as the
    # entries above.
    "region": "Place",
    "communication": "CommunicationContent",
    "animal": "Animate",
    # Weaker, deliberate calls (see data/SOURCES.md's VerbNet section):
    # render_requirement rejects a whole AnyOf/AllOf expression if *any*
    # leaf restriction is unmapped, so "concrete" alone blocked thousands
    # of rows whose *other* restrictions (animate/organization/location,
    # all already mapped above) were perfectly fine -- e.g. real WiMCor/
    # ConMeC sentences that go unsupported-action-role today. "concrete" is
    # VerbNet's broadest category (a physical, non-abstract entity); Entity
    # is this project's own top sort, so HasSort Entity is close to vacuous
    # as a filter on its own -- the actual selectivity for these roles
    # comes from whatever object/composition constraints apply downstream
    # (frame_argument_capabilities, composition_matrix), not from this
    # requirement. Compiled-but-weak was chosen over staying uncompiled: an
    # uncompiled role can never contribute to resolve_action at all, so it
    # silently discards real coverage rather than admitting a broad one.
    "concrete": "Entity",
    # int_control is VerbNet's own "intentional control" marker (the
    # argument acts deliberately), not an entity-type restriction at all --
    # but a role restricted to int_control entities is, in practice, almost
    # always a volitional agent in VerbNet's own frames.
    "int_control": "Agent",
}

THEMATIC_ROLE_DEFAULTS = {
    "Actor": "Agent",
    "Agent": "Agent",
    "Speaker": "Agent",
    "Experiencer": "Human",
    "Recipient": "Human",
    # Same weak-but-compiled reasoning as AUDITED_ROLE_SORTS["concrete"]
    # above, applied to roles VerbNet gives *no* restriction at all: Entity
    # (this project's own top sort) makes these compiled rather than
    # silently dropped, with real selectivity coming from whatever
    # downstream constraint actually applies to the argument.
    "Theme": "Entity",
    "Patient": "Entity",
    "Result": "Entity",
    "Stimulus": "Entity",
    "Location": "Entity",
    "Topic": "Entity",
    "Instrument": "Entity",
    "Attribute": "Entity",
    "Product": "Entity",
    "Source": "Entity",
    "Extent": "Entity",
    "Initial_State": "Entity",
    "Eventuality": "Entity",
    "Goal": "Entity",
    "Causer": "Entity",
    "Pivot": "Entity",
    "Destination": "Entity",
    "Value": "Entity",
    "Material": "Entity",
    "Co-Theme": "Entity",
}


def restriction_expression(element: ET.Element | None) -> dict | None:
    if element is None:
        return None
    if element.tag == "SELRESTR":
        return {
            "op": "atom",
            "sign": element.get("Value", ""),
            "type": element.get("type", ""),
        }
    children = [
        parsed
        for child in list(element)
        if (parsed := restriction_expression(child)) is not None
    ]
    if not children:
        return None
    logic = element.get("logic", "and").lower()
    return {"op": "any" if logic == "or" else "all", "args": children}


def effective_role_requirements(
    node: ET.Element,
    inherited: dict[str, dict | None],
) -> dict[str, dict | None]:
    result = dict(inherited)
    roles = node.find("THEMROLES")
    if roles is None:
        return result
    for role in roles.findall("THEMROLE"):
        result[role.get("type", "")] = restriction_expression(
            role.find("SELRESTRS")
        )
    return result


def render_requirement(expression: dict | None, role: str) -> str | None:
    if expression is None:
        default_sort = THEMATIC_ROLE_DEFAULTS.get(role)
        return f"HasSort {default_sort}" if default_sort else None
    operation = expression["op"]
    if operation == "atom":
        target_sort = AUDITED_ROLE_SORTS.get(expression["type"])
        if target_sort is None:
            return None
        base = f"HasSort {target_sort}"
        return base if expression["sign"] != "-" else f"Not ({base})"
    rendered = [render_requirement(child, role) for child in expression["args"]]
    if any(value is None for value in rendered):
        return None
    values = [value for value in rendered if value is not None]
    if len(values) == 1:
        return values[0]
    constructor = "AnyOf" if operation == "any" else "AllOf"
    return f"{constructor} [{','.join(values)}]"


def frame_realizations(frame: ET.Element) -> list[tuple[str, str]]:
    syntax = frame.find("SYNTAX")
    if syntax is None:
        return []
    before_verb: list[str] = []
    after_verb: list[str] = []
    seen_verb = False
    for element in list(syntax):
        if element.tag == "VERB":
            seen_verb = True
        elif element.tag == "NP":
            role = element.get("value", "")
            (after_verb if seen_verb else before_verb).append(role)
    realizations: list[tuple[str, str]] = []
    if before_verb:
        realizations.append((before_verb[0], "SubjectHole"))
    if after_verb:
        realizations.append((after_verb[0], "ObjectHole"))
        realizations.extend(
            (role, f"PostVerbHole{index}")
            for index, role in enumerate(after_verb[1:], 2)
        )
    return realizations


def frame_identity(class_id: str, frame: ET.Element) -> str:
    canonical = ET.tostring(frame, encoding="utf-8")
    digest = hashlib.sha256(canonical).hexdigest()[:16]
    return f"{class_id}:frame:{digest}"


def action_identity(class_id: str, lemma: str, verbnet_key: str) -> str:
    stable_key = verbnet_key or lemma
    digest = hashlib.sha256(f"{class_id}\0{stable_key}".encode()).hexdigest()[:16]
    return f"vn34:{class_id}:{digest}"


def collect_action_roles(
    node: ET.Element,
    inherited_requirements: dict[str, dict | None],
    inherited_frames: list[tuple[str, list[tuple[str, str]]]],
) -> tuple[list[ImportedAction], list[ImportedActionRole]]:
    class_id = node.get("ID", "")
    requirements = effective_role_requirements(node, inherited_requirements)
    frames_node = node.find("FRAMES")
    local_frames = (
        [
            (frame_identity(class_id, frame), frame_realizations(frame))
            for frame in frames_node.findall("FRAME")
        ]
        if frames_node is not None
        else []
    )
    frames = [frame for frame in local_frames if frame[1]] or inherited_frames
    actions: list[ImportedAction] = []
    action_roles: list[ImportedActionRole] = []
    members = node.find("MEMBERS")
    if members is not None:
        for member in members.findall("MEMBER"):
            lemma = member.get("name", "")
            if not lemma:
                continue
            verbnet_key = member.get("verbnet_key", "")
            identifier = action_identity(class_id, lemma, verbnet_key)
            provenance = f"VerbNet-3.4:{VERBNET_COMMIT}:{class_id}"
            actions.append(
                ImportedAction(
                    action_id=identifier,
                    lemma=lemma,
                    verbnet_key=verbnet_key,
                    class_id=class_id,
                    wordnet_senses=json.dumps(
                        sorted(filter(None, member.get("wn", "").split())),
                        separators=(",", ":"),
                    ),
                    propbank_groupings=json.dumps(
                        sorted(filter(None, member.get("grouping", "").split())),
                        separators=(",", ":"),
                    ),
                    framenet_frames=json.dumps(
                        sorted(filter(None, member.get("fn_mapping", "").split())),
                        separators=(",", ":"),
                    ),
                    provenance=provenance,
                )
            )
            for frame_id, realizations in frames:
                for role, hole in realizations:
                    expression = requirements.get(role)
                    compiled = render_requirement(expression, role)
                    executable = hole in {"SubjectHole", "ObjectHole"}
                    status = "compiled" if compiled and executable else "uncompiled"
                    action_roles.append(
                        ImportedActionRole(
                            action_id=identifier,
                            lemma=lemma,
                            frame_id=frame_id,
                            thematic_role=role,
                            hole_role=hole,
                            requirement=compiled
                            or json.dumps(expression, sort_keys=True, separators=(",", ":")),
                            strength="SelectionalPreference",
                            mapping_status=status,
                            provenance=(
                                f"{provenance}:role:{role}:"
                                f"{'audited-projection-v1' if compiled else 'lossless-v1'}"
                            ),
                        )
                    )
    subclasses = node.find("SUBCLASSES")
    if subclasses is not None:
        for subclass in subclasses.findall("VNSUBCLASS"):
            child_actions, child_roles = collect_action_roles(
                subclass, requirements, frames
            )
            actions.extend(child_actions)
            action_roles.extend(child_roles)
    return actions, action_roles


def extract_action_roles(
    source: Path,
) -> tuple[list[ImportedAction], list[ImportedActionRole]]:
    actions: list[ImportedAction] = []
    roles: list[ImportedActionRole] = []
    for xml_path in sorted(source.glob("*.xml")):
        root = ET.parse(xml_path).getroot()
        extracted_actions, extracted_roles = collect_action_roles(root, {}, [])
        actions.extend(extracted_actions)
        roles.extend(extracted_roles)
    unique_actions = {action.action_id: action for action in actions}
    unique_roles = {
        (
            role.action_id,
            role.frame_id,
            role.thematic_role,
            role.hole_role,
            role.requirement,
        ): role
        for role in roles
    }
    return (
        sorted(unique_actions.values(), key=lambda item: (item.lemma, item.action_id)),
        sorted(
            unique_roles.values(),
            key=lambda item: (
                item.lemma,
                item.action_id,
                item.frame_id,
                item.hole_role,
                item.thematic_role,
            ),
        ),
    )


def write_action_snapshots(
    actions_path: Path,
    roles_path: Path,
    actions: list[ImportedAction],
    roles: list[ImportedActionRole],
) -> None:
    actions_path.parent.mkdir(parents=True, exist_ok=True)
    with actions_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "action_id",
                "lemma",
                "verbnet_key",
                "class_id",
                "wordnet_senses_json",
                "propbank_groupings_json",
                "framenet_frames_json",
                "provenance",
            ]
        )
        for action in actions:
            writer.writerow(
                [
                    action.action_id,
                    action.lemma,
                    action.verbnet_key,
                    action.class_id,
                    action.wordnet_senses,
                    action.propbank_groupings,
                    action.framenet_frames,
                    action.provenance,
                ]
            )
    with roles_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, delimiter="\t", lineterminator="\n")
        writer.writerow(
            [
                "action_id",
                "lemma",
                "frame_id",
                "thematic_role",
                "hole_role",
                "requirement",
                "strength",
                "mapping_status",
                "provenance",
            ]
        )
        for role in roles:
            writer.writerow(
                [
                    role.action_id,
                    role.lemma,
                    role.frame_id,
                    role.thematic_role,
                    role.hole_role,
                    role.requirement,
                    role.strength,
                    role.mapping_status,
                    role.provenance,
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home()
        / ".cache"
        / "metonymy"
        / f"verbnet-{VERBNET_COMMIT[:12]}",
    )
    parser.add_argument(
        "--base-predicates",
        type=Path,
        default=Path("auxiliary/data/predicates.tsv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("auxiliary/data/verbnet-predicates.tsv"),
    )
    parser.add_argument(
        "--actions-output",
        type=Path,
        default=Path("auxiliary/data/verbnet-actions.tsv"),
    )
    parser.add_argument(
        "--roles-output",
        type=Path,
        default=Path("auxiliary/data/verbnet-action-roles.tsv"),
    )
    arguments = parser.parse_args()

    source = ensure_source(arguments.source)
    predicates = extract(source, existing_lemmas(arguments.base_predicates))
    if not predicates:
        raise SystemExit("VerbNet produced no mapped transitive predicates")
    write_snapshot(arguments.output, predicates)
    actions, roles = extract_action_roles(source)
    write_action_snapshots(
        arguments.actions_output,
        arguments.roles_output,
        actions,
        roles,
    )
    print(
        f"wrote {len(predicates)} projected predicates, "
        f"{len(actions)} actions, and {len(roles)} action roles"
    )


if __name__ == "__main__":
    main()
