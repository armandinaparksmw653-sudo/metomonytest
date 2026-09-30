# The contextual tower — main workflow

This is the publication-critical engine: the Haskell implementation of
the lexicalized contextual-fiber tower (`engine/src/Metonymy/Contextual.hs`,
`ContextualChecked.hs`), the curated 124-example database it resolves
against, and the tool that prints every example's per-layer resolution.

## Layout

- **`engine/src/Metonymy/`** — the tower itself (`Contextual.hs`,
  `ContextualChecked.hs`, `Snapshot.hs`, `ContextSpec.hs`, `Elaborator.hs`,
  `GF.hs`), the flagship-example modules (`Waterloo.hs`, `MoldeFK.hs`,
  `Rijeka.hs`, `Cathedrals.hs`, `Eswatini.hs`, `Busan.hs`,
  `ContainerContent.hs`, `PartWhole.hs`, `CauseEffect.hs`,
  `MaterialObject.hs`, `AuthorWork.hs`, `FleetStreet.hs`), the
  diagnostic-only `SyntheticTowers.hs`, and two modules added in this
  reorganization: `ExampleDatabase.hs` (the Haskell-module half of the
  124-example database, as data) and `Report.hs` (the rendering logic
  the CLI and the report tool both share).
- **`engine/app/Main.hs`** — the `metonymy` CLI (`parse`, `linearize`,
  `contextual-fiber SCENARIO`, `contextual-contract SCENARIO TARGET`).
- **`engine/app/Report.hs`** — the **main workflow**: `metonymy-report`,
  which runs every example in the curated database — the 52
  Haskell-module ones from `ExampleDatabase.hs` plus the 72 TSV-driven
  scale-tier scenarios from `data/contextual-scenarios.tsv` — through
  the real, Agda-checked `contextualFiberChecked`, and prints the
  per-layer breakdown for each (constraint, surviving candidates,
  `agda-layer-check=true`, any obstructions) in the same format the CLI
  has always used for a single scenario.
- **`engine/test/Main.hs`** — the actual correctness guarantee: every
  one of the 124 examples individually asserted against its expected
  real-world resolution. `ExampleDatabase.hs` is a second,
  independently hand-kept list used only for *printing*; if it ever
  drifts from this file the report may show something stale, but
  `make test` (this file) is what CI actually gates on.
- **`data/`** — the three inputs the tower reads at runtime:
  `wikidata-qid-snapshot/` and `container-content-snapshot/` (real and
  hand-built-but-honestly-labeled entity graphs), and
  `contextual-scenarios.tsv` (the 72 scale-tier scenario definitions).
  Also `synthetic-towers-snapshot/`, used only by five fully-fictional
  fixtures in the test suite that exercise multi-constraint narrowing
  mechanics — not part of the 124-example publication database.
- **`docs/architecture.md`** — the untrusted-proposer/trusted-checker
  design this engine follows.

## Building and running

From the repository root:

```bash
make engine   # builds build/metonymy, build/metonymy-report, build/metonymy-tests
make test     # the real correctness gate — runs engine/test/Main.hs
make report   # runs metonymy-report, writes build/evaluation/tower-report.txt
```

`metonymy-report` also runs standalone once built:

```bash
build/metonymy-report                       # prints to stdout
build/metonymy-report --output report.txt   # writes to a file instead
```

Sample output shape, one block per example:

```
=== waterloo (flagship) ===
sentence="Waterloo announced a programme in physics"
source=Waterloo (Q639408) action=announce role=SubjectHole
stage=0 constraint=graph-related
  survivors=[...]
  agda-layer-check=true
stage=1 constraint=Requires (AnyOf [...])@announce
  survivors=[University of Waterloo (Q1049470),Perimeter Institute (Q2004561)]
  agda-layer-check=true
...
```

The `sentence=` line is reconstructed directly from the Context's own
LexicalTree (every anchor's surface form, in source order) -- the same
lexicalized representation the formal checker verifies against, not a
separately-maintained transcription that could drift from it. Entity
ids are rendered with their real snapshot label alongside the QID.

## The 124-example database

Split narratively into a 16-row flagship tier (each row demonstrates a
distinct capability — a new mechanism, a new Sort target, a new
relation, an honest reject-test, a multi-hop walk — never two rows of
the same shape) and a 108-row scale tier (breadth: more domains, more
sentences, per already-covered mechanisms). `Metonymy.ExampleDatabase`
and `engine/test/Main.hs` are the per-row source of truth (name, tier,
relations, expected resolution); `metonymy-report`'s output is the
per-row breakdown itself.
