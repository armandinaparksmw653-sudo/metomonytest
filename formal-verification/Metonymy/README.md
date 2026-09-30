# Formal publication artifact

This directory is the canonical source of every machine-checked theorem in the
project. Do not maintain a second copied proof tree.

Entry point:

```text
Metonymy.PublicationTheorems
```

From the repository root:

```bash
make formal
./formal-verification/Metonymy/check.sh
```

`THEOREMS.md` states the publication-facing claims, assumptions, and exact
Agda witnesses. `ARTIFACT_MANIFEST.json` records SHA-256 hashes of all Agda
sources and the pinned toolchain metadata.

Compiler-specific publication witnesses live in
`CompilerSoundness.agda`. It proves that every supported positive GF subtree
compiles to a genuine refinement and that every inhabitant of the resulting
fiber restricts to the incoming fiber. It also re-exports the executable
non-filtering theorems for unpromoted preferences from `Checker.agda`.

The development is checked with `--safe`. Publication modules contain no
`postulate`, `TERMINATING`, `NON_TERMINATING`, `NO_POSITIVITY`, or unresolved
metavariables.

Scope is snapshot-relative. The artifact verifies the supplied lexicalized
context, finite knowledge graph, rules, certificates, refinements, paths, and
coherences. It does not prove that an external parser or knowledge source is
linguistically complete or factually correct.
