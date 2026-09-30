# Machine-checked mathematical core

Every result listed here is checked by Cubical Agda 2.6.3 with
`agda/cubical` v0.5. The formal directory contains no postulates, unresolved
metavariables, termination overrides, or disabled positivity checks.

## Raw grammar

`Grammar.agda` defines a free typed derivation language:

```text
RawDerivation G A B
```

Its terms are identities, primitive grammar rules, and typed composition.
`Structural₂` records the unit, associativity, symmetry, transitivity, and
horizontal-composition laws without quotienting the raw syntax.

## Directed ontology

`Ontology.agda` keeps semantic bridges directed:

```text
BridgePath O x y
Bridge₂ p q
```

`Bridge₂` relates parallel directed paths and includes identity, symmetry,
transitivity, composition, unit, and associativity coherence.

`ConcreteOntology.agda` interprets paths with the executable `pathCode`
model. The two routes

```text
author → work → text
author → book → text
```

compute to the same denotation, yielding `routeCoherence`. The
`GroundSystem` then defines grammatical `Basic₂` directly as this
ontology-level `Bridge₂`, and `ontologyGroundedCell₂` connects the two
concrete hard cells. Coherence is no longer an unrelated external
grammatical witness.

Hard and preferred resolutions are separate records. A preferred resolution
can become hard only through an explicit `PromotionEvidence` inhabitant.

## Grammatical cells and completion

`Cell.agda` defines cells between parallel raw derivations:

```text
HardCell f g
PreferredCell f g
Cell₂ left right
```

Only `HardCell` generates a path in `Completion.agda`:

```text
metonymic : HardCell f g → raw f ≡ raw g
```

`coherent` maps `Cell₂` witnesses to equalities between generated paths.
Preferred cells have no path constructor. `promotedPath` requires explicit
promotion evidence.

## Context-indexed compression

`Compression.agda` derives compatibility inside a fixed typed fiber:

```text
Fine Γ K source
  = target × HardResolution Γ K source target

SameMetonymicClass left right
  = TargetCompatible Γ K (target left) (target right)
```

The common source, context, and hole are indices, while each side contains
an admissible licensed bridge and target-fit proof. `compatibleRefl`,
`compatibleSym`, and `compatibleTrans` are machine-derived from those fit
proofs and the target-type compatibility laws. The quotient glues readings
only when the resulting relation is inhabited.

Expansion is the homotopy fiber of contraction:

```text
Expansion coarse = Σ explicit. contract explicit ≡ coarse
```

`roundTrip` proves that every explicit value remains in the expansion fiber
of its compressed image.

## Independent semantics

`Semantics.agda` does not define interpretation by first quotienting
meanings. A `SemanticModel` must independently supply:

```text
interpretRaw
respectCell
respectCoherence
```

Only then does `interpret` descend to the two-dimensional completion.
`factorization` proves that the descended interpretation agrees with the raw
interpretation on raw derivations.

## Checker reflection

`Checker.agda` defines an executable Boolean checker. `Admissible` contains
four separate proofs:

```text
non-empty path
valid predicate declaration
connected path of existing ontology edges
structured target requirement satisfied through the subsort graph
```

Requirements contain `hasSort`, `allOf`, `anyOf`, and `notRequirement`.
Negation is deliberately closed-world: it means that the frozen finite
knowledge base cannot derive the nested requirement.

The central reflection results are:

```text
checkSound    : check KB raw ≡ true → Admissible KB raw
checkComplete : Admissible KB raw → check KB raw ≡ true
```

The same `check` function is compiled through MAlonzo and called by the
runtime.

## End-to-end path theorem

`RuntimeBridge.agda` links the executable checker to the concrete runtime
grammar:

```text
runtimeCheck KB beforeGF afterGF certificate ≡ true
→ RuntimeAdmissible KB beforeGF afterGF certificate
→ HardCell (translate beforeGF) (translate afterGF)
→ Path Completion (raw beforeGF) (raw afterGF)
→ equality in RuntimeMeaning KB
```

`runtimeCheck` checks the direction, predicate and unchanged argument,
GF-function-to-entity bindings, certificate, hard strength, and generic
target safety for contraction. It therefore needs no external
cell-realization function.

`RuntimeMeaning KB` is defined separately from `Completion` as a list of
runtime clauses quotiented by accepted, certificate-indexed rewrites:

```text
RuntimeRelated KB before after
  = Σ certificate. RuntimeAdmissible KB before after certificate

RuntimeMeaning KB
  = List (RuntimeClause / RuntimeRelated KB)
```

`checkedRuntimeSemanticEquality` transports every accepted runtime path
through this quotient model. Because `RuntimeRelated` is defined from the
same accepted certificates, this proves consistency between the completion
and runtime quotient; it does not establish preservation of an external
denotational semantics. The theorem is generic in the knowledge base,
clauses, and certificate; `runtimeGenericSemanticEquality` is the concrete
Rumi inhabitant.

