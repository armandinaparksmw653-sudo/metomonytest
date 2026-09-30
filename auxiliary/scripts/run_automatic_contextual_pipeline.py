#!/usr/bin/env python3
"""Run text → proposal → data scenario → checked contextual tower.

Entity linking for the source mention (propose_contextual_scenario.py) is
allowed to be ambiguous: a surface like "Liverpool" routinely resolves to a
dozen distinct Wikidata QIDs (the real city, plus a pile of identically
named US townships -- see data/SOURCES.md). The action/role requirement,
the GF parse, and the compiled constraint set are all independent of which
QID that turns out to be, so this pipeline computes them exactly once and
then runs the contextual tower's own existing per-layer narrowing (the
same stage-by-stage HasSort/relation filtering that already narrows
candidate bridge *targets*) once per candidate source QID. A candidate
"survives" if its own run ends with a non-empty final-stage fiber -- i.e.
the tower found something reachable from *that* candidate satisfying every
constraint the sentence's own words imposed, which is exactly the
signal that distinguishes the real Liverpool (reachable to a university
satisfying the sentence's role/topic requirements) from a same-named
census-designated place (reachable to nothing that fits). Three outcomes:
exactly one candidate survives -> that is the answer, printed and scored
exactly as a single-candidate run always was; zero survive -> a legitimate
"no metonymic reading found" result (empty fiber, still exit 0, still
scored as literal), using any one candidate's own (empty) trace since
they are interchangeable; two or more survive -> genuine, irreducible
ambiguity even after full contextual narrowing, which gets its own
SystemExit(6) rather than silently picking one (the same
exact-match-or-abstain policy the entity linker itself already follows).

This candidate loop only applies to the "expand" direction
(contextual-fiber). --contract-target uses a different, safety-sensitive
operation (a contraction can be *correctly* rejected by the formal
checker, which is not a failure to disambiguate) and keeps requiring
exactly one resolved source QID, unchanged.

Before asking GF's own parser to read proposal["gf_sentence"], this also
tries scripts/build_gf_tree_from_dependencies.py's build_gf_tree, which
constructs a GF tree directly from --dependency-hint's "ud_words" (the
whole sentence's UD dependency graph, precomputed offline by
annotate_dependency_hints.py) -- see that module's own docstring for why.
Falls back to `engine parse` on raw text, unchanged, whenever there's no
ud_words hint, build_gf_tree declines (any UD shape outside its
deliberately narrow first slice), or `engine linearize` fails to validate
the tree it built -- so this can only ever be an *additional* source of
success, never a new source of failure.

When the Stanza-UD tier above declines and --llm-proposer-model is set,
a third tier tries next, before that same `engine parse` fallback: a
local Ollama server (scripts/llm_propose_clause_structure.py's
propose_clause_structure) is asked for this sentence's clause structure
around the already-resolved verb lemma, rendered into a tree by
build_gf_tree_from_llm_structure, and validated through the same
`engine linearize` gate as the Stanza-UD tier. Architecturally this LLM
tier is just another untrusted proposer, no different in kind from GF's
own parser or the UD-based tree-builder -- see docs/architecture.md's
"Hard search results are untrusted until `runtimeCheck` succeeds": the
tree text this tier produces never reaches Haskell/Agda directly, only
the constraints compile_gf_constraints later derives from it do, so this
tier adds zero new Agda theorems, same as the tier before it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from build_gf_tree_from_dependencies import (
    build_gf_tree,
    build_gf_tree_decline_reason,
    build_gf_tree_from_llm_structure,
    build_gf_tree_from_llm_structure_decline_reason,
    enumerate_gf_tree_blockers,
    load_gf_function_by_lemma,
)
from contextual_rule_compiler import compile_gf_constraints
from llm_propose_clause_structure import (
    DEFAULT_ENDPOINT as LLM_DEFAULT_ENDPOINT,
    propose_clause_structure_with_reason,
    query_ollama,
)

HEADER = "scenario\tsource_qid\taction\trole\tmax_depth\tbridge_relations\tconstraints\n"
FINAL_SURVIVORS = re.compile(r"survivors=(\[[^\]]*\])")
QID = re.compile(r"Q[0-9]+")


def final_fiber(stdout: str) -> list[str]:
    """The last "survivors=[...]" line's QIDs, or [] if there is none.

    Mirrors scripts/evaluation/run_contextual_corpus.py's own stage
    parsing (it keeps the *last* stage's survivors as the final fiber);
    duplicated narrowly here rather than imported, since that module is
    the batch-corpus driver and pulls in evaluation-only dependencies this
    single-instance pipeline script doesn't otherwise need.
    """
    matches = FINAL_SURVIVORS.findall(stdout)
    return QID.findall(matches[-1]) if matches else []


def encode_constraint(constraint: dict) -> str:
    origin = constraint["origin"]
    prefix = "|".join(
        [
            origin["constructor"],
            origin["lemma"],
            origin["surface"],
            str(origin["start"]),
            str(origin["end"]),
        ]
    )
    payload = constraint["payload"]
    if "requires" in payload:
        return (
            prefix
            + "|requires|"
            + payload["requires"]
            + "|"
            + constraint["provenance"]
        )
    if "prefers" in payload:
        return (
            prefix
            + "|prefers|"
            + payload["prefers"]
            + "|"
            + constraint["provenance"]
        )
    if "prefers_some" in payload:
        related = payload["prefers_some"]
        return (
            prefix
            + "|prefers-some|"
            + related["relation"]
            + "|"
            + related["requirement"]
            + "|"
            + constraint["provenance"]
        )
    if "prefers_relation" in payload:
        relation = payload["prefers_relation"]
        return (
            prefix
            + "|prefers-relation|"
            + relation["relation"]
            + "|"
            + relation["target"]
            + "|"
            + constraint["provenance"]
        )
    if "requires_some" in payload:
        related = payload["requires_some"]
        return (
            prefix
            + "|some|"
            + related["relation"]
            + "|"
            + related["requirement"]
            + "|"
            + constraint["provenance"]
        )
    relation = payload["requires_relation"]
    return (
        prefix
        + "|relation|"
        + relation["relation"]
        + "|"
        + relation["target"]
        + "|"
        + constraint["provenance"]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--sentence", required=True)
    parser.add_argument("--source")
    parser.add_argument("--linker-cache", type=Path)
    parser.add_argument("--contract-target")
    parser.add_argument(
        "--dependency-hint",
        help=(
            "compact JSON object precomputed by annotate_dependency_hints.py, "
            "passed through to propose_contextual_scenario.py"
        ),
    )
    parser.add_argument("--rules", default="auxiliary/data/contextual-language-rules.json")
    parser.add_argument(
        "--gf-actions", default="auxiliary/data/contextual-gf-actions.json"
    )
    parser.add_argument(
        "--gf-nouns", default="auxiliary/data/contextual-gf-nouns.json"
    )
    parser.add_argument("--framenet-snapshot", type=Path)
    parser.add_argument(
        "--llm-proposer-model",
        help=(
            "third tree-source tier, tried when the Stanza-UD build_gf_tree "
            "declines: model name for a local Ollama server (e.g. "
            "llama3.2:3b) via llm_propose_clause_structure.py. "
            "Unset (default) disables this tier entirely -- identical "
            "behaviour to before this tier existed."
        ),
    )
    parser.add_argument("--llm-proposer-endpoint", default=LLM_DEFAULT_ENDPOINT)
    parser.add_argument(
        "--ablation",
        choices=[
            "full",
            "no-wordnet",
            "no-framenet",
            "no-existential",
            "no-formal-filtering",
        ],
        default="full",
    )
    args = parser.parse_args()
    command = [
        "python3",
        "auxiliary/scripts/propose_contextual_scenario.py",
        "--snapshot",
        str(args.snapshot),
        "--sentence",
        args.sentence,
        "--rules",
        args.rules,
    ]
    if args.source:
        command.extend(["--source", args.source])
    if args.linker_cache:
        command.extend(["--linker-cache", str(args.linker_cache)])
    if args.contract_target:
        command.extend(["--target-surface", args.contract_target])
    if args.dependency_hint:
        command.extend(["--dependency-hint", args.dependency_hint])
    if args.ablation == "no-framenet":
        command.append("--disable-framenet")
    elif args.framenet_snapshot:
        command.extend(
            ["--framenet-snapshot", str(args.framenet_snapshot)]
        )
    proposed = subprocess.run(command, text=True, capture_output=True)
    if proposed.returncode != 0:
        # Deliberately not check=True: an uncaught CalledProcessError's
        # default traceback prints only "Command '...' returned non-zero
        # exit status N" and silently discards the captured stdout/stderr
        # -- which is exactly where propose_contextual_scenario.py's own
        # short, sentence-free error message (raise SystemExit(str(error))
        # for target-occurrence-not-found/unsupported-action-role/
        # nested-modifier-unsupported) actually landed, undiagnosable from
        # any caller that only sees this process's own combined output.
        print(
            json.dumps(
                {
                    "status": "propose-scenario-failed",
                    "sentence": args.sentence,
                    "detail": (proposed.stdout + proposed.stderr).strip(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1)
    proposal = json.loads(proposed.stdout)
    candidates = proposal.get("source_qid_candidates") or []
    if not candidates:
        print(
            json.dumps(
                {**proposal, "status": "source-qid-unresolved"},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(2)
    if args.contract_target and len(candidates) != 1:
        # --contract-target keeps the old, stricter single-candidate
        # requirement -- see the module docstring for why the multi-
        # candidate tower loop below is scoped to the expand direction
        # only.
        print(
            json.dumps(
                {**proposal, "status": "source-qid-unresolved"},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(2)
    # Phase 1 of the "Stanza instead of GF-as-parser" transition (see
    # scripts/build_gf_tree_from_dependencies.py and
    # docs/contextual-tower.md): action_map is loaded here, once, rather
    # than only later where gf_actions (its function->lemma direction,
    # for compile_gf_constraints) used to be built -- load_gf_function_by_lemma
    # needs the same JSON in the opposite (lemma->function) direction,
    # and build_gf_tree needs an answer *before* deciding whether to call
    # `engine parse` on raw text at all.
    action_map = json.loads(Path(args.gf_actions).read_text(encoding="utf-8"))
    dependency_hint_data = (
        json.loads(args.dependency_hint) if args.dependency_hint else None
    )
    # annotate_dependency_hints.py's own dep_status ("direct-argument",
    # "copula-argument", "nested-modifier", "no-governing-verb:<reason>",
    # "parse-error") -- reported here for the same reason tree_source/
    # decline_reason already are: it determines whether resolve_action
    # got a real governing_start at all (root-lemma-mismatch:no-
    # governing-start's own root cause), but was never itself visible in
    # any evaluation report until now. "no-hint" when --dependency-hint
    # wasn't passed at all (dependency_hint_data is None) -- a real,
    # distinct case from any status classify_word itself can produce.
    dep_status = (dependency_hint_data or {}).get("dep_status") or "no-hint"
    stanza_built_tree = None
    # "" once a Stanza-built tree is actually trusted (or never even
    # tried to build one is a different story -- see below); otherwise a
    # closed-vocabulary reason (see build_gf_tree_decline_reason's own
    # docstring for the full list) plus two extra reasons specific to
    # this module: "no-ud-words" (dependency_hint carried no UD parse at
    # all to build from -- Stanza's own per-sentence parse failed, or no
    # --dependency-hint was passed) and "linearize-validation-failed"
    # (build_gf_tree returned a tree, but GF's own type checker rejected
    # it -- see the comment below on why that check exists at all).
    # Round 3 of this session's plan measured zero real successes
    # (tree_source_counts: 100% "gf-parser") without any way to tell
    # why; this answers that with real data instead of another guess.
    # dependency_hint's own "governing_start" (below) is threaded into
    # build_gf_tree so it can build a tree around the target's actual
    # governing verb even when that verb isn't the sentence's own UD
    # root (a real corpus run found this -- "root-lemma-mismatch" --
    # was the single dominant Stanza-tier decline reason); on that path
    # it can also decline with "governing-start-not-found",
    # "governing-word-not-verb", "governing-lemma-mismatch", or
    # "embedded-leftover-words" -- see build_gf_tree's own docstring.
    decline_reason = "no-ud-words"
    # Every _Bail this sentence would hit in turn, not just the first
    # one decline_reason (above) reports -- see enumerate_gf_tree_
    # blockers's own docstring for the "ablate and retry" mechanism.
    # Computed unconditionally alongside decline_reason (even when a
    # Stanza tree is actually trusted, where it is always []) so a real
    # corpus run can directly confirm the "a sentence that now passes
    # an earlier check just hits a different, still-unaddressed one"
    # pattern several real evaluation rounds' growing decline_reason
    # buckets already suggested, rather than inferring it indirectly
    # from bucket sizes moving between runs. Wrapped defensively: this
    # is purely diagnostic, so any unexpected exception in it must never
    # take down a row that would otherwise have succeeded or failed for
    # an unrelated, already-understood reason.
    all_decline_reasons: list[str] = []
    gf_function_by_lemma = load_gf_function_by_lemma(action_map)
    if dependency_hint_data and dependency_hint_data.get("ud_words"):
        governing_start = dependency_hint_data.get("governing_start")
        try:
            all_decline_reasons = enumerate_gf_tree_blockers(
                dependency_hint_data["ud_words"],
                proposal["action"],
                gf_function_by_lemma,
                governing_start=governing_start,
            )
        except Exception:
            all_decline_reasons = ["enumeration-error"]
        built_tree = build_gf_tree(
            dependency_hint_data["ud_words"],
            proposal["action"],
            gf_function_by_lemma,
            governing_start=governing_start,
        )
        if built_tree is not None:
            # Still validate through GF's own type system before trusting
            # a hand-built tree -- build_gf_tree only ever bails out to
            # None on a UD shape it doesn't model, but a bug in it could
            # still produce syntactically-wrong-but-plausible-looking
            # text; `engine linearize` (the same diagnostic command added
            # for the comma-tokenizer investigation) exits non-zero on
            # anything that isn't a well-typed term of grammar/Metonymy.gf's
            # own abstract syntax, at zero cost to what reaches Haskell/Agda
            # either way (see this module's docstring: only the *derived*
            # constraints ever reach the formal core, never this tree text).
            validated = subprocess.run(
                [str(args.engine), "linearize", built_tree],
                text=True,
                capture_output=True,
            )
            if validated.returncode == 0:
                stanza_built_tree = built_tree
                decline_reason = ""
            else:
                decline_reason = "linearize-validation-failed"
        else:
            decline_reason = build_gf_tree_decline_reason(
                dependency_hint_data["ud_words"],
                proposal["action"],
                gf_function_by_lemma,
                governing_start=governing_start,
            )

    # Third tier, tried only when Stanza-UD declined and an LLM proposer
    # model was actually configured (--llm-proposer-model unset = this
    # whole block never runs, byte-identical to before this tier
    # existed). See llm_propose_clause_structure.py's own module
    # docstring and docs/contextual-tower.md's "Phase 1.5" section for
    # the full epistemic framing -- another untrusted proposer, same
    # `engine linearize` validation gate as the Stanza tier above, never
    # reaching the formal core directly either way.
    llm_built_tree = None
    llm_decline_reason = "not-attempted"
    if stanza_built_tree is None and args.llm_proposer_model:
        def query(prompt: str) -> dict:
            return query_ollama(
                prompt, model=args.llm_proposer_model, endpoint=args.llm_proposer_endpoint
            )

        structure, propose_decline_reason = propose_clause_structure_with_reason(
            proposal["gf_sentence"], proposal["action"], query
        )
        if structure is None:
            llm_decline_reason = propose_decline_reason
        else:
            llm_tree = build_gf_tree_from_llm_structure(
                structure, proposal["action"], gf_function_by_lemma
            )
            if llm_tree is None:
                llm_decline_reason = build_gf_tree_from_llm_structure_decline_reason(
                    structure, proposal["action"], gf_function_by_lemma
                )
            else:
                validated = subprocess.run(
                    [str(args.engine), "linearize", llm_tree],
                    text=True,
                    capture_output=True,
                )
                if validated.returncode == 0:
                    llm_built_tree = llm_tree
                    llm_decline_reason = ""
                else:
                    llm_decline_reason = "linearize-validation-failed"

    # Recorded once here and reused everywhere below (the exit-3/4/7
    # JSON payloads and the unconditional "tree-source="/"decline-reason="/
    # "llm-decline-reason=" stdout lines on success) -- see
    # docs/contextual-tower.md's "Phase 1, round 3"/"Phase 1.5" for why
    # this exists: isolating a real mystery (bare, unquoted capitalized
    # words in some exit-4 rows' trees) and later measuring the LLM
    # tier's own real contribution both needed to know which of the
    # three tree sources actually produced a given row's tree, across
    # every outcome, not just failures.
    tree_source = (
        "stanza"
        if stanza_built_tree is not None
        else "llm" if llm_built_tree is not None else "gf-parser"
    )

    if stanza_built_tree is not None or llm_built_tree is not None:
        trees = [stanza_built_tree or llm_built_tree]
    else:
        # Falls back here whenever build_gf_tree declined (an unhandled
        # UD shape, no ud_words hint at all, or the linearize validation
        # above failed) -- identical to this module's behaviour before
        # Phase 1 existed, so this can never be a new source of failure,
        # only an alternate source of success.
        parsed = subprocess.run(
            [str(args.engine), "parse", proposal["gf_sentence"]],
            text=True,
            capture_output=True,
        )
        if parsed.returncode != 0:
            print(
                json.dumps(
                    {
                        "status": "gf-parse-failed",
                        "gf_sentence": proposal["gf_sentence"],
                        "detail": parsed.stderr.strip(),
                        "tree_source": tree_source,
                        "decline_reason": decline_reason,
                        "all_decline_reasons": all_decline_reasons,
                        "llm_decline_reason": llm_decline_reason,
                        "dep_status": dep_status,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            raise SystemExit(3)
        trees = [line for line in parsed.stdout.splitlines() if line.strip()]
    if not trees or trees[0].startswith("The parser failed"):
        # A bare `raise SystemExit("some string")` prints that string to
        # stderr and exits 1 -- the same exit code as every ValueError
        # resolve_action/propose_contextual_scenario.py can raise, but
        # without the JSON-wrapped "status"/exit-code convention every
        # sibling failure in this function follows. That made it
        # invisible to score_contextual_detection.py's exit-1 token
        # search: two full contextual-tower-evaluation.yml rounds of
        # adding tokens for other suspected causes found nothing, because
        # this fixed 32-character string was never among them until a
        # safe, content-free fingerprint (a SHA-256 prefix, no sentence
        # text) of the real "unrecognized" failures matched a fingerprint
        # of exactly this string, taken locally, character for character.
        # Fixed by giving it its own exit code, like every sibling here.
        print(
            json.dumps(
                {
                    "status": "gf-parse-empty",
                    "gf_sentence": proposal["gf_sentence"],
                    "tree_source": tree_source,
                    "decline_reason": decline_reason,
                    "all_decline_reasons": all_decline_reasons,
                    "llm_decline_reason": llm_decline_reason,
                    "dep_status": dep_status,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(7)
    language_rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    wordnet_rules_path = Path("auxiliary/data/wordnet-context-rules.json")
    wordnet_rules = json.loads(wordnet_rules_path.read_text(encoding="utf-8"))
    if args.ablation == "no-wordnet":
        wordnet_rules = {"lexical_sorts": {}, "adjective_sorts": {}}
    context_triggers_path = Path("auxiliary/data/contextual-context-triggers.json")
    context_triggers = (
        json.loads(context_triggers_path.read_text(encoding="utf-8"))
        if context_triggers_path.exists()
        else {"triggers": []}
    )
    aliases = {}
    with (args.snapshot / "aliases.jsonl").open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            aliases.setdefault(row["alias"].casefold(), []).append(row["id"])
    gf_actions = {
        action["gf_function"]: action["lemma"]
        for action in action_map["actions"]
    }
    noun_map = json.loads(
        Path(args.gf_nouns).read_text(encoding="utf-8")
    )
    gf_nouns = {
        noun["gf_function"]: noun["lemma"]
        for noun in noun_map["nouns"]
    }
    try:
        proposal["constraints"].extend(
            compile_gf_constraints(
                proposal,
                trees[0],
                language_rules,
                wordnet_rules,
                aliases,
                enable_existential=args.ablation != "no-existential",
                gf_actions=gf_actions,
                gf_nouns=gf_nouns,
                context_triggers=context_triggers,
            )
        )
    except ValueError as error:
        print(
            json.dumps(
                {
                    "status": "semantic-composition-failed",
                    "gf_tree": trees[0],
                    "detail": str(error),
                    # "stanza" or "gf-parser" -- which of the two tree
                    # sources produced trees[0] this row actually used.
                    # Added to isolate a real, previously-hidden mystery
                    # a live corpus evaluation surfaced: bare, unquoted
                    # capitalized words (e.g. "Albright", "The") showing
                    # up as "unrecognized constructor(s)" in
                    # exit4_reason_bucket's own breakdown, on both Phase
                    # 1 rounds' first real runs. A Stanza-built tree
                    # already passed `engine linearize`'s own type check
                    # before ever reaching here (see above), which should
                    # make that source structurally incapable of this --
                    # confirming that with real data beats assuming it.
                    "tree_source": tree_source,
                    # "" when tree_source is "stanza" (build_gf_tree
                    # already succeeded here; this row's exit-4 failure
                    # is compile_gf_constraints's own, unrelated to
                    # tree-building) -- otherwise which of
                    # build_gf_tree_decline_reason's reasons applies.
                    "decline_reason": decline_reason,
                    "all_decline_reasons": all_decline_reasons,
                    # Same idea, for the LLM tier -- "" when tree_source
                    # is "llm", "not-attempted" when the LLM tier never
                    # ran at all (Stanza already succeeded, or
                    # --llm-proposer-model wasn't given).
                    "llm_decline_reason": llm_decline_reason,
                    "dep_status": dep_status,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(4)
    print("gf-tree=" + trees[0], flush=True)
    # Covers every outcome from here on (success, exit 5, exit 6) --
    # scripts/evaluation/run_contextual_corpus.py's own line-scan picks
    # this up into the result row directly, the same way it already
    # does for "gf-tree="/"graph_sha256="/etc. Exit 1/2 never reach this
    # line at all (tree-building isn't attempted before them); exit
    # 3/4/7 carry their own "tree_source"/"decline_reason"/
    # "llm_decline_reason"/"dep_status" in their JSON payload instead,
    # since they never reach these lines either.
    print("tree-source=" + tree_source, flush=True)
    print("decline-reason=" + decline_reason, flush=True)
    print("all-decline-reasons=" + ",".join(all_decline_reasons), flush=True)
    print("llm-decline-reason=" + llm_decline_reason, flush=True)
    print("dep-status=" + dep_status, flush=True)
    encoded_constraints = ";;".join(
        encode_constraint(item) for item in proposal["constraints"]
    )
    bridge_relations = ",".join(proposal["bridge_relations"])

    def run_engine(
        operation: list[str], source_qid: str, scenario_name: str, *, capture: bool
    ) -> subprocess.CompletedProcess:
        row = "\t".join(
            [
                scenario_name,
                source_qid,
                proposal["action"],
                proposal["role"],
                str(proposal["max_depth"]),
                bridge_relations,
                encoded_constraints,
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            scenarios = Path(directory) / "scenarios.tsv"
            scenarios.write_text(HEADER + row + "\n", encoding="utf-8")
            return subprocess.run(
                [
                    str(args.engine),
                    *operation,
                    "--snapshot",
                    str(args.snapshot),
                    "--scenarios",
                    str(scenarios),
                    *(
                        ["--no-formal-filtering"]
                        if args.ablation == "no-formal-filtering"
                        else []
                    ),
                ],
                text=True,
                capture_output=capture,
            )

    if args.contract_target:
        # Single, already-uniquely-resolved source QID (enforced above, by
        # the len(candidates) != 1 guard) -- unchanged from before the
        # multi-candidate expand-direction loop below was introduced.
        # Inherits stdout/stderr directly since there is nothing to choose
        # between, and a contraction can be *correctly* rejected by the
        # formal checker (see module docstring), which this must not
        # confuse with a disambiguation failure.
        target_candidates = []
        with (args.snapshot / "aliases.jsonl").open(encoding="utf-8") as source:
            for line in source:
                alias = json.loads(line)
                if alias["alias"].casefold() == args.contract_target.casefold():
                    target_candidates.append(alias["id"])
        target_candidates = sorted(set(target_candidates))
        if len(target_candidates) != 1:
            print(
                json.dumps(
                    {
                        "status": "contract-target-qid-unresolved",
                        "surface": args.contract_target,
                        "qid_candidates": target_candidates,
                    },
                    indent=2,
                )
            )
            raise SystemExit(5)
        source_qid = candidates[0]
        scenario_name = f"{source_qid.lower()}-{proposal['action']}"
        completed = run_engine(
            ["contextual-contract", scenario_name, target_candidates[0]],
            source_qid,
            scenario_name,
            capture=False,
        )
        raise SystemExit(completed.returncode)

    # Expand direction: run the tower's existing per-layer narrowing once
    # per ambiguous source candidate -- see the module docstring for why
    # this is a faithful (not an approximate) way to let the sentence's own
    # context disambiguate which candidate was actually meant.
    def run_candidate(source_qid: str) -> subprocess.CompletedProcess:
        scenario_name = f"{source_qid.lower()}-{proposal['action']}"
        return run_engine(
            ["contextual-fiber", scenario_name], source_qid, scenario_name, capture=True
        )

    results = [(source_qid, run_candidate(source_qid)) for source_qid in candidates]
    confirmed = [
        (qid, completed)
        for qid, completed in results
        if completed.returncode == 0 and final_fiber(completed.stdout)
    ]

    def emit(completed: subprocess.CompletedProcess) -> None:
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)

    if len(confirmed) == 1:
        _, completed = confirmed[0]
        emit(completed)
        raise SystemExit(completed.returncode)

    if not confirmed:
        # No candidate identity bridges to anything satisfying the
        # sentence's own constraints -- a legitimate "nothing metonymic
        # here" result (empty fiber, still exit 0, still scored as
        # literal), not a disambiguation failure. Any one candidate's own
        # trace is representative for scoring purposes since they are all
        # empty; prefer one whose own run actually completed (exit 0) over
        # one that hit a genuine engine-level rejection, so a real internal
        # error still surfaces instead of being masked by picking blindly.
        clean = [(qid, completed) for qid, completed in results if completed.returncode == 0]
        _, completed = clean[0] if clean else results[0]
        emit(completed)
        raise SystemExit(completed.returncode)

    # Two or more candidates survived full contextual narrowing: genuine,
    # irreducible ambiguity even given the sentence's own context. Never
    # silently pick one -- the same exact-match-or-abstain policy the
    # entity linker itself already follows (build_wikidata_api_index.py's
    # search_exact docstring: "an ambiguous surface simply resolves to more
    # than one QID here, and callers decide what to do with that").
    print(
        json.dumps(
            {
                "status": "source-disambiguation-ambiguous",
                "action": proposal["action"],
                "confirmed_source_qid_candidates": sorted(
                    qid for qid, _ in confirmed
                ),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(6)


if __name__ == "__main__":
    main()
