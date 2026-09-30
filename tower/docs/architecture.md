# Architecture and trust boundaries

This describes the engine as it actually exists in `tower/engine/src/Metonymy/`
today: the lexicalized **contextual-fiber tower**
(`Metonymy.Contextual`/`ContextualChecked`), not the earlier
certificate/bridge-path engine (`Metonymy.Resolution`'s `Automatic`-era
CLI, `expand`/`contract`/`list`) that this document used to describe —
that engine has been retired to [`trash/`](../../trash/), and its
`Metonymy.Resolution.expandFiber`/`contractTarget` functions now serve
only as the untrusted fiber-search primitive the current tower calls
internally (step 4 below), not as a standalone command.

## Pipeline

### 1. Grammatical analysis (optional, diagnostic-only)

`auxiliary/grammar/Metonymy.gf`/`MetonymyEng.gf` define a small,
hand-curated abstract syntax over the standard GF English Resource
Grammar Library. `Metonymy.GF.parseEnglish`/`linearize` expose this as
the CLI's `parse`/`linearize` commands — useful for checking that a
hand-built `LexicalTree` (below) actually corresponds to something GF
can parse/linearize, but neither command feeds the tower directly: the
124 curated examples build their `Context` values by hand
(`tower/engine/src/Metonymy/Waterloo.hs` and its 13 sibling modules) or
from `tower/data/contextual-scenarios.tsv`, not from a live GF parse.

### 2. Lexicalized context

`Metonymy.Contextual` defines the shared vocabulary every example is
built from:

- `LexicalAnchor` — one token's GF constructor, lemma, surface form,
  and character span;
- `LexicalTree` — `LexicalLeaf`/`LexicalApply`, the constituent shape
  used only for `validateContext`'s well-formedness checks and for
  `Metonymy.Report.reconstructSentence`'s sentence reconstruction;
- `ContextConstraint` — a `LexicalAnchor` paired with a
  `ConstraintPayload` (`Requires`/`RequiresRelation`/`RequiresSome`, or
  their `Prefers*` soft-preference counterparts) and a provenance
  string (which VerbNet/FrameNet/Wikidata/hand-audited rule justifies
  it);
- `Context` — a source `EntityId`, the surface action, which argument
  position is metonymic (`HoleRole`), and the ordered list of
  constraints that narrow it, one lexical trigger at a time.

`Metonymy.Elaborator.elaborateContext` can derive a `Context`'s
constraint list from a `LexicalTree` mechanically
(`collectConstraints`); the curated flagship/scale examples instead
construct both fields directly so each carries real, per-constraint
provenance (see `Metonymy.Contextual`'s own module comment for exactly
why these two representations are kept separate rather than one being
computed from the other).

### 3. Knowledge base

`Metonymy.Ontology` holds a `KnowledgeBase`: named entities
(`EntityInfo`), typed assertions, and relation assertions, each with
provenance. `Metonymy.Snapshot.loadSnapshot` reads one of the three
on-disk snapshots the tower runs against
(`tower/data/wikidata-qid-snapshot/`,
`tower/data/container-content-snapshot/`, or the fully synthetic
`tower/data/synthetic-towers-snapshot/` used only by five
diagnostic-only multi-constraint fixtures) — five files each
(`entities.jsonl`, `aliases.jsonl`, `claims.jsonl`, `rules.json`,
`manifest.json`), hash-verified before use. `proveRequirement` returns
a `Proof`, not a bare `Bool`, carrying the rule and premise that
justified it.

### 4. Fiber search (untrusted proposer)

`Metonymy.Resolution.expandFiber` performs the actual graph search:
every entity reachable from the context's source via the allowed
`Relation`s, up to `fiberMaxDepth` hops, that also satisfies the
current stage's requirement. This is ordinary, unchecked Haskell —
useful for *proposing* candidates quickly, but nothing downstream
trusts its result without independent re-verification (step 6).

### 5. Stage-by-stage narrowing

`Metonymy.Contextual.contextualFiber` applies a `Context`'s
`contextConstraints` one at a time: starting from every graph-related
candidate, each successive `Requires*` constraint drops candidates
that fail it (recorded as a `SnapshotObstruction`), while each
`Prefers*` constraint reorders survivors without eliminating any
(recorded separately as `stagePreferredCandidates`/
`stagePreferenceMisses`). The result is a `[FiberStage]`: one entry per
constraint, each showing exactly which candidates survived, which were
obstructed and why, and which were merely preferred.

### 6. Independent Agda re-verification (the trust boundary)

`Metonymy.ContextualChecked.contextualFiberChecked` is the production
entry point (`Metonymy.ContextualChecked.contextualContractionChecked`
for the inverse, target-to-source direction). For **every stage**, it
re-derives the prefix context up to that point and independently
re-checks, against the compiled Agda `contextLayerCheck`
(`Metonymy.Verified.verifyContextLayerWithAgda`, calling into
`Metonymy.CheckerAPI` — MAlonzo code compiled from
`formal-verification/Metonymy/Checker.agda`):

- that every candidate Haskell's search accepted is *also* accepted by
  Agda (`agda-rejected-survivor-at-stage-N` otherwise);
- that every candidate Haskell's search obstructed is *also* rejected
  by Agda (`agda-accepted-obstruction-at-stage-N` otherwise);
- the same, symmetrically, for the preference layer via
  `verifyPreferenceLayerWithAgda`.

Haskell's graph search is therefore an untrusted proposer only: nothing
it proposes — acceptance or rejection — reaches a caller unless the
independently compiled Agda checker agrees, at every single stage, not
just at the final answer.

### 7. Cubical formal core

`Checker.agda`'s Boolean-reflected `contextLayerCheck` is proven sound
and complete against the dependent, Cubical-type-theoretic construction
in `formal-verification/Metonymy/FilteredContext.agda`, via
`Metonymy.FilteredRuntime.runtimeFiberCheckerEquivalence` — so running
an example through `contextualFiberChecked` genuinely exercises the
proven theorems, not a separate, less-connected checker. See
[`formal-verification/OVERVIEW.md`](../../formal-verification/OVERVIEW.md)
for what exactly is proven and
[`formal-verification/Metonymy/THEOREMS.md`](../../formal-verification/Metonymy/THEOREMS.md)
for the exact theorem-to-file map, including the explicit non-claims.

## Trust model

Formally checked (in `formal-verification/`, zero `postulate`s,
`--safe` mode, CI-enforced):

- the dependent, quotient-based construction the compiled checker is
  proven equivalent to;
- that every accepted candidate at every stage genuinely satisfies its
  constraint, and every rejected one genuinely fails it;
- that safe contraction only forgets a checked generic reading.

Not formally claimed (see THEOREMS.md's "Explicit non-claims" for the
exact list): correctness/completeness of GF parsing arbitrary text;
factual correctness or completeness of the underlying Wikidata/WordNet/
VerbNet snapshots; uniqueness of the intended pragmatic reading beyond
what a given constraint set actually forces; competitive NLP recall.

This boundary prevents an unchecked graph search or a statistical
scorer from inventing an admissible reading, while avoiding the false
claim that type-checking alone resolves pragmatics or guarantees
broad-coverage recall.
