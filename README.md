# Cubical type theory for proof-carrying metonymy

Research prototype positioning metonymy (predicate transfer) as an
application of **Cubical Agda**: a metonymic reading is a *quotient* of a
context-indexed fiber of candidate referents by a contextual compatibility
relation, and the transfer itself is a proof-carrying path/equivalence,
not a heuristic rewrite.

**Scope, stated plainly**: this does not claim state-of-the-art metonymy
detection (for that, use an LLM). It demonstrates that predicate transfer
for *referential/encyclopedic* metonymy can be given a computable,
machine-checked semantics, on a curated set of deeply-verified real
examples plus the formal apparatus to combine several independent
contextual signals — not on large-corpus recall.

## Structure

- **[`formal-verification/`](formal-verification/)** — the machine-checked
  Cubical Agda core (29 modules, zero `postulate`s, `--safe` mode) and the
  scripts that guard it against silent regression. Start at
  [`formal-verification/OVERVIEW.md`](formal-verification/OVERVIEW.md) for
  a summary of what's proven, or
  [`formal-verification/Metonymy/THEOREMS.md`](formal-verification/Metonymy/THEOREMS.md)
  for the exact statement and witness of every claim.
- **[`tower/`](tower/)** — the main workflow: the Haskell engine
  implementing the lexicalized contextual-fiber tower, the curated
  124-example database it resolves against, and `metonymy-report`, the
  tool that runs every example through the real, Agda-checked apparatus
  and prints its per-layer resolution. Start at
  [`tower/README.md`](tower/README.md).
- **[`auxiliary/`](auxiliary/)** — the Python data-preparation pipeline
  (VerbNet/WordNet/FrameNet import, GF lexicon generation, the Stanza-based
  automatic scenario proposer), the GF grammar sources, the broader data
  files the pipeline consumes, and small real-corpus regression fixtures.
  Supports the two folders above without being on the publication-critical
  path.
- **`trash/`** — retired code and data, kept rather than deleted (two
  earlier engines, a benchmark that self-documented as not statistically
  meaningful, and the CI workflows that ran it). Not built, tested, or run
  in CI.
- **Root-level files** (`Makefile`, `cabal.project`, `metonymy.agda-lib`,
  `scripts/bootstrap.sh`, `scripts/reproduce.sh`, `toolchain.lock.json`)
  tie the three folders together — GitHub Actions/cabal/Agda conventions
  require certain paths at the repo root, and a single orchestrator needs
  to reference all three folders.

## Building and testing

There is no local Haskell/Agda toolchain on the machine this repository
is developed on; [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
(workflow `publication-artifact`) is the sole source of truth for whether
anything here actually compiles and type-checks, and runs on every push.
[`.github/workflows/tower-report.yml`](.github/workflows/tower-report.yml)
is a separate, manually-triggered workflow that exists purely to give a
reviewer a single "run everything and show me the full 124-example
breakdown" entry point in the Actions tab.

On a machine with the pinned toolchain (versions and commits recorded in
[`toolchain.lock.json`](toolchain.lock.json); `.cursor/` provides a
matching cloud/background-agent environment):

```bash
./scripts/bootstrap.sh   # fetches pinned Cubical + GF RGL, builds, runs make test
make formal-artifact     # type-checks the Agda core, bans postulate, checks the manifest
make report              # runs metonymy-report over all 124 curated examples
make reproduce           # the exact sequence CI runs end to end
```

Third-party terms are listed in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