For a selectional preference, `preferenceRuntimeCheck` produces only a
checked candidate. `checkPromotion` additionally validates target-indexed,
non-empty discourse evidence before `promoteAcceptedPreference` can produce
a path.

## Metatheorems

`MetaTheory.agda` proves full conservativity in the no-cell case:

```text
NoHardCells M →
RawDerivation G A B ≃ Completion M A B
```

`completionRetract` supplies the inverse homotopy, including the cubical
boundary fillers. Thus the completion is equivalent to raw derivations,
rather than merely injective on raw terms, when no metonymic cells exist.

It also proves semantic non-collapse:

```text
interpretRaw f ≠ interpretRaw g →
raw f ≠ raw g
```

whenever an independent semantic model separates the meanings.

`CompressionTheory.agda` proves:

- classification factors through the compatibility quotient;
- a separating quotient model prevents unrelated compressed meanings from
  becoming equal;
- unique contextual expansion gives a unique round-trip representative.

## Filtered lexical context theorem

`FilteredContext.agda` defines a positive constraint system with entities,
constraints, proof-valued satisfaction, and a decision procedure. A context is
a finite list and its fine fiber is:

```text
Fiber Γ = Σ entity. Bridge entity × All (Holds entity) Γ
```

A refinement transforms stronger evidence into weaker evidence.
`fiberFunctor` proves identity and composition, so fibers form a
contravariant filtered family in Cubical `Type`.

For a new constraint `c`, `ExtensionSpace c x` is logically equivalent to the
fiber of the restriction map over `x` (`extensionIsLiftingProblem`).
`extensionLiftingEquiv` strengthens this to `≃` whenever both witness spaces
are propositions; the assumptions are explicit and are not silently inferred.
`extensionOrObstruction` decides this lifting problem, while
`extensionObstructionDisjoint` proves the outcomes cannot coexist.

`naturalStageSection` assigns proof-carrying paths to every fiber inhabitant
and proves naturality, identity coherence, and composition coherence. These
are equalities between paths, hence cubical 2-paths.

The reverse path `sym (stagePath selected)` is the contraction of a selected
fiber inhabitant. `SafeContraction` packages this reverse path with
`UniqueEntity`, the hypothesis that every inhabitant of the final layer has
the same entity identifier. `uniqueEntityStrengthens` shows that uniqueness
at a weaker layer survives adding constraints; the converse is false, so a
two-element Waterloo physics fiber has no unique contraction.

Compatibility compression is a set quotient. `restrictCoarse`,
`coarseRestrictionIdentity`, `coarseRestrictionComposition`, and
`compressionNaturality` prove functoriality under refinement.

`FilteredRuntime.agda` instantiates the theorem with finite executable checker
constraints and hard-accepted runtime candidates. It proves both directions
between dependent satisfaction evidence and `rawConstraintsHold = true`, and
obtains paths from existing checked hard cells.

The internal `PositiveGFTree` is indexed by GF categories and supports
predication, complementation, PP modification, adjective modification, and
determiners. `gfElaborationExact` identifies elaboration with the structural
constraint fold, while `gfElaborationCertified` proves every emitted
constraint belongs to the supplied rule snapshot. The external GF parser is
still an untrusted producer of this checked AST.

`TwoTruncatedContext.agda` provides the higher compression:

```text
RawCoarse₂ Γ = Fiber Γ /ₜ Compatible Γ
Coarse₂ Γ    = ∥ RawCoarse₂ Γ ∥₄
```

The non-truncated quotient retains generated compatibility paths before the
standard Cubical 2-groupoid truncation removes structure strictly above
dimension two. Refinement acts on both levels and
`compression₂Naturality` proves naturality. `Compatibility₂System` and
`CoherentCompatibility₂` make equalities between parallel compatibility paths
explicit; `coherenceAboveDimension₂` supplies uniqueness above the retained
level.

Identity and composition are derived on quotient generators.
`Coarse₂Pseudofunctor` records the additional global coherence obligations for
an arbitrary compatibility system. `TwoTruncatedRuntime.agda` instantiates the
construction for runtime candidate identity. Richer semantic compatibility
must provide domain-specific 2-cell witnesses.

## Scope of the result

The theorems are relative to:

- the imported finite ontology;
- the declared predicate requirements and preferences;
- the supplied hard licenses, target compatibility basis, and semantic
  model;
- the checked GF-function/entity lexicon facts.

They do not prove that Wikidata is factually complete, that a VerbNet
preference is universally valid, or that pragmatic ranking selects the
speaker's intended interpretation. Those are empirical assumptions, not
hidden logical axioms.
