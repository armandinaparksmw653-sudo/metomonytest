# Formal verification — overview

This folder is the machine-checked mathematical core of the project: a
Cubical Agda development (`Metonymy/*.agda`, 29 modules) plus the
executable, Boolean-reflected checker the Haskell engine actually calls
at runtime, and the scripts that guard both against silent regression.

## What's here

- **`Metonymy/*.agda`** — the theorems. Entry point:
  `Metonymy.PublicationTheorems`, a flat import list of every proven
  module (see `Metonymy/README.md` for the full module map).
- **`Metonymy/THEOREMS.md`** — the human-readable index: every
  publication-facing claim, its exact Agda witness name, and its
  assumptions. Read this first if you want the precise statement of
  what is and isn't proven.
- **`Metonymy/Checker.agda`** — the executable, Boolean-reflection
  layer the Haskell engine (`tower/engine`) actually calls at runtime
  (`contextLayerCheck`, `contextualRuntimeCheck`, ...). Proven sound
  and complete against the dependent, Cubical-type-theoretic
  construction in `Metonymy/FilteredContext.agda` via
  `Metonymy.FilteredRuntime.runtimeFiberCheckerEquivalence` — running
  an example through the engine's `contextualFiberChecked` genuinely
  exercises the proven theorems, not a separate, less-connected
  checker.
- **`Metonymy/ARTIFACT_MANIFEST.json`** — SHA-256 of every `.agda`
  source file, regenerated and verified by `generate_manifest.py`.
- **`Metonymy/check.sh`** — a standalone convenience script that
  reproduces what `make formal-artifact` (see the repo-root `Makefile`)
  already does in CI: reject any `postulate`/`TERMINATING`/
  `NON_TERMINATING`/`NO_POSITIVITY` declaration, then verify the
  manifest.
- **`claims.md`, `mathematics.md`, `main-theorem.md`** — supporting
  reference prose for the theorems above (moved here from the former
  top-level `docs/` during the 2026-09-26 repository reorganization).

## Scope — what this does and does not prove

Verbatim from `Metonymy/THEOREMS.md`'s "Explicit non-claims" section —
this is the honest boundary of the formal core, and the right thing to
quote in a reviewer-facing description of the project:

> The artifact does not prove:
> - correctness or completeness of GF parsing arbitrary text;
> - factual correctness or completeness of Wikidata, WordNet, VerbNet, or
>   OpenAlex;
> - uniqueness of intended pragmatic interpretation;
> - that safe contraction is the inverse of expansion, or that uniqueness at
>   a stronger layer implies uniqueness at a weaker layer;
> - monotonicity of arbitrary negation, quantification, anaphora, or
>   discourse update;
> - a global `Coarse₂Pseudofunctor` for arbitrary compatibility without
>   supplied higher coherence;
> - external denotational equivalence beyond the stated semantic model;
> - competitive NLP accuracy from the formal theorems alone.

What it **does** prove, exhaustively within that boundary: given a
supplied lexicalized context, a finite knowledge-graph snapshot, and a
set of rules/certificates/refinements, the tower's narrowing (both the
raw, dependent construction and the executable checker the engine
actually runs) is sound and complete, functorial across the filtered
family of contexts, and — where a compatibility relation is supplied —
coherent up to 2-truncation. Zero `postulate`s, developed in Agda
`--safe` mode, CI-enforced.

## Reproducing the checks

From the repository root (these are the same commands
`scripts/reproduce.sh` runs in CI):

```bash
make formal            # type-checks every listed .agda module
make formal-artifact   # + the postulate-ban + manifest check
make checker           # compiles Checker.agda to the API the engine links against
```

None of this requires a local Haskell/GHC toolchain — only Agda 2.6.3+
and the pinned Cubical library (`toolchain.lock.json`, fetched by
`scripts/bootstrap.sh`). There is no local Agda toolchain on the
machine this repository was developed on either; real verification has
always gone through GitHub Actions (`.github/workflows/ci.yml`), which
remains the sole source of truth for whether these modules actually
check.
